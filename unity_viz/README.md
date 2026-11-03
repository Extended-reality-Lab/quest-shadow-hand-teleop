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
- The scene is static. The live state from the MuJoCo server comes next (#27, #29).
- Commit only `Assets/`, `Packages/` and `ProjectSettings/`; `.gitignore` here
  keeps the generated folders out.
