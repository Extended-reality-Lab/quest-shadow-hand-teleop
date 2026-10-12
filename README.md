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

Not built yet: arm control, inverse kinematics, device input, VR, learning. The plan for these is in `LESSONS.md`, a sequence of lessons from loading a model to reaching a target point with inverse kinematics and driving it from an input device. Every lesson ends in a script that asserts a measured number rather than relying on what the viewer shows.

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
archive/drone/           earlier drone simulation work, not used
CLAUDE.md, .claude/      instructions for the AI assistant, which reviews and explains rather than writes the code
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

Run the pendulum example:

```bash
.venv/bin/python pendulum.py       # Linux
.venv/bin/mjpython pendulum.py     # macOS
.\.venv\Scripts\python.exe pendulum.py   # Windows
```

On macOS, any script that opens the viewer with `launch_passive` must run under `mjpython`: the OS requires the GUI loop to own the main thread, and plain `python` raises a `RuntimeError`.

## Next steps

From `LESSONS.md`:

1. Inspect the loaded model: joint names and ranges, actuators and the joints they drive, total mass.
2. Hold a pose with position actuators, then move through joint-space waypoints.
3. Forward kinematics, then damped least-squares inverse kinematics to reach a target point.
4. Keyboard control through the device adapter, with workspace and speed limits.
5. VR controller teleoperation on that adapter.

## Credits

The Shadow Hand model was provided by [Shadow Robot Company](https://www.shadowrobot.com/) under the Apache 2.0 License and packaged as MJCF in MuJoCo Menagerie. See `assets/shadow_hand/README.md` and `assets/shadow_hand/LICENSE`.
