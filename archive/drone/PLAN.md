# Task 2 Planning — Environment / Terrain

Author: analysis pass, 2026-08-18. Read-only. No project code written.
Every claim below is either **VERIFIED** (I executed something on this machine and
pasted the result) or **UNVERIFIED** (explicitly labelled). Nothing is quoted from
memory.


---

## 0.0 AUDIT (2026-08-18, second pass) — corrections to this document

This document was re-audited against the repo and the installed packages. Errors
found in the first pass, corrected below and inline:

- **A1. Line counts in §1.1 were wrong for 4 of 12 files.** The table used
  `cat -n` display counts. `wc -l` gives: `view.py` **14** (was written 15),
  `basics.py` **18** (was 19), `.vscode/settings.json` **3** (was 4),
  `Jak-notes.txt` **7** (was 6). Cause: trailing-newline handling. Corrected in
  the table. No conclusion depended on these.
- **A2. "Total Phase 0–2: roughly 27 h" was wrong.** The tasks sum to
  **30.25 h**. Corrected in §5.
- **A3. `hfield_size` naming was imprecise.** The authoritative header
  `mjmodel.h:687` names the fields `(x, y, z_top, z_bottom)`, not
  "elevation_z, base_z". The behavioural point (radii, not extents) stands.
- **A4. T1.3 relied on an unverified normalisation model.** MuJoCo min–max
  normalises heightfield image data itself. See the corrected T1.3 trap — this
  is now the most valuable single fact in the document.
- **A5. T2.2's test was understated.** `<replicate>` does not merely resize the
  keyframe, it loses its contents. See corrected T2.2.
- **A6. The Task 1 absence claim was right but under-evidenced.** The first pass
  searched the working tree and `~` but never checked the git remote, the full
  commit set, or the deleted `README.md`. Now closed properly — see §1.2.
- **A7. Tooling for T1.3/T1.4 was never checked.** None of the required
  geospatial libraries are installed. See §2.3.
- **A8. Uncited claims.** Several statements carried no file, line, or version.
  They are now listed and labelled as guesses in §8.

Claims **added** in this pass are marked `VERIFIED-2`.

---

## 0. Headline findings (read these before the plan)

1. **Task 1 is not in this repository.** There is no CesiumJS, no WebSocket
   server, no three-drone scene, and no trajectory code anywhere in the repo or
   on this machine. What exists is four small single-drone / tutorial scripts.
   See §1.
2. **The CesiumJS question cannot be answered.** There is no Cesium in this
   project, so there is no version to check and no API surface to audit. I have
   not guessed one. See §2.2.
3. **"SDF" is ambiguous and the ambiguity may dissolve the whole problem.**
   MuJoCo 3.11.0 ships a *Signed Distance Function* plugin
   (`libsdf_plugin.dylib`, VERIFIED). If that is what the professor meant, the
   premise "MuJoCo cannot read SDF" is false and there is no converter to write.
   See §3.
4. **`assets/x2/x2.xml:3` is a stray `//` line** that is not upstream. It happens
   to be harmless today. It is a trap. See §1.3.
5. **The virtualenv is committed to git**: 8912 of 8924 tracked files are under
   `.venv/`. See §1.4.

---

## 1. Repo inventory

Total tracked files: **8924** (VERIFIED: `git ls-files | wc -l`).
Of those, **8912** are under `.venv/` (VERIFIED: `git ls-files | grep -c '^\.venv/'`).
**12 files are actual project content.**

### 1.1 Files that exist and do something

| File | Lines | What it is |
|---|---|---|
| [probe.py](probe.py) | 28 | Loads `assets/x2/scene.xml`, prints model stats, drops the drone from z=5.0 and steps 1000 times printing altitude every 100 steps. **No controller** — it is a free-fall test. |
| [view.py](view.py) | 14 | Same load, opens `mujoco.viewer.launch_passive`, steps in a loop with `time.sleep(model.opt.timestep)`. **No controller** — the drone falls in the GUI. |
| [drill.py](drill.py) | 14 | NumPy exercise. Computes `target - position`, its norm, and `kp * error` with `kp = 2`. Not wired to anything. |
| [basics.py](basics.py) | 18 | Pure-Python exercise on a hardcoded list of altitudes. No MuJoCo import. |
| [assets/x2/x2.xml](assets/x2/x2.xml) | 71 | Skydio X2 airframe from MuJoCo Menagerie. |
| [assets/x2/scene.xml](assets/x2/scene.xml) | 23 | Wrapper: includes `x2.xml`, adds skybox, groundplane material, one directional light, one infinite plane geom. |
| `assets/x2/assets/X2_lowpoly.obj` | — | 540,699 bytes. Visual mesh. |
| `assets/x2/assets/X2_lowpoly_texture_SpinningProps_1024.png` | — | 298,668 bytes. Texture. |
| [requirments.txt](requirments.txt) | 11 | Pinned deps. Note the filename is misspelled (`requirments`, not `requirements`). |
| [Jak-notes.txt](Jak-notes.txt) | 7 | One Menagerie URL and a note. |
| [.vscode/settings.json](.vscode/settings.json) | 3 | Two inline-suggestion editor settings. Unrelated to the sim. |
| `.DS_Store` | — | Committed by accident. |

### 1.2 What is stubbed, dead, or missing

