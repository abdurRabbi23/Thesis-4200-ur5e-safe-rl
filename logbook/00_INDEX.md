# Thesis Logbook — INDEX (read this first)

Front door for the UR5 Safe RL Grasping thesis. **Any new chat starts here.**

## How I work across chats

Each Cowork chat is a separate session, but they all share **this folder** as memory.
To start a new chat with full context:

1. Open the chat inside the thesis project.
2. Connect this folder (`Abdur_Rabbi_Thesis_updated`).
3. Say: *"Read `logbook/00_INDEX.md` and `logbook/<module>.md`, then continue with X."*

Three layers of memory:

- **`run_log.md`** — the daily timeline (what happened each day, chronological).
- **`logbook/NN_*.md`** — one file per work-stream (deep context: goals, decisions, files, next steps). Use these for "how / why did I do X".
- **`logbook/HANDOFF_next.md`** — the runbook for the *next* session. Rewritten at the end of every session.

Rule of thumb: work happens in a module → update that module file **and** add a dated line to `run_log.md`.

## Project one-liner

Safe Adaptive IBVS with constrained RL (cPPO) for precision grasping on a UR5e, sim → real.
Three layers: **L1** safe-RL grasping in sim (must-pass), **L2** IBVS visual loop (stretch),
**L3** sim-to-real on the physical UR5e (optional). See `PROJECT_INSTRUCTIONS.md`.

## Current status (updated 2026-07-28, Day 3 — MODULE 02: GRIPPER MOUNTED + MEASURED)

**The RH-P12-RN is on the arm as ONE articulation, and the geometry is measured.**
`make_ur5e_rhp12_usd.py` reports **7/7 PASS**: 10 joints / 12 bodies, nested articulation root
stripped, monotonic stroke, and an open clear opening of **106.4 mm against the ROBOTIS
published 106.0 mm (+0.4 mm)** — the first number in this thesis validated against a source
outside the project.

Measured here, all with reproducible commands:

| Quantity | Value |
|---|---|
| Pad gap, body origins, open → closed | 0.1145 → 0.0216 m |
| Pad **face** gap, open → closed | 0.1064 → 0.0137 m |
| Pad reach from origin (r + l) | 0.0081 m |
| TCP from wrist, open → closed | 0.0767 → 0.1049 m |
| DexCube edge, raw / at env scale 0.8 | **0.06000 / 0.04800 m** |

**Three things worth carrying:**

- **The archive's `TCP_OFFSET = 0.130` is invalidated.** It was calibrated against a 0.0412 m
  cube; the cube is really **0.048 m**, measured by drop test. Its "flat-pad parallel grip at
  delta +0.3 mm" is arithmetically impossible against the real cube. Reuse the archive's
  *method*, reject its *constants* — §14 earning its place.
- **The archive's origin-gap table replicates to 4 dp**, so its geometry work was sound. The
  failure is specifically in calibration against the cube.
- **New landmine: `Usd.PrimRange` silently skips instance proxies.** Isaac props and
  URDF-converted assets are instanced by default, so any traversal that counts or authors
  geometry finds nothing and reports success. Cost me one wrong diagnosis this session.

**Prediction banked for the grasp test: pads stall at q ≈ 0.69** against the 0.048 m cube.
Later → crushing or slipping; earlier → wedged on the curved `r1`/`l1` links.

**Next:** `ur5_grasp/robots/ur5e_rhp12_cfg.py`, then the grasp test. The open question from
Day 3 — sim gives 4 drivable finger joints where the real RH-P12-RN is 1-DOF — must be settled
before the PPO baseline, not after.

## Day 5 (2026-07-30) — SECOND GRIPPER (2F-85) WRITTEN, **NOT YET RUN**

Three files on disk, all compiling, none executed. **Nothing here is a result.**

> **Scope override, recorded not buried.** The Day 4 handoff said *"do not start the 2F-85
> this session"*. It was started anyway at the supervisor's instruction. **The one-day timebox
> stands; Layer 1 is not gated on the 2F-85.**

