HANDOFF — UR5e Safe-RL Thesis · Module 02: UR5e ROBOT CONFIG (Day 2, 2026-07-28)

READ FIRST: logbook/00_INDEX.md, then PROJECT_INSTRUCTIONS.md (§7 frozen stack, §9 landmines),
            then logbook/02_grasp_env.md and logbook/01_env_setup.md.
            The rationale and decision rules matter more than these commands.

## GOAL OF THIS SESSION
Get a UR5e arm — **arm only, no gripper** — loading cleanly in Isaac Lab as an `ArticulationCfg`,
and confirm it in the GUI.

## DONE MEANS
- `ur5_grasp/robots/ur5e_cfg.py` exists and defines a UR5e `ArticulationCfg`
- the arm loads in the Isaac Sim GUI with **no `ArticulationRootAPI` error**
- all 6 joints are found and named, and their limits print correctly
- the arm holds a commanded home pose without drifting or exploding
- `02_grasp_env.md` + `run_log.md` updated; committed and pushed

## WHY IT MATTERS
Isaac Lab ships no UR5 config — it has to be written. Every later module (grasp env, PPO baseline,
cPPO benchmark, IBVS) sits on this one file. A wrong joint order or a bad articulation root here
surfaces later as a training bug that looks like an RL problem, and costs days to trace back.

## STATE — what is already done (verified on disk 2026-07-27)
- Frozen stack confirmed: torch 2.7.0+cu128, CUDA True, numpy 1.26.0, RTX 5090, driver 580.173.02
- `IsaacLab/` cloned at **tag v2.3.0**, branch `frozen/2.3.0`, HEAD `3c6e67bb5`, gitignored
- `isaaclab` conda env reused; all five `isaaclab*` editable installs resolve to **this** folder;
  Isaac Sim 5.0.0.0; `rsl-rl-lib` 3.0.1
- RL loop validated: Cartpole 150 iters / ep length 300.00 / 16 s;
  Franka Reach 4096 envs 0 NaNs / position error 0.2702 → 0.0919 m / **~4.2 it/s**
- TensorBoard reachable from the laptop at `100.109.10.66:6006`
- `ur5_grasp/` is still an empty skeleton — **no robot config written yet**

## RUNBOOK

STEP 0 — session start (~1 min)
    conda activate isaaclab            # fresh NoMachine terminals start in (base)
    cd ~/Abdur_Rabbi_Thesis_updated
    git status                         # must be clean; if .git/index.lock is stuck: rm -f .git/index.lock
    ls ur5_grasp/robots/               # confirm what does / does not exist before writing

STEP 1 — read the pattern before writing anything (~15 min, do NOT skip)
    sed -n '1,120p' IsaacLab/source/isaaclab_assets/isaaclab_assets/robots/universal_robots.py
  CONFIRM FROM THE FILE: how UR10 declares `spawn` (USD path), `init_state.joint_pos`,
  and `actuators` (stiffness / damping / effort limits).
  QUESTION TO ANSWER BEFORE CODING: where does the UR5e USD come from — the Isaac Sim asset
  library (`ISAAC_NUCLEUS_DIR`) or a URDF we import ourselves? Find out; do not assume.

STEP 2 — locate a UR5e asset
    ls IsaacLab/source/isaaclab_assets/isaaclab_assets/robots/
    grep -rn "UR10_CFG\|ur10" IsaacLab/source/isaaclab_assets/ | head
  DECIDE: reuse a shipped UR5e USD if one exists; otherwise import the official UR5e URDF.
  Record the decision and the reason in `02_grasp_env.md` before proceeding.

STEP 3 — write `ur5_grasp/robots/ur5e_cfg.py`
  Arm only. No gripper. 6 joints. Modelled on the UR10 cfg, not invented from scratch.

STEP 4 — validate in the GUI (~5 min)
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/check_ur5e.py
  (a small script that spawns the arm at num_envs=1 and prints joint names + limits)
  CONFIRM FROM THE OUTPUT: 6 joint names in the expected order, sensible limits,
  and **no `ArticulationRootAPI` error**.
  WATCHING FOR: the arm resting at its home pose without drift, jitter, or explosion.

STEP 5 — close the session (§15, non-negotiable)
  Update `02_grasp_env.md`; dated line in `run_log.md`; refresh the status block in `00_INDEX.md`;
  rewrite this file for the next session; `git add -A && git commit && git push origin main`.

## DECISION RULES
| Symptom | Single knob | Action |
|---|---|---|
| `ArticulationRootAPI` error on load | the articulation root prim path | Fix the root path. Do NOT attach a gripper to "work around" it — build before attach. |
| USD asset not found | the spawn path | Resolve the asset first; do not hand-edit USD. |
| Joint count ≠ 6 | the USD / URDF source | Wrong asset. Go back to STEP 2. |
| Arm drifts or jitters at home pose | actuator stiffness/damping — **one at a time** | Copy the UR10 values first, change one number, re-run. |
| Arm explodes on first step | effort limit | Lower it. One knob only. |
| Tempted to attach a gripper "to test properly" | scope | Don't. Gripper is a separate step, after the arm is signed off. |

Never change two things at once. One symptom → one named knob.

## NOTES / LANDMINES RELEVANT TO THIS MODULE
- Robotiq 2F-85 is **rejected** for the critical path (mimic joints / kinematic loops, Isaac Lab
  issues #2424, #2626). Approved: simple two-finger prismatic gripper (Franka-hand style) or
  ROBOTIS RH-P12-RN. That decision comes *after* the arm loads.
- Run training from `cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab` with `-p ../ur5_grasp/scripts/...`;
  `isaaclab.sh` lives inside the clone, not the thesis root.
- Absolute `tee` paths always.
- `TiledCamera` hangs on Blackwell — use `Camera`. (Matters in Layer 2, not here.)
- `Kit/Isaac-Sim/5.1` in the logs is **benign** — asset library version, not the simulator.
- Task id pattern for later: `Isaac-Lift-Cube-UR5e-<variant>-v0`.
