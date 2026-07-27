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