> **Correction, caught by `ls` and not by any handoff.** The Day 4 handoff — and the first
> draft of the Day 5 one — both said run 7 was unrun. **It has run twice, and failed twice.**
> `02_grasp_hold_test_run7_30mm.log` FAIL 2/9; `02_grasp_hold_test_run7_depth.log` (newest)
> FAIL 3/9 on the 48 mm cube: **stall q = 0.3063 against the banked 0.69**, peak pad force
> **0.00 N**, static hold dropped **+32.31 mm**. Passing: prims and joints all resolved, cube
> square to the pads (0.00°), open pads clear the cube, TCP rose +84.2 mm, slip 0.12 mm.
> A stall at 0.31 against a predicted 0.69 is not a near miss — it is a contact neither the
> pad theory nor the throat theory predicts, and run 6's PHASE 0b remains WITHDRAWN, so the
> throat explanation is unproven rather than disproven. **This is the open Layer 1 question.**
> §5's rule earned its place again: verify on disk, never trust a handoff.

The archive was mounted and mined (§14). It confirms `ur5e.usd` carries a variant set
`Gripper = [None, Robotiq_2f_85]`, that the merged asset loads as ONE articulation at 12
joints / 16 bodies, and it names all six finger joints. **Caveat that governs all of it:** the
archive read that asset from `Assets/Isaac/`**`5.1`**`/Isaac` and this thesis is frozen on
**5.0**, so every name carried across is a hypothesis until PHASE C re-reads it here.

**The archive's 2F-85 failure has a precise cause, and it is not the one §9 states.** §9 rejects
the *URDF route* — a tree cannot hold a four-bar loop. The archive never used a URDF; it used
this same NVIDIA USD variant. What it did was drive `finger_joint` alone and leave the other
five finger joints **passive at stiffness 0**, expecting the mechanical loop to carry them. The
pads then transmitted no normal force, the cube fell straight through, stiffness 20→400 and
effort 50→200 did not help, and it fell back to a **proximity weld** — the fake gripper that
measured every headline number in the previous thesis.

