# Module 02 — Grasp environment

**Status:** ▶ ACTIVE — **arm signed off 2026-07-27 (Day 2)**, 9/9 checks PASS. Gripper is next.
**Owner file for:** UR5e articulation cfg, gripper, lift env, task registration, PPO baseline

---

## Goal

**Step 1 of this module (Day 2):** a UR5e — *arm only, no gripper* — loads in Isaac Lab as an
`ArticulationCfg`, with all 6 joints found and named, correct limits, no `ArticulationRootAPI`
error, and the arm holding a commanded home pose without drift.

Full-module goal: a registered UR5e lift/grasp task with a PPO baseline. Reached in stages —
arm → gripper → env → reward → PPO. **Build before attach.**

## Decision rules

_Written BEFORE any run. One symptom → one named knob. Never change two things at once._

| Symptom | Single knob to change | Threshold to act |
|---|---|---|
| `ArticulationRootAPI` error on load | the articulation root prim path | Fix the root path. Do **not** attach a gripper to work around it. |
| USD asset not found | the `spawn.usd_path` | Resolve the asset first. Never hand-edit USD. |
| Joint count ≠ 6 | the USD / URDF source | Wrong asset. Back to STEP 2. |
| Arm drifts or jitters at home pose | actuator `stiffness` **or** `damping` — one at a time | Start from the UR10e values, change one number, re-run. |
| Arm explodes on first step | `effort_limit_sim` | Lower it. One knob only. |
| Probe CONTROL comes back MISSING | network / Nucleus reachability | Server is down, not the asset absent. Fix connectivity before concluding anything. |
| Tempted to attach a gripper "to test properly" | scope | Don't. Gripper is a separate step, after the arm is signed off. |

## State — what is actually done

Verified on disk 2026-07-27, not assumed.

| Item | Verified | How checked |
|---|---|---|
| `ur5_grasp/robots/` | **empty** (`.gitkeep` only) — no cfg written yet | `find ur5_grasp -type f` |
| git | clean, HEAD `1ca7eef` | `git status --short`, `git log --oneline` |
| `IsaacLab/` | present, tag `v2.3.0` | `ls IsaacLab/` |

### STEP 1 — the UR10 pattern (read, not copied)

`IsaacLab/source/isaaclab_assets/isaaclab_assets/robots/universal_robots.py` ships **two**
usable patterns, and they differ in ways that matter:

| | `UR10_CFG` | `UR10e_CFG` |
|---|---|---|
| asset root | `ISAACLAB_NUCLEUS_DIR` | `ISAAC_NUCLEUS_DIR` |
| usd | `Robots/UniversalRobots/UR10/ur10_instanceable.usd` | `Robots/UniversalRobots/ur10e/ur10e.usd` |
| `disable_gravity` | `False` | `True` |
| `articulation_props` | not set | `solver_position_iteration_count=16` |
| actuators | one group, `.*`, stiffness 800 / damping 40 | **three** groups: shoulder 1320/72.66, elbow 600/34.64, wrist 216/29.39 |

Joint names are identical across both and are the ROS-industrial standard 6:
`shoulder_pan_joint`, `shoulder_lift_joint`, `elbow_joint`, `wrist_1_joint`, `wrist_2_joint`,
`wrist_3_joint`.

**Model on `UR10e_CFG`, not `UR10_CFG`.** Same generation of robot (e-series), per-group actuator
gains rather than one blanket `.*` group, and the higher solver iteration count is what a
contact-rich grasping task will need later. The single-group UR10 cfg is the older, coarser
pattern. Gains still need re-tuning for the UR5e — it is a lighter arm (5 kg payload vs 10 kg),
so UR10e gains are a *starting point to be checked*, not a value to trust.

`disable_gravity=True` in `UR10e_CFG` is a deliberate simplification, not an oversight — it makes
the arm hold pose without gravity compensation. Decide this explicitly in STEP 3 rather than
inheriting it silently: gravity off makes the arm easier to hold at home but makes any sim-to-real
claim weaker (Layer 3).

### STEP 2 — where does the UR5e asset come from? (probe written, not yet run)

Established by grep, 2026-07-27:

- Isaac Lab 2.3.0 defines **no** UR5 or UR5e config. `isaaclab_assets/robots/` contains
  `universal_robots.py` with UR10 / UR10e only.
- `grep -rni "ur5" IsaacLab/source/` returns **two hits, both in a 2022 changelog line** — no
  asset path, no config, nothing usable.

So the asset is not in the repo. Two live options, and the probe decides between them:

| | Option A — Nucleus asset library | Option B — import the official UR5e URDF |
|---|---|---|
| how | point `usd_path` at a shipped `ur5e.usd` | `scripts/tools/convert_urdf.py` on the `ur_description` URDF |
| cost | minutes | hours, plus mesh/inertia checking |
| risk | asset may not exist for UR5e | URDF importer is the component that crashed on the `release/2.3.0` branch (Module 01) |

**A is strongly preferred** — same class of asset Isaac Lab already uses for the UR10e, so the
articulation root and joint naming come out right by construction. B is the fallback only.

`ur5_grasp/scripts/probe_ur5e_asset.py` answers this with evidence rather than a guess: it lists
the Nucleus `UniversalRobots/` folders and checks named candidates, with the shipped UR10e path as
a **control** so an unreachable server can't be mistaken for a missing asset.

**RESOLVED — Option A.** Probe run 2026-07-27 (`logbook/02_probe_ur5e_asset.log`):

```
CONTROL   on Nucleus   .../ur10e/ur10e.usd        <- server reachable; result is trustworthy
listing   UniversalRobots/ -> ur3 ur3e ur5 ur5e ur10 ur10e ur16e ur20 ur30
listing   ur5e/            -> .thumbs  configuration  ur5e.usd
CAND      on Nucleus   .../UniversalRobots/ur5e/ur5e.usd
```

`usd_path = f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd"`. No URDF import needed.

Asset root resolves to `Assets/Isaac/**5.1**` — second independent sighting of the
5.1-assets / 5.0-sim split already closed as benign in `07_Troubleshooting.md` §5.

### STEP 2b — the archive's "robot with a table", inspected 2026-07-27

Checked on request. **The table is not archive work.** It is Isaac Lab stock —
`isaaclab_tasks/.../manipulation/lift/lift_env_cfg.py:45`, `ObjectTableSceneCfg.table`:
a SeattleLabTable at `pos=[0.5, 0, 0]`, `rot=[0.707, 0, 0, 0.707]` from the Nucleus props
library. The archive inherited it by subclassing `LiftEnvCfg`; this attempt will inherit the
same one from the same file in our own v2.3.0 clone. **Nothing to import.** The cube at
`[0.5, 0, 0.055]` is simply the tabletop height.

What *is* archive work is the gripper:

| Artifact | Size | Nature |
|---|---|---|
| `assets/rh_p12_rn/` | 88 K | ROBOTIS URDF + 5 STL + LICENSE — third-party **source**, not a result |
| `tools/make_ur5e_rhp12_usd.py` | — | URDF→USD, then USD surgery (reference stock `ur5e.usd` with `Gripper=None`, disable nested articulation root, add fixed mount joint) |
| `assets/ur5e_rhp12.usd` | **2 KB** | a reference *stub*, not a model — copying it would copy a pointer |
| `robots/ur5e_rhp12.py` | — | the cfg: 10 joints / 12 bodies, one articulation |

**Decision (2026-07-27):** copy the `rh_p12_rn/` URDF + meshes as third-party source, and
**rebuild** the USD conversion and mount here so the geometry is measured in this folder.
Not taken as-is: the built USD, the cfg, and every calibrated number (`TCP_OFFSET = 0.130`,
the pad-separation sweep) — those are measurements against the archive's gains and must be
re-measured. Per §14.

