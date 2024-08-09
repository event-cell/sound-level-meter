import serial


def read_stream_from_usb_serial_with_delimiter():
    ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)
    try:
        message_buffer = bytearray()
        while True:
            byte = ser.read(1)
            if byte:
                # Check if the byte is the delimiter (165 -> '¥')
                if byte == b"\xa5":  # '\xa5' is the hex representation of 165
                    # Process the message
                    if message_buffer:
                        for b in message_buffer:
                            print(f"{b:02x}", end=" ")
                        print()  # Print a newline after the entire message
                    else:
                        print("Message buffer is empty.")

                    # Reset the buffer for the next message
                    message_buffer = bytearray()
                else:
                    # Accumulate the byte in the buffer
                    message_buffer += byte
    except KeyboardInterrupt:
        print("Stream reading interrupted by user.")
    finally:
        ser.close()


if __name__ == "__main__":
    read_stream_from_usb_serial_with_delimiter()
