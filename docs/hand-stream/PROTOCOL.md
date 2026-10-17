# Hand stream protocol, version 1

This document is the contract between the Quest app (`quest_app/`) and the PC
receiver (`pc_receiver/`). Both must match it. If the format changes, change
this file first and bump `v`.

## Transport

- UDP, one datagram per hand per frame (two datagrams per rendered frame).
- Each datagram is one UTF-8 JSON object, no trailing newline.
- Default destination: broadcast `255.255.255.255:9000`. The address and port
  can be changed on the headset without rebuilding (see `SETUP.md`).
- A datagram is about 2 KB and is always under 8 KB. The receiver rejects
  anything larger.
- UDP gives no delivery guarantee. Lost datagrams are detected with `seq`.

## Fields

| Field     | Type            | Meaning |
|-----------|-----------------|---------|
| `v`       | integer         | Format version. Always `1`. |
| `seq`     | integer ≥ 0     | Counter in the app. Increases by 1 for every datagram sent; both hands share it. A jump of more than 1 means datagrams were lost. A smaller value means the app restarted. |
| `t_us`    | integer ≥ 0     | Headset monotonic time in microseconds since the app started (Godot `Time.get_ticks_usec()`). Not wall-clock time. The receiver logs its own receive time next to it. |
| `hand`    | string          | `"left"` or `"right"`. |
| `tracked` | boolean         | `true` only when the runtime has current tracking data for this hand, **every** joint has a valid position and orientation, and the data is not emulated from a held controller. Controller-emulated data counts as `false`. |
| `source`  | string          | `"optical"`, `"controller"` or `"unknown"`, as the runtime reports it (Godot `XRHandTracker.hand_tracking_source`: `UNOBSTRUCTED` → `"optical"`, `CONTROLLER` → `"controller"`, anything else → `"unknown"`). A runtime without the `XR_EXT_hand_tracking_data_source` extension may report `"unknown"` for real optical tracking, so `tracked` does not require `"optical"`. |
| `joints`  | list            | 26 entries when `tracked` is `true`; an empty list when `tracked` is `false`. |

The app keeps sending datagrams with `tracked: false` while a hand is not
visible. This lets the PC tell **tracking loss** (packets arrive, hand not
tracked) from **connection loss** (no packets at all).

## Joints

Each entry is `[px, py, pz, qx, qy, qz, qw]`:

- `px, py, pz`: joint position in metres.
- `qx, qy, qz, qw`: joint orientation as a unit quaternion, **w last**, with
  `qw >= 0` (q and −q are the same rotation; the app picks the sign so that
  consecutive samples are comparable).
- Every number is rounded to 4 decimals (0.1 mm for positions). After rounding
  a quaternion's norm can differ from 1 by about 1e-4; normalise before strict
  use.
- NaN and Infinity are never sent; the receiver rejects them.

The order is the OpenXR `XR_EXT_hand_tracking` joint order. It is identical to
Godot's `XRHandTracker.HandJoint` enum, so the app sends joint `i` as enum
value `i`.