**Caveat carried forward, from the archive's own `00_INDEX.md` (Day 17):** its Layer 1
headline (cPPO 6.65% vs PPO 16.86% violations) was measured with a **proximity weld standing
in for a gripper**, because the Robotiq 2f-85's closed-loop 4-bar transmits no pad force in
PhysX. *"cPPO has never been run on the RH-P12-RN in any configuration — that is the real
gap."* The archive is an unfinished target, not a finished one. Its most valuable finding is
the diagnosis, not the numbers: the RH-P12-RN URDF is a pure tree, so every joint is drivable
and force actually reaches the pads.

## What was run

All on the lab PC, `isaaclab` env, 2026-07-27 (Day 2). Absolute tee paths.

```bash
conda activate isaaclab

# STEP 2 — locate the asset (run twice; see "the buffering trap" below)
cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/scripts/probe_ur5e_asset.py \
    2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_probe_ur5e_asset.log

# STEP 4 — validate the arm (run 1 GUI; runs 2 and 3 headless)
PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/scripts/check_ur5e.py --headless \
    2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_check_ur5e.log
echo "EXIT=${PIPESTATUS[0]}"     # NOT $? — after a pipe that reports tee, always 0
```

Files created: `ur5_grasp/robots/ur5e_cfg.py`, `ur5_grasp/robots/__init__.py`,
`ur5_grasp/__init__.py`, `ur5_grasp/scripts/probe_ur5e_asset.py`,
`ur5_grasp/scripts/check_ur5e.py`.

## Results

**Arm signed off — `check_ur5e.py` run 3, all 9 checks PASS.**
Source for every number below: `logbook/02_check_ur5e.log`.

Asset facts read off the USD (not assumed, not from a datasheet):

| | value |
|---|---|
| bodies (7) | `base_link, shoulder_link, upper_arm_link, forearm_link, wrist_1_link, wrist_2_link, wrist_3_link` |
| joints (6) | UR convention, correct order |
| `is_fixed_base` | True |
| effort limits | 150 / 150 / 150 / 28 / 28 / 28 N·m — matches the UR5e datasheet |
| velocity limits | 3.142 rad/s (= 180 °/s) on all six — matches |
| position limits | ±6.283 rad, elbow ±3.142 |

**The one tuning change, and the measurement that justified it.**
Run 2 (UR10e gains verbatim) showed a constant steady-state sag. Multiplying each joint's error
by its own stiffness converts the table into the gravity torque each joint actually carries:

| joint | k | err (rad) | implied τ (N·m) |
|---|---|---|---|
| shoulder_pan | 1320 | 0.000080 | 0.1 |
| shoulder_lift | 1320 | 0.008904 | 11.8 |
| **elbow** | **600** | **0.026703** | **16.0** |
| wrist_1 | 216 | 0.006379 | 1.4 |
| wrist_2 / wrist_3 | 216 | 0.000000 | 0.0 |

`shoulder_pan ≈ 0` is the control that makes the rest trustworthy: its axis is vertical, so
gravity can exert no torque about it, and the sim agrees to four decimals. The arm is not
drifting — it is sagging exactly where gravity has leverage.

The elbow carried the **largest** gravity torque on **less than half** the shoulder's stiffness,
inherited from `UR10e_CFG` (a heavier robot, different link masses). All torques sit under 11%
of the 150 N·m limit, so effort limit was never the constraint.

**One knob moved: elbow stiffness 600 → 1320.** Prediction written before the run:
`err = 0.026703 × 600/1320 = 0.01214 rad`.

| joint | run 2 | run 3 | |
|---|---|---|---|
| shoulder_pan | 0.000080 | 0.000082 | unchanged |
| shoulder_lift | 0.008904 | 0.008926 | unchanged |
| **elbow** | **0.026703** | **0.011847** | predicted 0.01214, **−2.4%** |
| wrist_1 | 0.006379 | 0.006389 | unchanged |

One knob, one response, everything else constant to four decimals. The −2.4% shortfall is
explained, not noise: implied τ fell 16.02 → 15.64 N·m (also −2.4%), because gravity torque is
configuration-dependent and a less-sagged elbow carries slightly less of it. The `1/k` model is
very slightly conservative. Independent cross-check: EE rose z 0.466 → 0.473 m (+7 mm), against
+6.7 mm predicted from 0.0149 rad over a ~0.45 m lever.

**Usable result:** `τ = k · err` is now a calibrated way to set any arm gain from a measured
torque, rather than by taste. That is worth more than the fix itself.

Home-pose end-effector (`wrist_3_link`): **x = +0.433, y = +0.133, z = +0.473 m**.
`y ≠ 0` at `shoulder_pan = 0` is correct UR kinematics — the wrist is laterally offset from the
shoulder axis. This is the number that decides table/object placement.

## Open problems

**None blocking.** Three things carried forward:

1. **The buffering trap (new landmine).** `probe_ur5e_asset.py` run 1 produced a log ending
   mid-startup with *none* of the script's own output. Cause: Isaac Sim can die inside
   `simulation_app.close()`, and Python's `stdout` is **block-buffered** when piped to `tee`, so
   a hard exit discards the buffer. The Isaac Sim banner still appears because that is carb's C++
   logger writing directly — which makes the log look truncated rather than lost. Two fixes, both
   applied: `PYTHONUNBUFFERED=1` on the command line, and `sys.stdout.reconfigure(line_buffering=True)`
   inside the script. Related: after a pipe, `$?` reports **tee's** status (always 0) — use
   `${PIPESTATUS[0]}`. Recorded in `07_Troubleshooting.md`.
2. **Damping not re-tuned.** Elbow damping is still 34.64 (`= 2√300`) against k = 1320, so the
   damping ratio is now low. Steady-state error is unaffected and the step trace is flat by step
   50, so it is not a problem *at rest*. It may matter under motion. One knob, when there is a
   symptom — not before.
   Worth noting the upstream inconsistency: `UR10e_CFG` uses `d = 2√k` for shoulder (72.66 = 2√1320)
   and wrist (29.39 = 2√216), but the elbow's 34.64 is `2√300`. The elbow entry is internally
   inconsistent in Isaac Lab's own file.
3. **Home pose still provisional.** Chosen before the table exists. Re-check once the object is
   placed at `[0.5, 0, 0.055]`.

## Next single action

Attach the gripper. Decided this session (§14-compliant): copy `assets/rh_p12_rn/` (URDF + 5 STL
+ LICENSE — third-party source, not a result) from the archive, then **rebuild** the URDF→USD
conversion and the flange mount in this folder, using the archive's
`tools/make_ur5e_rhp12_usd.py` as the map. Every geometric number — `TCP_OFFSET`, pad separation —
gets re-measured here against *these* gains.

Robotiq 2F-85 stays rejected (§9): closed-loop 4-bar, passive pads transmit no force in PhysX.
The archive proved this the expensive way and it is the single most valuable thing in that folder.

---

## SCOPE CHANGE — two selectable grippers (2026-07-28, Day 3)

Requested: **one UR5e, two grippers** — RH-P12-RN and Robotiq 2F-85 — both really actuated
(no weld), chosen at run time.

Driver, as stated: **optionality plus comparability with the literature.** *Not* hardware —
the lab does not require a 2F-85 for Layer 3. That matters, because it means the 2F-85 is a
**bonus result, not the critical path.** RH-P12-RN remains the Layer 1 gripper.

### What the §9 rejection does and does not say