- **Dead code:** [basics.py](basics.py) and [drill.py](drill.py) are learning
  exercises. Nothing imports them. [drill.py:11-13](drill.py#L11-L13) is a
  proportional term that never reaches an actuator.
- **Stubbed:** [probe.py](probe.py) and [view.py](view.py) both set
  `data.qpos[2] = 5.0` ([probe.py:19](probe.py#L19),
  [view.py:8](view.py#L8)) and then step with `data.ctrl` left at zero. The
  four `thrust` actuators are never commanded, so both scripts simulate a brick.
  The model *has* a hover keyframe ready to use at
  [x2.xml:69](assets/x2/x2.xml#L69) — `ctrl="3.2495625 ..."` — and neither
  script loads it.
- **Missing entirely — this is the important part.** I searched the repo and the
  home directory. There is **no** file matching `*.js`, `*.html`, `*.ts`, `*.mjs`
  anywhere outside `.venv/`; the only `.json` is the VSCode settings. `grep -ril`
  for `cesium` and `websocket` across the project matches **only**
  [requirments.txt](requirments.txt), i.e. the `websockets==17.0.1` pin — no code
  imports it. A `find` over `~` for `*cesium*` / `*drone*` returned only this
  repo and its Claude project directory. (All VERIFIED.)

  So: **three drones, per-drone trajectories, the 50 Hz WebSocket stream, and
  both CesiumJS applications do not exist on this machine.** Either that work
  lives somewhere I cannot see (another machine, an unpushed branch, a
  classmate's repo), or Task 1 is not actually done. Nothing in Task 2 can be
  sequenced until this is resolved — see task **T0.1**.

  Note `websockets==17.0.1` is pinned but unused, which is consistent with
  "planned but not yet written" rather than "written and lost".

  **VERIFIED-2 — the first pass under-evidenced this. Now closed properly.**
  The first pass only searched the working tree and `~`. This pass checked the
  history and the remote:
  - `git ls-remote --heads --tags origin` returns exactly one ref:
    `refs/heads/main` at `6411a0d`, the same commit as local. There is no
    second branch, no tag, nothing unpushed on the remote
    (`https://github.com/Jakhangir18/drone-sim.git`).
  - Enumerating **every commit that has ever existed** (`git rev-list --all
    --reflog`, 5 commits: `6411a0d`, `0cc0242`, `8ef89fd`, `50bba56`,
    `f01b798`) and listing every tree: the only file matching
    `\.(js|html|ts|mjs|json)$` outside `.venv/` in any of them is
    `.vscode/settings.json`.
  - `git stash list` is empty.
  - The `README.md` deleted in `0cc0242` was recovered: it is **one line**,
    `# drone-sim`. It contains no results, no benchmarks, no architecture.

  So Task 1's code has never been committed to this repository on any branch.
  If it exists it is entirely outside git. **This is a question for you, not a
  search target for me.**

### 1.3 The `//` line

[assets/x2/x2.xml:3](assets/x2/x2.xml#L3) reads:

```
// TIMESTEP HERE IS 0.01 seconds
```

`//` is not an XML comment. I expected this to be a fatal parse error and it is
not: the model **loads OK** (VERIFIED). The reason is that the text sits as
character data inside the `<mujoco>` root element, and MuJoCo's parser ignores
stray text there. It is legal XML today purely by luck.

It becomes a hard parse error the moment anyone types a `<` or a bare `&` into
that line — e.g. editing it to `// timestep < 0.02`. Correct form is
`<!-- TIMESTEP HERE IS 0.01 seconds -->`. I have not changed it (read-only pass).

I diffed the local file against upstream Menagerie
(`raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/skydio_x2/x2.xml`,
fetched successfully). **The only difference in the entire file is this line**
— upstream has a blank line there. The airframe is otherwise pristine.

### 1.4 Repo hygiene

`.venv/` is committed, including compiled `.pyc` files and Windows `.dll`s
shipped inside PyOpenGL. There is **no `.gitignore`** (VERIFIED: file absent).
This makes the repo large, makes every dependency change a thousand-file diff,
and hardcodes absolute macOS paths into version control. See task **T0.2**.

---

## 2. Version verification

### 2.1 MuJoCo — VERIFIED

```
Python  3.12.3
mujoco  3.11.0   (.venv/lib/python3.12/site-packages/mujoco/__init__.py)
numpy   2.5.2    glfw 2.10.2    PyOpenGL 3.1.10    websockets 17.0.1
```

`pip freeze` matches [requirments.txt](requirments.txt) exactly — the pins are honest.

Compiling `assets/x2/scene.xml` (VERIFIED):

```
nq 7   nv 6   nu 4   nbody 2
timestep   0.01
total mass 1.325
```

#### The inertial frame — correcting the premise of the question

You asked me to quote the XML lines giving the inertial-frame rotation and the
COM offset. **Those lines do not exist.** There is no `<inertial>` element
anywhere in [x2.xml](assets/x2/x2.xml) (VERIFIED: the string `inertial` does not
occur in the file). MuJoCo's compiler *derives* the whole inertial frame from the
five geoms that carry mass. So the honest answer is the derived values plus the
lines that produce them.

Derived values for body `x2` (VERIFIED, read out of the compiled `MjModel`):

```
body_ipos    = [0.0, 0.0, 0.05396226]                              # COM offset
body_iquat   = [0.47776755, 0.47776755, -0.52128511, 0.52128511]   # (w,x,y,z)
body_inertia = [0.06071129, 0.03646840, 0.02541170]                # principal
body_mass    = 1.325
```

**Centre-of-mass offset: `[0, 0, 0.05396226]` m** — 5.396 cm above the body
origin, purely vertical, no lateral offset. The lines that produce it are
[x2.xml:43-47](assets/x2/x2.xml#L43-L47), quoted exactly:

```xml
      <geom name="rotor1" class="rotor" pos="-.14 -.18 .05" mass=".25"/>
      <geom name="rotor2" class="rotor" pos="-.14 .18 .05" mass=".25"/>
      <geom name="rotor3" class="rotor" pos=".14 .18 .08" mass=".25"/>
      <geom name="rotor4" class="rotor" pos=".14 -.18 .08" mass=".25"/>
      <geom size=".16 .04 .02" pos="0 0 0.02" type="ellipsoid" mass=".325" class="visual" material="invisible"/>
```

I re-derived the COM by hand from those five lines to confirm the compiler
agrees (VERIFIED):
`(0.25·(0.05+0.05+0.08+0.08) + 0.325·0.02) / 1.325 = 0.05396226` — exact match
to 8 decimal places. The mass budget is 4 × 0.25 (rotors) + 0.325 (body
ellipsoid) = 1.325 kg; note `<geom mass="0"/>` in the `x2` default class
([x2.xml:8](assets/x2/x2.xml#L8)) makes every *other* geom massless, so the
collision boxes on lines 39-42 contribute nothing.

**Inertial-frame rotation: `body_iquat = [0.47776755, 0.47776755, -0.52128511,
0.52128511]`**, which is a **122.92°** rotation about axis
`[0.5439, -0.5934, 0.5934]` (VERIFIED via `mju_quat2Mat` + axis-angle
extraction). Most of that is just an axis *permutation* — MuJoCo orders
principal axes by its own convention, not by body XYZ. Rotating the diagonal
inertia back into the body frame gives the physically meaningful quantity
(VERIFIED):

```
I_body = [[ 0.0366517,  0        , -0.0021    ],
          [ 0        ,  0.0254117,  0         ],
          [-0.0021   ,  0        ,  0.060528  ]]
```

So in body axes: Ixx (roll) 0.0367, Iyy (pitch) 0.0254, Izz (yaw) 0.0605
kg·m², plus a **non-zero Ixz = -0.0021** cross term. That coupling is real and
it is why the principal frame is tilted ~4.97° rather than axis-aligned: the
front rotors sit at `z=.08` and the rear rotors at `z=.05`
([x2.xml:43-46](assets/x2/x2.xml#L43-L46)), so the airframe is not
symmetric about its own XY plane.

**Why this matters for Task 2:** if you ever write a controller that assumes a
diagonal inertia in body axes, the Ixz term is a real (small) modelling error,
and the COM is 5.4 cm above the body origin — so the pose you stream to Cesium
from `data.qpos[0:3]` is the **body-origin** pose, not the COM. Mixing those up
is a silent 5.4 cm vertical bias in the visualisation.

One more MJCF detail worth recording: the visual mesh carries
`quat="0 0 1 1"` at [x2.xml:38](assets/x2/x2.xml#L38). That is a *mesh* rotation
(unnormalised, = 180°-ish reorientation of the OBJ), completely unrelated to the
inertial frame. Do not confuse the two.

#### Capabilities relevant to terrain — VERIFIED

- Heightfields are fully supported: `nhfield`, `hfield_data`, `hfield_size`,
  `hfield_nrow`, `hfield_ncol`, `mjGEOM_HFIELD` all present. I compiled a test
  hfield and confirmed the size vector semantics are
  **`size = (radius_x, radius_y, elevation_z, base_z)`** and that `hfield_data`
  is `nrow*ncol` floats normalised to `[0,1]`.
- `<replicate count="3" sep="-">` **works in 3.11.0** and auto-suffixes names
  (`d-0`, `d-1`, `d-2`), producing `nq = 21` for three free bodies (VERIFIED).
  This is the clean answer to multi-drone naming — see **T2.2**.
- `mjGEOM_SDF` exists as a geom type, and `mujoco/plugin/libsdf_plugin.dylib`
  ships in this install.

### 2.2 CesiumJS — CANNOT BE VERIFIED

**There is no CesiumJS in this project.** No `package.json`, no `node_modules`,
no HTML, no JS, no bundler config, no CDN `<script>` tag — because there is no
web front-end at all (VERIFIED, §1.2). A machine-wide search for a `cesium`
directory found nothing.

Therefore:

- The CesiumJS version in this project is **UNVERIFIED — not applicable, no
  Cesium present.**
- Whether the currently-used Cesium APIs are current, deprecated, or removed is
  **UNVERIFIED — there are no currently-used Cesium APIs to audit.**

Node **v22.17.1** and npm **10.9.2** are installed system-wide (VERIFIED), so
the toolchain to install Cesium exists; the library does not.

**VERIFIED-2 — re-checked this pass, still unresolvable.** No `package.json`,
no `node_modules`, no lockfile anywhere in the repo or in any commit that has
ever existed (see §1.2). **This cannot be resolved without you**: either point me
at the machine/repo holding the front-end, or install Cesium at a chosen version
here. Until then every Cesium statement in every document I produce is
necessarily about a library that is not present.

I am deliberately not naming any Cesium API, class, or version number in this
document. You asked me not to fabricate API names, and with nothing installed to
check against, anything I wrote would be recall, not verification. Once the
Task 1 front-end is recovered (**T0.1**) or Cesium is installed with a pinned
version, this section can be filled in properly — that is task **T1.5**.

### 2.3 Tooling gap — VERIFIED-2 (missed entirely in the first pass)

None of the libraries T1.3 and T1.4 require are installed in `.venv`. Checked by
import, all fail:

```
pyproj  rasterio  osgeo/gdal  PIL  affine  shapely   -> NOT INSTALLED
scipy   matplotlib  pandas                            -> NOT INSTALLED
```

Consequences the first pass should have stated:

- **T1.3 and T1.4 cannot begin without adding dependencies.** Reading a DEM
  needs a raster library; converting datums needs a geoid model, which is what
  `pyproj` would supply. Neither is present. Budget this inside those tasks or
  add a T0.4.
- **Any repro/benchmark script is currently limited to `numpy` for maths and
  plain `print` for output.** No `matplotlib` means no plots without a new
  dependency. See REPRO.md.
- **Good news, VERIFIED-2:** MuJoCo loads a PNG heightfield *natively* with no
  Pillow involved — I built a 4x4 greyscale PNG byte-by-byte and
  `<hfield file="...png">` compiled and populated `hfield_data` correctly. So
  the hfield step itself adds no Python image dependency; only reading the
  source DEM does.

---

## 3. The SDF question

Do not answer this from the plan; get it answered. But note first that the
question may be malformed.

### 3.1 "SDF" has three readings, and one of them is not a problem at all

| Reading | What it means | Does MuJoCo support it? |
|---|---|---|
| **A. SDFormat** — Simulation Description Format | Gazebo's XML world/robot format (`.sdf`, `.world`) | **No.** MuJoCo reads MJCF and URDF only. |
| **B. Signed Distance Function** | Implicit-surface collision geometry | **Yes, natively.** `libsdf_plugin.dylib` ships in 3.11.0 (VERIFIED), exposing `mujoco.sdf.bolt`, `.bowl`, `.gear`, `.nut`, `.torus` (VERIFIED via `strings`). `mjGEOM_SDF` is a first-class geom type. |
| **C. Signed distance field terrain** | Voxel/implicit terrain representation | Partially, via B; heightfields are the idiomatic route. |

A robotics professor saying "SDF" most likely means **A**. But **B** is a real,
shipped MuJoCo 3.x feature with the identical acronym, and it is exactly the kind
of thing that ends up in a project brief. If the professor meant B, the premise
"MuJoCo cannot read SDF" is simply **false**, there is no converter to write, and
the entire branch below evaporates.

**Ask which one before writing a line of converter code.** This is a one-sentence
email that can save a week. Suggested wording:

> When you say SDF for the environment — do you mean SDFormat, the Gazebo world
> format, or MuJoCo's signed-distance-function collision plugin? MuJoCo reads
> MJCF/URDF natively and ships an SDF *plugin* in the signed-distance sense, so
> the two readings lead to very different work.

### 3.2 Branch (a) — SDF is a suggestion → describe the environment in MJCF

**What changes:** nothing structural. Terrain becomes an MJCF `<hfield>` asset
plus static `<geom>` obstacles in `scene.xml`. The existing loader in
[probe.py:5](probe.py#L5) / [view.py:4](view.py#L4) keeps working unchanged.

**Cost:** this is the cheap branch. Phase 1 and Phase 2 below are the whole job.

**Risk:** essentially none technically. The only risk is that the professor
later says he meant SDFormat and Phase 3B lands late in the term.

### 3.3 Branch (b) — SDF is hard

Two sub-options.

**(b1) Write an SDFormat → MJCF converter for the subset we need.**

- Realistic subset: `<world>`, `<model>`, `<link>`, `<pose>` (6-vector,
  roll-pitch-yaw), `<geometry>` with `box`/`sphere`/`cylinder`/`plane`/`mesh`,
  `<heightmap>`, `<static>`, and materials reduced to an RGBA. Skip joints,
  sensors, and plugins entirely — the drone stays in MJCF; only the *world*
  converts.
- **The trap that makes this bigger than it looks:** SDFormat `<pose>` is
  `x y z roll pitch yaw` in **radians, extrinsic XYZ**, and poses nest through
  `<model>` → `<link>` → `<geometry>`; MJCF uses quaternions (or `euler` with a
  compiler-set convention) and its own frame nesting. Getting the composition
  order wrong yields a world that looks *almost* right, which is far more
  expensive to debug than one that is obviously broken. Also: SDFormat is
  Z-up like MJCF, so that part is free — but `<heightmap>` size semantics differ
  from MuJoCo's `(radius_x, radius_y, elevation_z, base_z)` (VERIFIED above),
  and that conversion must be unit-tested, not eyeballed.
- **Scope control:** a converter is only worth it if the professor supplies, or
  expects you to consume, an existing `.world` file. If the environment is
  something you author yourself, writing SDFormat *in order to* convert it to
  MJCF is pure overhead — say so and push back.

**(b2) Move the simulation to Gazebo.**

- Native SDFormat, no converter. But it discards the working MuJoCo setup, the
  Menagerie X2 airframe, and everything in Task 1 that touches `mujoco`.
- Gazebo has its own X2-equivalent airframes, but the Skydio X2 model you have
  is Menagerie/MJCF; porting it means redoing the mass and inertia work
  documented in §2.1 — and note that work is *implicit* (compiler-derived), so
  there is no `<inertial>` block to copy across. You would have to hand-author
  one from the derived numbers.
- Only justifiable if the professor's real requirement is "the project must run
  in Gazebo", not "the environment must be described in SDF".

**Recommendation:** if the answer is "hard requirement", push for **(b1) with a
minimal subset**, and only after establishing that a real `.world` file is
actually in play. (b2) is a term-scale rewrite.

---

## 4. Work plan

Tasks are sized 2–4 h for one student. Each states goal, the **single** test that
proves it works, and the trap most likely to cost a day.

Dependency on the SDF answer is flagged per task:
**[SDF-BLOCKED]** = cannot start until the professor answers.
**[SDF-FREE]** = safe to do tonight regardless of the answer.

### Phase 0 — Unblock (do these first; nothing else is real until they are done)

---

**T0.1 — Reconcile Task 1 with reality. [SDF-FREE] · 2 h · BLOCKS EVERYTHING**

- **Goal:** establish where the three-drone / WebSocket / CesiumJS code actually
  lives, or accept that it does not exist. Check other machines, unpushed
  branches, `git reflog`, `git stash list`, cloud storage, and any classmate
  repo. If it is gone, decide with the professor whether Task 2 proceeds on a
  rebuilt Task 1 or the two merge.
- **Test:** a single command — `git ls-files | grep -iE '\.(js|html)$'` — returns
  the Cesium application files, from whatever repo you have identified as the
  real one. Right now, in this repo, it returns nothing.
- **Trap:** assuming the code will "turn up" and starting terrain work anyway.
  Every Phase 1 task below streams poses to a viewer that does not exist yet; if
  you build terrain first you will have no way to see whether it is right, and
  you will debug two unknowns at once.

---

**T0.2 — Repo hygiene. [SDF-FREE] · 2 h**

- **Goal:** add a `.gitignore` (`.venv/`, `__pycache__/`, `.DS_Store`,
  `node_modules/`), `git rm -r --cached .venv .DS_Store`, and rename
  [requirments.txt](requirments.txt) → `requirements.txt`.
- **Test:** `git ls-files | wc -l` drops from **8924** to roughly **12**, and a
  fresh clone + `pip install -r requirements.txt` + `python probe.py` still
  prints the model stats.
- **Trap:** doing this *after* the Cesium app lands, when `node_modules/` has
  also been committed and the history is far heavier to clean. Do it now, while
  the repo is small. Note this rewrites nothing historical — the blobs stay in
  history; that is fine for a university project, and `git filter-repo` is not
  worth the risk here.

---

**T0.3 — Send the SDF disambiguation question. [SDF-FREE] · 15 min**

- **Goal:** the email in §3.1, plus: "should the environment be a real
  geographic location (which DEM/imagery source?) or a synthetic test world?"
  The second question drives Phase 1 as hard as the first.
- **Test:** an answer arrives naming (i) SDFormat or signed-distance, and (ii) a
  location or "synthetic".
- **Trap:** asking only about SDF and not about the location. If the answer is
  "real terrain at OSU Corvallis" the DEM/datum work in T1.3–T1.4 is the bulk of
  Task 2; if it is "synthetic", T1.3 and T1.4 collapse to about 90 minutes.

---

### Phase 1 — Environment foundation

---

**T1.1 — Fix the georeference origin and write it down once. [SDF-FREE] · 3 h**

- **Goal:** choose one WGS84 lat/lon/height anchor for MuJoCo's `(0,0,0)`, and
  one local tangent-plane convention (ENU recommended: +X east, +Y north, +Z up
  — which matches MuJoCo's Z-up world and the X2's Z-up body frame). Record it
  in a single constants module that both the physics side and the front-end read.
  Write the forward and inverse transform with no dependency on Cesium.
- **Test:** round-trip property test — for 1000 random local points within
  ±5 km, `local→geodetic→local` returns the original to < 1 mm.
- **Trap:** letting the origin live in two places (once in Python, once
  hardcoded in JS). They drift by a metre, nobody notices for a week, and the
  drone is consistently offset from the terrain. One source of truth, serialised
  to the client over the existing WebSocket on connect.

---

**T1.2 — Replace the infinite plane with a heightfield. [SDF-FREE] · 3 h**

- **Goal:** swap [scene.xml:21](assets/x2/scene.xml#L21)
  (`<geom name="floor" size="0 0 0.05" type="plane" material="groundplane"/>`)
  for an `<hfield>` asset + `type="hfield"` geom, initially with a flat or
  trivially-sloped synthetic elevation array. Keep the checker material so you
  can see scale.
- **Test:** load the scene, place the drone at a known `(x, y)` over a known
  slope, `mj_forward`, and assert the resting contact height matches the
  analytic terrain height at that `(x,y)` to < 1 cm.
- **Trap:** MuJoCo's `hfield_size` is documented in the shipped header
  `.venv/lib/python3.12/site-packages/mujoco/include/mujoco/mjmodel.h:687` as
  **`(x, y, z_top, z_bottom)`**, and the first two are **radii, not extents**
  (VERIFIED §2.1; the first pass called these "elevation_z, base_z" — use the
  header's names). Passing full width/height silently doubles the terrain
  footprint, and the drone then flies over terrain that is 2× too large in
  ground plane while all the elevations still look plausible. Assert the
  footprint in the test, not just the height.

---

**T1.3 — DEM ingest → normalised hfield array. [SDF-FREE, but scope set by T0.3] · 4 h**

- **Goal:** read a real DEM tile for the chosen location, crop to the region of
  interest, resample to an `nrow × ncol` grid MuJoCo can afford, and set `z_top`/`z_bottom`
  so the true elevation span is recoverable. **Do not rely on your own
  normalisation surviving** — see the trap.
- **Test:** pick three DEM pixels with known elevations, query the loaded
  MuJoCo hfield at the corresponding local `(x,y)`, and assert agreement to
  < 0.5 m.
- **Trap — corrected and now the most important fact in this document
  (VERIFIED-2).** **MuJoCo min–max normalises heightfield image data itself.**
  I wrote a PNG whose byte values span only 100..200 and loaded it as an
  `<hfield>`; `hfield_data` came back as exactly `0.0, 0.33, 0.66, 1.0` — not
  `100/255..200/255`. The loader stretches whatever range the image contains to
  fill `[0,1]`.

  Three consequences, each capable of eating a day:
  1. **Absolute elevation is destroyed at load.** Your careful pre-normalisation
     is silently overwritten. `z_top`/`z_bottom` (and the geom's z position) are
     the *only* carriers of true vertical scale — they must be computed from the
     DEM's real min/max and recorded alongside the image, or the terrain's
     absolute height is unrecoverable.
  2. **Each heightfield is normalised independently.** Two adjacent DEM tiles
     with different elevation ranges will *not* line up at the shared seam, even
     though each looks correct alone. Prefer one hfield over a tile grid; if you
     must tile, force a common range before export.
  3. **A single nodata pixel (often −9999 or −32768 — UNSURE, depends on the
     product; read your DEM's metadata) sets the min, and everything real
     collapses into a hair-thin band near 1.0.** The terrain will look flat and
     you will suspect your resampling. Mask nodata *before* export and assert the
     surviving range.


  4. **Row order runs opposite ways in XML and in memory. VERIFIED-2, and this
     is the one most likely to be missed.** Tested with a 3x3 ramp
     (`elevation="0 0 0 / 5 5 5 / 10 10 10"`) probed with `mj_rayHfield`:
     - The **first** row listed in the XML `elevation` attribute lands at
       **+Y (north)**; the last row lands at **-Y (south)**. So a north-up DEM
       written into the XML *in file order* is oriented **correctly**.
     - But `hfield_data` in memory is stored the **other way round**:
       `hfield_data[0]` is the XML's **last** row, i.e. **-Y / south**.

     Therefore: **assigning a north-up DEM straight into `model.hfield_data` in
     file order silently mirrors the terrain north-south.** Since any DEM large
     enough to matter will be written programmatically rather than as XML text,
     this is the path you will actually take. A mirrored terrain is plausible
     terrain — the drone flies over hills of the right size in the wrong places,
     and nothing looks broken. Assert the orientation with a ray probe against a
     known asymmetric feature; do not eyeball it.

  Separately, on grid resolution: a full-resolution DEM tile may load and look
  fine, then cost you step rate once something touches it. I have **not measured
  this** — see §8, it is a guess. Decide cell size from the physical area you
  need and measure the step rate before committing.

---

**T1.4 — Reconcile the vertical datum. [SDF-FREE] · 4 h · HIGHEST RISK**

- **Goal:** make "altitude" mean one unambiguous thing end to end. Establish
  whether the DEM is orthometric (geoid-referenced, typical for USGS products)
  or ellipsoidal, establish what the globe viewer expects, apply the geoid
  separation once, in one place, and document the direction of the correction.
- **Test:** one ground-truth point with an independently known elevation — a
  survey marker, or a building of known height — renders with its base on the
  terrain surface in the viewer, with vertical error < 1 m.
- **Trap:** **this is the day-eater, and it is the reason this task is 4 h and
  not 2.** Orthometric and ellipsoidal heights differ by the geoid separation,
  which in the Pacific Northwest is a large negative number of order tens of
  metres (I have **not** verified the value for Corvallis — do not take a number
  from this document, compute it from a geoid model). Get the sign backwards and
  the error doubles. The symptom is nasty because it is *not* obviously broken:
  the drone flies at a consistent, plausible-looking offset above or below the
  terrain, everything else works, and it reads as a controller bug for three days
  before anyone suspects the datum. Write the sign convention in a comment with
  the words "orthometric" and "ellipsoidal" spelled out.

---

**T1.5 — Install Cesium, pin it, and audit the API surface. [SDF-FREE] · 3 h**

- **Goal:** the task §2.2 could not do. Install CesiumJS at an explicit pinned
  version, record that version in `package.json`, and *then* check every Cesium
  call the Task 1 front-end makes (once T0.1 recovers it) against that version's
  own bundled type definitions and changelog.
- **Test:** the app builds with zero deprecation warnings in the console, and
  `npm ls cesium` prints one pinned version.
- **Trap:** auditing against documentation found by search rather than against
  the installed package. Cesium has renamed and removed public API across major
  versions; the only trustworthy source is the `.d.ts` and `CHANGES.md` inside
  the version actually in `node_modules`. Read those, not a blog post — and not
  this document, which deliberately names no Cesium API.

---

### Phase 2 — Environment content

---

**T2.1 — Static obstacles in MJCF. [SDF-BLOCKED — see note] · 3 h**

- **Goal:** add buildings / no-fly volumes as static `<geom>`s (boxes and
  cylinders) in a separate included XML so the world is editable without
  touching the airframe.
- **Test:** the drone commanded straight through a building volume registers a
  contact (`data.ncon > 0`) instead of passing through.
- **Trap:** authoring obstacles in the *airframe* file rather than a separate
  include. [x2.xml](assets/x2/x2.xml) is a pristine Menagerie file (VERIFIED,
  §1.3) — keeping it untouched means you can re-pull upstream. Put world content
  in `scene.xml` or a new `world.xml`.
- **SDF note:** the *content* is branch-independent, but the *file format* is
  exactly what branch (b1) would convert. If the professor says SDFormat is hard,
  this task's output becomes the converter's target and should be authored with
  the converter's subset in mind. Cheap to redo, but do T0.3 first.

---

**T2.2 — Three drones, properly namespaced. [SDF-FREE] · 3 h**

- **Goal:** get three X2s into one scene without name collisions. Use
  `<replicate count="3" sep="-">`, which is **VERIFIED working in 3.11.0** and
  produces `d-0`/`d-1`/`d-2`-style suffixes on bodies, joints, sites, and
  actuators (§2.1).
- **Test:** `model.nq == 21`, `model.nu == 12`, and `mj_id2name` returns three
  distinct thrust-actuator names per drone. **Additionally assert
  `model.key_ctrl[0]` is not all zeros** — see the trap.
- **Trap:** the naive approach — `<include>` the same `x2.xml` three times —
  fails, because every name in it (`x2`, `imu`, `thrust1..4`, `rotor1..4`, the
  `hover` keyframe) is a duplicate. If Task 1 already solved this by hand-editing
  three copies of the airframe, replace that with `<replicate>` now rather than
  maintaining three divergent files.

  **The keyframe trap — corrected, VERIFIED-2.** The first pass said
  `<replicate>` "replicates the keyframe, fix the ctrl vector length". That
  understates it: **the keyframe's contents are lost, not merely resized.**
  Wrapping the X2's `<worldbody>` contents in `<replicate count="3" sep="-">`
  compiles to `nq=21  nv=18  nu=12  nbody=4  nkey=4`, and:
  - `key_ctrl[0]` comes back **all zeros** — the hover values `3.2495625` from
    [x2.xml:69](assets/x2/x2.xml#L69) are **gone**.
  - `key_qpos[0]` places drone 0 at `z=0.3` but drones 1 and 2 at `z=0.1` (the
    body's own `pos`), so the "hover" key is not a hover for two of three.

  Load that key expecting hover and all three drones drop. Because the model
  compiles cleanly and `nkey` looks plausible, this reads as a controller bug.

  **Caveat on my own test (be honest with the professor about this):** I wrapped
  the *entire* `<worldbody>` contents — which also swept in the `<light>` on
  [x2.xml:33](assets/x2/x2.xml#L33) — rather than replicating the `<body>`
  alone. The idiomatic construction may behave differently. **Re-run this check
  with the exact construction you ship before trusting either result.**

---

**T2.3 — Terrain-aware trajectories. [SDF-FREE] · 3 h**

- **Goal:** make the three trajectories respect the terrain — a minimum
  above-ground-level clearance rather than a fixed absolute altitude.
- **Test:** fly all three full trajectories headless; assert
  `min(z_drone − terrain_height(x,y))` over every step stays above the clearance
  threshold, and that `data.ncon` for drone-vs-terrain stays 0.
- **Trap:** sampling terrain height at the *body origin* while the collision
  geometry extends below it — and remember from §2.1 that the pose you stream is
  the body origin, which sits **5.4 cm below the COM**. Small here, but it is the
  same class of error as T1.4 and it compounds with it.

---

### Phase 3 — SDF branch (start only after T0.3 is answered)

---

**Branch (a) — suggestion. T3a.1 · 2 h**

- **Goal:** write `world.xml`'s schema down: what an obstacle entry means, the
  units, the origin convention from T1.1, and how to add one. Half a page.
- **Test:** a person who has not seen the project adds a building at a given
  lat/lon and it appears in the right place on the first try.
- **Trap:** none material. This branch is done.

---

**Branch (b1) — hard requirement, converter. T3b.1–T3b.3 · 4 h each**

- **T3b.1 — Pose and frame composition.** Goal: parse SDFormat `<pose>`
  (`x y z roll pitch yaw`, radians) and compose nested `<model>`/`<link>` poses
  into MJCF `pos` + `quat`. Test: a three-level nested pose fixture converts to
  a transform matching an independently-computed one to 1e-9. Trap: extrinsic
  vs intrinsic Euler order — get it wrong and only *rotated, nested* objects are
  misplaced, which passes every simple test you will write first.
- **T3b.2 — Geometry subset.** Goal: `box`/`sphere`/`cylinder`/`plane`/`mesh`
  → MJCF geoms, with SDFormat's full-extent sizes converted to MuJoCo's
  half-extent/radius convention. Test: a fixture world of one of each renders
  with identical dimensions measured in the viewer. Trap: the size convention
  differs per primitive; a global "divide by two" is wrong for spheres and
  cylinders.
- **T3b.3 — Heightmap.** Goal: SDFormat `<heightmap>` → MuJoCo `<hfield>`.
  Test: reuse T1.3's three-known-pixels test through the converter. Trap: the
  `(radius_x, radius_y, elevation_z, base_z)` semantics (VERIFIED §2.1) versus
  SDFormat's own size vector — unit-test this, do not eyeball it.

---

**Branch (b2) — hard requirement, move to Gazebo.**

Not sequenced here. It is a term-scale rewrite that discards Task 1's MuJoCo
integration and requires re-authoring the X2's inertial properties by hand
(§3.3). If this becomes live, re-plan from scratch — do not treat it as a
continuation of this document.

---

## 5. Critical path

```
T0.3 (email, 15 min)  ─── unblocks Phase 3 branch choice
T0.1 (find Task 1)    ─── unblocks T1.5, T2.2, T2.3, and all visual testing
T0.2 (hygiene)        ─── independent, do while waiting

then:  T1.1 → T1.2 → T1.3 → T1.4 → T1.5 → T2.1 → T2.2 → T2.3 → Phase 3
```

**Tonight, without any answer from the professor, T0.2 and T1.1 are both safe
and both useful.** T0.1 is the highest-value hour in the whole plan.

Total Phase 0–2: **30.25 h** (corrected — the first pass said 27 h and was wrong). Phase 3 adds 2 h (branch a) or 12 h (branch b1).

---

## 6. Open questions for the professor

1. SDFormat or signed-distance-function? (§3.1 — the answer may delete Phase 3.)
2. Real geographic location or synthetic world? If real, which DEM and imagery
   source? (Drives T1.3/T1.4, the two most expensive tasks.)
3. Is there an existing `.world` file we are expected to consume, or would we be
   authoring SDFormat purely to convert it away? (Decides whether b1 is
   justifiable at all.)
4. Does "environment" include weather/wind, or is it geometry only? Nothing in
   the current model has wind; [x2.xml:4](assets/x2/x2.xml#L4) sets
   `density="1.225" viscosity="1.8e-5"`, so aerodynamic drag is already active
   but there is no wind field.

---

## 7. What I did not verify — status after the second pass

**RESOLVED this pass** (were UNVERIFIED in the first):

- ~~Whether `<replicate>` interacts correctly with the `<keyframe>`~~ →
  **Resolved, and it does not.** Contents are lost, not resized. See T2.2. One
  caveat on my test construction is stated there.
- ~~How heightfield elevation data is normalised~~ → **Resolved: min–max, by
  MuJoCo, at load.** See T1.3. This was the highest-value finding of the pass.
- ~~Whether a PNG heightfield needs Pillow~~ → **Resolved: it does not.** MuJoCo
  parses the PNG itself (§2.3).
- ~~Whether Task 1 code exists anywhere in git~~ → **Resolved: it has never been
  committed on any branch, local or remote, in any of the 5 commits that have
  ever existed.** See §1.2. Whether it exists *outside* git remains yours to
  answer.
- ~~"MuJoCo reads MJCF and URDF only"~~ → **Partially resolved.** A minimal URDF
  loads without error via `MjModel.from_xml_path`. The loader set is exactly
  `from_xml_path`, `from_xml_string`, `from_binary_path` (MJB). No SDFormat
  loader exists. I did **not** test URDF coverage beyond a single-link file.

**STILL UNVERIFIED — and here is exactly what each needs:**

- **CesiumJS version and API status.** Needs: you to install Cesium here at a
  chosen version, or point me at the machine holding the front-end. Cannot be
  resolved by me alone. Nothing about Cesium in any of my documents is checked
  against a real installation.
- **The Task 1 implementation** — architecture, WebSocket protocol, 50 Hz
  timing, and *all reported benchmark numbers*. Needs: the code. See DEFENSE.md,
  which treats every Task 1 claim as unevidenced until you produce it.
- **Geoid separation for Corvallis.** Needs: `pyproj` (not installed, §2.3) plus
  a geoid model. Deliberately not quoted. Do not take a number from any document
  I wrote.
- **Runtime performance of anything.** I ran no benchmarks and invented no
  numbers. Every performance statement in this plan is qualitative and flagged
  in §8.
- **SDFormat semantics** (pose convention, heightmap sizing, axis convention).
  Needs: the SDFormat specification, which is not on this machine. Everything I
  wrote about SDFormat in §3.3 is recall, not verification — see §8.

---

## 8. Claims in this document with no citation behind them

Per your instruction: a claim without a citation is a guess. These are the
statements in PLAN.md and SKILL.md that rest on recall rather than on something
I read or executed. **Treat every one as unreliable until checked.** I have left
them in the plan because they are still the right things to *worry* about — but
none of them should be repeated to the professor as fact.

| # | Claim | Where | Status |
|---|---|---|---|
| G1 | Heightfields "collide efficiently"; mesh terrain is "far more expensive to collide" | PLAN §"Decisions", SKILL "Decisions" | **GUESS.** No measurement. The decision may still be right for other reasons (DEM data maps directly onto a grid), but the performance justification is unevidenced. |
| G2 | Heightfield collision cost "scales with the triangles under the contacting geom" | PLAN T1.3 | **GUESS.** Plausible mechanism, not verified against source or measurement. |
| G3 | A full-resolution DEM "will collapse the step rate" | PLAN T1.3 | **GUESS.** Unmeasured. Direction is likely right; magnitude entirely unknown. |
| G4 | A DEM tile is "several thousand × several thousand" | PLAN T1.3 | **GUESS.** Varies by product. Read your DEM's metadata. |
| G5 | DEM nodata is "often −9999 or −32768" | PLAN T1.3 | **GUESS.** Product-dependent. |
| G6 | USGS DEM products are "typically orthometric" | PLAN T1.4 | **GUESS.** Must be read from the product's own metadata. |
| G7 | Geoid separation in the Pacific Northwest is "tens of metres", negative | PLAN T1.4, SKILL "stop and ask" | **GUESS, and I told you not to trust it in the same breath.** No geoid model installed. The *phenomenon* is real; the magnitude is recall. |
| G8 | SDFormat `<pose>` is `x y z roll pitch yaw`, radians, extrinsic XYZ | PLAN §3.3 | **GUESS.** No SDFormat spec on this machine. Check the spec before writing any converter. |
| G9 | "SDFormat is Z-up like MJCF, so that part is free" | PLAN §3.3 | **GUESS.** Unverified against the spec. |
| G10 | SDFormat `<heightmap>` size semantics "differ from" MuJoCo's | PLAN §3.3 | **GUESS.** I verified MuJoCo's side only. The SDFormat side is recall. |
| G11 | "Cesium has renamed and removed public API across major versions" | PLAN T1.5 | **GUESS.** Nothing installed to check. Generic to most libraries; specifics unknown. |
| G12 | Gazebo "has its own X2-equivalent airframes" | PLAN §3.3 | **GUESS.** Not checked. |
| G13 | `<replicate>` is "the sanctioned multi-drone mechanism" | SKILL "Decisions" | **PARTLY.** That it *works* is verified. That it is the *recommended* approach is my judgement, not a documented endorsement. |
| G14 | ENU "matches the X2's Z-up body frame" | SKILL invariant 3 | **NOW CITED.** The four thrust actuators use `gear="0 0 1 ..."` ([x2.xml:56-59](assets/x2/x2.xml#L56-L59)), i.e. thrust along body **+Z**. The body frame is Z-up. Upgraded from guess to VERIFIED-2. |
| G15 | Time estimates (2 h / 3 h / 4 h per task) | PLAN §4 throughout | **GUESSES, all of them.** No task has been executed. They are planning aids, not measurements — do not present them to the professor as estimates grounded in anything. |

Cited and re-confirmed this pass (these are *not* guesses): every `file:line`
reference in §1 and §2 was re-read and holds exactly — `x2.xml` lines 3, 4, 8,
38, 39-42, 43-47, 56-59, 69; `scene.xml:21`; `probe.py:5,19`; `view.py:4,8`;
`drill.py:11-13`. The 8924/8912/12 file counts re-confirmed. `mjmodel.h:687`
(hfield_size), `:386-390` (body_ipos/iquat/inertia) newly cited.
