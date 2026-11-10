# Unity viewer

Unity shows what MuJoCo simulates; it has no physics of its own. The scene
(table, ball, cube, can, Shadow Hand) comes from `scene/scene_manifest.json`,
which `scene/export_manifest.py` writes from the same function the simulator
uses (`teleop/run.py build_scene`). All values in the manifest are already in
Unity's frame (Y up, left-handed); see `scene/frames.py`.

## First setup (Windows lab PC or Mac)

1. Install Unity Hub and the newest Unity 6 LTS editor. No extra modules are
   needed for the desktop viewer.
2. Create the project before switching branches, while `unity_viz/` does not
   exist yet: Unity Hub, New project, template **Universal 3D**, project name
   `unity_viz`, location = the repository folder (the one that holds `scene/`
   and `teleop/`). Wait until the editor opens.
3. In a terminal in the repository folder:

   ```
   git fetch
   git switch feat/scene-manifest
   ```

   Unity picks up `Assets/Scripts/ManifestLoader.cs` on its own.
4. In the Hierarchy: right-click, Create Empty, name it `MuJoCo Scene`, keep its
   Transform at position 0, rotation 0, scale 1. Add Component, `ManifestLoader`.
5. Press Play. The Console shows `ManifestLoader: 30 bodies, 30 geoms from ...`
   and the Main Camera moves to the first view of the MuJoCo viewer.

If Unity Hub refuses the location because `unity_viz/` already exists, create
the project in another folder, copy `Assets/Scripts/ManifestLoader.cs` into it,
and set the `Manifest Path` field to the full path of `scene/scene_manifest.json`.

## Compare with MuJoCo

In the repository folder, with the Python setup from the main README:

```
.\.venv\Scripts\python.exe teleop\run.py      (Windows)
.venv/bin/mjpython teleop/run.py              (macOS)
```

The viewer opens on the same view; no headset is needed. If Windows asks to
allow network access, Cancel is fine for this check. Take a screenshot of each
window (Windows: Win+Shift+S) and put them side by side: the table, the red
ball, the blue cube, the green can and the hand must match in size, place and
orientation, and neither picture may be a mirror image of the other.

## Live link: Unity follows MuJoCo

`teleop/run.py` sends the simulation state to `127.0.0.1:9001` 60 times per
second (`scene/state_stream.py`, format in `docs/integration/DATA.md`), and
`StateReceiver` moves the hand and the objects to those poses.

1. Select the `MuJoCo Scene` object, Add Component, `StateReceiver` (same
   object as `ManifestLoader`).
2. Terminal 1, the simulator (MuJoCo window opens):

   ```
   .\.venv\Scripts\python.exe teleop\run.py
   ```

3. Terminal 2, a synthetic hand instead of the headset:

   ```
   .\.venv\Scripts\python.exe pc_receiver\fake_sender.py
   ```

4. Press Play in Unity. The box in the top left corner shows `MuJoCo: seq N`
   with N counting up, and the hand moves in Unity as in the MuJoCo window.
   `MuJoCo: no data` means nothing arrives: check that terminal 1 runs.

The fake hand is tracked for 3 s and lost for 2 s in a loop; while it is
lost, the hand holds still in both windows. Stop with Ctrl+C in each terminal.

If Unity shows a compile error in `StateReceiver.cs`, delete that file and the
static scene works as before.

## Headset: the scene in VR over a Link cable

Unity renders into the Quest and sends the tracked hands to MuJoCo itself; the
simulated hand appears on the real hand. Setup and the daily steps:
[docs/integration/HEADSET.md](../docs/integration/HEADSET.md).

## After a scene change

```
python scene/export_manifest.py
python -m unittest discover -s scene -v
```

Then press Play again, or use Rebuild in the ManifestLoader component menu.

## Limits for now

- Transparency is ignored: the small yellow marker at the wrist (the mocap
  target, see-through in MuJoCo) is opaque.
- Meshes are built when the scene loads and are not saved as assets, so use
  Play mode; an edit-mode Rebuild is lost when the scene is reopened.
- The live link applies the newest state as it arrives, without smoothing;
  interpolation comes with #29. Grasp states are always `free` until #26.
- Commit only `Assets/`, `Packages/` and `ProjectSettings/`; `.gitignore` here
  keeps the generated folders out.