§9 rejects the 2F-85 *URDF route*. A URDF is a tree and cannot express the four-bar loop, so
public 2F-85 URDFs break the loop and paper over it with `<mimic>` tags that Isaac Lab 2.3 does
not honour (issue #2424). That is a statement about **URDF**, not about the gripper.

A USD authored by NVIDIA has no tree restriction. So the rejection is **re-opened on one
condition only**: that a shipped, already-coupled asset exists. `probe_gripper_assets.py`
answers that with evidence, the same way STEP 2 settled the arm. Three outcomes, ranked:

| Probe outcome | Route | Cost |
|---|---|---|
| `ur5e.usd` has a `Gripper` variant listing a Robotiq value | spawn with `variants={"Gripper": ...}` | ~1 h |
| standalone 2F-85 USD on Nucleus | mount like the RH-P12-RN | ~4 h |
| nothing found | coupled-tree drive: break the loop, drive all finger joints from ONE command via the real transmission ratio | ~1 day, and §9 stands until measured |

**Timebox: one day.** Failure closes the 2F-85 with a header banner as a documented negative
result (§5) — which is the second time this project would have earned that paragraph, and this
time with a named cause rather than a weld.

### Sequencing (agreed)

1. RH-P12-RN to **sign-off** — pure tree, will work. Unchanged, still the next action.
2. Build the **switch** while writing that cfg. Nearly free if designed in now, expensive to
   retrofit later.
3. *Then* the 2F-85, timeboxed.

Layer 1 never waits on the 2F-85. If step 3 fails, Layer 1 is unaffected.

### The switch — design decision

**Chosen: two built USDs + a registry, selected by a `--gripper` flag.**
Rejected: authoring a custom multi-value USD variant set of our own. Variants are the elegant
answer but mean USD surgery on every rebuild; a dict costs nothing and is trivially inspectable.

```
ur5_grasp/robots/
    ur5e_cfg.py            arm only          (done, signed off)
    ur5e_rhp12_cfg.py      arm + RH-P12-RN
    ur5e_robotiq_cfg.py    arm + 2F-85       (only if the probe/timebox succeeds)
    __init__.py            GRIPPERS = {"rhp12": ..., "robotiq85": ...}
```

Each entry must carry **its own** measured values, never a shared constant:
`cfg`, `TCP_OFFSET`, `finger_joint_names`, `open`/`closed` commands, `body_names` for the
contact sensor. A single global `TCP_OFFSET` is the exact bug that would silently corrupt the
second gripper's results.

**Task ids stay separate per gripper** — `Isaac-Lift-Cube-UR5e-RHP12-v0`,
`Isaac-Lift-Cube-UR5e-Robotiq85-v0` — each with its **own `experiment_name`**. §9 already
records checkpoints being dumped on top of earlier results by a variant sharing a runner cfg.
Two grippers doubles that risk.

### Decision rules for the 2F-85 — written BEFORE the run

| Symptom | Single knob | Threshold to act |
|---|---|---|
| Asset loads, fingers do not move on command | the joint **names** in the actuator regex | Print the real joint list first. Never guess a regex. |
| Fingers move, cube is not held | measure **contact force at the pads**, not separation | Zero force with fingers visibly touching = the §9 failure reproducing. Stop, log, close. |
| Loads as 2+ articulations | the nested articulation root | Same fix as the RH-P12 mount. One knob. |
| Solver instability at high `num_envs` | `num_envs`, alone | Loop constraints cost solver iterations. Re-time before setting any training budget. |
| Timebox hits 1 day with no pad force | scope | Close as negative result. Do **not** extend. Layer 1 does not need it. |

### Open question for me to answer (not to be answered for me)

The RH-P12-RN URDF has **4 revolute joints and 0 `mimic` tags** — verified 2026-07-28 by
grepping our own copy, which independently confirms the archive's "pure tree" diagnosis.
But the real RH-P12-RN is a **1-DOF** gripper: one Dynamixel drives both fingers through a
mechanical coupling.

So sim gives 4 independently drivable joints where hardware gives 1 command. If the RL policy
is allowed to command all 4 freely, what exactly does a Layer 3 sim-to-real claim mean? And
note this is the *same* coupling question as the 2F-85 — just on a gripper where it is easy.
Decide the RH-P12 action space deliberately before the PPO baseline, not after.


---

## Day 3 (2026-07-28) — RH-P12-RN mounted, geometry measured, cube edge settled

### Goal / success criterion

Gripper on the arm as **one articulation**, and the pads shown by measurement — not by
looking — to be able to close on the cube.

### What was done

| Step | Artefact | Outcome |
|---|---|---|
| 1 | `ur5_grasp/assets/rh_p12_rn/` | 7 files, 88 K, MD5-identical to archive. No USD, no numbers. |
| 2 | `ur5_grasp/tools/make_ur5e_rhp12_usd.py` | written here; method from archive, values not |
| 3 | `ur5_grasp/tools/inspect_usd_geometry.py` | diagnostic for instancing + bounds |
| 4 | `ur5_grasp/tools/measure_dexcube_drop.py` | physical cube measurement |

### Results — all re-measured in this folder

**Topology.** 10 joints / 12 bodies, one articulation. Nested articulation root stripped at
`/Robot/RHP12/rh_p12_rn_base`; fixed joint `wrist_3_link -> rh_p12_rn_base`.

PhysX returns the gripper joints as `rh_l1, rh_p12_rn, rh_l2, rh_r2` — reordered by tree
depth, **not** the order they were requested in. Never index gripper joints by assumed
position when writing the ArticulationCfg.

**Stroke sweep** (`logbook/02_make_ur5e_rhp12.log`):

| q (rad) | origin gap (m) | face gap (m) | TCP from wrist (m) |
|---|---|---|---|
| 0.00 | 0.1145 | 0.1064 | 0.0767 |
| 0.50 | 0.0749 | 0.0668 | 0.0968 |
| 1.00 | 0.0216 | 0.0137 | 0.1049 |

Pad reach from body origin: 0.0041 (r) + 0.0040 (l) = **0.0081 m**.

**External validation.** Open clear opening **106.4 mm** against the ROBOTIS published stroke
**106.0 mm** — error **+0.4 mm**. Source: <https://emanual.robotis.com/docs/en/platform/rh_p12_rn/>
(stroke reduced 109 → 106 mm from 2019-11-04 for fingertip durability). This is now a permanent
acceptance criterion in the script, not a comment.

**Cube edge.** Raw **0.06000 m**, at env scale 0.8 **0.04800 m**. Measured by drop test —
resting centre height × 2 — because USD introspection was ambiguous. Scaling exactly linear.

### Two wrong diagnoses of my own, both caught

1. **`size/2` is not the reach from the origin.** The AABB is not centred on the body origin
   (that sits on the joint axis), so the pad reach must be the box **support**, not its
   half-width. Symptoms: 92.4 mm open gap against a 106 mm datasheet, and an impossible
   negative face gap at full close. Fixed; one knob; control (`origin_gap`, TCP) held
   byte-identical across the re-run, proving the change was surgical.

2. **"The gripper reference probably did not load."** It had loaded — 12 bodies. The real
   cause is that `Usd.PrimRange` does not descend into **instance proxies**, and all 10
   finger meshes are instances of `/__Prototype_1..10`. The per-mesh `displayColor` loop was
   removed rather than fixed: proxies and prototypes are both read-only, and the ancestor
   material binding already works — GUI confirms the hand renders black.

### Archive findings that change decisions

- **`TCP_OFFSET = 0.130` is invalidated.** Its stated justification — *"pad faces close to
  0.0415 m against a 0.0412 m cube, delta +0.3 mm, a true flat-pad parallel grip"* — rests on
  a cube that is really **0.048 m**. Pads cannot close to 0.0415 m around a 0.048 m cube. Do
  not carry 0.130 over. Measure the TCP against a real grasp here.
- The archive's **origin-gap table replicates exactly to 4 dp**, so the *geometry* work was
  sound. It is the *calibration against the cube* that fails. Useful distinction: reuse its
  method, reject its constants.

### Prediction banked for the grasp test

Interpolating our face-gap column at the measured 0.0480 m cube: **pads stall at q ≈ 0.69.**

- stall much **later** → cube being crushed, or slipping through
- stall much **earlier** → wedged on the curved proximal `r1`/`l1` links (the §9 failure mode
  that survives a static hold test and fails under lift accelerations)

### Caveat on the measurements

The pad reach comes from an axis-aligned box around a **curved** fingertip, so it
over-approximates. That biases the open gap small (conservative) but the closed gap small too
(optimistic). The closed-gap check is therefore the weakest of the seven — do not lean on it.

### Next

Write `ur5_grasp/robots/ur5e_rhp12_cfg.py` (arm actuators from the measured `ur5e_cfg.py`,
elbow 1320 — not a blanket 800), then the grasp test against the q ≈ 0.69 prediction.
The 4-drivable-joints vs 1-DOF-hardware question above is still unanswered and must be
settled before the PPO baseline.

---

## Day 4 (2026-07-29) — RH-P12-RN config + grasp/hold test

### What was written

- `ur5_grasp/robots/ur5e_rhp12_cfg.py` — UR5e + RH-P12-RN `ArticulationCfg`.
- `ur5_grasp/scripts/grasp_hold_test.py` — close, measure, release, lift, measure again.
- `ur5_grasp/robots/__init__.py` — exports the cfg and the joint-name constants.

### Three decisions taken, with reasons

**1. The gripper is ONE degree of freedom.** This answers the open question logged on Day 3.
All four finger joints (`rh_p12_rn`, `rh_l1`, `rh_r2`, `rh_l2`) sit in a single actuator group
and always receive the same scalar target.

The real RH-P12-RN has one Dynamixel and mechanically coupled fingers — there is no hardware
command that moves `r2` independently of `r1`. A policy trained on four free joints would learn
grasps the hardware cannot execute, and a Layer 3 transfer claim built on it would be about a
robot that does not exist. There is also evidence the same-`q` coupling is the *correct* one
rather than merely convenient: the Day 3 sweep drove all four to the same `q` and produced a
106.4 mm open opening against the published 106.0 mm. A different true coupling would not have
reproduced the datasheet.

It costs nothing to impose: `BinaryJointPositionAction` takes a joint-name list and one
open/close pair, so the action space is a single scalar either way. And it is only *possible*
to impose because the RH-P12-RN URDF is a pure tree with zero mimic tags — the whole reason it
was chosen over the Robotiq 2F-85.

**2. Grip force comes from the datasheet, not from the URDF.** The URDF ships `effort="1000"`
on every finger joint, which at a ~0.06 m lever is roughly 17 kN at the pad. Under that limit
the "stall width" would be a fact about PhysX, not about a gripper. ROBOTIS publishes
**Maximum Gripping Force 170 N** (also: 5 kg recommended payload, 75 mm/s max closing speed,
500 g). 170 N x 0.06 m gives `effort_limit_sim = 10.0 N-m`.

The 0.06 m is an estimate off the URDF link origins, so **the force is what gets validated, not
the torque**. The test prints the achieved pad force and the exact factor needed to land on
170 N. Source: <https://emanual.robotis.com/docs/en/platform/rh_p12_rn/>.

**3. No IK in the grasp test.** The arm holds the Day 2 home pose; the cube is teleported to the
pad midpoint and pinned kinematically while the fingers close, then released. Adding a reach
would mean a failure could be the grasp *or* the IK — and the TCP frame that IK needs is the
thing this script is measuring. Circular.

Two other config changes worth naming: `activate_contact_sensors` goes **True** (something
finally reads it), and `solver_position_iteration_count` goes **16 -> 32** (the arm alone never
touched anything; this articulation presses two pads into a rigid cube).

### Predictions banked BEFORE the run

| # | Quantity | Prediction | Basis |
|---|---|---|---|
| 1 | Stall `q` | **0.69 +/- 0.03** | Day 3 face-gap column interpolated at the 0.0480 m cube |
| 2 | Peak pad contact force | **100 - 300 N** | `effort_limit_sim` 10 N-m over a ~0.06 m lever; datasheet says 170 N |
| 3 | Static hold, cube drop | **< 5 mm** | pads flat, force present |
| 4 | Slip during the lift | **< 5 mm**, but this is the genuine unknown | the wedge failure mode is exactly what a static test cannot see |
| 5 | `TCP_OFFSET` magnitude | **~0.1015 m** | Day 3 `tcp_from_wrist` read at `q = 0.69` |

Prediction 4 is the one worth being honest about: it is the reason the session exists, and a
confident prediction there would be pretending. The archive never ran cPPO on this gripper
(its own `00_INDEX.md`, Day 17), so nothing is inherited here.

### Decision rules — written BEFORE the run, one knob per symptom

The Day 3 table still stands. These are the **new** symptoms this script can produce, because
it is the first thing in the thesis that reads a contact sensor.

| Symptom | Diagnosis | The one knob |
|---|---|---|
| "both pad prims resolved" FAILS | the pad prim path moved when the USD was re-authored | the path resolution in `find_prim_path`, alone |
| Pads visibly on the cube, force **exactly** 0.00 N | most likely `activate_contact_sensors` off on the **cube**, not on the robot | check the cube's spawn cfg first — do NOT touch the gripper |
| Force flat at 0 with sensors resolved and both cfgs on | the §9 Robotiq failure reproducing | **STOP.** Log as a negative result. Do not tune. |
| Force present but < 25 N | lever arm estimate too large, so 10 N-m is too little | `effort_limit_sim`, alone, scaled by the factor the script prints |
| Force > 700 N | lever arm estimate too small | same knob, same direction, same factor |
| Stall `q` < 0.62 | cube wedged on the curved proximal `r1`/`l1` links | TCP offset, alone |
| Stall `q` > 0.76 | crushing, or slipping through | `effort_limit_sim`, alone |
| No stall at all — tracks to `q = 1.0` | fingers closed **through** the cube, or never touched it | check the Phase 1 "offset from midpoint" line before changing anything |
| Holds statically, slips on lift | **the wedge** | TCP offset, alone |
| Cube launches when the pin releases | energy stored during the pinned close | `--q-step` down (gentler approach), alone |
| "TCP actually rose" FAILS | lift arc sign wrong for this home pose | flip `--lift-delta`, alone — this is a test-rig bug, not a robot result |

### Not touched this session

`ur5_grasp/scripts/probe_gripper_assets.py` (the 2F-85 second-gripper track) is still unrun and
still off the critical path.

### Day 4, run 1 — FAIL 3/8. Read the failures before believing any of them.

Log: `logbook/02_grasp_hold_test.log`. Header confirmed: cube edge 0.04800 m, `effort_limit_sim`
10.0 N-m, contact sensing True, **both pad prims resolved (2/2)**, all 4 gripper joints found by
name at indices `[7, 6, 9, 8]` — the tree-depth reordering, as warned.

**What is a real physical observation.** The fingers were mechanically blocked. Commanded lag
grows monotonically from 0.0210 rad at `q=0.50` to **0.2561 rad** at `q=1.00`, and the pad origin
gap stops falling at ~0.079 m and then oscillates between 0.073 and 0.082. Something stops them.

**What that observation is NOT.** It is not a grasp. **Minimum face gap reached: 0.0651 m against
a 0.0480 m cube — 17.1 mm too wide.** The pad faces never came within 17 mm of the cube faces.

**Three test-rig bugs, all mine. None of them are findings about the gripper.**

1. **The stall detector required lag AND force simultaneously.** Force never registered, so a
   real mechanical stall was printed as "pads never stalled: they tracked the command to q=1.0"
   — while the same table showed 0.256 rad of lag. A broken sensor was reported as a robot
   result. This is the same class of error as §9's "it ran without crashing": the detector
   asserted a conjunction where it should have measured two things separately. **Fixed:** lag
   and force are now detected and reported independently.

2. **`TCP_OFFSET` was computed across two different instants.** `grasp_mid` was captured at the
   end of PHASE 2; the wrist pose was read in PHASE 5, *after* PHASE 4 moved the arm 84.2 mm and
   0.3 rad. The reported `(+0.00019, -0.13407, +0.18172)`, magnitude **0.2258 m**, is meaningless
   — Day 3 puts `tcp_from_wrist` between 0.0767 and 0.1049 m. Pure bookkeeping. **Fixed:** the
   wrist pose is captured at the grasp alongside `grasp_mid`.

3. **The cube was placed in the throat of the hand, not at the pad faces.** `mid0` is the midpoint
   of the two pad BODY ORIGINS, and a body origin sits on its joint axis — at the *base* of the
   fingertip. Putting the cube's centre there parks it between the curved `r1`/`l1` links, which
   is precisely where Day 3 predicted the wedge. This is the leading hypothesis for the 17 mm
   early blockage, and it is **not yet confirmed** — see below.

**Unexplained, and instrumented rather than guessed at.** The pinned cube settled **8.78 mm** off
its commanded position, almost all in −z. One step of gravity at dt = 1/120 is 0.34 mm, so 8.1 mm
is roughly five steps of free fall — the pin is not holding every step. Per-step tracking error is
now printed: growing-then-resetting means an intermittent pin, constant means a frame offset.

**PHASE 3/4 read together are the interesting part.** The cube dropped 10.11 mm on release and
then **stopped**, and through the 84.2 mm lift it moved with the TCP to within 0.06 mm. Something
held it rigidly. A wedge would do that. So would a grasp. The force channel is what distinguishes
them, and the force channel is the thing that failed.

#### Run 2 is instrumentation only — zero physics knobs turned

Nothing about the robot, the config, or the placement changes. Only prints are added, plus the two
bookkeeping fixes above. The discriminator is **net (unfiltered) contact force alongside filtered**:

| Net | Filtered | Diagnosis | The one knob |
|---|---|---|---|
| > 0 | 0 | pads ARE in contact; the cube filter is not resolving | `filter_prim_paths_expr`, alone |
| 0 | 0 | pads touch nothing, yet the fingers are blocked → the blockage is the proximal `r1`/`l1` links. **The wedge.** | cube placement along the tool axis, alone |
| > 0 | > 0 | working | none |

Deciding this by measurement rather than by argument is the whole point. Two of the three
hypotheses above would each have justified turning a different knob, and turning the wrong one
first is how the previous attempt burned four days.

#### Diagnosis closed by the GUI capture — it is the wedge, and the cause is placement

The run-1 screenshot (`Thesis_Documentation/assets/02_day4_run1_wedge.png`) removes the
ambiguity. The cube is up in the **throat** of the hand, pinched corner-first between the
curved proximal `r1`/`l1` links and tilted roughly 15 degrees. The `r2`/`l2` pads — the long
distal segments — are splayed below and outside it, touching nothing.

That single image explains every run-1 symptom at once, which is what makes it a diagnosis
rather than another hypothesis:

| Symptom | Explained by the wedge |
|---|---|
| blocked at a 0.0651 m face gap, 17 mm wide of a 0.0480 m cube | the fingers are stopped by the cube higher up the linkage, nowhere near the pad faces |
| filtered pad force flat at 0.00 N | correct reading — the **pads** genuinely never touch the cube. Contact is on `r1`/`l1`, which carry no sensor |
| cube settled 10.11 mm on release, then stopped | dropped into the wedge and jammed |
| rode the 84.2 mm lift with 0.06 mm slip | a jam holds very well against a slow, smooth lift |

**The §9 Robotiq failure did NOT reproduce.** Run 1's `[FAIL] pads transmit real normal force`
was the script blaming the sensor for a placement bug. The pads were never given anything to
push against. Worth being precise about, because a false §9 positive would have argued for
abandoning the RH-P12-RN — the one gripper on the approved list.

#### The fix, and where the number comes from

`body_pos_w` reports a link ORIGIN, and a link origin sits on its JOINT AXIS. For `r2`/`l2`
that axis is at the top of the fingertip. The grasp centre is the midpoint of the two pad
**geometric** centres, obtained from the link-local AABB — the same `ComputeUntransformedBound`
machinery Day 3 already validated in `make_ur5e_rhp12_usd.py: pad_local_bounds`. No new method,
no new constant, and the script prints `face - origin` so the size of run 1's misplacement is
on the record rather than inferred.

Same known bias as Day 3: an AABB around a curved fingertip over-approximates, so this centre
is approximate. It does not need to be exact — it needs to be tens of millimetres closer to the
truth than the joint axis was.

`--place-at {padface,origin}` keeps run 1 reproducible on demand. `origin` re-creates the wedge
exactly. A negative result that cannot be re-run is an anecdote.

**Run 2 turns exactly one knob: where the cube is placed.** Everything else — config, gains,
effort limit, solver iterations, cube scale — is untouched.

**Predictions for run 2, banked now:**

1. `face - origin` prints **20–40 mm**, mostly along the tool axis.
2. Pads stall near the Day 3 prediction **q ≈ 0.69**, in a face gap close to 0.0480 m.
3. Filtered pad force becomes **non-zero** — and if net force is non-zero while filtered stays
   at 0, the diagnosis switches cleanly to the cube filter, which is the next knob and not
   this one.
4. `TCP_OFFSET` magnitude lands near **0.10 m**, consistent with Day 3's 0.0767–0.1049 m band.
   Run 1's 0.2258 m is void.
5. Lift slip stays the genuine unknown. A real pad grip may well hold *worse* than the jam did.

### Day 4, run 2 — FAIL 4/8, and it refutes my own diagnosis

Log: `logbook/02_grasp_hold_test_run2.log`. One knob turned: cube placement.

**Two things that got FIXED and stayed fixed** — worth separating from the failures:

- **`TCP_OFFSET` = `(+0.00000, +0.00834, +0.10263)`, magnitude 0.10297 m.** Inside Day 3's
  0.0767–0.1049 m band, and within 1 mm of the banked prediction of ~0.1015 m. The two-instant
  bookkeeping bug is confirmed dead. Run 1's 0.2258 m is void.
- **The 8.78 mm pin sag is gone.** Per-step tracking is a constant **0.681 mm** — a steady
  one-step readback lag, benign, and no longer a mystery. The instrumentation earned its place.

**And one prediction I got wrong.** `face - origin` came out at **12.62 mm**; I banked 20–40 mm.
The pad AABB centre sits much closer to the joint axis than the GUI capture suggested.

#### The refutation

| | cube placement | min face gap | outcome |
|---|---|---|---|
| Run 1 | pad body-origin midpoint | 0.0651 m | wedged, held through the lift |
| Run 2 | 12.62 mm lower, pad AABB centre | 0.0690 m | **fell 358.92 mm — straight to the floor** |

In run 2 the cube dropped to `z = 0.0240 m`, which is exactly its half-edge resting on the
ground. It was never jammed and never gripped. Yet the fingers still stalled — lag reaching
**0.2741 rad** — at a face gap of **0.0690 m**, twenty-one millimetres wide of a cube they
demonstrably were not touching. Net force zero on both pads throughout.

**So the cube is not what stops the fingers.** Two runs, two cube positions, the same stall
gap (~0.078 m origin gap in both). That is the signature of an obstruction that does not depend
on the cube at all — and I spent two runs assuming placement was the variable.

Note what the lag curve says on its own: `τ = k · lag` with `k = 100` means a lag of 0.274 rad
demands 27.4 N·m against a 10 N·m cap. **The finger joints are sitting on their effort limit.**
Something is resisting with the full 10 N·m in a gripper that, on Day 3's kinematic sweep,
closed all the way to a 0.0216 m origin gap. The difference between Day 3 and now is not the
cube — it is that Day 3 teleported the joints and this drives them through a PD loop.

#### Run 3 is the control experiment that should have come first

`--no-cube` removes the cube from the scene entirely — not parked elsewhere, absent. A cube
somewhere else is still a filter target and still a body the solver knows about; a control has
to remove the variable, not relocate it.

Also added, both measurements rather than knobs:

- **Contact sensors on `r1`/`l1` as well as `r2`/`l2`.** "Which link is touching?" has now been
  answered by argument twice and been wrong twice. It becomes a column.
- **`enabled_self_collisions` printed in the header.** If self-collision is live, the
  convex-decomposition colliders of adjacent finger links interpenetrate at their shared joint
  and PhysX shoves them apart — which stalls the gripper at a fixed opening regardless of what
  is between the pads. That is precisely the symptom both runs produced.

`--grasp-depth` is added but **defaults to 0**, so default behaviour is unchanged.

#### Prediction for run 3, banked before it runs

**The empty gripper will stall at the same place, around a 0.078 m origin gap.** If it does, the
cube was never the variable, both my placement diagnoses were wrong, and the knob is inside the
gripper — self-collision first, then `effort_limit_sim`.

If instead the empty gripper closes cleanly to Day 3's 0.0216 m, then the cube really is the
obstruction, the proximal-link force column will say so directly, and `--grasp-depth` is the
one knob.

#### Method note worth keeping for the write-up

I turned a knob twice on a diagnosis reached by argument, and the control run that would have
settled it in ninety seconds was never written. The lesson is not "the wedge hypothesis was
wrong" — it is that **a control experiment is cheaper than a correct hypothesis**, and the rule
against changing two things at once does not protect you if you are confidently changing the
wrong one thing.

### Day 4, run 3 (CONTROL, `--no-cube`) — the run that found it

Log: `logbook/02_grasp_hold_test_run3_control.log`. Header confirms `self collisions: False`,
`mode: CONTROL — NO CUBE`, all 4 finger prims resolved.

**The empty gripper is perfect.** Lag flat at −0.0002 rad across the entire stroke, `q_meas`
tracking `q_cmd` to 1.0002, closing to an origin gap of **0.0213 m** / face gap **0.0132 m** —
matching Day 3's kinematic sweep (0.0216 / 0.0137) to well under a millimetre. Zero contact on
all four links.

**My run-3 prediction was wrong, and that is the point.** I predicted the empty gripper would
stall at ~0.078 m and that the fault was internal — self-collision or the effort limit. It does
not stall at all. The gripper, the PD gains, the 10 N·m effort limit and the config are all
vindicated in one ninety-second run.

So the cube *was* the obstruction after all. Which sends the question back to: why does a
0.048 m cube stop the pads at 0.069 m?

#### The answer is in the arithmetic

| Width the cube can present | Value |
|---|---|
| edge | 0.0480 m |
| **face diagonal** | **0.0679 m** |
| body diagonal | 0.0831 m |

| Run | min face gap | |
|---|---|---|
| 1 | 0.0651 m | between edge and face diagonal |
| 2 | **0.0690 m** | **the face diagonal, within 1.1 mm** |
| 3 (empty) | 0.0132 m | = Day 3 kinematic |

**The pads were closing onto the cube's diagonal, not its face.** Both runs pinned the cube with
the identity quaternion — axis-aligned to the **world** — while the gripper hangs at the wrist's
orientation, which is nothing like world-aligned at this home pose. The cube was presented
corner-first from the very first run.

That closes every loose end at once:

- **Stall 21 mm wide of the cube** — not wide at all. The fingers closed correctly onto the
  widest section of a rotated cube.
- **Zero pad force** — a corner touches the pad geometry at a point, off the flat inner face,
  and in run 2 the proximal links were not yet sensed.
- **Fell the instant the pin released** — a corner grip has no flat contact to hold with.
- **Run 1's GUI capture showing the cube tilted ~15 degrees** — that tilt was the *cause*, and I
  read it as a symptom of the wedge.
- **Run 1 held while run 2 dropped** — run 1's cube jammed in the throat; run 2's, 12.6 mm
  lower, had nothing to jam against.

#### Run 4: one knob — pin the cube in the WRIST frame

`pin_cube_quat` now carries the wrist orientation, so the cube's faces are square to the pads.
And the claim is checked rather than asserted: PHASE 0 measures the pads' actual separation
direction from their body positions, compares it against the wrist's local +y (which the URDF
says is the direction the fingers travel — joint origins at y = ±0.008, axes along x), and
prints the angle with a PASS/FAIL at 5 degrees.

