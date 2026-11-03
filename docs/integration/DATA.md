# Shared data structures

Issue #22. The formats exchanged by the Quest app, the MuJoCo server and the
Unity viewer. The architecture and the frame conversions are in
[ARCHITECTURE.md](ARCHITECTURE.md). Anything marked **proposed** is a
suggestion for the issue named next to it, not built yet.

## Conventions

- Units: metres, radians (degrees only in `fov_deg`), seconds unless the name
  says otherwise (`t_us` is microseconds).
- Frames: `openxr` = OpenXR stage (Y up, right-handed), `unity` = Unity world
  (Y up, left-handed). Joint angles are frame-free. MuJoCo-frame values never
  leave the server.
- Quaternions are unit quaternions with **w last** in every message, because
  both OpenXR and Unity use `(x, y, z, w)`.
- JSON is UTF-8 and compact. Unity reads it with `JsonUtility`, so the
  formats Unity reads have no dictionaries and no nested arrays: vectors are
  flat number lists and keyed data is a list of objects with an `id`.

## Object identity

An object's id is its MuJoCo body name, the same in every message and in
Unity's GameObject names:

- objects: `ball`, `cube`, `can`;
- hand bodies: `rh_forearm`, `rh_wrist`, `rh_palm`, then per finger, e.g.
  `rh_ffknuckle`, `rh_ffproximal`, `rh_ffmiddle`, `rh_ffdistal` (`ff`, `mf`,
  `rf`, `lf` with `rh_lfmetacarpal`, and thumb `rh_thbase` … `rh_thdistal`);
  the left hand uses the prefix `lh_`;
- others: `world` (floor plane and table) and `hand_target` (the mocap
  marker the server moves).

Hand joints use the Shadow Hand names: `rh_WRJ2`, `rh_WRJ1`, `rh_FFJ4` …
`rh_FFJ1`, `rh_MFJ4` … `rh_MFJ1`, `rh_RFJ4` … `rh_RFJ1`, `rh_LFJ5` …
`rh_LFJ1`, `rh_THJ5` … `rh_THJ1`: 24 hinge joints, in this order (the MuJoCo
model order).

## 1. Hand message (Quest → MuJoCo)

The full contract is [PROTOCOL.md](../hand-stream/PROTOCOL.md); this table is
a summary. UDP, port 9000, one datagram per hand per rendered frame, at most
8 KB.

| Field | Type | Unit | Frame | Meaning |
|---|---|---|---|---|
| `v` | int | — | — | format version, `1` |
| `seq` | int ≥ 0 | — | — | +1 per datagram, shared by both hands; a jump means loss, a smaller value means the app restarted |
| `t_us` | int ≥ 0 | µs | headset clock | headset monotonic time since the app started; not wall time |
| `hand` | string | — | — | `left` or `right` |
| `tracked` | bool | — | — | `true` only when every joint has a valid position and orientation from real hand tracking |
| `source` | string | — | — | `optical`, `controller` or `unknown` |
| `joints` | list of 26 × `[px, py, pz, qx, qy, qz, qw]` | m, unit quaternion | `openxr` | OpenXR joint order (index 0 palm, 1 wrist, …, 25 little tip); empty when `tracked` is `false` |

The wrist pose the task asks for is joint 1 (`wrist`), position and
orientation.

### Tracking status and confidence

OpenXR gives no numeric confidence value for hand tracking. What it gives,
and what we send, is:

