HANDOFF — UR5e Safe-RL Thesis · Module 02: GRIPPER (RH-P12-RN) (Day 3, 2026-07-28)

READ FIRST: logbook/00_INDEX.md, then logbook/02_grasp_env.md
            (the STEP 2b archive inspection and the "Open problems" section matter most —
             rationale and decision rules outrank these commands)

## GOAL OF THIS SESSION
Get the ROBOTIS RH-P12-RN gripper onto the signed-off UR5e arm as **one articulation**, and
prove the fingers can physically close on the cube — by measuring pad separation, not by
looking at it.

## DONE MEANS
- `ur5_grasp/assets/rh_p12_rn/` holds the URDF + 5 STL + LICENSE (copied as third-party source)
- a build script in this folder converts that URDF to USD and mounts it on the flange
- the combined robot loads as **ONE** articulation: 10 joints / 12 bodies, no nested
  articulation root, no `ArticulationRootAPI` error
- a gripper sweep prints **measured pad separation** from open to closed, and the closed value
  is compared against the 0.0412 m DexCube
- `ur5_grasp/robots/ur5e_rhp12_cfg.py` written, with TCP offset **measured here**, not copied
- `02_grasp_env.md` + `run_log.md` + `00_INDEX.md` updated; committed and pushed

## WHY IT MATTERS
Layer 1's whole claim is safe *grasping*. The previous attempt's headline numbers were measured
with a proximity weld standing in for a gripper, because the Robotiq 2F-85's closed-loop 4-bar
transmits no pad force in PhysX — and its own `00_INDEX.md` (Day 17) records that cPPO was never
run on a real gripper at all. That is the gap this thesis has to close. A gripper that cannot be
*shown* to close on the cube makes every later benchmark number unfalsifiable.

## STATE — what is already done (verified on disk 2026-07-27)
- **Arm signed off.** `check_ur5e.py` 9/9 PASS. `ur5_grasp/robots/ur5e_cfg.py` points at
  `{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd`. Gravity ON.
- Elbow stiffness is **1320**, not the UR10e reference 600 — measured change, see
  `02_grasp_env.md` Results. Elbow damping is still 34.64 and deliberately un-retuned.
- Home-pose EE (`wrist_3_link`): **x=0.433, y=0.133, z=0.473 m**.
- Effort limits from the USD: 150/150/150/28/28/28 N·m. Velocity 3.142 rad/s.
- `ur5_grasp/` is a real package now (`__init__.py` in root and `robots/`).
- Existing scripts: `probe_ur5e_asset.py`, `check_ur5e.py`. Logs:
  `02_probe_ur5e_asset.log`, `02_check_ur5e.log`.
- **Nothing gripper-related exists yet.** `ur5_grasp/assets/` is empty except `.gitkeep`.

## RUNBOOK

STEP 0 — session start (~1 min)
    conda activate isaaclab                      # fresh NoMachine terminals start in (base)
    sudo cpupower frequency-set -g performance   # Day 2 logs showed "powersave" — do not skip
    cd ~/Abdur_Rabbi_Thesis_updated
    git status                                   # must be clean
    ls ur5_grasp/assets/ ur5_grasp/robots/       # confirm what does / does not exist

STEP 1 — copy the source assets ONLY (~2 min)
    cp -r ~/Abdur_Rabbi_THESIS/ur5_grasp/assets/rh_p12_rn ~/Abdur_Rabbi_Thesis_updated/ur5_grasp/assets/
    ls -R ur5_grasp/assets/rh_p12_rn/
  CONFIRM: 7 files — rh_p12_rn.urdf, LICENSE_ROBOTIS, meshes/{base,l1,l2,r1,r2}.stl (~88 K).
  DO NOT copy: `ur5e_rhp12.usd` (a 2 KB reference stub), `rh_p12_rn.usd`, `robots/ur5e_rhp12.py`,
  or any calibrated number. Those are the previous attempt's *measurements* — §14.

STEP 2 — read the archive build script for METHOD, then write our own (~30 min, do NOT skip)
    sed -n '1,60p' ~/Abdur_Rabbi_THESIS/ur5_grasp/tools/make_ur5e_rhp12_usd.py
  CONFIRM FROM THE FILE: the three-part method — (a) UrdfConverter with **convex decomposition**
  colliders so pad faces survive, (b) reference stock `ur5e.usd` with variant `Gripper=None`,
  (c) **disable the gripper's nested articulation root** and add a fixed mount joint
  `wrist_3_link -> base`.
  QUESTION TO ANSWER BEFORE CODING: why does step (c) matter — what breaks if two articulation
  roots survive in one prim tree? Answer it before you write the script.

