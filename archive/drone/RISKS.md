# RISKS.md — what makes Task 2 fail *late*

Ranked by **cost of discovering it late**, not by likelihood. A cheap bug found
in week one is not a risk; an invisible wrong number you build three weeks of
work on top of is.

The organising observation: **the expensive failures in this project all share a
shape — the model compiles, the viewer looks plausible, and the number is
silently wrong.** None of the top five raises an error.

---

## R1 — The vertical datum is wrong, and everything is calibrated around it

**Cost if late: catastrophic.** Discovering this after you have tuned a
controller, set clearance margins, and recorded results means every altitude
number in the project is wrong by a constant, and every tuning decision made to
compensate is also wrong. Fixing the datum then *breaks* a system that appeared
to work.

- **Why it survives review:** the error is a near-constant offset. The drone
  flies level, tracks its trajectory, and the only symptom is that it sits at a
  consistently odd height above terrain — which reads as a controller trim issue.
- **Detection, cheaply, now:** one ground-truth point with an independently known
  elevation, asserted in a test, before any controller work. T1.4.
- **Status:** unresolved and unresolvable here — `pyproj` is not installed and no
  geoid model is present (PLAN.md §2.3). I have quoted no separation value
  anywhere; PLAN.md §8 G7 marks my earlier "tens of metres" as a guess.

## R2 — Terrain elevation scale is destroyed at load and nobody notices

**Cost if late: very high.** **VERIFIED, not speculative** (PLAN.md T1.3):
MuJoCo min–max normalises heightfield data, whether it comes from a PNG or from
an inline `elevation` attribute. A DEM spanning 100..200 loads as 0..1.

- **Why it survives review:** the terrain has the right *shape*. Hills are where
  hills should be. Only the vertical scale is wrong, and it is wrong by a factor
  that depends on the data range — so it looks like terrain, just not *your*
  terrain.
- **Compounding failure:** each hfield normalises **independently**. Two adjacent
  tiles with different elevation ranges will not meet at the seam. If you
  discover this after building a multi-tile world, the fix is re-exporting every
  tile against a common range.
- **Worst variant:** a single nodata pixel sets the minimum, and all real terrain
  collapses into a thin band near 1.0. The terrain looks *flat*, and you will
  suspect your resampling code for a day before suspecting one pixel.
