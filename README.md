# drone-sim

Autonomous drone simulator built on MuJoCo, using the Skydio X2 airframe from
MuJoCo Menagerie. Course project for Prof. Raffaele De Amicis, Oregon State.

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirments.txt
```

Main dependency is `mujoco==3.11.0`. Python 3.12.

## Running it

```bash
.venv/bin/python probe.py
```

Loads the scene and prints the model's key numbers — degrees of freedom,
actuator count, total mass, timestep. Then drops the drone from 5 m and steps
the physics 1000 times, printing altitude every 100 steps. This is the quickest
way to confirm the model is intact.

Expected output starts like this:

```
qpos length: 7
actuators:   4
total mass:  1.325 kg
timestep:    0.01 s
```

```bash
.venv/bin/mjpython view.py
```

Same scene in an interactive viewer window. You can orbit the camera and watch
the drone.

On macOS the viewer must be launched with `mjpython`, not `python` — the OS
requires the GUI event loop to own the main thread. Running it under plain
`python` raises a RuntimeError from `launch_passive` telling you to use
`mjpython`. Headless scripts like `probe.py` are unaffected.

## What's in here

| Path | What it is |
|---|---|
| `assets/x2/x2.xml` | The Skydio X2 airframe. Stock Menagerie file, unmodified |
| `assets/x2/scene.xml` | Wraps the airframe — sky, ground plane, lighting |
| `probe.py` | Headless check: model stats + a drop test |
| `view.py` | The same scene in the MuJoCo viewer (run with `mjpython`) |
| `drill.py`, `basics.py` | Early Python/NumPy exercises. Not part of the sim |

## The model

Skydio X2, 1.325 kg, four thrust motors, physics at 100 Hz (timestep 0.01 s).

MuJoCo derives the inertial properties from the geometry rather than reading
them from an `<inertial>` block — there isn't one in the file. Worth knowing:

- Centre of mass sits **5.4 cm above the body origin**, so the position in
  `qpos[0:3]` is not the COM.
- The inertia tensor has a real off-diagonal term, because the front rotors are
  mounted 3 cm higher than the rear ones. The airframe isn't symmetric about its
  own XY plane.

## Current status

The model loads and simulates correctly. **There is no controller yet** — both
scripts leave `data.ctrl` at zero, so the drone falls. That's expected at this
stage, not a bug.

The model already ships a hover keyframe (`x2.xml`, line 69) with the thrust
values for a stable hover. Wiring that up is the next step.

Not built yet: controller, trajectory following, multi-drone scene, the
WebSocket pose stream, the CesiumJS front-end.

## Notes and planning

Longer working documents live alongside this file:

- `PLAN.md` — work plan for the environment/terrain task, broken into steps
- `LEARNING.md` — the concepts behind each step, with references
- `RISKS.md` — things that would be expensive to discover late
- `REPRO.md` — how performance numbers should be measured
- `DEFENSE.md` — current claims and what evidence backs each one

## Quest hand stream

A Meta Quest app (`quest_app/`, Godot 4) streams the hand-tracking skeleton
over Wi-Fi to a PC receiver (`pc_receiver/`, Python standard library only).

- [docs/hand-stream/PROTOCOL.md](docs/hand-stream/PROTOCOL.md): data format
- [docs/hand-stream/SETUP.md](docs/hand-stream/SETUP.md): setup, running, demo checklist

Quick test without a headset: `python3 pc_receiver/receiver.py --port 9000 --bind 127.0.0.1`,
then `python3 pc_receiver/fake_sender.py --host 127.0.0.1 --port 9000`.
