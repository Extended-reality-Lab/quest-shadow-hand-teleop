# REPRO.md — specification for regenerating the Task 1 numbers

**This is a specification, not an implementation.** It describes what a
`bench.py` must do so that `0.10 m RMS`, `0.57 m`, and `RTF 0.998` can be
regenerated on demand instead of asserted.

**Starting position: none of these numbers is currently reproducible.** No
controller, no trajectory generator, no metrics harness, and no results file
exists in the repo or in any commit. Every parameter below is currently
undefined — that is the point of the document.

---

## 1. What the script must run

Four stages, in order, all headless (no viewer, no WebSocket):

1. **Load** `assets/x2/scene.xml` — or the multi-drone scene, if the claim being
   reproduced is a multi-drone claim. Record which.
2. **Initialise** to a defined state. The model ships a hover keyframe at
   [x2.xml:69](assets/x2/x2.xml#L69). **Record whether the run starts from that
   keyframe or from an arbitrary pose** — this alone changes the transient and
   therefore the RMS. Note the `<replicate>` keyframe hazard in PLAN.md T2.2: in
   a replicated scene the hover keyframe's ctrl values come back **all zeros**,
   so "started from hover" may silently mean "started from zero thrust".
3. **Fly** the named trajectory for a defined duration, stepping the physics and
   recording, at every step: sim time, commanded position, achieved position.
   Achieved position must be explicitly either the body origin (`qpos[0:3]`) or
   the COM — they differ by **5.4 cm** vertically (PLAN.md §2.1). **Record which.**
4. **Report** the metrics in §3 with the full parameter block in §2.

Run each configuration **N times** and report spread, not a single value. One
run is an anecdote.

---

## 2. Parameters the script must record — every one is currently undefined

Nothing in the repo defines any of these. The script must print all of them
alongside the result, so a number is never separable from its conditions.

### 2.1 Trajectory geometry — UNDEFINED

| Parameter | Why it changes the answer |
|---|---|
| Trajectory type (`circle`, `survey`) | The two claims differ 5.7× |
| Circle radius | Larger radius at fixed speed → lower lateral acceleration → lower error |
| Circle plane and centre | A circle in the horizontal plane is a different control problem from a tilted one |
| Number of laps | Determines how much of the run is steady-state |
| Survey leg length, leg spacing, number of legs | Undefined entirely — "survey pattern" names nothing specific |
| Survey turn geometry (square, radius, or stop-and-turn) | **This is probably where the 0.57 m lives.** A square turn commands an infinite-acceleration corner |
| Altitude, and whether it is constant | A climbing trajectory couples into the thrust axis |

### 2.2 Speed and timing — UNDEFINED

| Parameter | Note |
|---|---|
| Commanded speed (m/s) | Error scales strongly with it. Must be stated |
| Speed profile | Constant, or trapezoidal with accel/decel limits |
| Total duration (s) and total steps | |
| Physics timestep | Currently `0.01` s at [x2.xml:4](assets/x2/x2.xml#L4). **If the benchmark used a different timestep, the number is not comparable** |
| Sampling rate of the error signal | Every step (100 Hz) or every stream frame (50 Hz)? RMS over 100 Hz samples ≠ RMS over 50 Hz samples |

### 2.3 The RMS definition — UNDEFINED, and the highest-leverage ambiguity

State all four explicitly:

1. **RMS of what?** Full 3-D position error magnitude, horizontal-only error, or
   per-axis RMS reported as one number? These differ substantially.
2. **Against what reference?** Commanded setpoint at time *t*, or nearest point
   on the geometric path? **These are different metrics.** Cross-track distance
   to the path ignores lag along the path; error against the timed setpoint
   includes it. A controller that flies the exact circle one second late has
   near-zero cross-track error and large setpoint error.
3. **Is the transient excluded?** If so, state the discard window in seconds and
   how it was chosen. Silently discarding the first lap can move the number by
   an order of magnitude.
4. **Aggregation across drones.** Per-drone RMS, or pooled across all three?

### 2.4 Controller — UNDEFINED

None of this exists in the repo; [drill.py:11](drill.py#L11) has a `kp = 2`
that reaches no actuator.

- Controller structure and every gain
- Control update rate vs. physics rate
- Actuator saturation: `ctrlrange="0 13"` per motor
  ([x2.xml:9](assets/x2/x2.xml#L9)). **Record the fraction of steps at
  saturation** — a trajectory flown at saturation is a different claim
- Whether the model's own hover thrust `3.2495625`
  ([x2.xml:69](assets/x2/x2.xml#L69)) is used as feed-forward

### 2.5 Environment — partly defined

- Air density and viscosity: `density="1.225" viscosity="1.8e-5"`
  ([x2.xml:4](assets/x2/x2.xml#L4)) — already set, so drag is active. Record it
- Wind: none exists. Record as zero
- Gravity: MuJoCo default. Record the actual value read from the model
- Number of drones in the scene, and whether they can collide

### 2.6 Hardware and versions

Machine identity, core count, whether on battery or mains (macOS throttles on
battery), Python version, and every pin from `requirments.txt`. Verified
present today: Python 3.12.3, mujoco 3.11.0, numpy 2.5.2. Print
`mujoco.mj_versionString()` rather than trusting the file.

---

## 3. What the script must print

One machine-readable block (JSON or equivalent) plus a human summary. The block
must contain the full §2 parameter set **and** the results, so no number ever
travels without its conditions. At minimum:

- Every parameter from §2.
- Per-configuration: `rms`, `max_error`, `median_error`, and a high percentile —
  the max matters because a 0.10 m RMS with a 3 m excursion at one corner is not
  a well-tracked trajectory.
- **For the survey pattern: per-segment error, split straight-leg vs. turn.**
  This is the single most useful output, because it answers the reviewer's
  sharpest question (DEFENSE.md C2) before it is asked.
- Actuator saturation fraction.
- The RTF fields in §4.
- `N` runs, with mean and spread.
- Git commit SHA and whether the working tree was dirty.

Write results to a versioned file. A number that exists only in terminal
scrollback is not reproducible.

---

## 4. RTF — where to check for the sleep artifact

**Check this first. `0.998` is suspicious precisely because it is just under
1.0, which is what a sleep-throttled loop produces by construction.**

**Where to look:** [view.py:11-14](view.py#L11-L14) is the only sim loop in the
repo and it has exactly the dangerous shape — `mj_step`, `viewer.sync()`, then
`time.sleep(model.opt.timestep)` on [view.py:14](view.py#L14). Any RTF measured
by wrapping a timer around a loop of that shape measures the sleep. If the Task 1
benchmark loop was derived from `view.py`, **the number is an artifact and must
be withdrawn rather than defended.**

The rule: **the benchmark must not contain any sleep, any `viewer.sync()`, and
any WebSocket send inside the timed region.** If pacing is needed for the live
demo, that is a different loop from the benchmark loop.

RTF must be defined and reported as: (simulated time advanced) ÷ (wall-clock
time spent in the timed region), where the timed region contains only the
physics stepping and the control computation.

Report all of:

- RTF headless, 1 drone, no rendering, no networking — the pure solver number.
- RTF headless, 3 drones — the number that matches the actual claim.
- RTF with rendering and streaming — the user-facing number, which **is**
  legitimately affected by pacing and should be labelled as such.
- Steps per second, and mean wall-clock time per step. **Report these
  alongside RTF** — they cannot be faked by a sleep, so they are the honest
  measure of solver speed, and they make a throttled RTF obvious immediately.
- Whether any sleep, sync, or send existed inside the timed region: an explicit
  boolean in the output.

---

## 5. Dependency note

`scipy`, `matplotlib`, and `pandas` are **not installed** (PLAN.md §2.3). The
harness is limited to `numpy` and `print` unless dependencies are added. This is
not a blocker — RMS and percentiles need only `numpy` — but there are no plots
without a new dependency.

---

## 6. Honest framing if the numbers cannot be regenerated

If the producing code cannot be found, the correct move is to say the numbers
are not currently reproducible and give the date they will be — not to repeat
them. A number you cannot regenerate on request is a liability in front of a
reviewer, and repeating it after discovering it is unreproducible is materially
worse than withdrawing it.