A "closer to the face diagonal than to the edge" warning is now printed on the stall width, so
this specific mistake announces itself instead of needing to be re-derived.

**Predictions banked for run 4:**

1. PHASE 0 angle between the pad closing axis and the wrist +y: **< 5 degrees**.
2. Stall at a face gap near **0.0480 m**, i.e. `q ≈ 0.69` — the Day 3 prediction, finally tested
   against a squarely presented cube.
3. Filtered pad force **non-zero**, and in the same order as the datasheet 170 N.
4. Static hold passes. Lift slip remains the genuine unknown.

#### Method note, and it is the real result of the day

Three runs, three hypotheses, all mine, all wrong: the proximal-link wedge, the placement depth,
the internal self-collision. Every one of them was reached by argument from a table. What broke
the loop was a **control** — remove the object entirely and see whether the mechanism works at
all — and it took ninety seconds. The confirming evidence was then a piece of *arithmetic*
(0.048 × √2 = 0.0679) that could have been done on Day 3.

`face - origin`, `--grasp-depth` and the proximal sensors were all built to chase hypothesis 2.
None of them were wrong to add, but none of them found this. The control did.

### Day 4, run 4 — the orientation fix worked, and the r1/l1 sensors named the culprit

Log: `logbook/02_grasp_hold_test_run4.log`.

