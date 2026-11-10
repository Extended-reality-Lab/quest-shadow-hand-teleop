"""Write scene/scene_manifest.json: the teleop scene as Unity needs it.

    python scene/export_manifest.py        (from the repo root, any OS)

The scene comes from teleop/run.py build_scene("right"), the same function the
simulator uses, so Unity never keeps its own copy of the geometry. The hand
starts at HOME, as in the simulator. Every visual geom (groups 0-2, what the
MuJoCo viewer shows) becomes a triangle mesh. All values are in Unity's frame
(see frames.py). Unity reads the file with JsonUtility, so the format has no
dictionaries and no nested arrays: vectors and meshes are flat number lists.
"""
import argparse
import json
import os
import re
import sys

import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "teleop"))

from frames import to_unity_quat, to_unity_triangles, to_unity_vec
from run import (  # teleop/run.py, on the path above  # pyright: ignore[reportMissingImports]
    TABLE_TOP,
    Teleop,
    build_scene,
    place_hand_at_home,
)

MANIFEST = os.path.join(HERE, "scene_manifest.json")
VERSION = 1
HAND = "right"
VISUAL_GROUPS = (0, 1, 2)  # the groups the MuJoCo viewer draws by default
DECIMALS = 5  # 0.01 mm
SEGMENTS = 24  # around round primitives
RINGS = 12  # pole to pole on spheres and capsules
PLANE_HALF_SIZE = 5.0  # m, for planes MuJoCo draws as infinite (size 0)
DEFAULT_RGBA = (0.5, 0.5, 0.5, 1.0)  # MuJoCo's geom colour when none is given
# The first view of the viewer in teleop/run.py main(), so screenshots match:
# from behind the hand, on the operator's side of the table.
CAMERA_LOOKAT = (0.0, 0.45, TABLE_TOP)
CAMERA_DISTANCE, CAMERA_AZIMUTH, CAMERA_ELEVATION = 1.1, 90.0, -30.0  # m, deg, deg


def initial_state(model):
    """Simulation data with the hand at HOME, after mj_forward."""
    data = mujoco.MjData(model)
    place_hand_at_home(model, data, Teleop(model, HAND), HAND)
    return data


def is_visual(model, geom):
    return int(model.geom_group[geom]) in VISUAL_GROUPS


# Primitive meshes in the geom frame, MuJoCo axes, triangles counter-clockwise
# seen from outside (the MuJoCo/OpenGL front face).


def combine(parts):
    verts, tris, offset = [], [], 0
    for v, t in parts:
        verts.append(v)
        tris.append(t + offset)
        offset += len(v)
    return np.concatenate(verts), np.concatenate(tris)


def drop_degenerate(verts, tris):
    """Remove zero-area triangles (the ones that touch a pole)."""
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    keep = np.linalg.norm(np.cross(b - a, c - a), axis=1) > 1e-12
    return verts, tris[keep]


def lathe(rings):
    """Surface of revolution about +Z. `rings` = (z, radius) from top to bottom."""
    phi = np.linspace(0.0, 2 * np.pi, SEGMENTS + 1)
    verts = np.array([(r * np.cos(a), r * np.sin(a), z) for z, r in rings for a in phi])
    n = SEGMENTS + 1
    tris = []
    for i in range(len(rings) - 1):
        for j in range(SEGMENTS):
            a, b, c, d = i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1
            tris += [(a, b, c), (a, c, d)]
    return drop_degenerate(verts, np.array(tris))


def disk(z, radius, up):
    phi = np.linspace(0.0, 2 * np.pi, SEGMENTS + 1)
    verts = np.array([(0.0, 0.0, z)] + [(radius * np.cos(a), radius * np.sin(a), z) for a in phi])
    if up:
        tris = [(0, j + 1, j + 2) for j in range(SEGMENTS)]
    else:
        tris = [(0, j + 2, j + 1) for j in range(SEGMENTS)]
    return verts, np.array(tris)


def box_mesh(size):
    """Box with half sizes `size`; four vertices per face so edges stay sharp."""
    verts, tris = [], []
    for axis in range(3):
        for sign in (1.0, -1.0):
            u, v = (axis + 1) % 3, (axis + 2) % 3
            if sign < 0:
                u, v = v, u  # keeps u x v pointing out of the face
            base = len(verts)
            for cu, cv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                p = np.zeros(3)
                p[axis], p[u], p[v] = sign * size[axis], cu * size[u], cv * size[v]
                verts.append(p)
            tris += [(base, base + 1, base + 2), (base, base + 2, base + 3)]
    return np.array(verts), np.array(tris)


def sphere_mesh(radii):
    theta = np.linspace(0.0, np.pi, RINGS + 1)
    verts, tris = lathe([(np.cos(t), np.sin(t)) for t in theta])
    return verts * np.asarray(radii, dtype=float), tris


