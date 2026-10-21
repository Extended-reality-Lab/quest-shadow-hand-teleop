"""Drive the Shadow Hand in MuJoCo with the Quest hand stream.

One program: it listens for the Quest datagrams (same port and format as
pc_receiver/receiver.py), turns the hand into robot joint targets
(retarget.py), and runs the simulation with a table and objects to grab.

    macOS:    .venv/bin/mjpython teleop/run.py
    Windows:  .\\.venv\\Scripts\\python.exe teleop\\run.py
    Linux:    .venv/bin/python teleop/run.py

Options: --hand left|right (default right), --port 9000.
Keys in the viewer: Enter = re-centre (hold your hand forward over the table).

Only one program can listen on a port: stop receiver.py before running this.
"""
import argparse
import os
import socket
import sys
import time

import mujoco
import mujoco.viewer
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pc_receiver"))

import protocol
from retarget import WRIST, Retargeter, build_hand_spec

TABLE_TOP = 0.75  # m
# Where the wrist goes after re-centring: above the near edge of the table.
HOME = np.array([0.0, 0.25, TABLE_TOP + 0.20])
# Safety limits on what reaches the simulation.
WORKSPACE_LOW = np.array([-0.6, -0.2, TABLE_TOP + 0.03])
WORKSPACE_HIGH = np.array([0.6, 0.9, TABLE_TOP + 0.6])
MAX_HAND_SPEED = 1.5  # m/s
MAX_JOINT_SPEED = 8.0  # rad/s
TIMEOUT = 0.5  # s without packets -> the hand holds still
KEY_ENTER = 257  # GLFW key code

# Quest (OpenXR: +Y up, -Z forward) -> MuJoCo world (+Z up). Same mapping as in
# PROTOCOL.md: (x, y, z)_mujoco = (x, -z, y)_openxr.
QUEST_TO_WORLD = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])


def build_scene(hand):
    """The hand on a free joint, moved by a mocap body, plus table and objects."""
    prefix = "rh_" if hand == "right" else "lh_"
    spec = build_hand_spec(hand)
    spec.option.timestep = 0.002
    forearm = spec.body(prefix + "forearm")
    forearm.add_freejoint()
    for body in spec.bodies:
        body.gravcomp = 1  # the hand floats; gravity still acts on the objects

    world = spec.worldbody
    world.add_light(pos=[0, 0, 2.5], dir=[0, 0, -1], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL)
    world.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[2, 2, 0.05], rgba=[0.3, 0.35, 0.4, 1])
    # A solid table down to the floor, so the hand cannot be pushed through it.
    world.add_geom(
        name="table",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[0, 0.5, TABLE_TOP / 2],
        size=[0.45, 0.3, TABLE_TOP / 2],
        rgba=[0.55, 0.4, 0.3, 1],
    )
    objects = [
        ("ball", mujoco.mjtGeom.mjGEOM_SPHERE, [0.035, 0, 0], [-0.12, 0.45], [0.9, 0.3, 0.2, 1]),
        ("cube", mujoco.mjtGeom.mjGEOM_BOX, [0.025, 0.025, 0.025], [0.0, 0.5], [0.2, 0.6, 0.9, 1]),
        ("can", mujoco.mjtGeom.mjGEOM_CYLINDER, [0.03, 0.05, 0], [0.13, 0.45], [0.3, 0.8, 0.4, 1]),
    ]
    for name, gtype, size, xy, rgba in objects:
        half_height = size[1] if gtype == mujoco.mjtGeom.mjGEOM_CYLINDER else size[0]
        body = world.add_body(name=name, pos=[xy[0], xy[1], TABLE_TOP + half_height + 0.001])
        body.add_freejoint()
        body.add_geom(
            type=gtype, size=size, rgba=rgba, mass=0.08, condim=4, friction=[1.2, 0.01, 0.001]
        )

    # The mocap body is moved by this program; a weld pulls the forearm onto
    # it. Physics stays in MuJoCo: the hand cannot pass through the table.
    target = world.add_body(name="hand_target", mocap=True)
    target.add_geom(
        type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.01, 0, 0], rgba=[1, 1, 0, 0.3],
        contype=0, conaffinity=0,
    )
    spec.add_equality(
        type=mujoco.mjtEq.mjEQ_WELD,
        name1="hand_target",
        name2=prefix + "forearm",
        objtype=mujoco.mjtObj.mjOBJ_BODY,
        data=[0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],  # anchor, relative pose = none, torque scale
        solref=[0.01, 1],
    )
    return spec.compile()


