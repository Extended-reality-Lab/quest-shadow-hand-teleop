"""Minimal PC receiver for the Quest hand stream (format v1).

Listens for UDP datagrams, prints the state of each hand a few times per
second, counts malformed datagrams and lost packets, and can log every valid
datagram to a JSON Lines file.

Usage:
    python pc_receiver/receiver.py --port 9000 [--bind 0.0.0.0] [--log hands.jsonl] [--timeout 0.5]
"""
import argparse
import json
import socket
import time
from collections import deque

import protocol

PRINT_INTERVAL = 0.2  # seconds between status lines, i.e. at most 5 per second

TRACKED = "TRACKED"
LOST_TRACKING = "LOST (tracking)"
LOST_NO_PACKETS = "LOST (no packets)"


class HandState:
    """Latest known state of one hand.

    `clock` returns seconds; tests pass a fake clock instead of sleeping.
    """

    def __init__(self, timeout, clock=time.monotonic):
        self.timeout = timeout
        self.clock = clock
        self.last_msg = None
        self.last_rx = None
        self.rx_times = deque()  # receive times within the last second, for the rate

    def update(self, msg):
        now = self.clock()
        self.last_msg = msg
        self.last_rx = now
        self.rx_times.append(now)

    def status(self):
        if self.last_msg is None or self.clock() - self.last_rx > self.timeout:
            return LOST_NO_PACKETS
        if not self.last_msg["tracked"]:
            return LOST_TRACKING
        return TRACKED

    def rate_hz(self):
        """Datagrams received for this hand during the last second."""
        now = self.clock()
        while self.rx_times and now - self.rx_times[0] > 1.0:
            self.rx_times.popleft()
        return len(self.rx_times)


class SeqCounter:
    """Counts datagrams missing from the shared `seq` sequence."""

    def __init__(self):
        self.last_seq = None
        self.lost = 0

    RESTART_JUMP = 1000  # a seq this far below the last one means the app restarted

    def update(self, seq):
        if self.last_seq is None or seq + self.RESTART_JUMP < self.last_seq:
            self.last_seq = seq  # first packet, or the app restarted: resync
        elif seq > self.last_seq:
            self.lost += seq - self.last_seq - 1
            self.last_seq = seq
        # Otherwise a late (reordered) packet: it was already counted as lost.


def lan_ip():
    """Best guess of this PC's LAN address. Connecting a UDP socket sends nothing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def fmt_pos(joint):
    return f"({joint[0]:6.3f} {joint[1]:6.3f} {joint[2]:6.3f})"


def describe(letter, hand):
    status = hand.status()
    text = f"{letter} {status:<17}"
    if status == TRACKED:
        joints = hand.last_msg["joints"]
        text += f" wrist {fmt_pos(joints[protocol.WRIST])} m  index_tip {fmt_pos(joints[protocol.INDEX_TIP])}"
    if status != LOST_NO_PACKETS:
        text += f" {hand.rate_hz():3d} Hz"
    return text


def main():
    parser = argparse.ArgumentParser(description="Receive Quest hand skeleton datagrams (v1).")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--bind", default="0.0.0.0", help="local address to listen on")
    parser.add_argument("--log", help="append every valid datagram to this JSON Lines file")
    parser.add_argument("--timeout", type=float, default=0.5,
                        help="seconds without packets before a hand counts as LOST (no packets)")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.bind, args.port))  # fails loudly if another receiver holds the port
    sock.settimeout(0.05)  # wake up regularly so timeouts show even with no traffic

    print(f"Listening on {args.bind}:{args.port}")
    print(f"Point the headset at {lan_ip()}:{args.port} (or leave the app on broadcast)")

    hands = {"left": HandState(args.timeout), "right": HandState(args.timeout)}
    seq = SeqCounter()
    malformed = 0
    log_file = open(args.log, "a", encoding="utf-8") if args.log else None
    next_print = time.monotonic()

    try:
        while True:
            try:
                data, _addr = sock.recvfrom(65535)
            except OSError:
                # The 50 ms poll timeout (socket.timeout is an OSError on every
                # Python 3 version) or, on Windows, a ConnectionResetError for an
                # ICMP "port unreachable". Neither is a reason to stop.
                data = None

            if data is not None:
                try:
                    msg = protocol.parse(data)
                except protocol.ProtocolError:
                    malformed += 1
                else:
                    hands[msg["hand"]].update(msg)
                    seq.update(msg["seq"])
                    if log_file:
                        msg["rx_time"] = round(time.time(), 6)
                        log_file.write(json.dumps(msg, separators=(",", ":")) + "\n")

            now = time.monotonic()
            if now >= next_print:
                next_print = now + PRINT_INTERVAL
                print(f"{describe('L', hands['left'])} | {describe('R', hands['right'])}"
                      f" | malformed {malformed}  lost {seq.lost}", flush=True)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        sock.close()
        if log_file:
            log_file.close()


if __name__ == "__main__":
    main()
