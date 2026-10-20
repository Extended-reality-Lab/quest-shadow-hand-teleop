---
name: drone-sim
description: Context for the OSU autonomous drone simulator (MuJoCo Skydio X2 + WebSocket + CesiumJS). Load when working on the drone simulator — terrain/environment work, the MJCF scene, the pose stream, the Cesium front-end, or any question about the X2's mass, inertia, or coordinate frames. Contains verified model facts, settled decisions, dead ends already ruled out, and the points where you must stop and ask.
---

# Drone Simulator — project context

Autonomous drone simulator for Prof. Raffaele De Amicis, Oregon State.
Task 1: three drones on independent trajectories in one MuJoCo scene, poses
streamed over WebSocket at 50 Hz, rendered in CesiumJS. Task 2: environment and
terrain — scope not yet fixed.

Companion documents at the repo root: [PLAN.md](../../../PLAN.md) (Task 2 work
plan + verification transcript), [DEFENSE.md](../../../DEFENSE.md) (what can and
cannot be defended to the professor), [REPRO.md](../../../REPRO.md),
[LEARNING.md](../../../LEARNING.md), [RISKS.md](../../../RISKS.md).

**Audited 2026-08-18 (second pass).** Corrections from the first pass are marked
**CORRECTED** inline. PLAN.md §0.0 lists them all; PLAN.md §8 lists every claim
in these documents that has no citation behind it — read that section before
repeating anything here to anyone.

---

## Architecture invariants

These hold unless the professor changes the brief. Breaking one is a redesign,
not a patch.

1. **MuJoCo owns physics; the browser owns rendering. Nothing else.**
   The simulator computes state; CesiumJS displays it. Never put dynamics in JS,
   never put globe/camera logic in Python.

2. **One georeference origin, defined once, serialised to the client.**
   MuJoCo works in a flat local Cartesian frame; Cesium works on the WGS84
   ellipsoid. Exactly one WGS84 anchor maps between them, it lives in one Python
   constants module, and the client receives it over the WebSocket on connect.
   **It is never hardcoded in JS.** Two copies of the origin is the failure mode
   that produces a slowly-drifting, hard-to-attribute offset.

3. **Local frame is ENU: +X east, +Y north, +Z up.**
   This matches MuJoCo's Z-up world and the X2's Z-up body frame, so no axis
   permutation is needed anywhere in the physics layer. (Body frame is Z-up:
   all four thrust actuators use `gear="0 0 1 ..."` at `x2.xml:56-59`, i.e.
   thrust along body +Z. **CORRECTED** — the first pass asserted this without
   the citation.)

4. **Altitude means one thing, and the datum is written down.**
   Orthometric vs ellipsoidal height is fixed in one place with the conversion
   direction spelled out in a comment. See "when to stop and ask" — this is the
   single most expensive thing to get wrong.

5. **`assets/x2/x2.xml` is upstream Menagerie and stays that way.**
   Verified byte-identical to
   `google-deepmind/mujoco_menagerie/main/skydio_x2/x2.xml` except for one stray
   line (see below). World content — terrain, buildings, lights — goes in
   `scene.xml` or a new `world.xml`, never in the airframe file. This preserves
   the ability to re-pull upstream.

6. **The streamed pose is the body origin, not the centre of mass.**
   `data.qpos[0:3]` is the body-origin position. The COM sits **5.4 cm above it**
   (verified below). Any code that treats the streamed pose as the COM
   introduces a silent constant vertical bias.

7. **Physics rate and stream rate are decoupled.**
   `timestep = 0.01` s → 100 Hz physics; the stream is 50 Hz → 2 physics steps
   per frame. Changing the timestep must not change the stream rate, and vice
   versa.

---

## Verified facts about the model

All of these were checked by executing against the installed packages on
2026-08-18, not recalled. Re-verify before relying on them if versions change.

**Environment:** Python 3.12.3, mujoco **3.11.0**, numpy 2.5.2,
websockets 17.0.1, glfw 2.10.2, PyOpenGL 3.1.10. `pip freeze` matches the pins
in `requirments.txt` exactly. Node v22.17.1 / npm 10.9.2 are installed
system-wide.

