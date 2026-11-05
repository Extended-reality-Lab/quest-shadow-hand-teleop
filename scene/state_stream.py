"""Simulation state stream, MuJoCo -> Unity (issue #27, first version).

One UDP datagram of compact JSON per message, in Unity's frame (see
frames.py), at most 60 per second. The format is section 3 of
docs/integration/DATA.md; this version sends the part Unity needs to move the
scene:

    v, seq, sim_time, send_time,
    bodies[]  {id, p, q}         every hand body and the mocap target
    objects[] {id, p, q, grasp}  ball, cube, can; grasp is "free" until #26

p is a position in metres, q a quaternion (x, y, z, w), both in Unity's world
frame. Unity applies them as they are.
"""
import json
import re
import socket
import time

import numpy as np
from frames import to_unity_quat, to_unity_vec

VERSION = 1
OBJECTS = ("ball", "cube", "can")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9001
MAX_RATE = 60.0  # messages per second
DECIMALS = 5  # 0.01 mm
# Plain decimals only (no 1e-05), so any JSON reader takes the numbers.
_EXPONENT = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?e-\d+")


def _flat(values):
    return [float(v) for v in np.round(values, DECIMALS)]


def build_state(model, data, seq, send_time=None):
    """The state message for the current simulation data (after mj_step or mj_forward)."""
    bodies, objects = [], []
    for body in range(1, model.nbody):  # body 0 is the world
        name = model.body(body).name
        pose = {
            "id": name,
            "p": _flat(to_unity_vec(data.xpos[body])),
            "q": _flat(to_unity_quat(data.xquat[body])),
        }
        if name in OBJECTS:
            pose["grasp"] = "free"
            objects.append(pose)
        else:
            bodies.append(pose)
    return {
        "v": VERSION,
        "seq": int(seq),
        "sim_time": round(float(data.time), 6),
        "send_time": time.time() if send_time is None else float(send_time),
        "bodies": bodies,
        "objects": objects,
    }


def encode(state):
    text = json.dumps(state, separators=(",", ":"))
    text = _EXPONENT.sub(lambda m: f"{float(m.group()):.{DECIMALS}f}", text)
    return text.encode("utf-8")


class StatePublisher:
    """Sends the state over UDP, at most `rate` messages per second."""

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, rate=MAX_RATE, clock=time.monotonic):
        self.address = (host, port)
        self.period = 1.0 / rate
        self.clock = clock
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = 0
        self.next_time = None

    def publish(self, model, data):
        """Send one message if one is due. Returns True if a datagram went out."""
        now = self.clock()
        if self.next_time is not None and now < self.next_time:
            return False
        # Keep a steady rate; after a stall start again from now, without a burst.
        if self.next_time is None or now - self.next_time > self.period:
            self.next_time = now
        self.next_time += self.period
        try:
            self.sock.sendto(encode(build_state(model, data, self.seq)), self.address)
        except OSError:
            return False  # network trouble: Unity misses one state, the next one follows
        self.seq += 1
        return True

    def close(self):
        self.sock.close()