class Teleop:
    """Quest message -> safe mocap pose and actuator targets for one hand."""

    def __init__(self, model, hand):
        self.model = model
        self.retarget = Retargeter(hand)
        prefix = "rh_" if hand == "right" else "lh_"
        self.mocap_id = model.body("hand_target").mocapid[0]

        # Pose of the palm inside the forearm at wrist angle 0, so a wanted
        # palm pose can be turned into a forearm (mocap) pose.
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        f_rot = data.body(prefix + "forearm").xmat.reshape(3, 3)
        p_rot = data.body(prefix + "palm").xmat.reshape(3, 3)
        self.palm_in_forearm_rot = f_rot.T @ p_rot
        self.palm_in_forearm_pos = f_rot.T @ (data.body(prefix + "palm").xpos - data.body(prefix + "forearm").xpos)

        self.origin = None  # Quest wrist position at the last re-centre
        self.yaw = np.eye(3)  # turns the user's forward direction into +Y
        self.ctrl = None
        self.mocap_pos = None
        self.mocap_quat = None
        self.last_update = None
        self.error = 0.0

    def recenter(self, joints):
        """Make the current wrist position HOME and the hand's forward +Y."""
        self.origin = joints[WRIST].copy()
        forward = QUEST_TO_WORLD @ self.retarget.human_frame(joints)[:, 2]
        heading = np.arctan2(forward[0], forward[1])  # angle from +Y, about +Z
        c, s = np.cos(heading), np.sin(heading)
        self.yaw = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])

    def update(self, msg, now):
        """Use one tracked message. Returns False if it was not used."""
        if not msg["tracked"]:
            return False
        joints = np.array(msg["joints"], dtype=float)[:, :3]
        if self.origin is None:
            self.recenter(joints)

        ctrl, self.error = self.retarget.solve(joints)

        # Palm pose in the world: human palm axes, turned into world axes,
        # matched to the robot's palm axes.
        to_world = self.yaw @ QUEST_TO_WORLD
        human = to_world @ self.retarget.human_frame(joints)
        palm_rot = human @ self.retarget.robot_frame.T
        palm_pos = HOME + to_world @ (joints[WRIST] - self.origin)
        forearm_rot = palm_rot @ self.palm_in_forearm_rot.T
        forearm_pos = palm_pos - forearm_rot @ self.palm_in_forearm_pos

        # Safety filter: workspace box, speed limits on the hand and joints.
        forearm_pos = np.clip(forearm_pos, WORKSPACE_LOW, WORKSPACE_HIGH)
        if self.last_update is not None:
            dt = max(now - self.last_update, 1e-3)
            step = forearm_pos - self.mocap_pos
            max_step = MAX_HAND_SPEED * dt
            if np.linalg.norm(step) > max_step:
                forearm_pos = self.mocap_pos + step * (max_step / np.linalg.norm(step))
            ctrl = self.ctrl + np.clip(ctrl - self.ctrl, -MAX_JOINT_SPEED * dt, MAX_JOINT_SPEED * dt)
        quat = np.zeros(4)
        mujoco.mju_mat2Quat(quat, forearm_rot.flatten())

        self.ctrl, self.mocap_pos, self.mocap_quat = ctrl, forearm_pos, quat
        self.last_update = now
        return True

    def apply(self, data):
        """Write the latest targets into the simulation. Holds still on loss."""
        if self.ctrl is None:
            return
        data.ctrl[:] = self.ctrl
        data.mocap_pos[self.mocap_id] = self.mocap_pos
        data.mocap_quat[self.mocap_id] = self.mocap_quat

    def status(self, now):
        if self.last_update is None:
            return "waiting for the hand"
        if now - self.last_update > TIMEOUT:
            return "HOLD (no tracked data)"
        return f"TRACKING  fit error {self.error * 1000:.1f} mm"


def place_hand_at_home(model, data, teleop, hand):
    """Start the hand at HOME, palm down, fingers to +Y, so nothing jumps."""
    forward = np.array([0.0, 1.0, 0.0])
    side = np.array([-1.0 if hand == "right" else 1.0, 0.0, 0.0])  # towards the thumb
    palm_rot = np.column_stack([side, np.cross(forward, side), forward]) @ teleop.retarget.robot_frame.T
    rot = palm_rot @ teleop.palm_in_forearm_rot.T
    pos = HOME - rot @ teleop.palm_in_forearm_pos
    quat = np.zeros(4)
    mujoco.mju_mat2Quat(quat, rot.flatten())
    data.mocap_pos[teleop.mocap_id] = pos
    data.mocap_quat[teleop.mocap_id] = quat
    data.qpos[0:3] = pos  # the forearm free joint is the first joint
    data.qpos[3:7] = quat
    teleop.mocap_pos, teleop.mocap_quat = pos, quat
    mujoco.mj_forward(model, data)


def open_socket(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sock.setblocking(False)
    return sock


def read_latest(sock, hand):
    """Drain the socket; return the newest valid message for `hand`, or None."""
    latest = None
    while True:
        try:
            data, _ = sock.recvfrom(protocol.MAX_DATAGRAM_BYTES + 1)
        except (BlockingIOError, OSError):
            return latest
        try:
            msg = protocol.parse(data)
        except protocol.ProtocolError:
            continue
        if msg["hand"] == hand:
            latest = msg


def main():
    parser = argparse.ArgumentParser(description="Quest hand -> Shadow Hand in MuJoCo.")
    parser.add_argument("--hand", choices=["right", "left"], default="right")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()

    model = build_scene(args.hand)
    data = mujoco.MjData(model)
    teleop = Teleop(model, args.hand)
    place_hand_at_home(model, data, teleop, args.hand)
    sock = open_socket(args.port)
    print(f"Listening on UDP port {args.port} for the {args.hand} hand. Enter in the viewer = re-centre.")

    recenter_requested = False

    def on_key(key):
        nonlocal recenter_requested
        if key == KEY_ENTER:
            recenter_requested = True

    with mujoco.viewer.launch_passive(model, data, key_callback=on_key) as viewer:
        viewer.cam.lookat[:] = [0, 0.45, TABLE_TOP]
        viewer.cam.distance, viewer.cam.azimuth, viewer.cam.elevation = 1.1, -90, -30
        start = time.monotonic()
        last_print = 0.0
        while viewer.is_running():
            now = time.monotonic()
            msg = read_latest(sock, args.hand)
            if msg is not None:
                if recenter_requested and msg["tracked"]:
                    teleop.recenter(np.array(msg["joints"], dtype=float)[:, :3])
                    recenter_requested = False
                teleop.update(msg, now)
            teleop.apply(data)

            # Step the physics until simulated time catches up with the clock.
            while data.time < now - start:
                mujoco.mj_step(model, data)
            viewer.sync()

            if now - last_print > 0.5:
                last_print = now
                print(f"\r{teleop.status(now):<45}", end="", flush=True)
            time.sleep(0.005)
    print()


if __name__ == "__main__":
    main()