**Compiled `assets/x2/scene.xml`:** `nq=7  nv=6  nu=4  nbody=2`,
`timestep=0.01`, total mass **1.325 kg**.

**Inertial properties of body `x2` — all compiler-derived:**

```
body_ipos    = [0.0, 0.0, 0.05396226]                              # COM offset, m
body_iquat   = [0.47776755, 0.47776755, -0.52128511, 0.52128511]   # (w,x,y,z)
body_inertia = [0.06071129, 0.03646840, 0.02541170]                # principal, kg·m²
body_mass    = 1.325
```

Rotated back into body axes:

```
I_body = [[ 0.0366517,  0        , -0.0021   ],     # Ixx roll
          [ 0        ,  0.0254117,  0        ],     # Iyy pitch
          [-0.0021   ,  0        ,  0.060528 ]]     # Izz yaw
```

The **Ixz = -0.0021 cross term is real**: front rotors sit at `z=.08`, rear at
`z=.05` (`x2.xml:43-46`), so the airframe is not symmetric about its XY plane.
The inertial frame is consequently tilted ~4.97° off the body axes (the rest of
`body_iquat`'s 122.92° rotation is MuJoCo's principal-axis ordering convention,
not physical tilt). A controller assuming diagonal body-frame inertia carries
this as a known small modelling error.

**Mass budget:** 4 × 0.25 kg rotors + 0.325 kg body ellipsoid = 1.325 kg.
`<geom mass="0"/>` in the `x2` default class (`x2.xml:8`) makes all other geoms
massless, so the collision boxes on `x2.xml:39-42` contribute nothing.

**Tooling that is NOT installed** (checked by import, all fail): `pyproj`,
`rasterio`, `osgeo`/`gdal`, `PIL`, `affine`, `shapely`, `scipy`, `matplotlib`,
`pandas`. DEM ingest and datum conversion therefore **cannot begin without new
dependencies**, and any repro script is limited to `numpy` + `print`.

**MuJoCo 3.11.0 capabilities confirmed by test:**
- `<hfield>` fully supported. **CORRECTED naming:** the shipped header
  `mujoco/include/mujoco/mjmodel.h:687` documents `hfield_size` as
  **`(x, y, z_top, z_bottom)`** — the first pass invented the names
  "elevation_z, base_z". The behavioural point stands: **the first two are
  radii, not extents.**
- **`hfield_data` is min–max normalised BY MUJOCO at load — this is the single
  most dangerous fact in the project.** A PNG whose bytes span 100..200 loads as
  exactly `0.0 … 1.0`, not `0.392 … 0.784`. Therefore: absolute elevation is
  destroyed at load; `z_top`/`z_bottom` are the only carriers of vertical scale;
  and **each hfield is normalised independently**, so adjacent DEM tiles will not
  meet at the seam. A single nodata pixel sets the minimum and flattens
  everything real. See PLAN.md T1.3.
- **Heightfield row order runs opposite ways in XML vs memory (VERIFIED-2).**
  The first row of the XML `elevation` attribute lands at **+Y (north)**; but
  `hfield_data[0]` in memory is the **last** XML row, i.e. **-Y (south)**.
  Writing a north-up DEM straight into `model.hfield_data` in file order
  **mirrors the terrain north-south**, and mirrored terrain looks completely
  plausible. Verified with a 3x3 ramp probed by `mj_rayHfield`. Assert
  orientation against a known asymmetric feature.
- **PNG heightfields need no Pillow.** MuJoCo parses the PNG itself; verified
  with a hand-built 4x4 greyscale file. Pillow is *not* installed (see below).
- `<replicate count="N" sep="-">` works and auto-suffixes names (`d-0`, `d-1`,
  `d-2`). Applied to the X2 it gives `nq=21  nv=18  nu=12  nbody=4` with
  actuators `thrust1-0 … thrust4-2`.
