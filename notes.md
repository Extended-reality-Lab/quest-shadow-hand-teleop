my tasks here 

what is really good - Shadow Hand в MuJoCo and 20 configuration 

task 1
I nedd to take 

# Cheat sheet: Quest → Shadow Hand

## Goal
Put on the Quest, move my hand, and the Shadow Hand in MuJoCo copies it.
Next: table + ball, the hand grasps the ball. Then dishes.

## Pipeline
Quest (cameras) → hand skeleton: joint positions + rotations
→ transport to Python (WebXR + WebSocket?)
→ retargeting: skeleton → Shadow Hand joint angles
→ safety filter: ranges, speed, tracking loss
→ data.ctrl → mj_step → viewer

The Quest does NOT give angles. I compute the angles myself.

## Terms
- DoF: degree of freedom, one independent motion.
- hand tracking: the Quest sees the hand with its cameras, no controllers.
- retargeting: mapping a human hand pose onto the robot hand.
- ctrl: a target for the actuator, not a force.
- mocap: a body I move myself, outside the physics (the wrist above the table).

## Stages
- [ ] 0. Teams: write how I understood the task. Quest: pick one, reset, label, charge, turn on hand tracking.
- [ ] 1. inspect.py: joints, ranges, actuators. Why are there more joints than 20 sliders? (<tendon>)
- [ ] 2. "Fist" pose through ctrl. Check: error < 0.01 rad after 2 s.
- [ ] 3. Quest data into Python. Check: fps; wrist → index fingertip = ruler ±1 cm.
- [ ] 4. Finger angles from bones. Check: flat palm ≈ 0° (±10°), fist ≈ max.
- [ ] 5. Live loop + safety filter. Check: no joint leaves its range; tracking lost → the hand freezes.
- [ ] 6. Table + ball in scene.xml. Check: ball lifted 5 cm and held for 3 s.

## Main deliverable for the professor
Table: Shadow joint ↔ the two Quest bones that give its angle.
Plus: what the robot lacks, and what the human hand lacks.

## Rules
- I write the code. Claude explains and reviews.
- Don't trust my eyes: check with a number.
- Don't touch the Menagerie XML; the scene goes in scene.xml.
- Mac: run the viewer with .venv/bin/mjpython.
- End of session: commit, push, one line in LOG.md.

## Read
- WebXR Hand Input Module
- OpenXR XR_EXT_hand_tracking
- AnyTeleop / dex-retargeting
- MuJoCo docs: mocap

## By Monday
Stages 0–2 + choose the transport.