STEP 3 — build the USD
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_rhp12_usd.py --headless \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_build_rhp12.log
    echo "EXIT=${PIPESTATUS[0]}"      # NOT $? — after a pipe that is tee's status, always 0
  CONFIRM FROM THE OUTPUT: exactly **one** articulation; 10 joints; 12 bodies.
  WATCHING FOR: the 4 gripper joints named and drivable, not passive.

STEP 4 — the real acceptance test: measure the pads
  Sweep the gripper open → closed and print pad separation at each step.
  CONFIRM: separation decreases monotonically and the closed value brackets the DexCube's
  0.0412 m. A gripper that visually closes but never reaches the cube width has not passed.
  Only then derive TCP offset — measured in this folder, against these gains.

STEP 5 — close the session (§15, non-negotiable)
  Update `02_grasp_env.md`; dated line in `run_log.md`; refresh `00_INDEX.md`; rewrite this file;
  `git add -A && git commit && git push origin main` from the lab PC.

## DECISION RULES
_Written before the run. One symptom → one named knob._

| Symptom | Single knob | Action |
|---|---|---|
| more than one articulation reported | the gripper's nested articulation root | Disable it in the USD authoring step. Do not "fix" it by editing the cfg. |
| `ArticulationRootAPI` error after mounting | the mount joint / root prim path | The arm alone passed on Day 2 — so the fault is the attachment, not the arm. Bisect against `check_ur5e.py`. |
| joint count ≠ 10 | the URDF conversion | Wrong or partial conversion. Back to STEP 3. |
| gripper visually clocked or sunk into the wrist | `--mount_pos` / `--mount_rpy` — **one at a time** | Nudge one, re-run, re-look. |
| pads close but never reach 0.0412 m | the TCP offset | Re-measure. Do NOT reuse the archive's 0.130 — it was calibrated against stiffness 800. |
| pads touch but the cube slips under motion | `effort_limit_sim` on the gripper drive | Grip force is set by effort, not stiffness (archive `05_layer3_sim2real.md:116`). |
| tempted to start the lift env "to see if it works" | scope | Don't. Gripper sign-off first. Build before attach. |

Never change two things at once. One symptom → one named knob.

## NOTES / LANDMINES RELEVANT TO THIS MODULE
- **Always `PYTHONUNBUFFERED=1`, always absolute `tee` paths, always `${PIPESTATUS[0]}`.**
  Day 2 lost a whole run to block-buffered stdout: Isaac Sim died inside
  `simulation_app.close()` and the log looked truncated rather than lost. New scripts should
  also call `sys.stdout.reconfigure(line_buffering=True)` at the top.
- Robotiq 2F-85 is **rejected** (§9): closed-loop 4-bar, passive pads transmit no normal force
  in PhysX. The RH-P12-RN URDF is a pure **tree** (5 links / 4 revolute joints), so every joint
  is directly drivable — that is the whole reason for choosing it.
- All four gripper joints take the **same scalar target**; opposed axis signs keep the pads
  parallel. r1/l1 allow 1.1 rad but r2/l2 only 1.0, so usable stroke is q ∈ [0, 1.0].
- The lift-env **table is Isaac Lab stock** — `lift_env_cfg.py:45`, SeattleLabTable at
  `[0.5, 0, 0]`, cube at `[0.5, 0, 0.055]`. Inherited by subclassing `LiftEnvCfg`. Nothing to
  build or import. That is next session's business, not this one's.
- Run from `cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab` with `-p ../ur5_grasp/...`;
  `isaaclab.sh` lives inside the clone, not the thesis root.
- `TiledCamera` hangs on Blackwell — use `Camera`. (Layer 2 concern, not here.)
- `Kit/Isaac-Sim/5.1` in logs is benign — asset library version, not the simulator.
- Task id pattern for later: `Isaac-Lift-Cube-UR5e-<variant>-v0`. Subclass the runner cfg and
  set a distinct `experiment_name` **before** the first run, or checkpoints collide.
