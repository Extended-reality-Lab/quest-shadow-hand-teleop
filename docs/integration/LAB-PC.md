# Lab PC (Windows) commands

Copy-paste commands for the lab Windows PC. Run them in PowerShell or in the
VS Code terminal (Terminal, New Terminal). Every command runs from the
repository root: the folder that holds `teleop`, `scene`, `unity_viz` and
`.venv`.

## Open a terminal in the repository root

Unity Hub shows the project path under `unity_viz`; the repository root is that
path without `\unity_viz` at the end.

```
cd "C:\path\to\quest-shadow-hand-teleop"
dir
```

`dir` must list `teleop`, `scene`, `unity_viz` and `.venv`.

## Python setup (once)

Only if `.venv` is missing:

```
.\setup.ps1
```

## MuJoCo viewer

Opens the same scene as Unity; the hand stays still without a headset.

```
.\.venv\Scripts\python.exe teleop\run.py
```

If Windows asks about the firewall, Cancel is fine for this check.

## Unity viewer

First setup and the side-by-side check: [unity_viz/README.md](../../unity_viz/README.md).

## Save the Unity project to GitHub

Leave Play mode and press `Ctrl+S` in Unity first.

```
git config user.name
git config user.email
```

If either is empty or not mine:

```
git config user.name "Jakhangir18"
git config user.email "dzhohadzhoha@gmail.com"
```

Check what goes into the commit (only `unity_viz/Assets`, `unity_viz/Packages`,
`unity_viz/ProjectSettings`; no `Library` or `Temp`):

```
git status --short
```

```
git add unity_viz
git commit -m "feat(unity): add the Unity project that builds the scene from the manifest"
git push
```

If `git push` asks to sign in, sign in through the browser.

## Regenerate the scene manifest

Only after a change to the MuJoCo scene (`teleop/run.py` `build_scene`):

```
.\.venv\Scripts\python.exe scene\export_manifest.py
```
