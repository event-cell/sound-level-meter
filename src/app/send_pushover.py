import logging
import configparser
from pushover import Client, Message
import time

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

# Pushover server configuration
pushover_group_key = config.get("Pushover", "group_key")
pushover_app_api_token = config.get("Pushover", "app_api_token")
pushover_msg_title = config.get("Pushover", "msg_title")

# --------------------- End of Configuration  ---------------------

# --------------------- Initialise Connections  ---------------------
# Pushover connection
if pushover_group_key and pushover_app_api_token:
    po_api = Client(pushover_group_key, pushover_app_api_token)
# --------------------- End Initialise Connections  ---------------------


def read_messages(file_path):
    messages = []
    try:
        with open(file_path, "r") as file:
            messages = file.readlines()
        # Clear the file after reading
        open(file_path, "w").close()
    except Exception as e:
        print(f"Error reading messages: {e}")
    return messages


def send_pushover_message(message, title=None):
    if po_api:
        if title:
            pushover_title = title
        else:
            pushover_title = pushover_msg_title
        po_send = po_api.send(Message(message, title=pushover_title))
        logger.info(f"Pushover message sent: {message}")
        logger.info(f"Pushover Send returned {po_send}")


def main():
    file_path = "pushover_messages.txt"  # Path to the local file for violation messages

    # Create the file if it does not exist
    open(file_path, "a").close()

    while True:
        messages = read_messages(file_path)

        for message in messages:
            send_pushover_message(message.strip())

        time.sleep(5)  # Wait for 5 seconds before checking for new messages


if __name__ == "__main__":
    main()
