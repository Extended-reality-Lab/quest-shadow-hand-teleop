# LEARNING.md — what to understand before writing each task yourself

One concept per task, the smallest source that teaches it, a worked example that
**already exists and you can open right now**, and three questions to answer
before you start. **The questions are deliberately unanswered.** No code here is
copyable — that is the point.

## A note on sources

Every path below beginning `.venv/lib/python3.12/site-packages/mujoco/` is **on this machine** and I have opened it.
Paths in `assets/` are in your repo.

Where a task needs something *not* on this machine — the SDFormat specification,
CesiumJS documentation, geodesy references — **I have named the document but not
a URL.** I could not verify a URL from here, and a wrong link wastes more of your
time than no link. Those are marked **OFF-MACHINE**.

---

## T0.1 — Reconcile Task 1 with reality

**MECHANICAL.** No new concept. It is a search-and-decide task, and the search is
already done (PLAN.md §1.2): the code is not in git, on any branch, in any of the
5 commits, or on the remote. What remains is your decision about what exists
off-git.

---

## T0.2 — Repo hygiene

**MECHANICAL**, with one concept worth five minutes.

- **Concept:** `.gitignore` only affects **untracked** files. Adding `.venv/`
  to it does nothing to the 8912 files already tracked — those need
  `git rm --cached`. People add the ignore rule, see no change, and conclude
  it is broken.
- **Source:** `man gitignore`, the section on which files the patterns apply to.
- **Worked example:** none needed.
- **Self-check:** (1) After `git rm -r --cached .venv`, are the files still on
  disk? (2) Does the history shrink? (3) What breaks for someone who already
  cloned the repo?

---

## T0.3 — Send the SDF disambiguation question

**MECHANICAL.** The concept — that "SDF" names two unrelated things — is already
in PLAN.md §3.1. Writing the email needs nothing further.

---

## T1.1 — Georeference origin

**Concept: a local tangent plane is an approximation to a curved surface, and it
has a usable radius.** ENU coordinates treat a patch of the ellipsoid as flat.
The error grows with distance from the origin. You must be able to state your
working radius and the error at its edge — otherwise you cannot defend the
choice of origin at all.

- **Source (OFF-MACHINE):** any geodesy reference covering *geodetic to ECEF to
  ENU* conversion. Look specifically for the WGS84 defining parameters
  (semi-major axis, flattening) and the standard ECEF→ENU rotation. I could not
  verify a URL; do not take one from me.
- **Worked example:** **none on this machine.** `pyproj` is not installed
  (PLAN.md §2.3). This is the one task with no local example — treat that as a
  signal to be extra careful, and to write the round-trip test in T1.1 *first*.
- **Self-check:** (1) At what distance from your origin does the flat-plane
  approximation exceed your accuracy target? (2) Which of the three ENU axes is
  affected by the ellipsoid's flattening, and why is it not all three equally?
  (3) If the origin moves 100 m, which parts of the system must change?

---

## T1.2 — Plane → heightfield

**Concept: MuJoCo's heightfield is a normalised grid stretched over a box whose
horizontal dimensions are radii, and whose vertical extent is set separately
from the data.** The data carries *shape*; `size` carries *scale*. Conflating
them is the whole difficulty.

- **Source (ON MACHINE):**
  `.venv/lib/python3.12/site-packages/mujoco/include/mujoco/mjmodel.h` **lines 687-692** — the authoritative field
  documentation. Line 687 defines `hfield_size` as `(x, y, z_top, z_bottom)`.
  Read those six lines before anything else; they are more precise than any prose.
  Also `.venv/lib/python3.12/site-packages/mujoco/include/mujoco/mjspec.h` **lines 543-552**, `mjsHField`.