| Index | Name                 | Godot enum value                          |
|------:|----------------------|-------------------------------------------|
| 0     | palm                 | `HAND_JOINT_PALM`                         |
| 1     | wrist                | `HAND_JOINT_WRIST`                        |
| 2     | thumb_metacarpal     | `HAND_JOINT_THUMB_METACARPAL`             |
| 3     | thumb_proximal       | `HAND_JOINT_THUMB_PHALANX_PROXIMAL`       |
| 4     | thumb_distal         | `HAND_JOINT_THUMB_PHALANX_DISTAL`         |
| 5     | thumb_tip            | `HAND_JOINT_THUMB_TIP`                    |
| 6     | index_metacarpal     | `HAND_JOINT_INDEX_FINGER_METACARPAL`      |
| 7     | index_proximal       | `HAND_JOINT_INDEX_FINGER_PHALANX_PROXIMAL`     |
| 8     | index_intermediate   | `HAND_JOINT_INDEX_FINGER_PHALANX_INTERMEDIATE` |
| 9     | index_distal         | `HAND_JOINT_INDEX_FINGER_PHALANX_DISTAL`  |
| 10    | index_tip            | `HAND_JOINT_INDEX_FINGER_TIP`             |
| 11    | middle_metacarpal    | `HAND_JOINT_MIDDLE_FINGER_METACARPAL`     |
| 12    | middle_proximal      | `HAND_JOINT_MIDDLE_FINGER_PHALANX_PROXIMAL`     |
| 13    | middle_intermediate  | `HAND_JOINT_MIDDLE_FINGER_PHALANX_INTERMEDIATE` |
| 14    | middle_distal        | `HAND_JOINT_MIDDLE_FINGER_PHALANX_DISTAL` |
| 15    | middle_tip           | `HAND_JOINT_MIDDLE_FINGER_TIP`            |
| 16    | ring_metacarpal      | `HAND_JOINT_RING_FINGER_METACARPAL`       |
| 17    | ring_proximal        | `HAND_JOINT_RING_FINGER_PHALANX_PROXIMAL` |
| 18    | ring_intermediate    | `HAND_JOINT_RING_FINGER_PHALANX_INTERMEDIATE` |
| 19    | ring_distal          | `HAND_JOINT_RING_FINGER_PHALANX_DISTAL`   |
| 20    | ring_tip             | `HAND_JOINT_RING_FINGER_TIP`              |
| 21    | little_metacarpal    | `HAND_JOINT_PINKY_FINGER_METACARPAL`      |
| 22    | little_proximal      | `HAND_JOINT_PINKY_FINGER_PHALANX_PROXIMAL` |
| 23    | little_intermediate  | `HAND_JOINT_PINKY_FINGER_PHALANX_INTERMEDIATE` |
| 24    | little_distal        | `HAND_JOINT_PINKY_FINGER_PHALANX_DISTAL`  |
| 25    | little_tip           | `HAND_JOINT_PINKY_FINGER_TIP`             |

The same list lives in code as `JOINT_NAMES` in `pc_receiver/protocol.py`.

## Coordinate frame

- Godot XR tracking space, which follows the OpenXR convention:
  right-handed, **+X right, +Y up, −Z forward**.
- Positions are relative to the `XROrigin3D` node, which sits at the origin of
  the OpenXR reference space the app requests.
- The app requests the **stage** reference space
  (`xr/openxr/reference_space = Stage` in `quest_app/project.godot`). On Quest
  its origin is on the floor, at the centre of the guardian boundary; with a
  stationary boundary that is roughly under the spot where the headset started.
  +Y is therefore height above the floor.
- `XROrigin3D` is not moved or scaled and the world scale is 1.0, so one unit
  is one metre.
- Joint orientation: in the OpenXR hand model each joint's −Z axis points along
  the bone towards the fingertip, +Y points out of the back of the hand.

### Note for the MuJoCo milestone (not implemented yet)

MuJoCo uses a Z-up frame and quaternions with **w first** (`[w, x, y, z]`).
The later PC-side conversion has to (1) rotate Y-up into Z-up, for example
`(x, y, z)_mujoco = (x, -z, y)_openxr`, applying the same rotation to the
orientations, and (2) reorder quaternions from `[x, y, z, w]` to `[w, x, y, z]`.

## Timestamps

- `t_us` is the headset clock: use it for the time between samples of the
  same session (velocity, jitter).
- The receiver adds `rx_time` (PC Unix time in seconds, float) to every logged
  line. The two clocks are not synchronised.

## Examples

Tracked hand (joint list shortened here; a real datagram has 26 entries):

```json
{"v":1,"seq":1234,"t_us":52341234,"hand":"left","tracked":true,"source":"optical",
 "joints":[[0.0123,1.0456,-0.321,0.0,0.0,0.0,1.0],[0.0101,1.0302,-0.2755,0.0123,-0.0042,0.0021,0.9999], "..."]}
```

Hand not tracked:

```json
{"v":1,"seq":1235,"t_us":52341250,"hand":"right","tracked":false,"source":"unknown","joints":[]}
```

## Receiver states

For each hand the receiver shows one of:

- `TRACKED`: the latest datagram for this hand has `tracked: true`.
- `LOST (tracking)`: datagrams arrive but the latest one has `tracked: false`.
- `LOST (no packets)`: no datagram for this hand within the timeout
  (default 0.5 s). Covers an app crash, a sleeping headset or a network drop.
