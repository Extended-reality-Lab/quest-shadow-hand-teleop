"""Fake headset: sends a synthetic moving hand pair in format v1.

Lets the receiver be tested and demonstrated without a Quest.
- Both hands move in a slow circle while the fingers curl and open.
- Every 5 s the right hand reports tracked=false for 2 s (tracking loss).
- Every 11 s the left hand sends nothing for 1.5 s (connection loss / timeout).

Usage:
    python pc_receiver/fake_sender.py --host 127.0.0.1 --port 9000 [--rate 60] [--seconds 0]
"""
import argparse
import math
import socket
import time

import protocol

# Finger layout of a right hand, palm down, fingers pointing forward (-Z).
# x offset of each finger base from the wrist (m), and bone lengths from the
# metacarpal joint to the tip (m). The thumb has one bone fewer.
FINGERS = [
    ("thumb", -0.030, [0.035, 0.032, 0.025]),
    ("index", -0.020, [0.065, 0.040, 0.024, 0.020]),
    ("middle", 0.000, [0.063, 0.044, 0.028, 0.022]),
    ("ring", 0.018, [0.060, 0.041, 0.026, 0.021]),
    ("little", 0.034, [0.055, 0.033, 0.019, 0.019]),
]


def bend_quat(angle):
    """Quaternion [qx, qy, qz, qw] for a rotation of `angle` rad about +X."""
    return [math.sin(angle / 2), 0.0, 0.0, math.cos(angle / 2)]


def synthetic_hand(hand, t):
    """Return 26 joints [px, py, pz, qx, qy, qz, qw] for time t in seconds."""
    side = 1.0 if hand == "right" else -1.0  # the left hand is the mirror image
    # Wrist moves on a 5 cm circle in front of the user, 1.2 m above the floor.
    angle = 2 * math.pi * t / 6.0
    wx = side * 0.20 + 0.05 * math.cos(angle)
    wy = 1.20 + 0.05 * math.sin(angle)
    wz = -0.35
    curl = 0.5 - 0.5 * math.cos(2 * math.pi * t / 3.0)  # 0 = open, 1 = fist

    identity = [0.0, 0.0, 0.0, 1.0]
    joints = [
        [wx, wy, wz - 0.045] + identity,  # palm: middle of the hand
        [wx, wy, wz] + identity,  # wrist
    ]
    for _name, x_offset, bones in FINGERS:
        # Metacarpal joint sits near the wrist; each next joint follows one bone.
        x, y, z = wx + side * x_offset * 0.5, wy, wz - 0.01
        bend = 0.0
        joints.append([x, y, z] + bend_quat(-bend))
        for i, length in enumerate(bones):
            if i > 0:
                bend += curl * 0.6  # each knuckle bends a bit more, downwards
            # Direction of a bone pointing along -Z, rotated down by `bend`.
            y -= length * math.sin(bend)
            z -= length * math.cos(bend)
            x += side * x_offset * 0.25 / len(bones)  # fingers fan out slightly
            joints.append([x, y, z] + bend_quat(-bend))
    return joints


def main():
    parser = argparse.ArgumentParser(description="Send a synthetic hand stream (v1).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--rate", type=float, default=60.0, help="frames per second")
    parser.add_argument("--seconds", type=float, default=0.0, help="run time; 0 = until Ctrl+C")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # allows 255.255.255.255
    print(f"Sending fake hands to {args.host}:{args.port} at {args.rate:g} Hz. Ctrl+C to stop.")

    seq = 0
    start = time.monotonic()
    frame = 0
    try:
        while True:
            t = time.monotonic() - start
            if args.seconds and t >= args.seconds:
                break
            for hand in ("left", "right"):
                if hand == "left" and t % 11.0 >= 9.5:
                    continue  # left hand silent: the receiver must time out
                tracked = not (hand == "right" and t % 5.0 >= 3.0)
                msg = protocol.make_message(
                    seq=seq,
                    t_us=int(t * 1_000_000),
                    hand=hand,
                    tracked=tracked,
                    source="optical" if tracked else "unknown",
                    joints=synthetic_hand(hand, t),
                )
                sock.sendto(protocol.encode(msg), (args.host, args.port))
                seq += 1
            frame += 1
            # Sleep until the next frame is due, without drifting.
            delay = start + frame / args.rate - time.monotonic()
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
    print(f"Sent {seq} datagrams.")


if __name__ == "__main__":
    main()
