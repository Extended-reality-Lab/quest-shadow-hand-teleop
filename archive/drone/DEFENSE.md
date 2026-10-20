# DEFENSE.md — Task 1 claims vs. evidence

Prepared 2026-08-18. Nothing here is softened.

**The situation in one paragraph.** Task 1 is described as: three drones on
independent trajectories in one MuJoCo scene, streamed over WebSocket at 50 Hz,
rendered in CesiumJS as two applications, with measured accuracy of 0.10 m RMS
on a circle, 0.57 m on a survey pattern, and a real-time factor of 0.998. **None
of that code, and none of those measurements, exists in this repository or in
any commit that has ever existed in it.** What the repo contains is a stock
Menagerie airframe and four short scripts, two of which do not command the
actuators at all. If the professor asks to see any of it running, there is
currently nothing to show him from this repo.

That is a statement about the repo, not about you. The work may exist elsewhere.
But every row below marked NO EVIDENCE is a question you cannot currently answer
from the artifact you would hand him.

## How the evidence search was done

So you can say precisely what was checked:

- Working tree: `find` for `*.js`, `*.html`, `*.ts`, `*.mjs` outside `.venv/` →
  nothing. Only `.json` is `.vscode/settings.json`.
- `grep -ril` for `cesium`, `websocket`, `RMS`, `RTF`, `circle`, `survey` across
  the project → `RMS`/`RTF`/`circle` appear in **no file**; `websocket` appears
  only as the unused pin in `requirments.txt`.
- The literal strings `0.10`, `0.57`, `0.998` appear only inside
  `assets/x2/assets/X2_lowpoly.obj`, as coincidental substrings of mesh vertex
  coordinates. They are not results.
- Git history: all 5 commits that have ever existed (`6411a0d`, `0cc0242`,
  `8ef89fd`, `50bba56`, `f01b798`), every tree listed → no JS/HTML ever.
- Remote `https://github.com/Jakhangir18/drone-sim.git`: `git ls-remote` returns
  exactly one ref, `refs/heads/main` at `6411a0d`. Nothing unpushed, no branches.
- `git stash list` → empty. Deleted `README.md` recovered → one line,
  `# drone-sim`.

---

## Tier 1 — Fatal if unanswered

These are specific, quantitative, and checkable. A reviewer who asks for one and
gets nothing will discount everything else you say.

### C1. "Circle trajectory tracks to 0.10 m RMS"

- **Evidence:** **NO EVIDENCE.** No trajectory code, no controller, no logging,
  no results file, no plot, in any commit.
- **Reproducible today?** **No.** There is nothing to run. Reproducing it
  requires a controller (does not exist), a circle generator (does not exist),
  and a metrics harness (does not exist). See REPRO.md.
- **Sharpest question:** *"RMS of what against what — commanded position against
  achieved position, sampled at what rate, over how many laps, and did you
  discard the transient while the controller converges?"* A 0.10 m RMS that
  silently excludes the first lap is a different claim from one that does not,
  and the number can move by an order of magnitude depending on the answer. If
  you cannot state the definition, the number means nothing.

### C2. "Survey pattern tracks to 0.57 m"

- **Evidence:** **NO EVIDENCE.** Same as C1. Additionally, "survey pattern" is
  undefined anywhere — no leg length, spacing, turn geometry, or speed.
- **Reproducible today?** **No.**
- **Sharpest question:** *"Why is the survey error 5.7× the circle error?"* This
  is the dangerous one, because it has a good answer and a bad answer. The good
  answer is a specific mechanism — error concentrates at the turns, where the
  velocity direction reverses and the controller saturates. The bad answer is
  not knowing. **If the professor asks where in the pattern the error lives and
  you have no per-segment breakdown, the number reads as a single lucky run.**

### C3. "Real-time factor 0.998"