- **`<replicate>` destroys the hover keyframe. CORRECTED — the first pass said
  it merely needed the ctrl vector resized.** It compiles to `nkey=4` with
  `key_ctrl[0]` **all zeros** (the `3.2495625` hover values from `x2.xml:69` are
  gone) and `key_qpos[0]` placing only drone 0 at `z=0.3`, the others at `z=0.1`.
  Load that key expecting hover and all three drop — and it reads as a controller
  bug because the model compiles cleanly. *Caveat: my test wrapped the whole
  `<worldbody>` including the `<light>`; re-test with the exact construction you
  ship.*
- `mjGEOM_SDF` exists; `mujoco/plugin/libsdf_plugin.dylib` ships, exposing
  `mujoco.sdf.{bolt,bowl,gear,nut,torus}`.

---

## Decisions already made, and why

**Airframe: Skydio X2 from MuJoCo Menagerie.** Settled in Task 1. It is a
validated model with a working hover keyframe at `x2.xml:69`
(`ctrl="3.2495625 ..."`). Do not substitute another airframe to work around a
controller problem.

**Terrain via `<hfield>`, not a mesh.** Heightfields are the idiomatic MuJoCo
terrain primitive, collide efficiently, and map directly onto DEM raster data.
A triangle-mesh terrain is more general but far more expensive to collide and
has no advantage for the overhanging-free terrain this project needs.

**Multi-drone via `<replicate>`, not three `<include>`s.** See rejected
hypotheses.

**World content separated from airframe.** Invariant 5, above.

**Keep `websockets` (pinned 17.0.1) as the transport.** Already chosen in
Task 1 and already pinned. No reason to revisit.

---

## Hypotheses tested and rejected

Do not re-investigate these. Each cost real time on 2026-08-18.

**REJECTED: "`x2.xml:3` is a fatal XML syntax error."**
The line `// TIMESTEP HERE IS 0.01 seconds` uses a C-style comment in an XML
file, which looks fatal. **The model loads fine.** The text is legal XML
*character data* sitting inside the `<mujoco>` root element, and MuJoCo's parser
ignores stray text there. It is valid by luck, not design: it becomes a genuine
parse error the instant anyone types a `<` or a bare `&` into it (e.g. editing it
to `// timestep < 0.02`). Correct form is `<!-- ... -->`. Left unchanged so far.

**REJECTED: "`x2.xml` has an explicit `<inertial>` element to read the COM and
inertia from."** The string `inertial` does not occur in the file. Every inertial
property is derived by MuJoCo's compiler from the five massive geoms on
`x2.xml:43-47`. The COM was re-derived by hand from those lines and matches the
compiler to 8 decimal places. **Consequence: there is no inertial block to copy
if the project ever ports to another simulator — it would have to be authored
from the derived numbers.**

**REJECTED: "The local `x2.xml` has been modified and might have drifted from
upstream."** Diffed against upstream Menagerie. The *only* difference in the
entire 71-line file is the stray `//` line above. The airframe is otherwise
pristine.

**REJECTED: "Task 1's code is somewhere in this repository."** It is not. No
`.js`, `.html`, `.ts`, or `.mjs` exists outside `.venv/`; the only `.json` is
`.vscode/settings.json`. `grep -ril` for `cesium`/`websocket` matches only the
dependency pin in `requirments.txt`. A machine-wide search for `*cesium*` found
nothing. `websockets==17.0.1` is pinned but **imported by no file**. The repo
contains 12 real files: two single-drone MuJoCo scripts (`probe.py`, `view.py` —
neither commands the actuators, so both simulate a brick), two unrelated Python
exercises (`basics.py`, `drill.py`), the X2 assets, and notes.

**REJECTED: "Three drones by `<include>`-ing `x2.xml` three times."** Every name
in the file (`x2`, `imu`, `thrust1..4`, `rotor1..4`, the `hover` keyframe)
collides on the second include. `<replicate>` is the mechanism; verified working
in 3.11.0.

