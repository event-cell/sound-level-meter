import curses
from time import sleep
import serial


def clear_chars(win, y, x, num_chars):
    win.move(y, x)
    win.addstr(" " * num_chars)


def main(stdscr):
    # Hide the cursor
    curses.curs_set(0)
    # Clear screen
    stdscr.clear()

    # Create an 80x25 window starting at the top-left corner of the screen
    win = curses.newwin(25, 80, 0, 0)
    win.scrollok(False)  # Disable scrolling

    ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)

    # Build Screen to display the following bytes
    # 13, 12, 27, 6, 75, 14, 8, 11, 25, 2, 31, 26
    # 13: Range, dB
    # 12: Unknown
    # 27: Unknown
    # 6: Unknown
    # 75: Unknown
    # 14: Unknown
    # 8: Unknown
    # 11: Unknown
    # 25: Unknown
    # 2: Speed (FAST/SLOW)
    # 31: Unknown
    # 26: Unknown

    try:
        message_buffer = bytearray()
        while True:
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
                                win.addstr(1, 1, "dB: ")
                                clear_chars(win, 1, 10, 10)
                                clear_chars(win, 1, 40, 10)
                                db = msg[1] * 10 + msg[2] / 10
                                win.addstr(1, 10, f"{db} dB")
                                win.addstr(1, 40, msg.hex())
                            elif key == 0x0C:
                                win.addstr(3, 1, "Unknown: ")
                                clear_chars(win, 3, 10, 10)
                                win.addstr(3, 10, msg.hex())
                            elif key == 0x1B:
                                win.addstr(5, 1, "Unknown: ")
                                clear_chars(win, 5, 10, 10)
                                win.addstr(5, 10, msg.hex())
                            elif key == 0x06:
                                win.addstr(7, 1, "Unknown: ")
                                clear_chars(win, 7, 10, 10)
                                win.addstr(7, 10, msg.hex())
                            elif key == 0x4B:
                                win.addstr(9, 1, "Unknown: ")
                                clear_chars(win, 9, 10, 10)
                                win.addstr(9, 10, msg.hex())
                            elif key == 0x0E:
                                win.addstr(11, 1, "Unknown: ")
                                clear_chars(win, 11, 10, 10)
                                win.addstr(11, 10, msg.hex())
                            elif key == 0x08:
                                win.addstr(13, 1, "Unknown: ")
                                clear_chars(win, 13, 10, 10)
                                win.addstr(13, 10, msg.hex())
                            elif key == 0x0B:
                                win.addstr(15, 1, "Unknown: ")
                                clear_chars(win, 15, 10, 10)
                                win.addstr(15, 10, msg.hex())
                            elif key == 0x19:
                                win.addstr(17, 1, "Unknown: ")
                                clear_chars(win, 17, 10, 10)
                                win.addstr(17, 10, msg.hex())
                            elif key == 0x02:
                                win.addstr(19, 1, "Speed: ")
                                clear_chars(win, 19, 10, 10)
                                win.addstr(19, 10, "FAST")
                            elif key == 0x03:
                                win.addstr(19, 1, "Speed: ")
                                clear_chars(win, 19, 10, 10)
                                win.addstr(19, 10, "SLOW")
                            elif key == 0x1F:
                                win.addstr(21, 1, "Unknown: ")
                                clear_chars(win, 21, 10, 10)
                                win.addstr(21, 10, msg.hex())
                            elif key == 0x1A:
                                win.addstr(23, 1, "Unknown: ")
                                clear_chars(win, 23, 10, 10)
                                win.addstr(23, 10, msg.hex())
                            elif key == 0x11:
                                win.addstr(23, 20, "Unknown: ")
                                clear_chars(win, 23, 30, 10)
                                win.addstr(23, 30, msg.hex())
                            else:
                                # Handle unknown byte
                                win.move(24, 10)
                                win.clrtoeol()
                                win.addstr(
                                    24,
                                    10,
                                    f"Unknown message: {msg.hex()}",
                                )
                    else:
                        win.addstr(24, 10, "Message buffer is empty.")
                    # Update the screen
                    win.refresh()
                    message_buffer = (
                        bytearray()
                    )  # Reset the message buffer for the next message
                else:
                    # Accumulate the byte in the buffer
                    message_buffer += byte
    except KeyboardInterrupt:
        print("Stream reading interrupted by user.")
    finally:
        ser.close()


# Wrap the main function to initialize curses and ensure proper cleanup
curses.wrapper(main)
