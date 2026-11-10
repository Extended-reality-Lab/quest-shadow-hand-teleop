# Unity inside the headset (Link cable)

With the scene only on the monitor, grasping is awkward: the eyes look at the
screen while the hand works below it. This mode renders the Unity scene into
the headset, placed so that the simulated Shadow Hand sits where the real hand
is. The headset becomes display and hand tracker; MuJoCo stays the only physics.

```
Quest ──Link cable──> Meta Horizon Link ──OpenXR──> Unity (renders, reads the hands)
                                                      │ hand stream v1, UDP 127.0.0.1:9000
                                                      ▼
                                                   teleop/run.py (MuJoCo)
                                                      │ state stream, UDP 127.0.0.1:9001
                                                      ▼
                                                   Unity (StateReceiver, XR rig)
```

Unity sends the hands itself (`HandSender.cs`), in the same format as the Quest
app (`docs/hand-stream/PROTOCOL.md`), so `teleop/run.py` runs unchanged. The
Quest app and the relay are for the wireless mode; they are not used here, and
the Godot project must not run on the PC at the same time (one OpenXR session
per PC).

## One-time setup on the lab PC

1. **Meta Horizon Link app** (already installed for the cable): Settings →
   General → *OpenXR Runtime*: set Meta Horizon as active. Settings → Beta →
   *Developer Runtime Features*: on. Without it, no hand data goes over Link.
2. **Headset:** Settings → Movement tracking → *Hand tracking*: on.
3. **Unity:** open `unity_viz`. The package manager installs XR Plug-in
   Management 4.5.4, OpenXR Plugin 1.14.0 and XR Hands 1.5.1 from
   `Packages/manifest.json` and rewrites `Packages/packages-lock.json`; commit
   that file with the scene. If Unity asks to enable the new Input System
   backend, answer Yes (the editor restarts).
4. **Edit → Project Settings → XR Plug-in Management**, Windows tab: tick
   *OpenXR*. In the *OpenXR* page that appears below: under *Interaction
   Profiles* add *Oculus Touch Controller Profile*; under *OpenXR Feature
   Groups* tick *Hand Tracking Subsystem*. Fix anything the validator (the
   warning icon) still lists.
5. **Scene:** select the `MuJoCo Scene` object (`unity_viz/README.md` creates
   it, with *Manifest Loader* and *State Receiver*): *Add Component* → *Hand
   Sender* (host 127.0.0.1, port 9000). `Ctrl+S`. The camera needs no setup:
   at Play, when a headset is connected and the teleop has re-centred, *State
   Receiver* puts `Main Camera` under an `XR Rig` object (the one in its *Xr
   Rig* field, or a new one) and adds *Head Tracker*,
   which moves the camera with the head. The table then stays in place when
   you look around. Without a headset the camera keeps the fixed view from the
   manifest.
6. **Edit → Project Settings → Player → Resolution and Presentation:** *Run In
   Background* on, so Unity keeps rendering when the terminal has the focus.

Save the project to GitHub afterwards (`docs/integration/LAB-PC.md`).

## Each session

1. Connect the cable; in the headset accept *Quest Link*. The Link app shows
   the headset as connected.
2. Terminal in the repository root: `.\.venv\Scripts\python.exe teleop\run.py`
3. Unity: *Play*. Put the headset on. The Game view mirrors what the headset
   shows.
4. Hold the hand in front of you. The first tracked frame re-centres: the
   simulated wrist goes to its home position above the near edge of the table,
   and the scene moves so that this position is where your real wrist is. To
   re-centre again, hold the OK sign with the left hand for 1.5 s (thumb tip
   on index tip, the other three fingers straight), or press Enter in the
   MuJoCo viewer window. Nothing else moves the scene: a resting left hand
   does not, and with `--no-gesture` only Enter does. Re-centre with the
   right hand where it is comfortable and with free space in front of it: the
   table starts at the wrist and reaches 60 cm forward and 20 cm down, so a
   real desk there is in the way. The direction the fingers point becomes the
   direction of the table.

The two status boxes in Unity say what works: `MuJoCo: seq N` (state stream
arriving) and `hands -> 127.0.0.1:9000  left LOST  right TRACKED`.

## Recording a video

Over Link the PC renders the image, so the PC records it. In a terminal in
the repository root, after Link and Unity *Play* are running:

```
.\mirror
```

`mirror.bat` opens Oculus Mirror, a desktop window with the exact view of the
headset. Record that window with the Snipping Tool (`Win+Shift+R`) or the
Xbox Game Bar (`Win+Alt+R`).

## How the alignment works

`teleop/run.py` maps the headset's tracked wrist into the MuJoCo world with a
rotation (the frame change plus the yaw chosen at re-centring) and a
translation (home minus the wrist position at re-centring). The state stream
carries this mapping as the pose `stage` (in Unity's frame, computed by
`scene/frames.py: stage_to_unity`), and `StateReceiver` sets the `XR Rig`
transform to it. The camera and the hands are children of the rig in tracking
space, so a tracked point renders exactly where MuJoCo put it. Unity does no
frame math of its own; the conversion is tested in `scene/test_scene.py`.

What the rig does not undo: the workspace box and the speed limits in
`teleop/run.py`. When the real hand leaves the workspace, the simulated hand
stops at the border and the two separate until the hand comes back.

## If something does not work

| Symptom | Cause, fix |
|---|---|
| `hands: no XR hand subsystem` | OpenXR not enabled, *Hand Tracking Subsystem* not ticked, or *Developer Runtime Features* off |
| Both hands `LOST` | Hand tracking off in the headset, or the controllers are held: put them down |
| Hands `TRACKED`, MuJoCo says `waiting for the hand` | teleop not running, or started with another `--port` |
| Scene moves but the hand is not on your hand | the Godot project is open on the PC and also sends to port 9000; close it |
| The image is fixed to the face | no state with a `stage` pose has arrived yet: start the teleop and hold the hand in view. Or the camera is not tagged `MainCamera` |
| The table is to the side or behind you | the re-centre took a bad hand pose: hold the right hand forward and hold the OK sign with the left hand for 1.5 s |
| No image in the headset | Link not started in the headset, or OpenXR runtime not set to Meta Horizon |