**The orientation fix is confirmed, exactly:**

```
pad closing axis : [-1.000 -0.000 +0.032]
wrist local +y   : [-1.000 -0.000 +0.032]
angle between    : 0.00 deg
[PASS] cube frame is square to the pads (angle < 5 deg)
```

The cube is now presented square to the pads. That hypothesis was right and is closed.

**And the corner-grip theory is now dead too.** With a square cube the stall is still at a
0.0695 m face gap, so 0.0679 m was a coincidence of arithmetic, not the mechanism. Being right
about the orientation did not make me right about the cause.

**What actually names it is the column that was added as instrumentation:**

| | pads `r2`/`l2` | proximal `r1`/`l1` |
|---|---|---|
| peak net contact force | **0.0 N** | **589.8 N** |

The proximal links carry the entire load. The pads carry nothing. **That is the wedge, measured
rather than argued** — the same conclusion I asserted twice without evidence, now with a number
behind it. The cube is riding the throat of the hand, and the earlier placement corrections
(12.62 mm) moved it nowhere near far enough.

**One reporting bug found in the same run.** `peak_net` was maxing over both the pad and the
proximal columns, so it inherited the 589.8 N and the channel diagnosis printed "the pads ARE in
contact; the cube filter is not resolving" — the wrong branch. Fixed. The table underneath was
correct throughout, which is the argument for printing raw columns next to any derived verdict.