- **Worked example (ON MACHINE, open this):**
  `.venv/lib/python3.12/site-packages/mujoco/testdata/model.xml` — a complete inline `<hfield>` with
  `nrow="3" ncol="3" size=".2 .2 .03 .03"` and a 3x3 `elevation` attribute.
  It is nine numbers; you can hold the whole thing in your head. Compare against
  the ground plane in [assets/x2/scene.xml:21](assets/x2/scene.xml#L21) that you
  are replacing.
- **Self-check:** (1) A heightfield with `size="10 10 2 0.5"` — how many metres
  across is it? (2) Which of the four numbers changes if you want the same
  terrain shape twice as tall? (3) Where is the hfield's z origin relative to the
  geom's `pos`?

---

## T1.3 — DEM → heightfield

**Concept: MuJoCo destroys your elevation scale on load, and stores rows in the
opposite order from the XML.** Both are verified in PLAN.md T1.3. This task is
90% understanding those two facts and 10% resampling.

- **Source (ON MACHINE):** the same `mjmodel.h:687-692`, but this time read
  `hfield_data` (line 691, "elevation data") **against the behaviour I
  measured** — the header does not tell you it is min–max normalised. That gap
  between what the header says and what the code does is the lesson.
- **Worked example (ON MACHINE, open this):**
  `.venv/lib/python3.12/site-packages/mujoco/specs_test.py` **lines 1521-1537**, `test_incorrect_hfield_size` — an
  existing test of hfield sizing failures, i.e. someone else's worked example of
  exactly the mistake you are about to make. Also `specs_test.py:230-233` for
  the minimal `add_hfield` construction.
- **Self-check:** (1) If your DEM spans 60 m to 140 m, what must `z_top` and
  `z_bottom` be for the loaded terrain to sit at true elevation? (2) You load
  two adjacent tiles, one spanning 60-140 m and one 60-90 m — what happens at the
  seam, and why? (3) You assign a north-up DEM array straight into
  `model.hfield_data`. Which compass direction ends up wrong, and what would
  you measure to detect it?

---

## T1.4 — Vertical datum

**Concept: "height" is meaningless without naming its reference surface.** An
ellipsoidal height is measured from a smooth mathematical figure; an orthometric
height is measured from the geoid, which is a gravity equipotential surface. The
difference between them varies by location. Every altitude in your system is one
or the other, and you must know which at every boundary.

- **Source (OFF-MACHINE):** a geodesy text or national mapping agency
  documentation on the **geoid–ellipsoid separation** (often written *N*), and
  the metadata of the specific DEM product you choose — **the product's own
  metadata is the authoritative source for which datum it uses**, not any general
  reference. I have deliberately not quoted a separation value anywhere; PLAN.md
  §8 G7 marks my earlier "tens of metres" as a guess.
- **Worked example:** **none on this machine**, and no geoid model is installed.
- **Self-check:** (1) Which of the two heights would a barometric altimeter
  approximate, and which would a GNSS receiver report natively? (2) If you add
  *N* where you should subtract it, is the resulting error `N` or `2N`?
  (3) Your terrain and your drone use different datums — does the error vary as
  the drone flies across the scene, or stay constant, and what does that tell you
  about how to detect it?

---

## T1.5 — Cesium install and API audit

**Concept: the installed package is the only authority on its own API.** Not
documentation, not a tutorial, not me.

- **Source:** the `CHANGES.md` and the TypeScript declaration file **inside the
  version you install**. **OFF-MACHINE** — nothing Cesium exists here, so I
  cannot name a file or a version, and PLAN.md §8 G11 marks my earlier claim
  about Cesium API churn as an unverified guess.
- **Worked example:** none available until you install it.
- **Self-check:** (1) Where in an installed npm package do you find its API
  surface without internet access? (2) How do you tell a deprecated-but-working
  call from a removed one? (3) What pins the version for the next person who
  clones — and is a caret range a pin?

---

## T2.1 — Static obstacles in MJCF

**Concept: MJCF's default-class inheritance.** Geoms inherit from
`<default class="...">`, and a geom's final properties come from the class
chain, not only its own attributes. Miss this and you will write obstacles that
are invisible, massless, or non-colliding without any error message.

- **Source (ON MACHINE):** [assets/x2/x2.xml:6-22](assets/x2/x2.xml#L6-L22) —
  your own file, a compact nested `<default>` block with classes `x2`,
  `visual`, `collision`, `rotor`. Read it against lines 38-47 and work out
  where each geom's properties come from. **This is the best available example
  and it is already in your repo.**
- **Worked example (ON MACHINE):** the same lines. Note especially
  [x2.xml:8](assets/x2/x2.xml#L8) `<geom mass="0"/>` — one line that makes
  every non-explicit geom in the model massless.
- **Self-check:** (1) Why does [x2.xml:47](assets/x2/x2.xml#L47) carry
  `class="visual"` yet have mass? (2) What do `contype`/`conaffinity` on
  line 12 do, and what would happen to your buildings if you copied that class?
  (3) Which group do collision geoms use here, and why does the viewer not show
  them by default?

---

## T2.2 — Three drones

**Concept: `<replicate>` is a compile-time macro that rewrites names, and it
rewrites more than you expect.** It is not instancing — the model is expanded
before compilation, and elements you did not mean to duplicate (keyframes,
lights) come along.

- **Source (ON MACHINE):** `.venv/lib/python3.12/site-packages/mujoco/include/mujoco/mjspec.h` for the spec-level
  view of what elements exist and can be duplicated. The verified behaviour is in
  PLAN.md T2.2 — `nkey=4`, `key_ctrl[0]` all zeros.
- **Worked example (ON MACHINE):** `.venv/lib/python3.12/site-packages/mujoco/specs_test.py` — 2356 lines of
  worked model-construction, including `add_key` at line 236. Search it for
  keyframe handling. Also compare `.venv/lib/python3.12/site-packages/mujoco/bindings_test.py`, which exercises
  `key_ctrl`.
- **Self-check:** (1) After replication, what is the length of `data.ctrl`, and
  which slice belongs to drone 1? (2) Why does the hover keyframe stop being a
  hover? (3) The `<light>` at [x2.xml:33](assets/x2/x2.xml#L33) has
  `mode="targetbodycom" target="x2"` — what happens to it under replication, and
  is that what you want?

---

## T2.3 — Terrain-aware trajectories

**Concept: querying terrain height is a ray cast, not an array lookup.** You
need the height under an arbitrary `(x, y)`, which falls between grid cells.
MuJoCo has a ray API for exactly this, and using it avoids reimplementing
interpolation and the row-order trap from T1.3.

- **Source (ON MACHINE), and you can read this without leaving the terminal:**
  `.venv/bin/python -c "import mujoco; help(mujoco.mj_rayHfield)"` — the
  docstring gives the exact signature and states it returns nearest distance or
  `-1` for no intersection. Same for `mujoco.mj_ray`. **Verified present in
  3.11.0.**
- **Worked example (ON MACHINE):** `.venv/lib/python3.12/site-packages/mujoco/rollout.py` — DeepMind's own
  implementation of rolling trajectories out from initial states. It is the
  closest thing in this install to a trajectory harness, and it is worth reading
  before writing your own loop.
- **Self-check:** (1) If you cast a ray straight down from high above, what does
  a return value of `-1` mean, and when can it happen over valid terrain?
  (2) Should clearance be measured from the body origin or the lowest collision
  geom — and how far apart are they on the X2? (3) Why is a ray cast per step
  potentially a bad idea at 100 Hz across three drones, and what would you
  measure before worrying about it?

---

## T3a.1 — Document the MJCF world schema (branch a)

**MECHANICAL.** Writing down decisions you have already made. No new concept.

---

## T3b.1 — SDFormat pose composition (branch b)

**Concept: rotation conventions do not commute, and "Euler angles" names a
family, not a convention.** You must know the axis order, whether rotations are
intrinsic or extrinsic, and the units, before a single conversion is correct.

- **Source (OFF-MACHINE):** the **SDFormat specification**, the `<pose>`
  element. PLAN.md §8 G8/G9 marks my description of SDFormat's pose convention as
  an unverified guess — **read the spec, do not take it from PLAN.md.**
- **Worked example (ON MACHINE, for the MJCF half only):**
  [assets/x2/x2.xml:36](assets/x2/x2.xml#L36) uses `xyaxes`;
  [x2.xml:38](assets/x2/x2.xml#L38) uses `quat="0 0 1 1"` unnormalised;
  [x2.xml:42](assets/x2/x2.xml#L42) uses `quat="1 0 0 1"`. Three different
  orientation notations in one file — work out what each means and you understand
  the MJCF side.
- **Self-check:** (1) Is `quat="0 0 1 1"` a valid unit quaternion, and if not
  what does MuJoCo do with it? (2) For extrinsic vs intrinsic XYZ Euler angles,
  which composition order differs and does it matter for a single rotation?
  (3) Given nested model→link→geometry poses, in what order do they compose?

---

## T3b.2 — SDFormat geometry subset (branch b)

**Concept: size conventions differ per primitive.** Half-extents versus full
extents, radius versus diameter. There is no single scale factor that converts a
whole format.

- **Source (OFF-MACHINE):** SDFormat spec, `<geometry>` element, per shape.
- **Worked example (ON MACHINE):** [assets/x2/x2.xml:39-47](assets/x2/x2.xml#L39-L47)
  — boxes with `size=".06 .027 .02"` and ellipsoids with `size=".13 .13 .01"`.
  Determine from the rendered model whether those are half-extents or full, and
  you have learned the MJCF convention by measurement rather than by assumption.
- **Self-check:** (1) Is MJCF box `size` a half-extent or a full extent?
  (2) Does the same answer hold for `sphere` and `cylinder`? (3) Which
  primitives take fewer size numbers than they have dimensions, and what fills in?

---

## T3b.3 — SDFormat heightmap (branch b)

**Concept: two formats' heightmap sizing conventions, plus the normalisation and
row-order traps from T1.3, compounding.**

- **Source:** SDFormat `<heightmap>` (**OFF-MACHINE**) against
  `mjmodel.h:687` (**ON MACHINE**).
- **Worked example:** `.venv/lib/python3.12/site-packages/mujoco/testdata/model.xml` for the MuJoCo side; nothing
  local for the SDFormat side.
- **Self-check:** (1) Does SDFormat's heightmap size vector mean the same thing
  as MuJoCo's `(x, y, z_top, z_bottom)`? (2) If both formats normalise
  elevation, where does absolute scale live in each? (3) How would you unit-test
  this conversion without opening a viewer?

---

## The one thing worth internalising across all of it

Three of the four costliest traps in this project — heightfield normalisation,
heightfield row order, and the replicated keyframe — share a shape: **the model
compiles cleanly, the viewer looks plausible, and the number is wrong.** None of
them raises an error. The habit that catches all three is asserting a physical
quantity you computed independently, rather than looking at the screen and
judging that it seems about right.
