# Forked from https://raw.githubusercontent.com/silkyclouds/NoiseBuster/
# Original author: silkyclouds
# License: GPL-3

import logging
import serial
import time
import traceback
from datetime import datetime
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
# from pushover import Pushover

# Configure logging level and output format
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Create a logger
logger = logging.getLogger(__name__)

# --------------------- Configuration Section ---------------------

# InfluxDB host address (IP or URL)
influxdb_host = "localhost"
# InfluxDB port (usually 8086)
influxdb_port = 8086
# InfluxDB authentication token
influxdb_token = ""
# InfluxDB organization name
influxdb_org = "SDMA"
# InfluxDB bucket name
influxdb_bucket = "SLM"
# InfluxDB timeout in milliseconds
influxdb_timeout = 20000

# Pushover user key for notifications (leave empty to disable Pushover notifications)
pushover_user_key = ""
# Pushover API token (leave empty to disable Pushover notifications)
pushover_api_token = ""

# Minimum noise level for logging events (in dB)
minimum_noise_level = 30

# Message content for Pushover notifications
pushover_message = "Lets bust these noise events"
# Title for Pushover notifications
pushover_title = "Noise Buster"

# Message to display when starting the script
start_message = "Noise Level Logging"

# InfluxDB measurement name (where data will be written in the DB)
influxdb_measurement = "noise_events"
# Location tag for InfluxDB measurement
influxdb_location = "noise"

# dB adjustment for distance (in dB)
dB_adjustment = 0

# device path for serial communication
serial_device = "/dev/ttyUSB0"

# --------------------- End of Configuration Section ---------------------

# Counter for failed InfluxDB pings
failed_influxdb_pings = 0

# Last recorded dB and timestamp
last_dB = None
last_timestamp = None


# Functions to get the high and low nibbles of a byte
def get_high_nibble(byte):
    return (byte & 0xF0) >> 4


def get_low_nibble(byte):
    return byte & 0x0F


# Function to check the health of the InfluxDB server
def check_influxdb_health():
    global failed_influxdb_pings
    try:
        if influxdb_client.health():
            failed_influxdb_pings = 0
        else:
            failed_influxdb_pings += 1
    except Exception as e:
        failed_influxdb_pings += 1

    if failed_influxdb_pings >= 10:
        message = "InfluxDB server is down. Failed to respond to 10 consecutive pings."
        # if pushover_user_key and pushover_api_token:
        #     client.send_message(message, title=pushover_title)
        logger.info(message)
        failed_influxdb_pings = 0

    time.sleep(5)


# Function to update noise level and log it
def update():
    global dB, last_dB, last_timestamp
    ser = serial.Serial(serial_device, 9600, timeout=1)
    message_buffer = bytearray()
    while True:
        while True:
            # receive bytes from serial until a db value is received
            byte = ser.read(1)
            if byte:
                # Check if the byte is the delimiter (165 -> '¥')
                if byte == b"\xa5":  # '\xa5' is the hex representation of 165
                    if message_buffer:
                        # Read the first byte of the message to determine the cursor position
                        msg = message_buffer
                        key = msg[0]
                        if key:
                            if key == 0x0D:
                                # DB Noise Level
                                hundreds = get_high_nibble(msg[1])
                                tens = get_low_nibble(msg[1])
                                ones = get_high_nibble(msg[2])
                                tenths = get_low_nibble(msg[2])
                                dB = hundreds * 100 + tens * 10 + ones + tenths / 10
                                # logging.info({msg.hex()})
                                # logging.info("Noise Level: %.1f dB", dB)
                    message_buffer = (
                        bytearray()
                    )  # Reset the message buffer for the next message
                    break
                else:
                    # Accumulate the byte in the buffer
                    message_buffer += byte

        dB += dB_adjustment  # Apply dB adjustment based on distance
        timestamp = timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        if dB >= minimum_noise_level and (dB != last_dB or timestamp != last_timestamp):
            last_dB = dB
            last_timestamp = timestamp
            logger.info("%s, %.1f dB", timestamp, round(dB, 1))

            # data = [
            #     {
            #         "measurement": influxdb_measurement,
            #         "tags": {"location": influxdb_location},
            #         "time": timestamp,
            #         "fields": {"level": round(dB, 1)},
            #     }
            # ]
            # write_api.write(influxdb_bucket, record=data)

            # Log data to CSV
            with open("noise.csv", "a") as f:
                f.write(f"{timestamp},{round(dB, 1)}\n")

        # time.sleep(0.25)


# Main function Start
#
#

global dB

try:
    # if pushover_user_key and pushover_api_token:
    #     client = Client(pushover_user_key, api_token=pushover_api_token)
    #     client.send_message(pushover_message, title=pushover_title)

    dB = 0

    logger.info(start_message)

    influxdb_client = InfluxDBClient(
        url=f"http://{influxdb_host}:{influxdb_port}",
        token=influxdb_token,
        org=influxdb_org,
        timeout=influxdb_timeout,
    )
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

    if influxdb_client.health():
        logger.info("Connected to InfluxDB successfully.")
        # if pushover_user_key and pushover_api_token:
        #     client.send_message(
        #         "Successfully connected to InfluxDB", title=pushover_title
        #     )
    else:
        logger.info("Error connecting to InfluxDB.")
        # if pushover_user_key and pushover_api_token:
        #     client.send_message("Error connecting to InfluxDB", title=pushover_title)

    # Start the InfluxDB server health check in a separate thread
    from threading import Thread

    Thread(target=check_influxdb_health).start()

    # Start updating noise level
    update()
except Exception as e:
    with open("error.log", "a") as f:
        f.write(str(e) + "\n")
        f.write(traceback.format_exc())
        logger.error(str(e))
        logger.error(traceback.format_exc())
