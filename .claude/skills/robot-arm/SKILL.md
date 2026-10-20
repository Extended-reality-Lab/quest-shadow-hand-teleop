---
name: robot-arm
description: Context for the OSU robot arm simulator (MuJoCo, later a human input device). Load when working in this repo on the arm model, actuators, kinematics, the device adapter, or the teaching workflow. Holds the teaching contract, invariants, settled decisions, and the points where you must stop and ask.
---

# Robot arm simulator - project context

Robot arm in MuJoCo for Prof. Raffaele De Amicis, Oregon State. Later driven by
a human input device: a "bracelet" (unknown) and, per the user on 2026-10-07, a
**VR controller or joystick** whose motion the arm mirrors with smooth animation.
Both are adapters behind the same normalized command message. Pivoted from a drone simulator on
2026-10-06; the drone work is in `archive/drone/` and is not used.

Companion documents: `LESSONS.md` (curriculum), `LOG.md` (the user's learning
log), `TECHNOLOGY_RESEARCH.md` (stack choice and adapter architecture).

## Teaching contract - this overrides normal "just do it" behaviour

The user is learning. **They write the code. You do not.**

- Explain one concept, point to the exact source on this machine, set the task
  from `LESSONS.md`, review what they wrote, say what is wrong and why.
- Stuck ~20 min: give a hint. Still stuck: a skeleton with TODO gaps. Never the
  full solution.
- Mechanical work (file moves, README edits, git hygiene) you may do directly.
  Anything in the lesson task is theirs.
- Every lesson ends with a number asserted in code, not a viewer judgement.
- Every lesson ends with a pushed commit and a line in `LOG.md`.
- They work from a **Windows desktop and a macOS laptop**. Start sessions by
  asking which one and whether they pulled. Give commands for the right OS.

## Architecture invariants

1. **MuJoCo owns physics.** No dynamics anywhere else.
2. **One normalized command message** between any input device and the
   controller (timestamp, pose/velocity if available, gripper intent,
   confidence, source). Devices plug in through an adapter that emits it.
3. **A safety filter sits between the command and the simulator**: workspace,
   joint, velocity, acceleration limits, disconnect timeout. The sim never
   trusts raw input.
4. **Menagerie model files stay upstream-pristine.** Scene content goes in
   `scene.xml` or a new world file, never in the arm XML itself.

## Verified environment (2026-10-06)

Desktop: Windows 11, Python 3.12.10 via `py -3.12`, venv at `.venv\Scripts\`,
`mujoco==3.11.0`, `numpy==2.5.2`. Setup is `.\setup.ps1`.
Laptop: macOS, setup is `./setup.sh` (needs `python3.12`, e.g. Homebrew).
**Not yet verified on the Mac.** On macOS any script that opens the viewer must
run under `.venv/bin/mjpython`, not `python`. `.gitignore`
excludes `.venv/`. NOT installed: scipy, matplotlib, pandas, PIL. Any
measurement harness is numpy + print until that changes.

MuJoCo 3.11.0 facts verified in the drone phase that still apply: `<replicate>`
works and rewrites names; keyframes do not survive it; inertial properties are
compiler-derived when no `<inertial>` block exists.

## Decisions

- **MuJoCo, not Isaac Lab**, for now. Reasons in `TECHNOLOGY_RESEARCH.md`.
  Revisit only if imitation learning, camera simulation or GPU-scale training
  become requirements.
- **Arm model: chosen by the user in L1.** Do not pick it for them.
- **Rendering: the MuJoCo viewer.** Browser streaming is a stretch goal.

## Stop and ask

1. Anything that depends on **what the bracelet or VR controller is**. Unknown. Build to the
   adapter interface, do not guess a device.
2. You are about to **write a lesson task's code** for the user. Do not. Hint
   or skeleton only.
3. A change would **modify a Menagerie XML file**. The fix belongs in
   `scene.xml`.
4. You need a **Menagerie model fact** (joint count, site names, actuator
   type). Read the downloaded XML in `assets/`; do not recall it.
5. You want to **quote a performance number**. Measure or say unmeasured.
