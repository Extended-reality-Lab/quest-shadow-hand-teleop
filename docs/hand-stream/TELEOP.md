# Quest hand -> Shadow Hand in MuJoCo

`teleop/run.py` receives the Quest hand stream and drives the Shadow Hand in a
MuJoCo scene with a table, a ball, a cube and a can. Move your hand, the robot
hand follows; close your hand over an object to pick it up.

## Run it

It replaces `pc_receiver/receiver.py` (same port, same format). Stop the
receiver first: only one program can listen on a port.

macOS (the viewer needs `mjpython`):

```
.venv/bin/mjpython teleop/run.py
```

Windows:

```
.\.venv\Scripts\python.exe teleop\run.py
```

Options: `--hand left` (default `right`), `--port 9000`.

The first tracked frame sets the starting point: hold your hand forward,
palm down. Press **Enter** in the viewer to re-centre at any time. The
terminal shows `TRACKING` with the fit error, or `HOLD` when the hand is not
tracked (the robot hand then keeps its last pose).

The network setup is the same as for the receiver (SETUP.md): the PC and the
headset on one network, or the headset pointed at the PC's address.

Tests (no headset, no window):

```
.venv/bin/python -m unittest discover -s teleop -v
```

## How it works

```
Quest  --UDP-->  read_latest()  -->  Retargeter.solve()  -->  Teleop.update()  -->  MuJoCo
26 joints        newest message      finger joint angles      safety filter          data.ctrl
                 for one hand        (inverse kinematics)     + wrist pose           data.mocap_pos/quat
```

Files:

- `teleop/retarget.py`: human hand -> robot joint angles.
- `teleop/run.py`: scene, network, safety filter, main loop.
- `teleop/test_teleop.py`: tests.

### 1. The robot model (no Menagerie file is changed)

`build_hand_spec()` loads `assets/shadow_hand/right_hand.xml` as an `MjSpec`
and adds five fingertip sites in memory. `build_scene()` then adds:

- a free joint on the forearm, so the hand can move in space;
- `gravcomp = 1` on the hand bodies, so the hand does not sag;
- a table (a solid box, top at 0.75 m) and three free objects;
- a **mocap body** `hand_target` and a **weld** that pulls the forearm onto it.

The program moves only the mocap body. The weld is a soft constraint, so
MuJoCo still resolves contacts: the hand stops at the table instead of
passing through it, and objects are pushed and grasped by physics.

### 2. Retargeting: points to angles (`retarget.py`)

The Quest gives positions, not angles, and the Shadow Hand has other
proportions (5 thumb joints, coupled last two finger joints). Instead of
computing each angle by hand, the solver moves the robot fingers until their
points match the human points:

1. **Palm frame.** From four landmarks (wrist, index, middle and little
   knuckles) build three axes: forward (wrist to middle knuckle), side (little
   to index knuckle), back (forward x side). The same function builds the
   frame on the robot from the same landmarks.
2. **Targets.** Every human point is written in the human palm frame, scaled
   by the hand-length ratio (robot / human, wrist to middle knuckle), and put
   in the robot palm frame. 15 points: per finger the middle knuckle, the last
   knuckle and the tip.
3. **Damped least squares.** For each point `mj_jacSite` / `mj_jacBody` gives
   how the point moves per joint. The update
   `dq = J^T (J J^T + lambda^2 I)^-1 e` reduces the weighted error `e`; joints
   are clipped to their ranges; 8 iterations per frame, starting from the
   previous frame's answer. The wrist joints are not used: the whole hand is
   moved instead.
4. **Actuator targets.** `actuator_length` after `mj_fwdPosition` is the
   actuator's input for the solved pose: the joint angle, or for the coupled
   finger joints the tendon length J1 + J2. Clipped to `ctrlrange`, this is
   `data.ctrl`.

### 3. Wrist pose (`Teleop.update`)

- Quest to MuJoCo axes: `(x, y, z)_mujoco = (x, -z, y)_openxr` (Y-up to Z-up).
- Re-centring stores the wrist position as the origin and turns the scene so
  the hand's forward direction is +Y (towards the table).
- The palm orientation is the human palm frame matched to the robot palm
  frame. The forearm pose follows from the fixed palm-in-forearm transform.

### 4. Safety filter (`Teleop.update`)

The simulation never takes raw input:

- the hand target stays inside a box above the table (`WORKSPACE_LOW/HIGH`);
- the hand moves at most 1.5 m/s, each joint target at most 8 rad/s;
- untracked messages are ignored, so on tracking loss or after a network
  drop the hand holds its last pose.

### 5. Main loop (`main`)

Each turn: read the newest datagram for the chosen hand, update the targets,
write them into `data`, step the physics until simulated time catches up with
the wall clock (timestep 2 ms), sync the viewer.

## What the tests check

| Test | Check |
|---|---|
| `test_finds_a_robot_pose_again` | a skeleton taken from the robot itself in a random pose, then rotated, scaled 1.3x and moved, is matched within 4 mm mean point error (both hands) |
| `test_fist_bends_the_fingers_more_than_open_hand` | fake hand closed vs open: index and middle flexion targets differ by more than 1 rad |
| `test_hand_follows_the_target_and_stays_in_limits` | 3 s of the fake hand: no NaN, every ctrl in range, forearm within 2 cm of the target |
| `test_tracking_loss_holds_the_last_pose` | untracked messages leave the targets unchanged |
| `test_hand_target_stays_in_the_workspace` | a hand 5 m below the floor keeps the target above the table |
| `test_hand_can_lift_the_ball` | scripted grasp without the Quest: the ball rises more than 5 cm and is still held after 3 s |

## Known limits

- Not yet tried with live Quest data in the viewer; the tests use the fake
  hand and the robot's own skeleton.
- The thumb has 5 joints on the robot and 4 points on the human: the solver
  picks one of several thumb poses that fit.
- One hand at a time.
- Grasping depends on contact parameters (friction 1.2 on the objects); heavy
  or slippery objects need tuning.