- **Detection:** assert three known DEM elevations against ray-cast terrain
  heights (T1.3's test). Cheap, and it catches all three variants.

## R3 — The terrain is mirrored north–south

**Cost if late: very high.** **VERIFIED** (PLAN.md T1.3): the first row of the
XML `elevation` attribute lands at **+Y (north)**, but `hfield_data[0]` in memory
is the **last** XML row, i.e. **−Y (south)**. The two orderings run opposite ways.

- **Why it survives review:** a mirrored landscape is a perfectly plausible
  landscape. Hills are the right size and shape, in the wrong places. Nothing
  errors, nothing looks broken, and the drone flies over it happily.
- **Why it hits you specifically:** any DEM large enough to matter gets written
  programmatically into `model.hfield_data`, not as XML text — which is exactly
  the path that mirrors.
- **When it surfaces:** the first time someone overlays the MuJoCo terrain on
  Cesium imagery and the rivers run the wrong way. By then the trajectories are
  authored against mirrored terrain.
- **Detection:** ray-probe a known asymmetric feature and assert which side is
  higher. Do not eyeball it.

## R4 — Task 1's numbers cannot be regenerated

**Cost if late: high, and reputational rather than technical.** If the professor
asks for the circle/survey/RTF numbers late in the term and there is no script,
the numbers must be withdrawn *after* Task 2 has been built on the assumption
that Task 1 was sound.

- **Specific technical trap inside this:** RTF measured around a loop containing
  `time.sleep(...)` measures the sleep. [view.py:14](view.py#L14) has exactly
  that shape, and `0.998` is what a sleep-throttled loop produces by
  construction. See REPRO.md §4 and DEFENSE.md C3.
- **Detection:** now, by looking. It costs ten minutes and it is the single
  highest-return check in this document.

## R5 — The replicated hover keyframe is dead and it reads as a controller bug

**Cost if late: high**, because it burns debugging time in the wrong place.
**VERIFIED** (PLAN.md T2.2): wrapping the X2 in `<replicate>` yields `nkey=4`
with `key_ctrl[0]` **all zeros** — the `3.2495625` hover values are gone — and
`key_qpos[0]` placing only drone 0 at `z=0.3`.

- **Why it survives review:** the model compiles cleanly and `nkey` looks
  plausible. Loading the "hover" key drops all three drones, which looks exactly
  like a controller that cannot hold altitude. You will tune gains for a day.
- **Detection:** assert `key_ctrl[0]` is not all zeros (T2.2's corrected test).
- **Caveat:** my test wrapped the whole `<worldbody>` including the `<light>`.
  Re-run with the construction you actually ship.

## R6 — Cesium is an entirely unaudited dependency

**Cost if late: high and unbounded — this is the largest *unknown* in the
project.** Not because Cesium is fragile, but because **nothing about it has been
verified.** There is no Cesium in this repo, on this machine, or in any commit
that has ever existed. No version has ever been pinned.

Everything I or anyone else has written about the Cesium side of this project is
about a library that is not present. Concretely unknown: which version, whether
the Task 1 code uses current API, how the origin is transformed client-side,
whether terrain and drone altitudes share a datum (see R1), and what happens when
frames arrive late.

- **Detection:** T1.5 — install it, pin it, read its own `CHANGES.md` and type
  declarations. **Until then treat every Cesium-side estimate in every document
  as unfounded**, including mine.

## R7 — Heightfield collision cost is unmeasured

**Cost if late: moderate to high.** If terrain resolution has to drop late, the
DEM pipeline, the georeferencing tests, and possibly the trajectories are all
touched.

- **Honesty:** I have **not measured this**. PLAN.md §8 G1/G2/G3 mark my
  performance statements as guesses. The direction is plausible; the magnitude is
  unknown, and I will not invent one.
- **Detection:** measure steps/second at your intended resolution *before*
  building on it. Steps/second and wall-clock per step cannot be faked by a
  sleep — unlike RTF (R4).

## R8 — Scope reopens because the SDF question was never answered

**Cost if late: schedule-fatal rather than technical.** If "SDF" turns out to
mean SDFormat and the answer arrives in the final weeks, branch (b1) is ~12 h of
converter work that was never budgeted, and branch (b2) is a term-scale rewrite.

- **Mitigation:** T0.3, a 15-minute email, unanswered as of 2026-08-18.
- **Note the upside:** the answer may *delete* work — MuJoCo 3.11.0 supports
  signed-distance functions natively (`libsdf_plugin.dylib`).

## R9 — Georeference origin drifts because it exists in two places

**Cost if late: moderate.** A hardcoded origin in JS and another in Python drift
apart. The symptom is a small constant offset — easily confused with R1, which is
what makes it expensive: you will fix the wrong one first.

- **Detection:** SKILL.md invariant 2 — one source of truth, serialised to the
  client on connect. Enforce it before the front-end exists, not after.

## R10 — Dependencies for the DEM pipeline are not installed

**Cost if late: low-moderate.** `pyproj`, `rasterio`, GDAL, Pillow, scipy,
matplotlib, pandas — **none installed** (PLAN.md §2.3, verified by import).
T1.3/T1.4 cannot start without adding them.

- **Mitigating detail, verified:** MuJoCo parses PNG heightfields itself, so the
  hfield step adds no Python imaging dependency. Only reading the source DEM does.
- **Interaction with repo hygiene:** adding dependencies while `.venv/` is
  committed produces thousand-file diffs. Do T0.2 first.

## R11 — `x2.xml:3` becomes a parse error

**Cost if late: low** — it fails loudly and immediately, which is the good kind
of failure. Listed only because it is a known live defect.

The stray `// TIMESTEP HERE IS 0.01 seconds` at
[x2.xml:3](assets/x2/x2.xml#L3) is legal XML character data *by luck*. It becomes
fatal the moment anyone types a `<` or bare `&` into it. Correct form is
`<!-- ... -->`.

---

## Deprecated / removed API in the pinned versions

### MuJoCo 3.11.0 — VERIFIED against the shipped headers

Loading `assets/x2/scene.xml`, constructing `MjData`, and stepping raises
**zero** Python warnings (`python -W all`, `warnings.simplefilter('always')`).
Nothing currently in this repo uses a deprecated API.

Deprecations that exist in the shipped headers, and which of them you are likely
to hit in Task 2:

| Symbol | Marked at | Relevance to Task 2 |
|---|---|---|
| `mjContact.geom1` / `.geom2` | `include/mujoco/mjdata.h:57-58` — *"deprecated, use geom[0]"* / *"geom[1]"* | **This is the one you will actually hit.** T2.1 and T2.3 both test contacts. Filtering drone-vs-terrain contacts by `contact.geom1` is the natural thing to write. **Verified: both spellings work today** — `contact.geom1, contact.geom2` and `contact.geom[0], contact.geom[1]` return the same ids. Write the array form. |
| `njmax`, `nconmax`, `nstack` | `include/mujoco/mjspec.h:227-229`; also `mjmodel.h:336-337` marked *(legacy)* | Only if you hand-tune constraint buffers for terrain collision. Do not. |
| legacy error/warning handlers | `include/mujoco/mujoco.h:48` — *"prefer `mju_setLogHandler`"* | Only if you install a custom error handler. |
| compiler-warning check | `include/mujoco/mujoco.h:1030` — *"use `mjs_numWarnings(s) > 0`"* | Only if you build models via `MjSpec` and inspect warnings. |
| `mjMESH_INERTIA_LEGACY` | `include/mujoco/mjspec.h:69` | Only if you set mesh inertia explicitly. The X2 does not. |

**Not checked:** whether MuJoCo 3.11.0 removed anything that older tutorials
still use. I checked what is *marked* deprecated in the shipped headers; I did
not diff 3.11.0 against earlier releases. **UNSURE** — if you follow a tutorial
written against MuJoCo 2.x, verify each call against `help()` in this install.

### CesiumJS — NOT CHECKABLE

**No CesiumJS is installed in this project, on this machine, or in any commit
that has ever existed. No version has ever been pinned.**

I therefore cannot list a single deprecated or removed Cesium API, and I have not
guessed one. PLAN.md §8 G11 marks my earlier general claim about Cesium API churn
as an unverified guess. **This section can only be written after T1.5.** Anyone
who hands you a list of deprecated Cesium calls for this project without
installing it first is making it up.

---

## The cheapest checks, in order

1. **Is there a sleep inside the RTF timed region?** (R4) — ten minutes, and it
   may require withdrawing a number you have already reported.
2. **Send the SDF email.** (R8) — fifteen minutes, may delete 12 h of work.
3. **Assert terrain orientation and elevation scale before anything is built on
   the terrain.** (R2, R3) — one ray-probe test, kills the two worst silent bugs.
4. **Assert `key_ctrl[0]` is non-zero after replication.** (R5) — one line, saves
   a day of gain-tuning.
5. **Pin one georeference origin before the front-end exists.** (R9)