Why passive cannot work, from upstream rather than from us: Isaac Sim resolves closed-loop
kinematics automatically through USD schemas, but **Isaac Lab requires every mimic joint to be
fully specified in the ArticulationCfg** (IsaacLab #2424, #2626, #2665). A joint Isaac Lab was
never told about is not coupled — it is limp, and limp joints fold under contact instead of
transmitting it. That is "pads touch, force ≈ 0 N" exactly.

**The bet: all six finger joints DRIVEN from one scalar through an explicit sign table, none
passive.** Not a new idea — it is the pattern that already worked here on the RH-P12-RN, where
four coupled joints sharing one scalar reproduced the published 106.0 mm to +0.4 mm. The signs
live in the binary-action command, not the gains, so the policy still sees ONE scalar and the
two grippers stay benchmark-comparable.

| File | Status |
|---|---|
| `ur5_grasp/tools/make_ur5e_robotiq_usd.py` | written, unrun — PHASES A–F |
| `ur5_grasp/robots/ur5e_robotiq_cfg.py` | written, unrun — six driven joints, contact sensors ON |
| `ur5_grasp/robots/__init__.py` | `GRIPPERS` registry added, `DEFAULT_GRIPPER = "rhp12"` |

**Banked before the run:** Robotiq publishes **stroke 85 mm** and **gripping force 20–235 N**.
PHASE F checks the open clear opening against 85 mm ± 4 mm — the same external-target move that
made the RH-P12-RN's 106.4 mm worth something. Effort limit 12.0 N·m is **PROVISIONAL**;
calibrate against measured force, not torque. The archive's 200.0 is ~17× the datasheet.

**Day 4's lesson is built into the tool, not written under it.** PHASE E measures the free-space
closest approach of *every* finger link to the centreline before anything touches anything — the
nine rows of numbers that would have saved six runs on the RH-P12-RN. `PAD_BODIES` is a labelled
hypothesis with a test attached.

**If the pads still read ≈ 0 N with all six driven, §9 is confirmed on its own terms** — close
the 2F-85 as a documented negative result. That is a paragraph in the book, not a failed session.

**Next:** run the build tool, read PHASES A→F in order, stop at the first FAIL. Then **return to
the RH-P12-RN critical path** — run 7 and the withdrawn run-6 conclusion.

## Day 4 (2026-07-29) — CONFIG + GRASP TEST WRITTEN, **NOT YET RUN**

Two files on disk, both compiling, neither executed. Nothing here is a result yet.

- `ur5_grasp/robots/ur5e_rhp12_cfg.py` — arm gains carried from the **measured** `ur5e_cfg.py`
  (shoulder 1320 / elbow 1320 / wrist 216), contact sensing on, solver iterations 16 → 32.
- `ur5_grasp/scripts/grasp_hold_test.py` — close, measure stall + force, release, lift, measure
  slip, then read `TCP_OFFSET` **at the grasp**. No IK, by design.

**Day 3's open question is answered: the gripper is ONE degree of freedom.** All four finger
joints share one actuator group and one scalar target, because the real hardware has a single
Dynamixel and coupled fingers. Evidence the same-`q` coupling is the correct one and not merely
convenient: the Day 3 sweep used it and reproduced the published 106.0 mm stroke to +0.4 mm.

**Second external validation entered the thesis:** ROBOTIS publishes **Maximum Gripping Force
170 N**. The URDF's `effort="1000"` placeholder is worth ~17 kN at the pad, so
`effort_limit_sim = 10.0 N·m` (170 N × ~0.06 m). The lever arm is an estimate — so the **force**
is the thing validated, not the torque.

Five predictions banked before the run (stall `q` 0.69±0.03, peak force 100–300 N, static drop
< 5 mm, lift slip < 5 mm, `TCP_OFFSET` ≈ 0.1015 m). The lift-slip one is the genuine unknown and
is labelled as such — the wedge is exactly what a static test cannot see.

## Previous status (2026-07-27, Day 2 — MODULE 02: ARM SIGNED OFF)

**The UR5e arm loads, holds pose, and is signed off.** `check_ur5e.py` reports **9/9 PASS**:
6 joints in UR order, 7 bodies, fixed base, no `ArticulationRootAPI` error, effort limits
150/150/150/28/28/28 N·m and velocity 3.142 rad/s — both matching the UR5e datasheet, read off
the USD rather than assumed. Home-pose EE at **x=0.433, y=0.133, z=0.473 m**.

Two decisions worth carrying:

- **Asset:** Isaac Lab ships no UR5e *config*, but the Nucleus library does ship the *USD*
  (`Robots/UniversalRobots/ur5e/ur5e.usd`). No URDF import for the arm. Confirmed by
  `probe_ur5e_asset.py`, which includes a reachability control.
- **One tuning change, measured not guessed:** elbow stiffness 600 → 1320. `τ = k · err` showed
  the elbow carrying the largest gravity torque (16.0 N·m) on the weakest gain — inherited from
  `UR10e_CFG`, tuned for a heavier robot. Prediction 0.01214 rad was recorded *before* the run;
  measured 0.011847 (−2.4%, explained). Every other joint unchanged to 4 dp.

**Module 02 continues with the gripper.** Plan: copy the
archive's `assets/rh_p12_rn/` URDF + meshes as **third-party source**, then rebuild the URDF→USD
conversion and flange mount *here*, re-measuring every geometric number. Detail in
`02_grasp_env.md`; runbook in `HANDOFF_next.md`.

**Scope change 2026-07-28 (Day 3):** the robot now carries **two selectable grippers** —
RH-P12-RN *and* Robotiq 2F-85 — both really actuated, chosen at run time via a `--gripper` flag
over a `GRIPPERS` registry, with separate task ids and `experiment_name` per gripper. §9's 2F-85
rejection is a statement about the **URDF** route (tree cannot hold the four-bar loop), not about
the gripper; it is re-opened **only** if `probe_gripper_assets.py` finds a shipped, already-coupled
USD. The 2F-85 is a bonus result driven by literature comparability, **not** lab hardware —
**Layer 1 never waits on it**, and the attempt is timeboxed to one day. Detail + decision rules in
`02_grasp_env.md` § "SCOPE CHANGE".

**Archive correction (2026-07-27):** the lift-env **table is Isaac Lab stock**
(`lift_env_cfg.py:45`, SeattleLabTable at `[0.5, 0, 0]`), inherited by subclassing `LiftEnvCfg`.
It was never previous-attempt work and needs no import. Separately, the archive's Layer 1
headline (cPPO 6.65% vs PPO 16.86%) was measured with a **proximity weld** standing in for a
gripper — its own `00_INDEX.md` Day 17 records that cPPO was never run on the RH-P12-RN. Treat
the archive as an unfinished target, valuable for its diagnoses rather than its numbers.

## Previous status (2026-07-27, Day 1 — MODULE 01 COMPLETE)

**Module 01 is done. The stack is verified and the RL loop trains in this folder.** Six gates green:
frozen stack confirmed, Isaac Lab cloned at **tag `v2.3.0`** (HEAD `3c6e67bb5`), the `isaaclab` env
resolves to **this** folder, Cartpole converged (150 iters, ep length 300.00), Franka Reach trained
clean (0 NaNs, position error 0.2702 → 0.0919 m, ~4.2 it/s at 4096 envs), TensorBoard reachable at
`100.109.10.66:6006`. Detail in `01_env_setup.md`; replication steps in
`Thesis_Documentation/01_Environment_Setup.md`.

**Module 02 is next.** Write the UR5e `ArticulationCfg` modelled on the UR10 pattern in
`isaaclab_assets/robots/universal_robots.py`. **Validate the arm alone in the GUI before attaching
any gripper** — build before attach.

**Two corrections made to `PROJECT_INSTRUCTIONS.md` §7 this session** (logged in `09_Changelog.md`):
Isaac Lab ref is the **tag `v2.3.0`**, not the `release/2.3.0` branch — the branch reproduces the
previous attempt's URDF-importer startup crash, and §7 had carried the wrong value forward into the
Module 01 handoff. Driver corrected to 580.173.02. The archive's Franka Reach throughput table
(2.44 it/s) is superseded by ~4.2 it/s measured here.

**Carried over from the archive:** the working method, the documentation system, the frozen stack,
and the landmine list in `Thesis_Documentation/07_Troubleshooting.md`. **No code, no configs and
no results were carried over.** Any number that enters this thesis must be re-measured here.

## Modules

| File | Work-stream | Status |
|---|---|---|
| `01_env_setup.md` | Stack install, Isaac validation, reaching tasks | ✅ complete (Day 1) |
| `02_grasp_env.md` | UR5e lift env, grasp, PPO baseline | ▶ ACTIVE — arm ✅ (Day 2), gripper mounted + measured ✅ (Day 3); grasp test next |
| `03_cppo_benchmark.md` | Safety constraints + cPPO vs PPO (**Layer 1 deliverable**) | ◻ not started |
| `04_layer2_ibvs.md` | IBVS visual loop, RL-tuned image Jacobian (Layer 2) | ◻ not started |
| `05_layer3_sim2real.md` | Real gripper + ROS 2 transfer (Layer 3) | ◻ not started |
| `06_writing.md` | Thesis chapters, figures, defence prep | ◻ ongoing |
| `07_documentation.md` | The documentation system itself | ✅ skeleton created |

## Roadmap

| Weeks | Work | Module |
|---|---|---|
| 1–4 | Environment setup; validate RL loop on a stock reaching task | `01` |
| 5–8 | Grasping task with privileged pose info | `02` |
| 9–10 | Safety constraints + cPPO vs PPO benchmark → **Layer 1 done** | `03` |
| 11–13 | Layer 2 (IBVS); Layer 3 if time allows | `04`, `05` |
| 14–16 | Results, writing, defence prep | `06` |
