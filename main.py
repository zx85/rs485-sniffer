import machine
import time
import ubinascii
import network
import socket

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


# Network Configuration
def load_config(filename):
    config = {}
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        config[parts[0].strip()] = parts[1].strip()
    except OSError:
        print(f"Warning: Could not load {filename}")
    return config


params = load_config(".env")
WIFI_SSID = params.get("WIFI_SSID", "")
WIFI_PASS = params.get("WIFI_PASS", "")
SERVER_PORT = int(params.get("SERVER_PORT", 8080))


def ensure_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Connecting to WiFi: {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASS)

        # Wait for connection with a timeout
        max_wait = 10
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print("waiting for connection...")
            time.sleep(1)

    if wlan.status() != 3:
        print("Network connection failed")
    else:
        print(f"Connected. IP: {wlan.ifconfig()[0]}")


def main():
    # Initialize UART
    # We only configure RX. We explicitly re-assert DI as Low after init just in case.
    uart = machine.UART(UART_ID, baudrate=BAUD_RATE, rx=PIN_RO)
    PIN_DI.init(machine.Pin.OUT, value=0)

    ensure_wifi()
    # Setup TCP Server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", SERVER_PORT))
    s.listen(1)
    s.setblocking(False)  # Non-blocking to allow sniffing to continue without a client

    client_socket = None

    print(f"RS485 Sniffer started on UART{UART_ID} at {BAUD_RATE} baud.")
    print(f"Listening for TCP connections on port {SERVER_PORT}...")

    while True:
        # Handle Network Connections
        try:
            # Accept new connection if we don't have one or just to handle re-connects
            # For simplicity, we accept one client at a time in this loop
            if not client_socket:
                res = s.accept()
                if res:
                    client_socket, addr = res
                    client_socket.setblocking(False)
                    print(f"Client connected from {addr}")
        except OSError:
            # No new connection
            pass

        # Check if there is data in the buffer
        if uart.any():
            # Read all available bytes
            data = uart.read()

            if data:
                # Get current timestamp (milliseconds since boot)
                timestamp = time.ticks_ms()

                # Convert binary data to hex string separated by spaces
                hex_str = ubinascii.hexlify(data, " ").decode("utf-8")
                output_line = f"[{timestamp} ms] {hex_str}"

                # Print to local console
                print(output_line)

                # Send to network client if connected
                if client_socket:
                    try:
                        client_socket.send((output_line + "\n").encode("utf-8"))
                    except OSError:
                        print("Client disconnected")
                        client_socket.close()
                        client_socket = None


if __name__ == "__main__":
    main()