#### Run 5: grasp AT THE FINGERTIP — one knob, and it is what the supervisor asked for

New placement mode `--place-at tip`, now the default. It puts the cube's OUTER face flush with
the distal end of the pads, 2 mm of margin back from the very end:

```
tip_mid = wrist_origin + tool_axis * (pad_reach_along_tool - cube_edge/2 - 0.002)
```

`pad_reach_along_tool` is measured, not assumed: the eight corners of each pad's link-local AABB
are transformed into world by the link's current pose and projected onto the tool axis. It is
read at the pose it is used at, because the pads rotate as `q` changes.

This is also the physically right answer independent of the debugging. A parallel gripper is
designed to hold at the fingertips — that is where the faces are flat, where the moment arm on
the finger is smallest, and where the ROBOTIS 170 N figure is specified. Holding mid-face lets
the cube reach the curved proximal links, which is precisely what run 4 measured.

`padface` and `origin` are kept, so every earlier failure stays reproducible on demand.

**Predictions banked for run 5:**

1. `tip - padface` prints **20–40 mm** further out.
2. Proximal force `Nr1`/`Nl1` drops to **~0 N**; pad force `Nr2`/`Nl2` becomes the loaded pair.
3. Stall at a face gap near **0.0480 m**, i.e. `q ≈ 0.69` — Day 3's prediction, on its first
   genuinely fair test.
