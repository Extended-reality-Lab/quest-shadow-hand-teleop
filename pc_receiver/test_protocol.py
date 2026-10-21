"""Tests for the v1 hand stream format.

Run from the repo root:
    python -m unittest discover -s pc_receiver -v
"""
import unittest

import protocol
import receiver

# 26 identical joints: position (0.0123, 1.0456, -0.321) m, identity rotation.
JOINTS_26 = [[0.0123, 1.0456, -0.321, 0.0, 0.0, 0.0, 1.0]] * 26
JOINTS_26_JSON = ",".join(["[0.0123,1.0456,-0.321,0.0,0.0,0.0,1.0]"] * 26)

VALID_TRACKED = (
    b'{"v":1,"seq":1234,"t_us":52341234,"hand":"left","tracked":true,'
    b'"source":"optical","joints":[' + JOINTS_26_JSON.encode() + b"]}"
)
VALID_LOST = (
    b'{"v":1,"seq":1235,"t_us":52341300,"hand":"right","tracked":false,'
    b'"source":"unknown","joints":[]}'
)


class ParseTest(unittest.TestCase):
    def test_valid_tracked_datagram_parses(self):
        msg = protocol.parse(VALID_TRACKED)
        self.assertEqual(msg["hand"], "left")
        self.assertEqual(msg["seq"], 1234)
        self.assertEqual(msg["t_us"], 52341234)
        self.assertTrue(msg["tracked"])
        self.assertEqual(len(msg["joints"]), 26)
        self.assertEqual(msg["joints"][1], [0.0123, 1.0456, -0.321, 0.0, 0.0, 0.0, 1.0])

    def test_untracked_with_empty_joints_parses(self):
        msg = protocol.parse(VALID_LOST)
        self.assertEqual(msg["hand"], "right")
        self.assertFalse(msg["tracked"])
        self.assertEqual(msg["joints"], [])

    def test_wrong_joint_count_is_rejected(self):
        data = VALID_TRACKED.replace(b"[0.0123,1.0456,-0.321,0.0,0.0,0.0,1.0],", b"", 1)
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse(data)

    def test_tracked_without_joints_is_rejected(self):
        data = VALID_LOST.replace(b'"tracked":false', b'"tracked":true')
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse(data)

    def test_unknown_hand_is_rejected(self):
        data = VALID_LOST.replace(b'"right"', b'"middle"')
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse(data)

    def test_invalid_json_is_rejected(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse(b'{"v":1, "seq":')

    def test_non_utf8_is_rejected(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse(b"\xff\xfe\x00")

    def test_round_trip_rounds_to_four_decimals(self):
        msg = protocol.make_message(7, 1000, "left", True, "optical",
                                    [[0.123456, 1.0, -0.5, 0.0, 0.0, 0.0, 1.0]] * 26)
        parsed = protocol.parse(protocol.encode(msg))
        self.assertEqual(parsed["joints"][0][0], 0.1235)


class FakeClock:
    """Clock the test moves by hand, so no test has to sleep."""

    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class HandStateTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.hand = receiver.HandState(timeout=0.5, clock=self.clock)

    def test_no_packet_yet_is_lost_no_packets(self):
        self.assertEqual(self.hand.status(), "LOST (no packets)")

    def test_tracked_then_timeout_switches_to_lost_no_packets(self):
        self.hand.update(protocol.parse(VALID_TRACKED))
        self.clock.now = 100.4
        self.assertEqual(self.hand.status(), "TRACKED")
        self.clock.now = 100.6
        self.assertEqual(self.hand.status(), "LOST (no packets)")

    def test_untracked_datagram_is_lost_tracking(self):
        self.hand.update(protocol.parse(VALID_LOST))
        self.assertEqual(self.hand.status(), "LOST (tracking)")

    def test_rate_counts_last_second_only(self):
        for t in (100.0, 100.5, 101.0, 101.2):
            self.clock.now = t
            self.hand.update(protocol.parse(VALID_TRACKED))
        self.assertEqual(self.hand.rate_hz(), 3)


class SeqCounterTest(unittest.TestCase):
    def test_gap_is_counted(self):
        counter = receiver.SeqCounter()
        for seq in (1, 2, 5, 6):
            counter.update(seq)
        self.assertEqual(counter.lost, 2)

    def test_reordered_packet_is_not_counted_twice(self):
        counter = receiver.SeqCounter()
        for seq in (1, 3, 2, 4, 5):
            counter.update(seq)
        self.assertEqual(counter.lost, 1)

    def test_app_restart_is_not_a_gap(self):
        counter = receiver.SeqCounter()
        for seq in (5000, 5001, 0, 1):
            counter.update(seq)
        self.assertEqual(counter.lost, 0)


class MalformedInputTest(unittest.TestCase):
    def test_huge_integer_is_rejected_not_raised(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse(b'{"v":1,"seq":' + b"9" * 5000 + b"}")

    def test_deep_nesting_is_rejected_not_raised(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse(b"[" * 3000 + b"]" * 3000)

    def test_nan_joint_is_rejected(self):
        data = VALID_TRACKED.replace(b"0.0123", b"NaN", 1)
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse(data)

    def test_boolean_version_is_rejected(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse(VALID_LOST.replace(b'"v":1', b'"v":true'))


if __name__ == "__main__":
    unittest.main()
