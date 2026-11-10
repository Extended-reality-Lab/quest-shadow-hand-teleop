"""Tests for the retargeting and the teleop loop. No headset or viewer needed.

    python -m unittest discover -s teleop -v
"""
import os
import sys
import unittest

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pc_receiver"))

import fake_sender
import protocol
from retarget import CHAINS, WRIST, Retargeter
from run import (
    MAX_FRAME_GAP,
    MAX_HAND_SPEED,
    MAX_HAND_TURN_SPEED,
    OTHER_FINGERS,
    SIGN_HOLD,
    WORKSPACE_LOW,
    OkSign,
    Teleop,
    build_scene,
    place_hand_at_home,
)


def robot_skeleton(retargeter, qpos):
    """A 26-joint 'human' skeleton taken from the robot hand itself in pose qpos.

    If the solver is right, it must be able to find this pose again.
    """
    m = retargeter.model
    d = mujoco.MjData(m)
    d.qpos[:] = qpos
    mujoco.mj_kinematics(m, d)
    p = retargeter.prefix
    joints = np.zeros((26, 3))
    joints[WRIST] = d.body(p + "palm").xpos
    for human, robot in CHAINS:
        for index, name in zip(human, robot):
            obj = d.site(p + name) if name.endswith("_tip") else d.body(p + name)
            joints[index] = obj.xpos
    return joints


def random_rotation(rng):
    q = rng.normal(size=4)
    q /= np.linalg.norm(q)
    mat = np.zeros(9)
    mujoco.mju_quat2Mat(mat, q)
    return mat.reshape(3, 3)


def message(joints, tracked=True, hand="right"):
    rows = [list(p) + [0.0, 0.0, 0.0, 1.0] for p in joints]
    return protocol.make_message(0, 0, hand, tracked, "optical", rows)


class RetargetTest(unittest.TestCase):
    def test_finds_a_robot_pose_again(self):
        rng = np.random.default_rng(1)
        for hand in ("right", "left"):
            r = Retargeter(hand)
            m = r.model
            qpos = np.zeros(m.nq)
            for i in r.dofs:
                lo, hi = m.jnt_range[i]
                qpos[i] = rng.uniform(lo, lo + 0.6 * (hi - lo))
            qpos[m.joint(r.prefix + "LFJ5").qposadr[0]] = 0  # moves a palm landmark
            # Bigger, turned and moved: like a human hand somewhere in the room.
            rot, scale, shift = random_rotation(rng), 1.3, np.array([0.2, 1.1, -0.4])
            joints = shift + scale * robot_skeleton(r, qpos) @ rot.T
            for _ in range(20):  # 20 frames of the same pose
                _, error = r.solve(joints)
            self.assertLess(error, 0.004, hand)  # mean point error under 4 mm

    def test_short_straight_fingers_stay_straight(self):
        # A human hand has shorter fingers for its palm than the Shadow Hand.
        r = Retargeter("right")
        joints = robot_skeleton(r, np.zeros(r.model.nq))  # the open robot hand
        for human, _ in CHAINS:
            base = joints[human[0]].copy()
            for index in human[1:]:
                joints[index] = base + 0.6 * (joints[index] - base)
        for _ in range(20):
            r.solve(joints)
        self.assertLess(np.abs(r.data.qpos).max(), 0.05)  # rad: no joint bends

    def test_fist_bends_the_fingers_more_than_open_hand(self):
        r = Retargeter("right")
        names = ["rh_A_FFJ3", "rh_A_FFJ0", "rh_A_MFJ3", "rh_A_MFJ0"]
        ids = [r.model.actuator(n).id for n in names]

        def bend(t):
            joints = np.array(fake_sender.synthetic_hand("right", t))[:, :3]
            for _ in range(20):
                ctrl, _ = r.solve(joints)
            return ctrl[ids].sum()

        open_hand, fist = bend(0.0), bend(1.5)  # fake curl: 0 at t=0, 1 at t=1.5
        self.assertGreater(fist, open_hand + 1.0)