4. Filtered pad-to-cube force non-zero. If `Nr2 > 0` while `Fc_r2 = 0`, that is the cube filter
   and it is the NEXT knob, not this one.
5. Static hold passes. Lift slip still the honest unknown.

### Day 4, run 5 (`--place-at tip`) — the fingertip move barely moved anything

Log: `logbook/02_grasp_hold_test_run5_tip.log`.

```
pad reach along tool : 0.1165 m from the wrist origin
tip - padface        : 1.39 mm
```

**1.39 mm.** I predicted 20–40 mm. The pad is roughly 53 mm long along the tool axis and the
cube is 48 mm, so the cube already fills the pad almost end to end — "flush with the tip" and
"centred on the face" are practically the same placement. There was never 20 mm of room to move
into.

And the load is unchanged: **peak 654 N on `r1`/`l1`, 0 N on `r2`/`l2`.** The pads still take
nothing, with the cube as far out as the pad geometry allows.

#### Four wrong geometric predictions in one day

| # | Prediction | Actual |
|---|---|---|
| 1 | proximal-link wedge is the cause | it was, but not for the reason given, and unmeasured |
| 2 | `face - origin` = 20–40 mm | 12.62 mm |
| 3 | empty gripper stalls at ~0.078 m | it closes perfectly |
| 4 | `tip - padface` = 20–40 mm | 1.39 mm |

Every one was an inference from joint origins and a screenshot. The two things that actually
advanced the diagnosis were a **control run** and a **contact sensor on a link I had assumed was
irrelevant**. The lesson has now repeated often enough to be the finding: on this hand, do not
reason about geometry — instrument it.

#### The question nobody has measured

`PAD_BODIES` was set to `r2`/`l2` on the assumption that the distal link is the gripping
surface. That assumption has never been checked. The URDF puts `r2`'s origin **49.4 mm outboard**
of `r1`'s, so at `q = 0` the `r2` origins are 114.7 mm apart while the `r1` origins are 16 mm
apart. The proximal links start much closer to the centreline, and the run-5 GUI capture shows
the cube pinched between surfaces that could belong to either link.

If `r1`/`l1` are the inner gripping surface, then **this script has had the two links' roles
backwards since it was written**, "the pads read 0 N" has been the expected result all along,
and every placement fix was aimed at the wrong geometry.

#### PHASE 0b — the measurement that should have existed on Day 3

Added: a free-space sweep, no cube, no contact. At each `q`, the closest approach of **all four**
finger links to the gripper centreline, along the measured closing axis, from the eight corners
of each link's AABB transformed into world at that pose.

The link with the smallest number is the one a centred cube meets first. The `q` at which twice
that number crosses 0.048 m is where the cube is actually captured, and by which link.

This is pure geometry — it cannot be confounded by placement, orientation, contact filtering or
the effort limit, all of which have already sent me down a wrong path once each.

**Prediction, banked, and I am now deliberately low-confidence given the record above:** the
`r1`/`l1` columns will be smaller than `r2`/`l2` over most of the stroke, and `PAD_BODIES` is
naming the wrong links.

### Day 4, run 6 (PHASE 0b) — SOLVED. It was never a bug.

Log: `logbook/02_grasp_hold_test_run6_linkgeom.log`. (First attempt crashed: `pad_idx` was built
from `PAD_BODIES` only, so `r1` raised a `KeyError`. One-line fix, no physics involved.)

**The measurement, free space, no cube, no contact — closest approach of each link to the
centreline, doubled to give the opening:**

| q | pads apart (mm) | proximal apart (mm) |
|---|---|---|
| 0.00 | 106.86 | 7.98 |
| 0.40 | 76.84 | 16.68 |
| 0.60 | 57.40 | 27.30 |
| 0.70 | 46.90 | 31.98 |
| 0.80 | 36.00 | 36.18 |
| **0.90** | 24.84 | **39.86** ← proximal maximum |
| 1.00 | 13.50 | 30.52 |

**The proximal links never open wider than 39.9 mm.** They converge faster than the fingertips
and reach their widest at `q = 0.90`. So any object wider than ~40 mm is captured by the throat
before the pads can close on it — always, at every `q`, regardless of placement, orientation or
grip force.

| cube | pads reach it at | proximal links there | verdict |
|---|---|---|---|
| 48 mm | q = 0.69 | 31.5 mm | **throat first** |
| 40 mm | q = 0.76 | 34.6 mm | throat first |
| 35 mm | q = 0.81 | 36.5 mm | clear by 1.5 mm |
| **30 mm** | **q = 0.85** | **38.2 mm** | **clear by 8.2 mm** |
| 25 mm | q = 0.90 | 39.8 mm | clear by 14.8 mm |

**Day 3's banked prediction of `q ≈ 0.69` was correct.** The pads genuinely do reach a 48 mm
cube at that `q`. What Day 3 could not know — because it only measured the pads — is that the
proximal links get there first. The prediction was right and the conclusion drawn from it was
still wrong, which is worth a sentence in the write-up on its own.

**Nothing was broken.** Not the config, not the gains, not the effort limit, not the contact
sensors, not the orientation, not the placement. Runs 1 through 5 were the gripper behaving
correctly on a cube it is mechanically incapable of fingertip-grasping.

#### Decision: 30 mm cube, `--cube-scale 0.5`

Chosen by measurement, with 8.2 mm of clearance. 35 mm is the largest that clears at all, but by
only 1.5 mm — and Day 3 already flagged that the pad AABB over-approximates a curved fingertip,
so that margin is inside our own error bar. Not a foundation for a benchmark.

Defaults updated: `--cube-scale 0.5`, `--predicted-q 0.85`.

**This must be stated in the methods chapter**, because it changes the task relative to the
archive (which used 0.8 → 48 mm, and never ran cPPO on this gripper). The justification is
strong and external: the object size is set by the gripper's measured kinematics, not chosen for
convenience.

#### Predictions for run 7 — 30 mm cube

1. Proximal force `Nr1`/`Nl1` → **~0 N**; pad force `Nr2`/`Nl2` becomes the loaded pair. This is
   the swap that has failed to appear for five runs.
2. Stall near `q = 0.85`, face gap near 0.030 m.
3. Filtered pad-to-cube force non-zero, same order as the datasheet 170 N. If `Nr2 > 0` while
   `Fc_r2 = 0`, that is the cube filter — the next knob, not this one.
4. Static hold passes.
5. Lift slip: still the honest unknown, but for the first time it will be a real fingertip grip
   being tested rather than a jam.

#### The day in one line

Six runs. Five wrong hypotheses, all mine, all reached by reasoning about geometry from joint
origins and screenshots. Two things worked: a **control run**, and **measuring the geometry
directly instead of arguing about it**. The final answer came from nine rows of numbers that
could have been produced on Day 3 in ten minutes.

---

# Day 5 (2026-07-30) — SECOND GRIPPER: Robotiq 2F-85 opened

> **Scope note, recorded not buried.** The Day 4 handoff said in writing *"that is the 2F-85
> second-gripper track and is NOT on the critical path. Do not start it this session."* It was
> started anyway, at the supervisor's instruction. Module 02's critical path remains open: run 7
> unrun, run 6's PHASE 0b conclusion withdrawn as SUSPECT, pad-vs-proximal load on the RH-P12-RN
> still unmeasured. **The one-day timebox stands. Layer 1 is not gated on this.**