- **Evidence:** **NO EVIDENCE.**
- **Reproducible today?** **No** — and worse, the one loop shape in the repo
  that resembles a sim loop is [view.py:11-14](view.py#L11-L14), which calls
  `time.sleep(model.opt.timestep)` every step. **An RTF measured around a loop
  containing that sleep measures the sleep, not the solver, and will land just
  under 1.0 by construction.** 0.998 is exactly the value a sleep-throttled loop
  produces.
- **Sharpest question:** *"Is the sleep inside your timed region?"* If it is, the
  number is an artifact and says nothing about compute speed. **Do not present
  this number until you have checked.** Related: *"RTF with how many drones, and
  with rendering on or off?"* — a 1-drone headless RTF is not the 3-drone
  rendered RTF, and only the latter is relevant to the claim. See REPRO.md §4.

### C4. "Three drones stream at 50 Hz over WebSocket"

- **Evidence:** **NO EVIDENCE.** `websockets==17.0.1` is pinned at
  [requirments.txt:10](requirments.txt#L10) but **imported by no file in the
  repo**. That pin is the entire trace.
- **Reproducible today?** **No.**
- **Sharpest question:** *"50 Hz measured at the sender or at the browser, and
  what happens when a frame is late?"* Physics runs at 100 Hz
  ([x2.xml:4](assets/x2/x2.xml#L4), `timestep="0.01"`), so the stream is every
  second step. A reviewer will want to know whether you drop, block, or buffer
  when the client is slow — each choice produces visibly different behaviour, and
  "I send every other step" is not an answer about what the client receives.

### C5. "Rendered in CesiumJS as two separate applications"

- **Evidence:** **NO EVIDENCE.** No Cesium, no `package.json`, no HTML, in the
  repo or on this machine. No version was ever pinned.
- **Reproducible today?** **No.**
- **Sharpest question:** *"Why two applications?"* If the answer is a real
  architectural reason, it is fine. If the honest answer is "they evolved
  separately", say that — a reviewer respects it more than a retrofitted
  rationale, and the follow-up (*"then which one is authoritative when they
  disagree?"*) is the one that actually matters.

---

## Tier 2 — Damaging, but survivable with an honest answer

### C6. "The georeference origin is handled correctly"

- **Evidence:** **NO EVIDENCE.** No constants module, no transform code.
- **Reproducible today?** **No.**
- **Sharpest question:** *"Is your altitude orthometric or ellipsoidal, and
  where is that conversion applied?"* This is the question most likely to expose
  an unnoticed bug, because the symptom is a constant offset that looks
  plausible. If the front-end and the physics disagree about the datum, the
  drones fly at a consistent wrong height and everything still "works". **You
  cannot answer this today, and you should not bluff it.**

### C7. "Physics runs at 100 Hz; the stream is decoupled at 50 Hz"

- **Evidence:** **PARTIAL — the 100 Hz half is solid.**
  [x2.xml:4](assets/x2/x2.xml#L4) sets `timestep="0.01"`, confirmed by loading
  the model (`model.opt.timestep == 0.01`). The 50 Hz half has no evidence.
- **Reproducible today?** **The timestep, yes** — `python probe.py` prints
  `timestep: 0.01 s` from [probe.py:14](probe.py#L14). The stream rate, no.
- **Sharpest question:** *"What happens to the physics when the renderer
  stalls?"* If the sim loop is driven by the WebSocket send, a slow client slows
  physics and the simulation is no longer deterministic.

### C8. "The Skydio X2 model is validated / physically correct"

- **Evidence:** **STRONG.** The airframe is byte-identical to upstream Menagerie
  except one stray comment line — verified by diff against
  `google-deepmind/mujoco_menagerie/main/skydio_x2/x2.xml`. Mass 1.325 kg,
  derived from [x2.xml:43-47](assets/x2/x2.xml#L43-L47).
- **Reproducible today?** **Yes.** `python probe.py` prints
  `total mass: 1.325 kg`, `actuators: 4`, `qpos length: 7`.
- **Sharpest question:** *"You did not author this model — what do you actually
  know about it?"* The defensible answer is the inertial analysis: COM is 5.4 cm
  above the body origin, and the inertia tensor has a real `Ixz = -0.0021`
  coupling because the front rotors sit 3 cm higher than the rear. **That answer
  demonstrates you read the model rather than downloaded it,** and it is the
  strongest single thing you can say in this defense.

### C9. "Task 1 is done and approved in principle"

- **Evidence:** **NO EVIDENCE in the repo**, and this one is about a
  conversation, not code — so the repo's silence is not itself damning.
- **Reproducible today?** N/A.
- **Sharpest question:** *"Approved on the basis of what — a demo, a video, or a
  description?"* If it was approved from a live demo, that demo is your evidence
  and you should locate the code that produced it **before** the meeting.

---

## Tier 3 — Defensible today

### C10. "The model loads and simulates"

- **Evidence:** [probe.py](probe.py), [view.py](view.py).
- **Reproducible today?** **Yes**, and this is your one live demo:
  `python probe.py` steps 1000 times and prints altitude every 100 steps.
- **Sharpest question:** *"Your drone falls. Where is the controller?"* Both
  scripts leave `data.ctrl` at zero, so they simulate a brick. **Say this before
  he notices it.** The model ships a hover keyframe at
  [x2.xml:69](assets/x2/x2.xml#L69) with `ctrl="3.2495625 …"` that neither
  script loads — knowing that, and saying so, converts an embarrassment into
  evidence that you understand the model.

### C11. "MuJoCo 3.11.0, pinned dependencies"

- **Evidence:** [requirments.txt](requirments.txt), all 11 pins.
- **Reproducible today?** **Yes.** `pip freeze` matches the file exactly;
  `mujoco.mj_versionString()` returns `3.11.0`.
- **Sharpest question:** *"Why is the virtualenv committed?"* 8912 of 8924
  tracked files are `.venv/`. There is no `.gitignore`. It is indefensible on
  the merits; the answer is "that is a mistake and it is being fixed" (PLAN.md
  T0.2), not a justification.

---

## What to do before the meeting

Ranked by return on effort:

1. **Find the Task 1 code, or decide to say plainly that it is not in the
   repo.** Everything in Tier 1 turns on this. Going in with numbers you cannot
   show is far worse than going in saying "the code is on another machine, here
   is the plan to consolidate it".
2. **Check whether the RTF measurement includes a sleep** (C3). If it does, the
   number must be withdrawn, not defended.
3. **Write down the RMS definition and the trajectory parameters** (C1, C2).
   REPRO.md lists exactly what is undefined.
4. **Rehearse C8's inertial answer.** It is the one place where you are
   genuinely strong, and it demonstrates real understanding of the model.
5. **Pre-empt C10.** Say the drone falls and say why, before he runs it.
