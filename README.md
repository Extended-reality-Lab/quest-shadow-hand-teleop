# Robot arm and hand simulation (MuJoCo)

Lab research in Prof. Raffaele De Amicis's lab at Oregon State University. **Work in progress.**

## Goal

A MuJoCo simulation of a robot arm and hand that a person can drive in real time, as the base for:

- VR teleoperation: move a controller (Meta Quest) and the simulated arm copies the motion
- reinforcement learning and imitation learning on the same model

The input side is kept behind a small adapter, so the device (keyboard first, then a VR controller or another wearable) can change without touching the simulation. `TECHNOLOGY_RESEARCH.md` explains that design and why MuJoCo was chosen over Isaac Lab.

## Current state

What exists and runs today:

- **Hand model.** The Shadow Hand E3M5 (right and left) from [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie/tree/main/shadow_hand) is in `assets/shadow_hand/`. Each hand has 24 joints and 20 position actuators; the scene files add a free-floating object to manipulate. Both scenes load in MuJoCo 3.11.0.
- **`pendulum.py`.** A first control example: a single hinge joint driven by a position actuator whose target flips between +1 and -1 rad every two seconds, shown in the interactive viewer.
- **Quest hand stream.** A Meta Quest app streams the 26-joint hand skeleton of both hands over Wi-Fi (UDP, JSON, about 72 Hz) to a PC receiver. Tested live on 2026-10-20 with a Quest Pro.
- **Hand teleoperation in MuJoCo.** `teleop/run.py` turns the stream into Shadow Hand motion: inverse kinematics maps the human finger joints to robot joint targets, a mocap body moves the whole hand, and a safety filter keeps the hand above the table and limits its speed. The scene has a table, a ball, a cube and a can to grasp. Eight tests pass without a headset, including a scripted lift of the ball. Tested with the live headset on 2026-10-22.

Not done yet:

- Arm control (the hand currently floats on its own), learning.

`LESSONS.md` is the step-by-step plan, from loading a model to inverse kinematics and device input. Every lesson ends in a script that asserts a measured number rather than relying on what the viewer shows.

The repository started as a drone simulator (a Skydio X2 quadrotor model). That work stopped in October 2026 and is kept in `archive/drone/` for reference; nothing outside the archive uses it.

## Structure

```
assets/shadow_hand/      Shadow Hand MJCF model, meshes, scenes, keyframes (Apache 2.0)
pendulum.py              position-actuator example in the viewer
requirements.txt         pinned Python dependencies (mujoco==3.11.0)
setup.sh / setup.ps1     create .venv with Python 3.12 and install requirements
LESSONS.md               plan to the first milestone: the arm reaches a target under my control
LOG.md                   work log
TECHNOLOGY_RESEARCH.md   simulator choice and the device-adapter architecture
quest_app/               Meta Quest app (Godot 4) that streams the hand skeleton over Wi-Fi
pc_receiver/             PC receiver for that stream (Python standard library only)
teleop/                  Quest hand -> Shadow Hand in MuJoCo, with objects to grasp
docs/hand-stream/        stream protocol and setup guide
archive/drone/           earlier drone simulation work, not used
```

## Setup

Python 3.12 is required. The setup scripts create `.venv` and install `requirements.txt`.

macOS or Linux (`brew install python@3.12` on macOS if needed):

```bash
./setup.sh
```

Windows:

```powershell
.\setup.ps1
```

## Run

Open the Shadow Hand scene in the MuJoCo viewer:

```bash
.venv/bin/python -m mujoco.viewer --mjcf="$PWD/assets/shadow_hand/scene_right.xml"
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m mujoco.viewer --mjcf="$PWD\assets\shadow_hand\scene_right.xml"
```

Run the pendulum example:

```bash
.venv/bin/python pendulum.py       # Linux
.venv/bin/mjpython pendulum.py     # macOS
.\.venv\Scripts\python.exe pendulum.py   # Windows
```

On macOS, any script that opens the viewer with `launch_passive` must run under `mjpython`: the OS requires the GUI loop to own the main thread, and plain `python` raises a `RuntimeError`.

## Quest hand stream and teleoperation

```
Quest app  --UDP, port 9000-->  PC
                                 |- pc_receiver/receiver.py   shows left/right and tracking state
                                 '- teleop/run.py             drives the Shadow Hand in MuJoCo
```

Run one of the two at a time: both listen on port 9000.

- [docs/hand-stream/PROTOCOL.md](docs/hand-stream/PROTOCOL.md): data format
- [docs/hand-stream/SETUP.md](docs/hand-stream/SETUP.md): headset setup, network, demo checklist
- [docs/hand-stream/TELEOP.md](docs/hand-stream/TELEOP.md): how the teleoperation works and how to run it

Drive the hand in MuJoCo (stop `receiver.py` first):

```bash
.venv/bin/mjpython teleop/run.py              # macOS
.\.venv\Scripts\python.exe teleop\run.py      # Windows
```

Hold your right hand forward, palm down; press Enter in the viewer to re-centre. `--hand left` for the left hand.

Without a headset, the fake sender plays a hand that opens and closes:

```bash
python3 pc_receiver/fake_sender.py --host 127.0.0.1 --port 9000
```

Send it to `receiver.py` to check the receiver, or to `teleop/run.py` to see the robot hand move. Tests: `.venv/bin/python -m unittest discover -s teleop -v`.

Network: the headset and the PC must reach each other over UDP. Some campus Wi-Fi networks block traffic between devices; SETUP.md lists the options (a phone hotspot, or the PC-over-Link fallback).

## Roadmap

Each step is an issue; the [project board](../../projects) shows its status.

Done:

- [x] Stream the Quest hand skeleton to a PC over Wi-Fi (#5)
- [x] Drive the Shadow Hand in MuJoCo from the Quest hand (#6)

In progress:

- [ ] Run the teleoperation on the lab Windows PC (#7)

Planned:

- [ ] Grasp objects with the live headset and tune the hand (#8)
- [ ] Record a demo video (#9)
- [ ] Mount the hand on a robot arm (#10)
- [ ] Record teleoperation demonstrations for learning (#11)
- [ ] Imitation learning baseline (#12)

## Credits

The Shadow Hand model was provided by [Shadow Robot Company](https://www.shadowrobot.com/) under the Apache 2.0 License and packaged as MJCF in MuJoCo Menagerie. See `assets/shadow_hand/README.md` and `assets/shadow_hand/LICENSE`.
