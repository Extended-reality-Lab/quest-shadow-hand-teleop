"""Tests for the frame conversions and the scene manifest.

    python -m unittest discover -s scene -v
"""
import json
import os
import sys
import unittest

import mujoco  # pyright: ignore[reportMissingImports]
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from export_manifest import (
    VISUAL_GROUPS,
    build_manifest,
    build_scene,  # pyright: ignore[reportAttributeAccessIssue]  (re-exported from teleop/run.py)
    initial_state,
    to_json,
)
from frames import (
    mat_to_quat_xyzw,
    stage_to_unity,
    to_mujoco_quat,
    to_mujoco_vec,
    to_unity_quat,
    to_unity_vec,
)


def rotate(q, v):
    """Rotate vector v by unit quaternion q = (w, x, y, z), Hamilton convention."""
    w, u = q[0], np.asarray(q[1:])
    t = 2 * np.cross(u, v)
    return v + w * t + np.cross(u, t)


def unity_to_wxyz(q):
    x, y, z, w = q
    return np.array([w, x, y, z])


class FramesTest(unittest.TestCase):
    def test_rotation_commutes_with_the_frame_change(self):
        rng = np.random.default_rng(7)
        for _ in range(200):
            q = rng.normal(size=4)
            q /= np.linalg.norm(q)
            v = rng.normal(size=3)
            expected = to_unity_vec(rotate(q, v))
            got = rotate(unity_to_wxyz(to_unity_quat(q)), to_unity_vec(v))
            np.testing.assert_allclose(got, expected, atol=1e-12)

    def test_up_axis(self):
        np.testing.assert_allclose(to_unity_vec([1.0, 2.0, 3.0]), [1.0, 3.0, 2.0])

    def test_round_trip(self):
        q = np.array([0.5, 0.5, -0.5, 0.5])
        np.testing.assert_allclose(to_mujoco_quat(to_unity_quat(q)), q)
        np.testing.assert_allclose(to_mujoco_vec(to_unity_vec([1.0, 2.0, 3.0])), [1.0, 2.0, 3.0])

    def test_matrix_to_quaternion_matches_mujoco(self):
        rng = np.random.default_rng(3)
        for _ in range(200):
            q = rng.normal(size=4)
            q /= np.linalg.norm(q)
            m = np.zeros(9)
            mujoco.mju_quat2Mat(m, q)
            got = mat_to_quat_xyzw(m.reshape(3, 3))
            expected = q if q[0] >= 0 else -q
            np.testing.assert_allclose(unity_to_wxyz(got), expected, atol=1e-9)

    def test_stage_rig_puts_the_stage_point_where_the_world_point_is(self):
        """The rig pose in Unity maps a left-handed stage point to the Unity
        position of the world point that the same (rotation, translation) gives."""
        rng = np.random.default_rng(11)
        for _ in range(200):
            axis_angle = rng.normal(size=3)
            rotation = np.zeros(9)
            quat = np.zeros(4)
            mujoco.mju_axisAngle2Quat(quat, axis_angle / np.linalg.norm(axis_angle), rng.uniform(-np.pi, np.pi))
            mujoco.mju_quat2Mat(rotation, quat)
            rotation = rotation.reshape(3, 3)
            translation = rng.normal(size=3)
            point = rng.normal(size=3)  # OpenXR stage frame, right-handed
            expected = to_unity_vec(rotation @ point + translation)

            position, rig_quat = stage_to_unity(rotation, translation)
            unity_point = point * [1.0, 1.0, -1.0]  # the same point as Unity's OpenXR plugin reports it
            got = rotate(unity_to_wxyz(rig_quat), unity_point) + position
            np.testing.assert_allclose(got, expected, atol=1e-9)

    def test_stage_without_yaw_is_a_plain_offset(self):
        quest_to_world = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
        position, quat = stage_to_unity(quest_to_world, [0.0, 0.25, 0.95])
        np.testing.assert_allclose(position, [0.0, 0.95, 0.25])
        np.testing.assert_allclose(quat, [0.0, 0.0, 0.0, 1.0])


class ManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = build_scene("right")
        cls.data = initial_state(cls.model)
        # Through JSON, as Unity reads it.
        cls.manifest = json.loads(to_json(build_manifest(cls.model, cls.data)))
        cls.bodies = {b["id"]: b for b in cls.manifest["bodies"]}

    def test_body_poses_match_mujoco(self):
        self.assertEqual(len(self.bodies), self.model.nbody)
        for i in range(self.model.nbody):
            body = self.bodies[self.model.body(i).name]
            np.testing.assert_allclose(to_mujoco_vec(body["position"]), self.data.xpos[i], atol=1e-4)
            q = to_mujoco_quat(body["rotation"])
            if np.dot(q, self.data.xquat[i]) < 0:
                q = -q  # q and -q are the same rotation
            np.testing.assert_allclose(q, self.data.xquat[i], atol=1e-4)

    def test_every_visual_geom_is_exported(self):
        expected = sum(1 for g in range(self.model.ngeom) if self.model.geom_group[g] in VISUAL_GROUPS)
        exported = sum(len(b["geoms"]) for b in self.manifest["bodies"])
        self.assertEqual(exported, expected)
        self.assertGreater(expected, 0)

    def test_objects_are_named_bodies(self):
        for name in ("ball", "cube", "can", "rh_palm"):
            self.assertIn(name, self.bodies)

    def test_triangles_index_their_own_vertices(self):
        for body in self.manifest["bodies"]:
            for geom in body["geoms"]:
                tris = np.array(geom["triangles"])
                self.assertEqual(len(tris) % 3, 0, geom["name"])
                self.assertEqual(len(geom["vertices"]) % 3, 0, geom["name"])
                self.assertGreater(len(tris), 0, geom["name"])
                self.assertLess(tris.max(), len(geom["vertices"]) // 3, geom["name"])
                self.assertGreaterEqual(tris.min(), 0, geom["name"])

    def test_cube_faces_point_outward_in_unity(self):
        (geom,) = self.bodies["cube"]["geoms"]
        verts = np.array(geom["vertices"]).reshape(-1, 3)
        tris = np.array(geom["triangles"]).reshape(-1, 3)
        centre = verts.mean(axis=0)
        for a, b, c in tris:
            normal = np.cross(verts[b] - verts[a], verts[c] - verts[a])
            outward = (verts[a] + verts[b] + verts[c]) / 3 - centre
            self.assertGreater(np.dot(normal, outward), 0)

    def test_cube_size_matches_mujoco(self):
        (geom,) = self.bodies["cube"]["geoms"]
        verts = np.array(geom["vertices"]).reshape(-1, 3)
        cube_geom = self.model.body("cube").geomadr[0]
        half = to_unity_vec(self.model.geom_size[cube_geom])
        np.testing.assert_allclose(verts.max(axis=0), half, atol=1e-5)
        np.testing.assert_allclose(verts.min(axis=0), -half, atol=1e-5)

    def test_plain_decimals_only(self):
        text = to_json(build_manifest(self.model, self.data))
        self.assertNotIn("e-", text)
        self.assertNotIn("NaN", text)


if __name__ == "__main__":
    unittest.main()