- `tracked` and `source` per hand (in v1);
- per-joint flags, planned for v1.1 (planned, #24):

| Field | Type | Unit | Frame | Meaning |
|---|---|---|---|---|
| `joint_flags` | list of 26 ints | bit field | — | per joint, in the `joints` order: Godot `XRHandTracker.get_hand_joint_flags()` masked to 4 bits. 1 orientation valid, 2 orientation tracked, 4 position valid, 8 position tracked (Godot `HandJointFlags`, the OpenXR location flags). "Valid but not tracked" means the runtime inferred the joint. Sent also when `tracked` is `false`. |

The v1 receiver rejects any `v` other than `1` and ignores fields it does not
know. So v1.1 keeps `v: 1` and only adds the optional `joint_flags` field: old
receivers keep working, new ones read the flags when present.

The server reports one tracking status per hand to Unity (section 3):
`tracked`, `lost_tracking` (datagrams arrive with `tracked: false`) or
`no_packets` (no datagram for 0.5 s). These are the receiver states of
PROTOCOL.md.

## 2. Scene manifest (MuJoCo → Unity, file)

`scene/scene_manifest.json`, written by
[`scene/export_manifest.py`](../../scene/export_manifest.py) from
`build_scene("right")` after `mj_forward`, with the hand at `HOME`.
Regenerate with `python scene/export_manifest.py`. Unity reads it once at
start and builds one GameObject per body and one mesh per visual geom.
Every pose and vertex is already in the `unity` frame; the conversion is in
[`scene/frames.py`](../../scene/frames.py).

| Field | Type | Unit | Frame | Meaning |
|---|---|---|---|---|
| `version` | int | — | — | `1` |
| `frame` | string | — | — | `unity_y_up_left_handed` |
| `units` | string | — | — | `m` |
| `source` | string | — | — | which scene was exported |
| `camera.position` | float[3] | m | `unity` world | camera position matching the MuJoCo viewer's first view |
| `camera.look_at` | float[3] | m | `unity` world | point the camera looks at |
| `camera.fov_deg` | float | deg | — | vertical field of view, like Unity's `Camera.fieldOfView` |
| `bodies[].id` | string | — | — | MuJoCo body name, the object id |
| `bodies[].position` | float[3] | m | `unity` world | body origin |
| `bodies[].rotation` | float[4] (x, y, z, w) | — | `unity` world | body orientation |
| `bodies[].geoms[].name` | string | — | — | MuJoCo geom name, or `<body>/geom<index>` when the geom has none |
| `bodies[].geoms[].type` | string | — | — | `plane`, `sphere`, `capsule`, `ellipsoid`, `cylinder`, `box` or `mesh` |
| `bodies[].geoms[].position` | float[3] | m | `unity`, body-local | geom position in its body |
| `bodies[].geoms[].rotation` | float[4] (x, y, z, w) | — | `unity`, body-local | geom orientation in its body |
| `bodies[].geoms[].rgba` | float[4] | 0-1 | — | the colour MuJoCo draws: the material's, unless the geom sets its own |
| `bodies[].geoms[].vertices` | float[3n] | m | `unity`, geom-local | flat `x, y, z` list |
| `bodies[].geoms[].triangles` | int[3m] | — | — | vertex indices; for every triangle `(a, b, c)`, `cross(b − a, c − a)` points out of the surface, which is the front face in Unity |

Rules of the exporter:

- Only visual geoms are exported: groups 0-2, what the MuJoCo viewer draws by
  default. Collision geoms (group 3) are skipped.
- Primitives are turned into triangle meshes in Python (24 segments around,
  12 rings from pole to pole); a plane MuJoCo draws as infinite becomes a 10 m
  square.
- Numbers are rounded to 5 decimals (0.01 mm) and never use exponent
  notation.
- Today: 30 bodies, 30 geoms, 43,424 vertices, 58,914 triangles, 1.88 MB.

## 3. Simulation state (MuJoCo → Unity)

Built in #27 and documented in full in `STATE_STREAM.md` there; this is the
draft it starts from. One UDP datagram per message, UTF-8 JSON, 60 Hz, to
`127.0.0.1` port 9001 (port proposed) when Unity runs on the same PC. A
message is about 4 KB and must stay under 8 KB, the same limit as the hand
stream. Hand body poses are sent as world poses, so Unity needs no
kinematics; the joint values are there for logging and checks.

| Field | Type | Unit | Frame | Meaning |
|---|---|---|---|---|
| `v` | int | — | — | format version, `1` |
| `seq` | int ≥ 0 | — | — | +1 per message; a smaller value means the server restarted |
| `sim_time` | float | s | — | MuJoCo `data.time` |
| `send_time` | float | s | server wall clock | Unix time when the server sent the message; not synchronised with other machines |
| `hand` | string | — | — | `left` or `right` (proposed) |
| `tracking` | string | — | — | `tracked`, `lost_tracking` or `no_packets` (section 1) |
| `hand_seq` | int | — | — | `seq` of the last hand datagram the server used (proposed) |
| `hand_root.p` | float[3] | m | `unity` world | `rh_forearm` position, the root of the hand chain |
| `hand_root.q` | float[4] (x, y, z, w) | — | `unity` world | `rh_forearm` orientation |
| `joint_names` | string[24] | — | — | joint order of `joints` (proposed; could move to the manifest) |
| `joints` | float[24] | rad | — | hand joint angles (`qpos`) |
| `bodies[]` | list of `{id, p, q}` | m; (x, y, z, w) | `unity` world | world pose of every hand body (`rh_*` or `lh_*`, plus `hand_target`) |
| `objects[].id` | string | — | — | `ball`, `cube`, `can` |
| `objects[].p` | float[3] | m | `unity` world | object position |
| `objects[].q` | float[4] (x, y, z, w) | — | `unity` world | object orientation |
| `objects[].grasp` | string | — | — | `free`, `touching` or `grasped` (#26); `free` until #26 lands |
| `objects[].fingers` | string[] | — | — | fingers in contact: subset of `th`, `ff`, `mf`, `rf`, `lf` (#26; names proposed) |
| `objects[].contacts` | int | — | — | number of hand-object contacts (#26) |

Example, shortened (a real message has 25 hand bodies and 24 joints):

```json
{"v":1,"seq":1801,"sim_time":30.016,"send_time":1793740000.512,"hand":"right",
 "tracking":"tracked","hand_seq":5123,
 "hand_root":{"p":[0.0,0.95,0.05],"q":[0.0,0.0,0.0,1.0]},
 "joint_names":["rh_WRJ2","rh_WRJ1","..."],"joints":[0.0,0.1,"..."],
 "bodies":[{"id":"rh_palm","p":[0.0,0.95,0.25],"q":[0.0,0.0,0.0,1.0]}],
 "objects":[{"id":"ball","p":[-0.12,0.785,0.45],"q":[0.0,0.0,0.0,1.0],
             "grasp":"grasped","fingers":["th","ff","mf"],"contacts":5}]}
```

### Grasp rule (draft, #26 owns the final rule)

Per object, every physics step:

- `touching`: at least one contact between a hand geom and the object.
- `grasped`: the thumb and at least one other finger touch the object, and
  the object is off the table: no contact with the table, and its lowest
  point is at least 5 mm above the table top (5 mm proposed).
- `free`: otherwise.

### What Unity does with it (#29)

- Receive on a background thread; parse with `JsonUtility`.
- Keep the newest few messages ordered by `seq`; drop anything older than the
  newest. A `seq` much smaller than the last one means a server restart:
  clear the buffer.
- Render a fixed delay behind the newest message (proposed 50 ms) and
  interpolate positions linearly and rotations with slerp.
- Apply poses by `id` to the GameObjects built from the manifest. Show
  `grasp`, `tracking` and connection loss (no message for 0.5 s, proposed).
