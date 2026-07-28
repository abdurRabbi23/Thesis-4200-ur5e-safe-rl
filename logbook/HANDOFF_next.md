HANDOFF — UR5e Safe-RL Thesis · Module 02: GRASP TEST + RHP12 CFG (Day 4, 2026-07-29)

READ FIRST: logbook/00_INDEX.md, then logbook/02_grasp_env.md
            (the Day 3 section and the "Open question" at the end of that file matter most —
             rationale and decision rules outrank these commands)

## GOAL OF THIS SESSION
Write the RH-P12-RN ArticulationCfg, then prove by measurement that the gripper HOLDS the
cube — not merely that it can close to the right width in free space.

## DONE MEANS
- `ur5_grasp/robots/ur5e_rhp12_cfg.py` written, arm actuators taken from the MEASURED
  `ur5e_cfg.py` (elbow stiffness 1320, per-group bands — NOT a blanket 800/40)
- a grasp script closes on the cube and prints the **stall width** and the **contact force at
  the pads**, then lifts and reports cube z-drop
- the stall width is compared against the banked prediction **q ≈ 0.69**, with the verdict
  written by the script, not inferred by the reader
- `TCP_OFFSET` for this thesis measured HERE against a real grasp
- `02_grasp_env.md` + `run_log.md` + `00_INDEX.md` updated; committed and pushed

## WHY IT MATTERS
Layer 1's claim is safe *grasping*. The previous attempt's headline numbers were measured with
a proximity WELD standing in for a gripper, and its own `00_INDEX.md` Day 17 records that cPPO
was never run on the RH-P12-RN. Everything measured on Day 3 is free-space geometry: it shows
the pads CAN reach the right separation and says nothing about whether a grasp survives lift
accelerations. This session closes that gap, or the thesis carries the archive's hole.

## STATE — what is already done (verified on disk 2026-07-28)
- **Arm signed off** (Day 2). `check_ur5e.py` 9/9. Elbow stiffness **1320**, measured.
  Home-pose EE x=0.433 y=0.133 z=0.473 m. Effort 150/150/150/28/28/28 N·m.
- **Gripper mounted** (Day 3). `ur5_grasp/assets/ur5e_rhp12.usd` built, validated 7/7:
  10 joints / 12 bodies, ONE articulation.
- Measured geometry (`logbook/02_make_ur5e_rhp12.log`):
  - face gap open **0.1064 m**, closed **0.0137 m**
  - open clear opening **106.4 mm** vs ROBOTIS published **106.0 mm** (+0.4 mm)
  - TCP from wrist **0.0767 m** open → **0.1049 m** closed — travels 28.2 mm, NOT a fixed point
  - pad reach from body origin: 0.0041 (r) + 0.0040 (l) = 0.0081 m
- **DexCube edge measured by drop test**: raw **0.06000 m**, at scale 0.8 **0.04800 m**
  (`logbook/02_measure_dexcube.log`). The archive's 0.0412 m is WRONG by 8.5 mm raw, and its
  `TCP_OFFSET = 0.130` is invalidated with it — do not carry either over.
- Tools on disk: `make_ur5e_rhp12_usd.py`, `inspect_usd_geometry.py`, `measure_dexcube_drop.py`.
- `ur5_grasp/scripts/probe_gripper_assets.py` exists but has **NOT been run**. That is the
  2F-85 second-gripper track and is NOT on the critical path. Do not start it this session.
- **Nothing in `ur5_grasp/robots/` for the gripper yet** — only `ur5e_cfg.py` (arm).

## RUNBOOK

STEP 0 — session start (~1 min)
    conda activate isaaclab                      # fresh NoMachine terminals start in (base)
    sudo cpupower frequency-set -g performance
    cd ~/Abdur_Rabbi_Thesis_updated
    git status                                   # must be clean
    ls ur5_grasp/robots/ ur5_grasp/assets/       # confirm what does / does not exist

STEP 1 — write ur5e_rhp12_cfg.py (~30 min)
  CONFIRM BEFORE WRITING: read `ur5e_cfg.py` and carry the three per-group actuator bands
  across. The archive used ONE blanket arm group at stiffness 800 / damping 40; using that
  throws away Day 2's measured elbow correction.
  Gripper joints: rh_p12_rn, rh_r2, rh_l1, rh_l2 — all four take the SAME scalar target.
  Usable stroke q ∈ [0, 1.0] (r2/l2 cap at 1.0 even though r1/l1 allow 1.1).
  Grip force is set by `effort_limit_sim`, NOT by stiffness.
  Leave TCP_OFFSET to STEP 3.