## What the archive gave us (§14 read, nothing copied wholesale)

`~/Abdur_Rabbi_THESIS` was mounted and read. It supplied:

| Item | Value | Status here |
|---|---|---|
| Variant set on `ur5e.usd` | `Gripper = [None, Robotiq_2f_85]` | **hypothesis** — archive read Isaac **5.1**, we are frozen on **5.0** |
| Merged articulation | 12 joints / 16 bodies, ONE articulation | hypothesis, re-checked in PHASE C |
| Nested root to disable | `.../Gripper/Robotiq_2F_85` | method carried, path re-found by name |
| Gripper joints (6) | `finger_joint` + `right_outer_knuckle_joint`, `left`/`right_inner_finger_joint`, `left`/`right_inner_finger_knuckle_joint` | hypothesis |
| Drive stroke | 0 = open, ~0.8 rad = closed | hypothesis, confirmed in PHASE F |

Method carried, constants rejected — the same discipline that caught `TCP_OFFSET = 0.130` on Day 3.

## The archive's failure, named precisely

Its own `Thesis_Documentation/07_Troubleshooting.md`:

> *"the 2f-85's passive pads transmit no normal force, so the gripper can't truly grip"*
> *"cube falls straight through a closed gripper ... raising finger stiffness (20 → 400) /
> effort (50 → 200) did not help"*

Its fix was the **proximity weld** — latch the cube when CLOSE is commanded within 6 cm. That is
not a gripper, and it measured every headline number in the previous thesis.

**The cause is narrower than §9 states, and that distinction is the whole reason this track is
worth a day.** §9 rejects the **URDF route**: a URDF is a tree, cannot express a four-bar loop, so
public 2F-85 URDFs break the loop and paper over it with `<mimic>` tags that Isaac Lab 2.3 does not
honour (#2424, #2626). **The archive never used a URDF.** It used the NVIDIA USD variant, where the
loop is rigged in USD and no tree restriction applies. What it did was drive `finger_joint` alone
and leave the other five joints **passive at stiffness 0**, on the stated reasoning that *"the
mechanical loop makes them follow."*

That reasoning fails in Isaac Lab specifically, and the source is upstream rather than me:
**Isaac Sim resolves closed-loop kinematics automatically through USD schemas; Isaac Lab requires
every mimic joint to be fully specified in the ArticulationCfg** (#2424, #2626, #2665). A joint
Isaac Lab was never told about is not coupled — it is limp. Limp joints fold under contact instead
of transmitting it. That *is* "pads touch, force ≈ 0 N".

## The bet

**All six finger joints DRIVEN from one scalar through an explicit sign table. None passive.**

Not a new idea: it is the pattern that already worked in this folder on the RH-P12-RN, where four
coupled joints sharing one scalar target reproduced the ROBOTIS published 106.0 mm to +0.4 mm. The
signs live in the binary-action command, not in the actuator gains — so the policy still sees ONE
scalar and the two grippers remain benchmark-comparable.

**If the pads still read ≈ 0 N with all six driven, §9 is confirmed on its own terms.** That closes
the 2F-85 as a documented negative result and is worth a paragraph in the book. It is not a failed
session. Do not tune gains to escape it — the archive already tried exactly that.

## Files written (Day 5) — none run

| File | What it does |
|---|---|
| `ur5_grasp/tools/make_ur5e_robotiq_usd.py` | PHASES A–F: variant discovery → build → topology → **sign table tested** → **free-space link sweep** → stroke vs 85 mm |
| `ur5_grasp/robots/ur5e_robotiq_cfg.py` | ArticulationCfg. Arm gains from the measured `ur5e_cfg.py`. Six driven finger joints. Contact sensors **ON**. |
| `ur5_grasp/robots/__init__.py` | `GRIPPERS = {"rhp12", "robotiq85"}` registry, `DEFAULT_GRIPPER = "rhp12"` |

Checked offline only: all 12 joints matched by exactly one actuator group, no overlaps.
**Nothing above is a result.**

## Day 4's lesson, built in rather than written under

PHASE E measures the free-space closest approach of **every** finger link to the centreline before
anything touches anything — the nine rows of numbers that would have saved six runs on the
RH-P12-RN. `PAD_BODIES` is carried as a **labelled hypothesis with a test attached**, because that
exact assumption went unchecked for two days on the other hand.

The AABB caveat that withdrew the run-6 conclusion is written into `support()`: an axis-aligned box
around a curved link reports its inner face at every height, so every clearance is a **lower** bound.
Safe for the open gap, optimistic for the closed gap. A passing closed check is not proof the pads
meet — contact force is.

## Banked BEFORE the run

- Robotiq published: **stroke 85 mm**, **gripping force 20–235 N**, payload 5 kg.
- PHASE F checks open clear opening against **85 mm ± 4 mm**.
- `GRIPPER_EFFORT_LIMIT = 12.0 N·m` from 235 N × ~0.05 m — **PROVISIONAL**, calibrate against the
  measured FORCE not the torque. The archive's `200.0` is ~17× the datasheet and is rejected.
- Prediction, low confidence given Day 4's record: PHASE D keeps `standard-mimic`, and PHASE E finds
  the pads innermost (the 2F-85 is a designed *parallel* gripper, unlike the RH-P12-RN's adaptive
  throat) — so the RH-P12-RN's throat-capture problem should **not** reappear here.

## Decision rules — written BEFORE the run, one knob per symptom

| Symptom | Diagnosis | ONE knob |
|---|---|---|
| PHASE A: `ISAAC_NUCLEUS_DIR` says 5.1 | not the frozen stack | **STOP.** Fix the env. Every number below belongs to a different asset. |
| PHASE A: no `Gripper` variant set | variant route closed on Isaac 5.0 | **STOP.** Close the 2F-85 as a negative result. Do not improvise a URDF import. |
| PHASE A: `Gripper` exists, `Robotiq_2f_85` not among options | renamed on 5.0 | Update `WANT_VARIANTS["Gripper"]` to the printed name. Nothing else. |
| PHASE B: gripper prim not found | variant selection did not take | Read the printed prim paths, fix `GRIPPER_ROOT_NAME`. Nothing else. |
| PHASE C: joint names differ from the archive | 5.0-vs-5.1 asset difference | Update `MIMIC` keys from the printed list. **Record it — it is a finding, not a nuisance.** |
| PHASE C: counts ≠ 12/16 | same | Record. Do **not** tune. The names are authoritative, the counts are not. |
| PHASE D: neither table closes the gripper | §9 arriving at the kinematic level | **STOP.** Negative result, header banner. Do not touch gains. |
| PHASE D: `mirrored-right` kept | NVIDIA axes ≠ ros-industrial convention | Copy that table into `MIMIC`. **Worth a line in 07_Troubleshooting.md and the methods chapter.** |
| PHASE E: a non-pad link is innermost | throat capture, as on the RH-P12-RN | Set cube size from the table. Object size fixed by measured kinematics — state it in methods. |
| PHASE F: opening off by ≫ 4 mm | wrong stroke `q`, not wrong gains | Adjust `Q_CLOSE` only. |
| Grasp test: pads touch, force ≈ 0 N | **the §9 failure reproducing with all six driven** | **STOP. Log as a negative result. Do not tune.** This is the answer, not a bug. |
| Grasp test: arm twists when closing | IsaacLab #3385, not the reward | Note it and move on. Out of timebox. |

## Next steps

1. Run `make_ur5e_robotiq_usd.py`. Read PHASES A→F **in order** and stop at the first FAIL.
2. Only on a clean pass: `grasp_hold_test.py --gripper robotiq85`.
3. **Return to the RH-P12-RN critical path** — run 7, and the withdrawn run-6 conclusion.
