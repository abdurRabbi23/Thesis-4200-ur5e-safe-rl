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

## Current status (updated 2026-07-27, Day 2 — MODULE 02: ARM SIGNED OFF)

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

**Module 02 continues with the gripper.** Robotiq 2F-85 stays rejected (§9). Plan: copy the
archive's `assets/rh_p12_rn/` URDF + meshes as **third-party source**, then rebuild the URDF→USD
conversion and flange mount *here*, re-measuring every geometric number. Detail in
`02_grasp_env.md`; runbook in `HANDOFF_next.md`.

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
| `02_grasp_env.md` | UR5e lift env, grasp, PPO baseline | ▶ ACTIVE — arm ✅ signed off (Day 2), gripper next |
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