STEP 2 — grasp + hold test (~45 min)
  CONFIRM FROM THE HEADER: cube edge printed as 0.04800 m, and the gripper joint list read
  off the articulation — never assumed. PhysX returns them as rh_l1, rh_p12_rn, rh_l2, rh_r2,
  reordered by tree depth.
  WATCHING FOR: the q at which the pads stall.
  PREDICTION, banked 2026-07-28: **q ≈ 0.69**.
  The test MUST print CONTACT FORCE at the pads, not just separation. Zero force with the
  fingers visibly touching is the §9 Robotiq failure reproducing on a different gripper.

STEP 3 — measure TCP_OFFSET here (~15 min)
  Take it from the pad midpoint AT THE GRASP, not at q=0. The midpoint travels 28.2 mm over
  the stroke, so a q=0 reading is the wrong point by construction.

## DECISION RULES — written BEFORE the run, one knob per symptom
| Symptom | Diagnosis | The one knob |
|---|---|---|
| stall at q ≈ 0.69 ± 0.03, pads flat on cube | working as predicted | none — record and move on |
| stall EARLIER than ~0.62 | cube wedged on the curved proximal r1/l1 links | TCP offset, alone |
| stall LATER than ~0.76 | cube slipping through, or being crushed | `effort_limit_sim`, alone |
| pads touch, contact force ≈ 0 | the §9 failure mode reproducing | STOP. Log as negative result. Do not tune. |
| cube launches on close | drive too aggressive | `effort_limit_sim` down, alone |
| holds statically, drops on lift | the wedge — a static test cannot see it | TCP offset, alone |

Never change two things at once. The previous attempt burned four days and produced three
wrong diagnoses by pairing one change with four "compensating" ones.

## OPEN QUESTION — answer before the PPO baseline, not after
The RH-P12-RN URDF gives **4 independently drivable joints**; the real hardware is **1-DOF**
(one Dynamixel, mechanical coupling). If the policy commands all four freely, what does a
Layer 3 sim-to-real claim actually mean? Decide the action space deliberately.

## REFERENCE NOTES (carried forward)
- **NEW, Day 3: `Usd.PrimRange` silently skips instance proxies.** Isaac props and
  URDF-converted assets are instanced by default, so any traversal that counts or authors
  geometry finds nothing and reports success. Use `Usd.TraverseInstanceProxies()`. Instance
  proxies AND prototypes are read-only — to edit geometry, clear the instanceable flag first,
  or bind from an ancestor outside the prototype (which is how the gripper colour works).
- **Always `PYTHONUNBUFFERED=1`, absolute `tee` paths, `${PIPESTATUS[0]}`.** Day 2 lost a run
  to block-buffered stdout: Isaac Sim died inside `simulation_app.close()` and the log looked
  truncated rather than lost. New scripts should call
  `sys.stdout.reconfigure(line_buffering=True)` at the top.
- Robotiq 2F-85 is **rejected for the critical path** (§9): closed-loop 4-bar, passive pads
  transmit no normal force in PhysX. The RH-P12-RN URDF is a pure **tree**, so every joint is
  directly drivable — the whole reason for choosing it.
- The lift-env **table is Isaac Lab stock** — `lift_env_cfg.py:45`, SeattleLabTable at
  `[0.5, 0, 0]`, cube at `[0.5, 0, 0.055]`. Inherited by subclassing `LiftEnvCfg`. Nothing to
  build or import.
- Run from `cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab` with `-p ../ur5_grasp/...`;
  `isaaclab.sh` lives inside the clone, not the thesis root.
- `TiledCamera` hangs on Blackwell — use `Camera`. (Layer 2 concern, not here.)
- `Kit/Isaac-Sim/5.1` in logs is benign — asset library version, not the simulator.
- Task id pattern for later: `Isaac-Lift-Cube-UR5e-<variant>-v0`. Subclass the runner cfg and
  set a distinct `experiment_name` **before** the first run, or checkpoints collide.

## AT SESSION END (§15 — non-negotiable)
1. Update `logbook/02_grasp_env.md`
2. Add the dated lines to `run_log.md`
3. Update the status block in `logbook/00_INDEX.md`
4. Rewrite this file for the next session
5. `git add -A && git commit && git push origin main` — from the lab PC