def capsule_mesh(radius, half_length):
    top = np.linspace(0.0, np.pi / 2, RINGS // 2 + 1)
    bottom = np.linspace(np.pi / 2, np.pi, RINGS // 2 + 1)
    rings = [(half_length + radius * np.cos(t), radius * np.sin(t)) for t in top]
    rings += [(-half_length + radius * np.cos(t), radius * np.sin(t)) for t in bottom]
    return lathe(rings)


def cylinder_mesh(radius, half_length):
    side = lathe([(half_length, radius), (-half_length, radius)])
    return combine([side, disk(half_length, radius, up=True), disk(-half_length, radius, up=False)])


def plane_mesh(size):
    a = size[0] if size[0] > 0 else PLANE_HALF_SIZE
    b = size[1] if size[1] > 0 else PLANE_HALF_SIZE
    verts = np.array([(-a, -b, 0.0), (a, -b, 0.0), (a, b, 0.0), (-a, b, 0.0)])
    return verts, np.array([(0, 1, 2), (0, 2, 3)])


def geom_mesh(model, geom):
    """Vertices (n, 3) and triangles (m, 3) of a geom, in its own MuJoCo frame."""
    gtype, size = int(model.geom_type[geom]), model.geom_size[geom]
    g = mujoco.mjtGeom
    if gtype == g.mjGEOM_MESH:
        mesh = model.geom_dataid[geom]
        v0, nv = model.mesh_vertadr[mesh], model.mesh_vertnum[mesh]
        f0, nf = model.mesh_faceadr[mesh], model.mesh_facenum[mesh]
        return model.mesh_vert[v0 : v0 + nv].astype(float), model.mesh_face[f0 : f0 + nf].astype(int)
    if gtype == g.mjGEOM_BOX:
        return box_mesh(size)
    if gtype == g.mjGEOM_SPHERE:
        return sphere_mesh([size[0]] * 3)
    if gtype == g.mjGEOM_ELLIPSOID:
        return sphere_mesh(size)
    if gtype == g.mjGEOM_CAPSULE:
        return capsule_mesh(size[0], size[1])
    if gtype == g.mjGEOM_CYLINDER:
        return cylinder_mesh(size[0], size[1])
    if gtype == g.mjGEOM_PLANE:
        return plane_mesh(size)
    raise ValueError(f"geom {geom}: type {mujoco.mjtGeom(gtype).name} is not supported")


def geom_rgba(model, geom):
    """The colour MuJoCo draws: the material's unless the geom sets its own."""
    material = model.geom_matid[geom]
    rgba = model.geom_rgba[geom]
    if material >= 0 and np.allclose(rgba, DEFAULT_RGBA):
        return model.mat_rgba[material]
    return rgba


def flat(values):
    return np.round(np.asarray(values, dtype=float), DECIMALS).ravel().tolist()


def camera(model):
    """Position and target of the viewer's first view, in Unity's frame."""
    az, el = np.radians(CAMERA_AZIMUTH), np.radians(CAMERA_ELEVATION)
    forward = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    position = np.array(CAMERA_LOOKAT) - CAMERA_DISTANCE * forward
    return {
        "position": flat(to_unity_vec(position)),
        "look_at": flat(to_unity_vec(CAMERA_LOOKAT)),
        "fov_deg": float(model.vis.global_.fovy),  # vertical, like Unity's fieldOfView
    }


def build_manifest(model, data):
    bodies = []
    for body in range(model.nbody):
        geoms = []
        first = model.body_geomadr[body]
        for geom in range(first, first + model.body_geomnum[body]) if first >= 0 else []:
            if not is_visual(model, geom):
                continue
            verts, tris = geom_mesh(model, geom)
            geoms.append({
                "name": model.geom(geom).name or f"{model.body(body).name}/geom{geom}",
                "type": mujoco.mjtGeom(int(model.geom_type[geom])).name.removeprefix("mjGEOM_").lower(),
                "position": flat(to_unity_vec(model.geom_pos[geom])),
                "rotation": flat(to_unity_quat(model.geom_quat[geom])),
                "rgba": flat(geom_rgba(model, geom)),
                "vertices": flat(to_unity_vec(verts)),
                "triangles": to_unity_triangles(tris).ravel().tolist(),
            })
        bodies.append({
            "id": model.body(body).name,
            "position": flat(to_unity_vec(data.xpos[body])),
            "rotation": flat(to_unity_quat(data.xquat[body])),
            "geoms": geoms,
        })
    return {
        "version": VERSION,
        "frame": "unity_y_up_left_handed",
        "units": "m",
        "source": f'teleop/run.py build_scene("{HAND}"), hand at HOME',
        "camera": camera(model),
        "bodies": bodies,
    }


def to_json(manifest):
    """Compact JSON with plain decimals only (no 1e-05), for any JSON reader."""
    text = json.dumps(manifest, separators=(",", ":"))
    return re.sub(r"(?<![\w.])-?\d+(?:\.\d+)?e-\d+", lambda m: f"{float(m.group()):.{DECIMALS}f}", text)


def main():
    parser = argparse.ArgumentParser(description="Write the scene manifest for Unity.")
    parser.add_argument("--out", default=MANIFEST, help=f"output file (default {MANIFEST})")
    args = parser.parse_args()

    model = build_scene(HAND)
    manifest = build_manifest(model, initial_state(model))
    text = to_json(manifest)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")

    geoms = [g for b in manifest["bodies"] for g in b["geoms"]]
    verts = sum(len(g["vertices"]) // 3 for g in geoms)
    tris = sum(len(g["triangles"]) // 3 for g in geoms)
    print(f"{args.out}: {len(manifest['bodies'])} bodies, {len(geoms)} geoms, "
          f"{verts} vertices, {tris} triangles, {len(text) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