class OkSignTest(unittest.TestCase):
    def hand(self, gap, tracked=True, curl=0.0):
        """Thumb and index tips `gap` apart; the other fingers bend by `curl` rad at each joint."""
        joints = np.zeros((26, 3))
        joints[10] = [gap, 0.0, 0.0]  # index tip; the thumb tip stays at 0
        for n, chain in enumerate(OTHER_FINGERS):
            point = np.array([0.02 * (n + 1), 0.0, 0.0])
            joints[chain[0]] = point
            for k, length in enumerate((0.07, 0.045, 0.025, 0.022)):
                point = point + length * np.array([0.0, np.cos(k * curl), -np.sin(k * curl)])
                joints[chain[k + 1]] = point
        return message(joints, tracked=tracked, hand="left")

    def feed(self, sign, gap, start, seconds, tracked=True, curl=0.0):
        """Messages at 50 Hz; returns how many times the sign fired."""
        steps = round(seconds * 50)
        return sum(sign.update(self.hand(gap, tracked, curl), start + i / 50) for i in range(steps + 1))

    def test_a_held_sign_fires_once(self):
        sign = OkSign()
        self.assertEqual(self.feed(sign, 0.01, 0.0, SIGN_HOLD - 0.1), 0)  # not long enough yet
        self.assertEqual(self.feed(sign, 0.01, SIGN_HOLD, 2.0), 1)  # one long sign, one request

    def test_a_resting_hand_does_not_fire(self):
        sign = OkSign()
        self.assertEqual(self.feed(sign, 0.01, 0.0, 5.0, curl=0.6), 0)  # thumb on index, every finger bent
        self.assertEqual(self.feed(sign, 0.01, 5.5, 5.0, curl=0.35), 0)  # 20 degrees at each joint is bent too
        self.assertEqual(self.feed(sign, 0.01, 12.0, SIGN_HOLD - 0.5), 0)  # the sign starts
        self.assertEqual(self.feed(sign, 0.01, 12.0 + SIGN_HOLD - 0.48, 1.0, curl=0.6), 0)  # the fingers bend: over
        self.assertEqual(self.feed(sign, 0.01, 14.0 + SIGN_HOLD, SIGN_HOLD - 0.1), 0)  # and the count starts again

    def test_a_new_sign_needs_an_open_hand_first(self):
        sign = OkSign()
        self.assertEqual(self.feed(sign, 0.01, 0.0, SIGN_HOLD + 0.5), 1)
        self.assertEqual(self.feed(sign, 0.03, 3.0, SIGN_HOLD + 0.5), 0)  # half open: still the same sign
        self.assertEqual(self.feed(sign, 0.08, 6.0, 0.2), 0)
        self.assertEqual(self.feed(sign, 0.01, 7.0, SIGN_HOLD + 0.5), 1)

    def test_short_open_or_lost_hands_do_not_fire(self):
        sign = OkSign()
        self.assertEqual(self.feed(sign, 0.01, 0.0, 0.5), 0)  # a short sign
        self.assertEqual(self.feed(sign, 0.08, 1.0, 0.1), 0)
        self.assertEqual(self.feed(sign, 0.03, 2.0, 3.0), 0)  # never closed
        self.assertEqual(self.feed(sign, 0.01, 6.0, 3.0, tracked=False), 0)
        self.assertFalse(sign.update(None, 10.0))

    def test_a_sign_does_not_continue_over_a_silent_stream(self):
        sign = OkSign()
        self.assertEqual(self.feed(sign, 0.01, 0.0, 0.5), 0)
        self.assertEqual(self.feed(sign, 0.01, 30.0, SIGN_HOLD - 0.5), 0)  # counted from 30 s, not from 0
        self.assertEqual(self.feed(sign, 0.01, 30.0 + SIGN_HOLD - 0.48, 0.6), 1)


