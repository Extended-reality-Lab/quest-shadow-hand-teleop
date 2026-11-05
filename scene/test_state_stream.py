"""Tests for the state stream MuJoCo -> Unity. No viewer, headset or Unity needed.

    python -m unittest discover -s scene -v
"""
import json
import os
import socket
import sys
import unittest

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "teleop"))
sys.path.insert(0, os.path.join(HERE, "..", "pc_receiver"))

import fake_sender  # pyright: ignore[reportMissingImports]
import protocol  # pyright: ignore[reportMissingImports]
from frames import to_mujoco_vec
from run import (  # pyright: ignore[reportMissingImports]
    Teleop,
    build_scene,
    place_hand_at_home,
)
from state_stream import OBJECTS, StatePublisher, build_state, encode

HAND = "right"


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def settled_scene():
    """The scene with the hand at HOME after 0.2 s of physics, so objects have moved a little."""
    model = build_scene(HAND)
    data = mujoco.MjData(model)
    place_hand_at_home(model, data, Teleop(model, HAND), HAND)
    for _ in range(100):
        mujoco.mj_step(model, data)
    return model, data


class StateMessageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.data = settled_scene()
        cls.state = build_state(cls.model, cls.data, seq=7)

    def test_positions_map_back_to_mujoco(self):
        for pose in self.state["bodies"] + self.state["objects"]:
            body = self.model.body(pose["id"]).id
            np.testing.assert_allclose(to_mujoco_vec(pose["p"]), self.data.xpos[body], atol=1e-4)

    def test_bodies_and_objects_split(self):
        names = {self.model.body(b).name for b in range(1, self.model.nbody)}
        self.assertEqual([o["id"] for o in self.state["objects"]], list(OBJECTS))
        self.assertEqual({b["id"] for b in self.state["bodies"]}, names - set(OBJECTS))
        self.assertTrue(all(o["grasp"] == "free" for o in self.state["objects"]))
        self.assertTrue(all(len(p["q"]) == 4 for p in self.state["bodies"] + self.state["objects"]))

    def test_one_message_fits_a_datagram(self):
        size = len(encode(self.state))
        print(f"\nstate message: {size} bytes")
        self.assertLess(size, 60000)
        self.assertNotIn(b"e-", encode(self.state))


class PublisherTest(unittest.TestCase):
    def setUp(self):
        self.model, self.data = settled_scene()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.settimeout(2.0)
        self.clock = FakeClock()
        self.publisher = StatePublisher("127.0.0.1", self.listener.getsockname()[1], clock=self.clock)

    def tearDown(self):
        self.publisher.close()
        self.listener.close()

    def test_loopback_round_trip(self):
        self.assertTrue(self.publisher.publish(self.model, self.data))
        self.clock.now += 1 / 30
        self.assertTrue(self.publisher.publish(self.model, self.data))
        first = json.loads(self.listener.recv(65536))
        second = json.loads(self.listener.recv(65536))
        self.assertEqual(second["seq"], first["seq"] + 1)
        self.assertEqual(first["v"], 1)

    def test_rate_limit(self):
        sent = 0
        for i in range(600):  # 600 calls over one simulated second
            self.clock.now = i / 600
            sent += self.publisher.publish(self.model, self.data)
        self.assertEqual(sent, 60)


class LiveHandTest(unittest.TestCase):
    """The loop of teleop/run.py main() without the viewer, fed by the fake sender."""

    def test_fake_hand_moves_the_streamed_hand(self):
        model = build_scene(HAND)
        data = mujoco.MjData(model)
        teleop = Teleop(model, HAND)
        place_hand_at_home(model, data, teleop, HAND)
        start = build_state(model, data, 0)
        for frame in range(120):  # 2 s at 60 Hz
            t = frame / 60
            msg = protocol.make_message(frame, int(t * 1e6), HAND, True, "optical", fake_sender.synthetic_hand(HAND, t))
            teleop.update(protocol.parse(protocol.encode(msg)), t)
            teleop.apply(data)
            while data.time < t:
                mujoco.mj_step(model, data)
        end = build_state(model, data, 1)
        moved = {
            a["id"]: float(np.linalg.norm(np.subtract(a["p"], b["p"])))
            for a, b in zip(start["bodies"], end["bodies"], strict=True)
        }
        print(f"\nlargest hand body motion in 2 s: {max(moved.values()) * 100:.1f} cm ({max(moved, key=moved.get)})")
        self.assertGreater(max(moved.values()), 0.01)


if __name__ == "__main__":
    unittest.main()