**REJECTED: "'MuJoCo cannot read SDF' is an unambiguous statement."** It is not.
**SDF has two live meanings here** and they lead to opposite conclusions:
*SDFormat* (Gazebo's world format) — MuJoCo genuinely cannot read it; and
*Signed Distance Function* — MuJoCo 3.11.0 supports it **natively**, with a
shipped plugin. If the professor meant the latter, there is nothing to build.
Never act on "SDF" without knowing which one is meant.

---

## When to stop and ask me

Stop and ask rather than continuing to investigate, when:

1. **Anything depends on which "SDF" the professor meant.** Do not start a
   SDFormat→MJCF converter, and do not start a Gazebo port, on an assumption.
   The question is unanswered as of 2026-08-18. Work the SDF-free tasks in
   PLAN.md instead — there are ~27 h of them.

2. **You are about to conclude Task 1 exists somewhere.** Its absence from git
   is now established exhaustively (**CORRECTED** — the first pass asserted this
   from a working-tree search alone, which was not enough evidence): the remote
   `https://github.com/Jakhangir18/drone-sim.git` has exactly one ref,
   `refs/heads/main` at `6411a0d`; all 5 commits that have ever existed contain
   no `.js`/`.html`/`.ts`/`.mjs`; `git stash list` is empty; the deleted
   `README.md` was one line, `# drone-sim`. Whether it lives outside git is
   **mine to answer, not yours to search for.** Ask; do not go hunting.

2b. **You encounter a benchmark number for this project — 0.10 m RMS, 0.57 m,
   RTF 0.998, or any other.** There is **no evidence for any of them anywhere**:
   not in the working tree, not in any commit, not on the remote. No file in this
   project contains the strings `RMS`, `RTF`, `circle`, or `survey`. Do not
   reproduce these numbers, do not build on them, and do not help defend them
   until the producing code exists. See DEFENSE.md and REPRO.md.

3. **You need a CesiumJS version, API name, or deprecation status.** There is no
   Cesium installed in this project or on this machine, so there is nothing to
   verify against. **Do not supply an API name from memory** — check the `.d.ts`
   and `CHANGES.md` inside the actually-installed pinned version, or ask. This
   restriction is deliberate and has already been enforced once.

4. **A vertical offset appears between drone and terrain.** Do not debug it as a
   controller problem. Ask about the datum first: orthometric vs ellipsoidal
   height differs by the geoid separation, which in the Pacific Northwest is tens
   of metres, and getting the sign backwards doubles the error. The symptom
   presents as a plausible-looking constant altitude bias with everything else
   working — it reads as a control bug for days. **Never quote a geoid separation
   value from memory; compute it from a geoid model.**

5. **You are about to benchmark or quote a performance number.** No benchmarks
   have been run on this project by me, and none are reproducible in it today.
   Do not invent step rates, frame times, or terrain resolution limits. Measure,
   or say it is unmeasured. Note `scipy`/`matplotlib`/`pandas` are **not
   installed**, so any measurement harness is `numpy` + `print` until that
   changes.

8. **A real-time-factor claim is in play.** RTF measured around a loop that
   contains `time.sleep(...)` measures the sleep, not the solver.
   [view.py:14](../../../view.py#L14) is exactly that shape. Check whether the
   sleep is inside the timed region before believing any RTF number. See
   REPRO.md §4.

6. **A change would touch `assets/x2/x2.xml`.** It is pristine upstream
   (invariant 5). Ask before modifying it — the fix almost certainly belongs in
   `scene.xml`.

7. **Scope of "environment" is in question** — e.g. whether wind is included.
   `x2.xml:4` sets `density="1.225" viscosity="1.8e-5"`, so aerodynamic drag is
   already active, but there is no wind field. Whether Task 2 adds one is
   unresolved.

---

## Repo hygiene note

`.venv/` is committed: **8912 of 8924 tracked files**. There is no `.gitignore`.
This should be fixed before the Cesium front-end lands and `node_modules/` joins
it. See task T0.2 in PLAN.md.