class TeleopTest(unittest.TestCase):
    def setUp(self):
        self.model = build_scene("right")
        self.data = mujoco.MjData(self.model)
        self.teleop = Teleop(self.model, "right")
        place_hand_at_home(self.model, self.data, self.teleop, "right")

    def run_fake(self, seconds, tracked=lambda t: True):
        m, d = self.model, self.data
        t = 0.0
        while t < seconds:
            joints = np.array(fake_sender.synthetic_hand("right", t))[:, :3]
            self.teleop.update(message(joints, tracked(t)), t)
            self.teleop.apply(d)
            for _ in range(round(1 / 60 / m.opt.timestep)):
                mujoco.mj_step(m, d)
            t += 1 / 60

    def test_hand_follows_the_target_and_stays_in_limits(self):
        self.run_fake(3.0)
        d = self.data
        self.assertTrue(np.all(np.isfinite(d.qpos)))
        lo, hi = self.model.actuator_ctrlrange.T
        self.assertTrue(np.all((d.ctrl >= lo - 1e-9) & (d.ctrl <= hi + 1e-9)))
        forearm = d.body("rh_forearm").xpos
        self.assertLess(np.linalg.norm(forearm - d.mocap_pos[0]), 0.02)

    def test_tracking_loss_holds_the_last_pose(self):
        self.run_fake(1.0)
        before = (self.teleop.ctrl.copy(), self.teleop.mocap_pos.copy())
        self.run_fake(1.0, tracked=lambda t: False)
        np.testing.assert_array_equal(self.teleop.ctrl, before[0])
        np.testing.assert_array_equal(self.teleop.mocap_pos, before[1])

    def test_hand_target_stays_in_the_workspace(self):
        joints = np.array(fake_sender.synthetic_hand("right", 0.0))[:, :3]
        self.teleop.update(message(joints), 0.0)
        far = joints + np.array([0.0, -5.0, 0.0])  # 5 m down, through the floor
        for i in range(600):
            self.teleop.update(message(far), (i + 1) / 60)
        self.assertGreaterEqual(self.teleop.mocap_pos[2], WORKSPACE_LOW[2] - 1e-9)


    def test_hand_does_not_jump_when_tracking_comes_back_elsewhere(self):
        self.run_fake(1.0)
        before_pos, before_quat = self.teleop.mocap_pos.copy(), self.teleop.mocap_quat.copy()
        joints = np.array(fake_sender.synthetic_hand("right", 1.0))[:, :3]
        moved = joints + np.array([0.3, 0.0, 0.0])  # 30 cm away, 3 s later
        flipped = moved.copy()
        flipped[:, 1] = 2 * moved[WRIST, 1] - moved[:, 1]  # hand upside down
        self.teleop.update(message(flipped), 4.0)
        step = np.linalg.norm(self.teleop.mocap_pos - before_pos)
        self.assertLessEqual(step, MAX_HAND_SPEED * MAX_FRAME_GAP + 1e-9)
        turn = 2 * np.arccos(min(1.0, abs(np.dot(self.teleop.mocap_quat, before_quat))))
        self.assertLessEqual(turn, MAX_HAND_TURN_SPEED * MAX_FRAME_GAP + 1e-6)

    def test_broken_frame_is_skipped(self):
        self.run_fake(0.5)
        before = self.teleop.ctrl.copy()
        same_point = np.zeros((26, 3))  # every joint at one point
        self.assertFalse(self.teleop.update(message(same_point), 0.6))
        np.testing.assert_array_equal(self.teleop.ctrl, before)
        self.assertTrue(np.all(np.isfinite(self.teleop.retarget.data.qpos)))


class GraspTest(unittest.TestCase):
    def test_hand_can_lift_the_ball(self):
        """Scripted grasp, no Quest: down over the ball, close, lift, hold 3 s."""
        m = build_scene("right")
        d = mujoco.MjData(m)
        teleop = Teleop(m, "right")
        place_hand_at_home(m, d, teleop, "right")
        mocap = teleop.mocap_id
        offset = d.mocap_pos[mocap] - d.site("grasp_site").xpos  # mocap vs palm centre

        lo, hi = m.actuator_ctrlrange.T
        open_hand = np.clip(np.zeros(m.nu), lo, hi)
        fist = open_hand.copy()
        for i in range(m.nu):
            name = m.actuator(i).name
            if name.endswith(("J3", "J0")) and "TH" not in name:
                fist[i] = 0.8 * hi[i]
        for name, angle in [("THJ5", 0.5), ("THJ4", 1.2), ("THJ2", 0.3), ("THJ1", 1.0)]:
            fist[m.actuator("rh_A_" + name).id] = angle

        def move(grasp_target, seconds, ctrl):
            start, goal = d.mocap_pos[mocap].copy(), grasp_target + offset
            steps = int(seconds / m.opt.timestep)
            for k in range(steps):
                d.mocap_pos[mocap] = start + (goal - start) * min(1.0, (k + 1) / (0.7 * steps))
                d.ctrl[:] = ctrl
                mujoco.mj_step(m, d)

        ball = d.body("ball")
        start = ball.xpos.copy()
        move(start + [0, 0, 0.08], 1.0, open_hand)
        move(start + [0, 0, 0.025], 1.0, open_hand)
        here = d.site("grasp_site").xpos.copy()
        move(here, 1.0, fist)
        move(here + [0, 0, 0.15], 1.5, fist)
        move(here + [0, 0, 0.15], 3.0, fist)  # hold
        self.assertGreater(ball.xpos[2] - start[2], 0.05)  # lifted 5 cm, held 3 s


if __name__ == "__main__":
    unittest.main()
