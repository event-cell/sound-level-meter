import configparser
import logging
import time
import traceback
import statistics
from datetime import datetime, timezone

import pytz
import serial
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pushover import Client, Message

# Configure logging level and output format
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Create a logger
logger = logging.getLogger(__name__)

# --------------------- Configuration  ---------------------

# Read configuration file
config = configparser.ConfigParser()
config.read("slm-log.ini")

# Set variables from configuration file
# InfluxDB server configuration
influxdb_host = config.get("InfluxDB", "host")
influxdb_port = int(config.getint("InfluxDB", "port"))
influxdb_token = config.get("InfluxDB", "token")
influxdb_org = config.get("InfluxDB", "org")
influxdb_bucket = config.get("InfluxDB", "bucket")
influxdb_measurement = config.get("InfluxDB", "measurement")
influxdb_measurement_compliance = f"{influxdb_measurement}-compliance"
influxdb_location = config.get("InfluxDB", "location")
influxdb_timeout = int(config.getint("InfluxDB", "timeout"))

# Pushover server configuration
pushover_group_key = config.get("Pushover", "group_key")
pushover_app_api_token = config.get("Pushover", "app_api_token")
pushover_msg_title = config.get("Pushover", "msg_title")

# Minimum noise level for logging events (in dB)
maximum_noise_level = int(config.get("Monitoring", "maximum_noise_level"))

# device path for serial communication
serial_device = config.get("Hardware", "serial_device")

# sample interval in milliseconds
sample_interval = int(config.get("Monitoring", "sample_interval"))
compliance_sample_interval = int(config.get("Monitoring", "compliance_sample_interval"))

# CSV logging timezone
log_tz = pytz.timezone(config.get("Monitoring", "timezone"))

# --------------------- End of Configuration  ---------------------

logger.info("Configuration loaded")
logger.info("InfluxDB Host: %s", influxdb_host)

# --------------------- Initialise Connections  ---------------------
# InfluxDB connection
influxdb_client = InfluxDBClient(
    url=f"http://{influxdb_host}:{influxdb_port}",
    token=influxdb_token,
    org=influxdb_org,
    timeout=influxdb_timeout,
)
write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

# --------------------- End Initialise Connections  ---------------------

# Counter for failed InfluxDB pings
failed_influxdb_pings = 0

# Last recorded dB and timestamp
last_dB = None
last_timestamp = None

# List to store the last 4 samples
last_4_samples = []


# Get the high and low nibbles of a byte
def get_high_nibble(byte):
    return (byte & 0xF0) >> 4


def get_low_nibble(byte):
    return byte & 0x0F

def write_pushover_message(message):
    with open("pushover_messages.txt", "a") as file:
        file.write(message + "\n")

# Write data to InfluxDB
def write_data_to_influxdb(dB, timestamp, measurement_point):
    point = (
        Point(measurement_point)
        .tag("location", influxdb_location)
        .field("dB", dB)
        .time(timestamp, WritePrecision.NS)
    )
    try:
        write_api.write(bucket=influxdb_bucket, org=influxdb_org, record=point)
    except Exception as e:
        logger.error(f"Error writing to InfluxDB")

