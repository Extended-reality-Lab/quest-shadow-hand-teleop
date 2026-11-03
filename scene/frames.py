"""Frame conversions between MuJoCo and Unity.

MuJoCo is the authoritative frame: +Z up, right-handed, metres, quaternions
(w, x, y, z). Unity is +Y up, left-handed, metres, quaternions (x, y, z, w).

Decision: every frame conversion happens in Python, on the MuJoCo side. The
scene manifest and the state stream are written in Unity's frame, and Unity
applies the values as they are, with no math of its own.

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
