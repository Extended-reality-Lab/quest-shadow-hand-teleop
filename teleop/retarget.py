"""Retargeting: Quest hand skeleton -> Shadow Hand joint targets.

The Quest gives 26 joint positions (PROTOCOL.md), not angles. The Shadow Hand
has different proportions and fewer joints, so the angles are found with
inverse kinematics on a copy of the Shadow Hand:

1. Build a palm frame (forward, side, back-of-hand) from four landmarks on the
   human hand, and the same frame from the same four landmarks on the robot.
2. Take the direction of every human finger bone in the human palm frame. Lay
   the robot's own bones along these directions, starting at the robot's own
   knuckle. The ends of the bones are the targets: three per finger. The
   robot's bone lengths are used, not the human's, so a straight human finger
   gives a straight robot finger whatever the proportions of the two hands.
3. Damped least squares moves the robot's finger joints until its own points
   reach the targets. The result is one target per actuator (data.ctrl).

The same palm frame also gives the wrist pose, which run.py uses to move the
whole hand in the scene.
"""
import os

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets", "shadow_hand")

# OpenXR joint indices, see docs/hand-stream/PROTOCOL.md.
WRIST = 1
INDEX_PROXIMAL = 7
MIDDLE_PROXIMAL = 12
LITTLE_PROXIMAL = 22

# One chain per finger: the OpenXR joints from the base of the finger to its
# tip, and the Shadow Hand points at the same places. A Shadow point is a body
# origin (the joint at the base of that bone) or one of the tip sites added in
# build_hand_spec(). OpenXR names: thumb = metacarpal, proximal, distal, tip;
# fingers = proximal (the knuckle), intermediate, distal, tip.
CHAINS = [
    ((2, 3, 4, 5), ("thproximal", "thmiddle", "thdistal", "th_tip")),
    ((7, 8, 9, 10), ("ffproximal", "ffmiddle", "ffdistal", "ff_tip")),  # index
    ((12, 13, 14, 15), ("mfproximal", "mfmiddle", "mfdistal", "mf_tip")),  # middle
    ((17, 18, 19, 20), ("rfproximal", "rfmiddle", "rfdistal", "rf_tip")),  # ring
    ((22, 23, 24, 25), ("lfproximal", "lfmiddle", "lfdistal", "lf_tip")),  # little
]
# How hard the solver tries to match the end of the first bone, of the second
# bone, and the fingertip.
WEIGHTS = (0.5, 0.7, 1.0)

# Fingertip sites: (site name, distal body, length of the last bone in m).
TIPS = [
    ("th_tip", "thdistal", 0.030),
    ("ff_tip", "ffdistal", 0.026),
    ("mf_tip", "mfdistal", 0.026),
    ("rf_tip", "rfdistal", 0.026),
    ("lf_tip", "lfdistal", 0.026),
]


def build_hand_spec(hand):
    """Load the Menagerie hand as an MjSpec and add fingertip sites.

    The XML file itself is not changed; everything is added in memory.
    """
    prefix = "rh_" if hand == "right" else "lh_"
    spec = mujoco.MjSpec.from_file(os.path.join(ASSETS, f"{hand}_hand.xml"))
    for site, body, length in TIPS:
        spec.body(prefix + body).add_site(name=prefix + site, pos=[0, 0, length])
    return spec


def palm_frame(wrist, index, middle, little):
    """3x3 matrix whose columns are the palm axes: side, back, forward.

    forward: wrist -> middle knuckle.  side: little knuckle -> index knuckle.
    back = forward x side. For a right hand it points out of the back of the
    hand; for a left hand out of the palm. The same formula is used for the
    human and the robot hand of the same side, so this does not matter.
    """
    forward = middle - wrist
    side = index - little
    if np.linalg.norm(forward) < 1e-3:
        raise ValueError("wrist and middle knuckle coincide")
    forward /= np.linalg.norm(forward)
    side -= forward * np.dot(side, forward)  # make it perpendicular
    if np.linalg.norm(side) < 1e-3:
        raise ValueError("knuckles in a line with the wrist")
    side /= np.linalg.norm(side)
    back = np.cross(forward, side)
    return np.column_stack([side, back, forward])