# Function to update noise level and log it
def update():
    # Declare global variables
    global last_4_samples

    # Initialize variables
    # Data processing variables
    dB = None
    key = None
    tracking_peak = False

    # Serial communication variables
    ser = serial.Serial(serial_device, 9600, timeout=1)
    message_buffer = bytearray()
    key = 0x00

    # time tracking variables
    now = datetime.now(pytz.utc)
    start_of_script = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    milliseconds_since_start_of_script = int(
        (now - start_of_script).total_seconds() * 1000
    )
    next_sample_time = milliseconds_since_start_of_script + sample_interval
    next_compliance_sample_time = (
        milliseconds_since_start_of_script + compliance_sample_interval
    )

    while True:
        current_date = now.astimezone(log_tz).strftime("%Y-%m-%d")
        # Scan incoming packets for a dB value
        message_buffer = bytearray()  # Reset the message buffer for the next message
        while True:
            # receive bytes from serial until a db value is received
            try:
                byte = ser.read(1)
            except serial.SerialException:
                logger.error("Serial communication error")
                # loop until serial communication is restored
                while True:
                    try:
                        ser.close()
                        ser = serial.Serial(serial_device, 9600, timeout=1)
                        byte = ser.read(1)
                        if byte:
                            logger.info("Serial communication restored")
                        # reset message buffer
                        message_buffer = bytearray()
                        break
                    except serial.SerialException:
                        logger.error("Serial communication error")
                        time.sleep(5)
                break
            if byte:
                # Check if the byte is the delimiter (165 -> '¥')
                if byte.hex() == "a5":  # '\xa5' is the hex representation of 165
                    if message_buffer:
                        # Read the first byte of the message to determine the cursor position
                        msg = message_buffer
                        key = msg[0]
                        if key:
                            if key == 0x0D:
                                # Record time of collection
                                now = datetime.now(pytz.utc)
                                # logging.info("Message: %s", message_buffer.hex())
                                # Check if msg[1] and msg[2] exist
                                if len(msg) > 2:
                                    # DB Noise Level
                                    hundreds = get_high_nibble(msg[1])
                                    tens = get_low_nibble(msg[1])
                                    ones = get_high_nibble(msg[2])
                                    tenths = get_low_nibble(msg[2])
                                    dB = hundreds * 100 + tens * 10 + ones + tenths / 10
                                    # Calculate next sample time
                                    timestamp = now.astimezone(log_tz).strftime(
                                        "%Y-%m-%dT%H:%M:%S.%fZ"
                                    )[:-4]
                                    # Fractional seconds since epoc in UTC
                                    database_timestamp = now.isoformat()
                                    milliseconds_since_start_of_script = int(
                                        (now - start_of_script).total_seconds() * 1000
                                    )
                                else:
                                    logger.warning(
                                        "Message buffer too short to extract dB values"
                                    )
                    break
                else:
                    # Accumulate the byte in the buffer
                    message_buffer += byte
        while True:
            if (key == 0x0D) and (
                milliseconds_since_start_of_script >= next_sample_time
            ):
                next_sample_time = milliseconds_since_start_of_script + sample_interval
                logger.info("%s, %.1f dB", timestamp, round(dB, 1))
                write_data_to_influxdb(dB, database_timestamp, influxdb_measurement)
                # if dB > maximum_noise_level or tracking_peak:
                #     if not tracking_peak:
                #         # Start tracking the peak
                #         tracking_peak = True
                #         sample_count = 0
                #         max_dB = dB
                #     else:
                #         # Update the maximum dB value
                #         if dB > max_dB:
                #             max_dB = dB
                #
                #     sample_count += 1
                #
                #     if sample_count >= 20:
                #         # Log the maximum dB value found in the 20 samples
                #         send_pushover_message(
                #             f"VIOLATION: Peak Noise Level of {max_dB} dB"
                #         )
                #         logger.info("VIOLATION: Peak Noise Level of %.1f dB", max_dB)
                #         tracking_peak = False  # Stop tracking after logging the peak
                #         max_dB = None  # Reset the peak value
                #         sample_count = 0  # Reset the sample count

                # Update the list of last 4 samples
                last_4_samples.append(dB)
                if len(last_4_samples) > 4:
                    last_4_samples.pop(0)

                # Calculate the median value in the last 4 samples
                if len(last_4_samples) == 4:
                    median_dB_last_4 = statistics.median(last_4_samples)
                    logger.info("Median dB in last 4 samples: %.1f dB", median_dB_last_4)

                    if median_dB_last_4 > maximum_noise_level:
                        write_pushover_message(
                            f"VIOLATION: Median Noise Level of {median_dB_last_4} dB"
                        )
                        logger.info("VIOLATION: Median Noise Level of %.1f dB", median_dB_last_4)

                # Log data to CSV
                # Full resolution
                with open(f"logs/{current_date}-noise.csv", "a") as f:
                    f.write(f"{timestamp},{round(dB, 1)}\n")

                # Compliance resolution
                if milliseconds_since_start_of_script >= next_compliance_sample_time:
                    next_compliance_sample_time = (
                        milliseconds_since_start_of_script + compliance_sample_interval
                    )
                    with open(f"logs/{current_date}-noise-compliance.csv", "a") as f:
                        f.write(f"{timestamp},{round(dB, 1)}\n")
                    # write a copy to influxdb for display in Grafana
                    write_data_to_influxdb(
                        dB, database_timestamp, influxdb_measurement_compliance
                    )
                break
            else:
                # Discard the current sample and select the next sample
                break


def main():
    try:
        logger.info("Starting Sound Level Meter")
        write_pushover_message("SDMA Sound Level Meter starting")

        heath_check = influxdb_client.health().status
        logger.info("InfluxDB health check returned %s", heath_check)
        if heath_check == "pass":
            logger.info("Connected to InfluxDB successfully.")
        elif heath_check == "fail":
            logger.error("Exception while connecting to InfluxDB")
            write_pushover_message("Sound Level Meter failed to connect to InfluxDB")

        # Start updating noise level
        update()

    except Exception as e:
        with open("error.log", "a") as f:
            f.write(str(e) + "\n")
            f.write(traceback.format_exc())
            logger.error(str(e))
            logger.error(traceback.format_exc())


# Execute the main function
#
if __name__ == "__main__":
    main()
