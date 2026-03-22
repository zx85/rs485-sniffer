import machine
import time
import ubinascii

# Configuration
UART_ID = 0
BAUD_RATE = 9600  # Ensure this matches the target RS485 bus speed

# Pin Definitions
PIN_DI = machine.Pin(0, machine.Pin.OUT, value=0)  # Connect to MAX485 DI (Driver Input)
PIN_RO = machine.Pin(
    1
)  # Connect to MAX485 RO. WARNING: 5V output! Use 2k/3k divider to Pico.
PIN_DE = machine.Pin(
    2, machine.Pin.OUT, value=0
)  # Connect to MAX485 DE (Driver Enable)
PIN_RE = machine.Pin(
    3, machine.Pin.OUT, value=0
)  # Connect to MAX485 RE (Receiver Enable)


def main():
    # Initialize UART
    # We only configure RX. We explicitly re-assert DI as Low after init just in case.
    uart = machine.UART(UART_ID, baudrate=BAUD_RATE, rx=PIN_RO)
    PIN_DI.init(machine.Pin.OUT, value=0)

    print(f"RS485 Sniffer started on UART{UART_ID} at {BAUD_RATE} baud.")
    print("Listening...")

    while True:
        # Check if there is data in the buffer
        if uart.any():
            # Read all available bytes
            data = uart.read()

            if data:
                # Get current timestamp (milliseconds since boot)
                timestamp = time.ticks_ms()

                # Convert binary data to hex string separated by spaces
                hex_str = ubinascii.hexlify(data, " ").decode("utf-8")

                print(f"[{timestamp} ms] {hex_str}")


if __name__ == "__main__":
    main()
