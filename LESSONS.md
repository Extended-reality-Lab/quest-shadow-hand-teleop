# Lessons to the first milestone

Milestone: **the arm moves in simulation under my control** (reaches a target point).

Each lesson has a concept, a source to read, a task I write myself, and a check
that is a number asserted in code. A lesson is done when the check passes and
the commit is pushed. Tick the box then.

Sources marked ON MACHINE are under `.venv\Lib\site-packages\mujoco\` on Windows
and `.venv/lib/python3.12/site-packages/mujoco/` on the Mac.
Sources marked OFF MACHINE are named but not linked; find them yourself.

## How a session goes

1. One question about the previous lesson.
2. Concept and where to read it (10-15 min).
3. I write the task (30-90 min). Claude answers questions, gives no solutions.
4. Review. I fix what is wrong.
5. Commit, push, one line in `LOG.md`.

## Rules

- I write the code. Claude gives hints after ~20 min stuck, then a skeleton with gaps, never the answer.
- Paste errors in full.
- Say "I don't get it" early.
- Never trust the viewer. Assert a number.

---

- [ ] **L1 - Choosing a model like an engineer**
.venv/bin/python -c "import mujoco; print(mujoco.__version__)"   # works always
python -c "import mujoco; print(mujoco.__version__)"             # works only after activate
 
  - Concept: a Menagerie model is a validated MJCF with actuators, keyframes and collision classes already set. Choosing one means reading its README and XML, not its picture.
  - Source (OFF MACHINE): the `mujoco_menagerie` repository by google-deepmind.
  - Criteria: number of joints, has a gripper, has position actuators, has a `home` keyframe, license, matches what the lab might own.
  - Task: shortlist 3 arms, pick one, write 5 lines in `LOG.md` why. Download into `assets/<arm>/`.
  - Check: `scene.xml` loads with `mujoco.MjModel.from_xml_path`.

- [ ] **L2 - What a loaded model is**
  - Concept: `MjModel` is constant (geometry, masses, joints, actuators). `MjData` is state (`qpos`, `qvel`, `ctrl`, `time`). `nq`, `nv`, `nu`, and why `nq` can differ from `nv`.
  - Source (ON MACHINE): `include/mujoco/mjmodel.h`, `include/mujoco/mjdata.h`; the arm XML.
  - Task: `inspect.py` prints joint names, ranges, actuator names and which joint each drives, total mass.
  - Check: joint count and ranges match the XML by hand.

- [ ] **L3 - The simulation loop and real time**
  - Concept: `mj_step` advances one `timestep`. Viewer `sync`. Real-time factor, and why a `sleep` inside the timed region lies.
  - Source (ON MACHINE): `viewer.py`, `rollout.py`.
  - Task: `view.py` shows the arm in the viewer. It collapses. Explain in `LOG.md` why.
  - Mac: run it with `.venv/bin/mjpython view.py`. Find out why plain `python` fails there and write one line about it.
  - Check: measure steps per second without sleep and print it.

- [ ] **L4 - Actuators: holding a pose**
  - Concept: a position actuator applies `kp * (target - q)`. `ctrl` is a target, not a torque. The `home` keyframe.
  - Source: the arm `<actuator>` block; `mjmodel.h` fields `actuator_gainprm`, `actuator_biasprm`.
  - Task: load `home`, copy `qpos` into `ctrl`, the arm holds still. Then move one joint to a new angle.
  - Check: after 2 s, `max|qpos - ctrl| < 0.01` rad.

- [ ] **L5 - Joint-space trajectories**
  - Concept: interpolation between configurations, velocity limits, why linear in joint space is not linear in task space.
  - Source: NumPy `linspace`; the joint `range` attributes in the arm XML.
  - Task: `move_joints.py` moves smoothly through 3 waypoints, respecting ranges.
  - Check: no joint leaves its range; error at each waypoint < 0.02 rad.

- [ ] **L6 - Forward kinematics: where is the hand**
  - Concept: `site_xpos` after `mj_forward`. Frames. `mj_kinematics`.
  - Source (ON MACHINE): `mjdata.h` (`site_xpos`, `xquat`); the arm XML for the end-effector site name.
  - Task: print the end-effector position at `home`. Verify one easy configuration by hand (arm straight up: z equals the sum of link lengths).
  - Check: hand-computed vs `site_xpos` within 1 mm.

- [ ] **L7 - Inverse kinematics: reach a point (the milestone)**
  - Concept: the Jacobian maps joint velocity to end-effector velocity. Damped least squares. Iterate.
  - Source: `help(mujoco.mj_jacSite)`; NumPy `linalg.solve`.
  - Task: `reach.py` drives the arm to a target xyz, in the viewer.
  - Check: final error < 5 mm on 5 random reachable targets. Unreachable targets are reported, not flailed at.

- [ ] **L8 - Interactive control and the adapter pattern**
  - Concept: the normalized command message and safety filter from `TECHNOLOGY_RESEARCH.md`. Keyboard as the first "device".
  - Task: arrow keys move the target. The filter clamps workspace and speed. IK follows.
  - Check: a target outside the workspace is rejected and logged. No joint ever exceeds its limit.

After L8 the professor can see an arm I control.

## After the milestone: candidates

- **VR controller / joystick teleoperation.** Move a VR controller or joystick, the arm copies the motion with smooth animation. This is the L8 adapter with a real device behind it. Open questions: which headset or controller, and does it give full 6-DoF pose or only sticks and buttons?
- The bracelet, once the device is known.
- Gripper and contacts (pick and place).
- Streaming the arm pose to a browser for nicer rendering.
