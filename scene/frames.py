"""Frame conversions between MuJoCo and Unity.

MuJoCo is the authoritative frame: +Z up, right-handed, metres, quaternions
(w, x, y, z). Unity is +Y up, left-handed, metres, quaternions (x, y, z, w).

Decision: every frame conversion happens in Python, on the MuJoCo side. The
scene manifest and the state stream are written in Unity's frame, and Unity
applies the values as they are, with no math of its own. One exception:
unity_viz/Assets/Scripts/HandSender.cs turns the hand poses it reads back into
the OpenXR frame before sending them, because teleop/run.py expects the
headset's own frame. This module stays numpy-only (no mujoco import), so it
has its own matrix-to-quaternion function.

    position:    (x, y, z)_unity = (x, z, y)_mujoco
    quaternion:  (x, y, z, w)_unity = (-x, -z, -y, w)_mujoco

Swapping Y and Z is a reflection (determinant -1). A rotation R becomes
P R P, whose axis is -P times the old axis, hence the minus signs. A
reflection also flips the winding of every triangle, so each triangle
(a, b, c) becomes (a, c, b) to keep its front face outside.
"""
import numpy as np


def to_unity_vec(v):
    """MuJoCo position or direction (..., 3) -> Unity (..., 3)."""
    v = np.asarray(v, dtype=float)
    return v[..., [0, 2, 1]]


def to_mujoco_vec(v):
    """Unity position or direction (..., 3) -> MuJoCo (..., 3). Its own inverse."""
    return to_unity_vec(v)


def to_unity_quat(q):
    """MuJoCo quaternion (w, x, y, z) -> Unity quaternion (x, y, z, w)."""
    w, x, y, z = np.asarray(q, dtype=float)
    return np.array([-x, -z, -y, w])


def to_mujoco_quat(q):
    """Unity quaternion (x, y, z, w) -> MuJoCo quaternion (w, x, y, z)."""
    x, y, z, w = np.asarray(q, dtype=float)
    return np.array([w, -x, -z, -y])


def to_unity_triangles(triangles):
    """Triangle indices (n, 3) -> the same triangles with the winding reversed."""
    return np.asarray(triangles)[:, [0, 2, 1]]


# Swap Y and Z (MuJoCo <-> Unity) and negate Z (OpenXR <-> Unity). Both are
# reflections and each is its own inverse.
_MUJOCO_TO_UNITY = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]])
_OPENXR_TO_UNITY = np.diag([1.0, 1.0, -1.0])


def stage_to_unity(rotation, translation):
    """Pose of the headset's tracking origin, for the XR rig in Unity.

    `rotation` (3x3) and `translation` (3) map a point of the OpenXR stage frame
    (+Y up, -Z forward, right-handed) into the MuJoCo world:
    world = rotation @ p + translation. This is the mapping teleop/run.py applies
    to the tracked wrist. Unity's OpenXR plugin reports the same stage with Z
    negated (left-handed). The returned Unity position and quaternion (x, y, z, w)
    are the pose of a rig such that rig.TransformPoint(unity_stage_point) is the
    Unity position of the same point of the world: the rendered hand then sits on
    the real hand.
    """
    rotation = np.asarray(rotation, dtype=float)
    rig = _MUJOCO_TO_UNITY @ rotation @ _OPENXR_TO_UNITY  # two reflections: a rotation
    return to_unity_vec(translation), mat_to_quat_xyzw(rig)


def mat_to_quat_xyzw(m):
    """Unit quaternion (x, y, z, w) of a rotation matrix (3x3), with w >= 0."""
    m = np.asarray(m, dtype=float)
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    if trace > 0.0:
        s = 2.0 * np.sqrt(trace + 1.0)
        q = np.array([(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s])
    elif m[0, 0] >= m[1, 1] and m[0, 0] >= m[2, 2]:
        s = 2.0 * np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2])
        q = np.array([0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s])
    elif m[1, 1] >= m[2, 2]:
        s = 2.0 * np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2])
        q = np.array([(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s])
    else:
        s = 2.0 * np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1])
        q = np.array([(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s])
    if q[3] < 0.0:
        q = -q
    return q / np.linalg.norm(q)