class Retargeter:
    """Turns one Quest hand (26 joints) into Shadow Hand actuator targets."""

    def __init__(self, hand="right", iterations=8, damping=0.02):
        self.prefix = "rh_" if hand == "right" else "lh_"
        self.iterations = iterations
        self.damping = damping
        # A private copy of the hand, fixed in space, used only for the solver.
        self.model = build_hand_spec(hand).compile()
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)

        p = self.prefix
        self.palm_id = self.model.body(p + "palm").id
        # Robot palm frame, written in the robot palm body's own coordinates.
        palm_pos = self.data.body(p + "palm").xpos.copy()
        palm_rot = self.data.body(p + "palm").xmat.reshape(3, 3).copy()

        def local(name):
            if name.endswith("_tip"):
                return palm_rot.T @ (self.data.site(p + name).xpos - palm_pos)
            return palm_rot.T @ (self.data.body(p + name).xpos - palm_pos)

        self.robot_frame = palm_frame(
            np.zeros(3), local("ffproximal"), local("mfproximal"), local("lfproximal")
        )

        # Per finger, from the open hand the model starts in: where the chain
        # begins in the palm, and the length of each bone.
        self.chains = []
        # Solver points: body origins or tip sites, and the dofs it may move
        # (every finger joint; the two wrist joints stay at 0 because run.py
        # moves the whole hand instead).
        self.points = []
        for human, robot in CHAINS:
            places = [local(name) for name in robot]
            lengths = np.linalg.norm(np.diff(places, axis=0), axis=1)
            self.chains.append((human, places[0], lengths))
            for name, weight in zip(robot[1:], WEIGHTS):
                if name.endswith("_tip"):
                    self.points.append(("site", self.model.site(p + name).id, weight))
                else:
                    self.points.append(("body", self.model.body(p + name).id, weight))
        wrist_dofs = {self.model.joint(p + j).dofadr[0] for j in ("WRJ1", "WRJ2")}
        self.dofs = np.array([i for i in range(self.model.nv) if i not in wrist_dofs])
        self.lower = self.model.jnt_range[:, 0]
        self.upper = self.model.jnt_range[:, 1]

    def human_frame(self, joints):
        """Palm frame of the human hand, in Quest (OpenXR) coordinates."""
        return palm_frame(
            joints[WRIST], joints[INDEX_PROXIMAL], joints[MIDDLE_PROXIMAL], joints[LITTLE_PROXIMAL]
        )

    def targets(self, joints):
        """Target positions for the solver points, in the solver's world."""
        # human Quest coordinates -> human palm axes -> robot palm axes
        to_robot = self.robot_frame @ self.human_frame(joints).T
        palm_pos = self.data.xpos[self.palm_id]
        palm_rot = self.data.xmat[self.palm_id].reshape(3, 3)
        out = []
        for human, start, lengths in self.chains:
            point = start
            for a, b, length in zip(human, human[1:], lengths):
                bone = joints[b] - joints[a]
                size = np.linalg.norm(bone)
                if size < 1e-4:
                    raise ValueError("two joints of one finger coincide")
                point = point + length * (to_robot @ bone) / size
                out.append(palm_pos + palm_rot @ point)
        return np.array(out)

    def solve(self, joints):
        """Run the solver for one frame. Returns (ctrl, error in m).

        `joints` is a (26, 3) array of positions. The previous solution is the
        starting point, so consecutive frames converge in a few iterations.
        """
        m, d = self.model, self.data
        goal = self.targets(joints)  # raises ValueError for a broken frame
        jac = np.zeros((3, m.nv))
        for _ in range(self.iterations):
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)
            rows, errors = [], []
            for (kind, obj, weight), target in zip(self.points, goal):
                if kind == "site":
                    pos = d.site_xpos[obj]
                    mujoco.mj_jacSite(m, d, jac, None, obj)
                else:
                    pos = d.xpos[obj]
                    mujoco.mj_jacBody(m, d, jac, None, obj)
                rows.append(weight * jac[:, self.dofs])
                errors.append(weight * (target - pos))
            J = np.vstack(rows)
            e = np.concatenate(errors)
            # Damped least squares: dq = J^T (J J^T + lambda^2 I)^-1 e
            dq = J.T @ np.linalg.solve(J @ J.T + self.damping**2 * np.eye(len(e)), e)
            # Every joint here is a hinge, so qpos index == dof index.
            d.qpos[self.dofs] += dq
            np.clip(d.qpos, self.lower, self.upper, out=d.qpos)
        if not np.all(np.isfinite(d.qpos)):
            d.qpos[:] = 0  # never let a bad frame poison the next ones

        mujoco.mj_fwdPosition(m, d)  # also fills actuator_length
        error = self._mean_error(goal)
        # A position actuator's input is its joint angle, or for the coupled
        # finger joints (J1 + J2) the tendon length. actuator_length is exactly
        # that number for the current pose.
        ctrl = np.clip(d.actuator_length, m.actuator_ctrlrange[:, 0], m.actuator_ctrlrange[:, 1])
        return ctrl, error

    def _mean_error(self, goal):
        d = self.data
        dist = []
        for (kind, obj, _), target in zip(self.points, goal):
            pos = d.site_xpos[obj] if kind == "site" else d.xpos[obj]
            dist.append(np.linalg.norm(target - pos))
        return float(np.mean(dist))
