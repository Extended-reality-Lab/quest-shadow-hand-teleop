"""Receive the hand stream through a relay server when the PC cannot accept
inbound UDP (campus network, firewall without admin rights).

The PC only sends outbound: it registers with the relay every second, and the
relay sends the headset's datagrams back on the same path. Each datagram is
passed to 127.0.0.1:<local-port>, where teleop/run.py or receiver.py listens.

    .\\.venv\\Scripts\\python.exe pc_receiver\\relay_client.py --relay <relay IP>

Point the headset app at the same relay IP and port. Standard library only.
"""

import argparse
import socket
import time

REGISTER = b"REGISTER"


def main():
    parser = argparse.ArgumentParser(description="Hand stream through a relay server.")
    parser.add_argument("--relay", required=True, help="relay server IP")
    parser.add_argument("--relay-port", type=int, default=9000)
    parser.add_argument("--local-port", type=int, default=9000, help="where teleop/run.py listens")
    args = parser.parse_args()

    relay = (args.relay, args.relay_port)
    local = ("127.0.0.1", args.local_port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.2)
    out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    registered = False
    forwarded = 0
    last_register = 0.0
    last_print = 0.0
    print(f"Relay {relay[0]}:{relay[1]} -> 127.0.0.1:{args.local_port}. Ctrl+C to stop.")
    try:
        while True:
            now = time.monotonic()
            if now - last_register >= 1.0:
                sock.sendto(REGISTER, relay)
                last_register = now
            try:
                data, addr = sock.recvfrom(8192)
            except (TimeoutError, ConnectionResetError):
                data, addr = b"", None
            if addr is not None and addr[0] == relay[0]:
                if data == b"OK":
                    if not registered:
                        print("registered with the relay")
                    registered = True
                elif data:
                    out.sendto(data, local)
                    forwarded += 1
            if now - last_print >= 2.0:
                last_print = now
                state = "registered" if registered else "waiting for the relay"
                print(f"\r{state}, forwarded {forwarded}   ", end="", flush=True)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
