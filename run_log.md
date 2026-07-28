# Run log — UR5e Safe-RL Thesis (clean restart)

One dated line per training run or notable event. Newest at the bottom.
Deep context lives in `logbook/NN_*.md`; this file is the timeline only.

Format: `YYYY-MM-DD | Day N | module | what happened | result / where logged`

---

2026-07-27 | Day 0 | setup | Clean restart. New working folder created at ~/Abdur_Rabbi_Thesis_updated. Skeleton, PROJECT_INSTRUCTIONS.md, CLAUDE.md, logbook and Thesis_Documentation stubs written. Landmine list carried over from the archive into 07_Troubleshooting.md. No code, no configs, no results carried over. | skeleton only, nothing measured

2026-07-27 | Day 1 | 01_env_setup | Stack verified on lab PC: torch 2.7.0+cu128 / CUDA True / numpy 1.26.0 / RTX 5090 / driver 580.173.02 (drift from recorded 580.159.03). Existing `isaaclab` conda env reused — Isaac Sim 5.0.0.0 already present. | all §7 values match except driver; §7 corrected

2026-07-27 | Day 1 | 01_env_setup | Isaac Lab cloned into this folder and pinned to **tag v2.3.0** (branch `frozen/2.3.0`, HEAD 3c6e67bb5) — not the `release/2.3.0` branch, which carries the URDF-importer 2.4.31 startup crash. `./isaaclab.sh -i` run; all five isaaclab* editable installs resolve to this folder, rsl-rl-lib 3.0.1. | clone verified; archive-code import risk cleared

2026-07-27 | Day 1 | 01_env_setup | Cartpole smoke test, `Isaac-Cartpole-v0 --headless`. | PASS — 150 iters, mean ep length 300.00, time_out 0.9988, 16 s. Log: logbook/01_smoke_cartpole.log

2026-07-27 | Day 1 | 01_env_setup | Franka Reach validation, `Isaac-Reach-Franka-v0 --headless --num_envs 4096 --max_iterations 100`. | PASS — 0 NaNs, position_error 0.2702 → 0.0919 m monotonic, reward −2.14 → −0.49 rising, 0.24 s/iter ≈ **4.2 it/s** (archive recorded 2.44 — superseded). Log: logbook/01_smoke_franka_reach.log

2026-07-27 | Day 1 | 01_env_setup | TensorBoard `--bind_all` reachable from laptop at 100.109.10.66:6006; both runs render. | PASS

2026-07-27 | Day 1 | 01_env_setup | False alarm investigated and closed: Kit writes to `Kit/Isaac-Sim/5.1/` while pip reports Isaac Sim 5.0.0.0. Archive logs show the same path across working runs; archive logbook records it as the 5.1 *asset library* vs 5.0 sim. pip is authoritative. | benign — logged in 07_Troubleshooting.md §5

2026-07-27 | Day 1 | 01_env_setup | **Module 01 COMPLETE.** All six gates green. Next: Module 02 UR5e ArticulationCfg. | ✅

2026-07-27 | Day 1 | git | First real push failed: remote was `https://` and GitHub no longer accepts password auth. `ssh -T git@github.com` confirmed the key works; `git remote set-url origin git@github.com:abdurRabbi23/Thesis-4200-ur5e-safe-rl.git` fixed it. | pushed — commit d5f4b47, `[new branch] main -> main`, 52 objects. §5 corrected (it claimed SSH)

2026-07-27 | Day 2 | 02_grasp_env | STEP 2 — asset probe. `probe_ur5e_asset.py` listed the Nucleus UniversalRobots folder with the shipped UR10e path as a reachability CONTROL. | RESOLVED Option A — `ur5e/ur5e.usd` exists on Nucleus (alongside ur3/ur3e/ur5/ur10/ur10e/ur16e/ur20/ur30). No URDF import needed. Log: logbook/02_probe_ur5e_asset.log

2026-07-27 | Day 2 | infra | **New landmine.** Probe run 1 logged the Isaac Sim banner then stopped dead — zero script output. Cause: Isaac Sim dies inside `simulation_app.close()` and Python stdout is block-buffered through `tee`, so the buffer is discarded. Also `$?` after a pipe reports tee (always 0), not the script. | Fixed by `PYTHONUNBUFFERED=1` + `sys.stdout.reconfigure(line_buffering=True)`; use `${PIPESTATUS[0]}`. Logged in 07_Troubleshooting.md

2026-07-27 | Day 2 | 02_grasp_env | STEP 3 — wrote `ur5_grasp/robots/ur5e_cfg.py`, arm only, modelled on **UR10e_CFG** (three actuator groups), not UR10_CFG. Gravity kept ON, against the UR10e reference, matching FRANKA_PANDA_CFG — the analogue for joint-position RL, and the honest choice for Layer 3. | cfg written; effort limits deliberately left to the USD

2026-07-27 | Day 2 | 02_grasp_env | STEP 4 run 2 — `check_ur5e.py`, UR10e gains verbatim. 8/9 PASS. Elbow steady-state sag 0.026703 rad (1.53°) vs 0.0089 elsewhere; `shoulder_pan` 0.000080 confirms physics (vertical axis, no gravity torque). τ = k·err gives elbow 16.0 N·m — largest load, weakest gain (600 vs shoulder 1320), inherited from the heavier UR10e. | FAIL on drift tolerance only. Diagnosis: under-gained elbow, not instability

2026-07-27 | Day 2 | 02_grasp_env | STEP 4 run 3 — **one knob**: elbow stiffness 600 → 1320. Prediction recorded before the run: 0.01214 rad. | **PASS 9/9.** Measured 0.011847 (−2.4%, explained by τ falling 16.02 → 15.64 N·m). All other joints unchanged to 4 dp. EE +7 mm in z vs +6.7 predicted. `τ = k·err` now calibrated. Log: logbook/02_check_ur5e.log

2026-07-27 | Day 2 | 02_grasp_env | Archive inspected on request ("robot with a table"). **The table is Isaac Lab stock** — `lift_env_cfg.py:45`, SeattleLabTable at [0.5,0,0]; the archive inherited it via `LiftEnvCfg` and so will we. Nothing to import. Archive's own work is the gripper; `ur5e_rhp12.usd` is a 2 KB reference stub, not a model. Archive `00_INDEX.md` Day 17: its Layer 1 headline rests on a **proximity weld**, cPPO never run on RH-P12-RN. | Decision: copy `rh_p12_rn/` URDF+meshes as third-party source, rebuild USD + mount here, re-measure every geometric number

2026-07-27 | Day 2 | 02_grasp_env | **ARM SIGNED OFF.** UR5e ArticulationCfg loads clean: 6 joints correct order, 7 bodies, fixed base, effort 150/150/150/28/28/28 N·m and vel 3.142 rad/s both matching the UR5e datasheet, no ArticulationRootAPI error, home pose held. EE at x=0.433 y=0.133 z=0.473 m. | ✅ Next: gripper (RH-P12-RN)

**2026-07-28 (Day 3)** — Scope change agreed: **one UR5e, two selectable grippers** (RH-P12-RN +
Robotiq 2F-85), both really actuated. Driver is optionality + literature comparability, *not* lab
hardware — so the 2F-85 is a bonus, RH-P12-RN stays the Layer 1 critical path. §9's rejection
re-opened on one condition: a shipped, already-coupled USD must exist. Wrote
`ur5_grasp/scripts/probe_gripper_assets.py` (not yet run) — checks the stock `ur5e.usd` for a
`Gripper` variant set, lists Nucleus gripper folders, and inspects any candidate's variants, with
the ur10e path as control. Switch design decided: two built USDs + a `GRIPPERS` registry behind a
`--gripper` flag; separate task ids and `experiment_name` per gripper. 2F-85 timeboxed to ONE day.
Verified by grep on our own copy: RH-P12-RN URDF has 4 revolute joints, **0 mimic tags** — pure
tree, independently confirming the archive diagnosis. Open question logged: sim gives 4 drivable
finger joints where the real RH-P12-RN is 1-DOF. Detail in `logbook/02_grasp_env.md`.

2026-07-28 | Day 3 | 02_grasp_env | STEP 1 — copied `ur5_grasp/assets/rh_p12_rn/` from the archive as third-party source: 7 files, 88 K (URDF + LICENSE_ROBOTIS + 5 STL), MD5-identical. **No `.usd` and no calibrated number copied.** | done

2026-07-28 | Day 3 | 02_grasp_env | STEP 2 — read the archive's `make_ur5e_rhp12_usd.py` for METHOD only, then wrote our own `ur5_grasp/tools/make_ur5e_rhp12_usd.py`. Method carried over: convex-decomposition colliders, `Gripper=None` variant, strip the nested articulation root, fixed mount joint. Departures: no borrowed numbers, cube edge measured not hardcoded, PASS/FAIL criteria written into the script, report to `logbook/`. | script written

2026-07-28 | Day 3 | 02_grasp_env | STEP 3 run 1 — build + validate. **Mount works: 10 joints / 12 bodies, ONE articulation**, nested articulation root stripped at `/Robot/RHP12/rh_p12_rn_base`. Stroke sweep monotonic, origin gap 0.1145 → 0.0216 m — **matches the archive's table to 4 dp**, an independent replication of the geometry. | PASS on topology; two measurements wrong (below)

2026-07-28 | Day 3 | 02_grasp_env | **My bug, not Isaac's.** `measure_pad_half_thickness` used `size/2` and projected it — correct only if the AABB is centred on the body origin, which it is not (the origin sits on the joint axis). Symptoms: open clear opening 92.4 mm against a published 106 mm, and an impossible **negative** face gap (−0.0004 m) at full close. | Diagnosed before re-running

2026-07-28 | Day 3 | 02_grasp_env | STEP 3 run 2 — **one knob**: AABB half-size → true AABB support, and the two pads measured in OPPOSITE directions. Predictions recorded before the run. | **7/7 PASS.** face_gap q=0 **0.1064 m** (predicted 0.1067), q=1.00 **0.0137 m** (predicted 0.0138), pad reach 0.0041+0.0040 = **0.0081 m** (predicted 0.0078). Control held: origin_gap and TCP byte-identical to run 1. Log: `logbook/02_make_ur5e_rhp12.log`

2026-07-28 | Day 3 | 02_grasp_env | **External validation.** Open clear opening **106.4 mm** vs the ROBOTIS published stroke **106.0 mm** (+0.4 mm). Source: emanual.robotis.com/docs/en/platform/rh_p12_rn/ (stroke cut 109 → 106 mm from 2019-11-04 for fingertip durability). First geometry number in this thesis validated against a source outside the project. | ✅ datasheet check added as a permanent acceptance criterion

2026-07-28 | Day 3 | 02_grasp_env | Wrote `ur5_grasp/tools/inspect_usd_geometry.py` — one diagnostic for two open problems, because both are USD **instancing** questions. Walks a stage with and without `Usd.TraverseInstanceProxies()` and reports bounds per purpose, extent hints and raw mesh points. | run on cube + gripper

2026-07-28 | Day 3 | 02_grasp_env | **Cube edge settled by physical measurement.** USD reading was ambiguous (visuals-after-transform 0.060, collision extent 0.060, but `purpose=guide` gave a nonsensical 0.0036). Drop test on a plane at z=0: raw cube rests at **0.03000 m** → edge **0.06000 m**; at env scale 0.8 rests at 0.02400 → **0.04800 m**. Scaling exactly linear. Both at rest (|v| = 0.00012 m/s). | **The archive's 0.0412 m is WRONG by 8.5 mm (raw).** My own prior prediction of 0.0515 also refuted. Log: `logbook/02_measure_dexcube.log`

2026-07-28 | Day 3 | 02_grasp_env | **Consequence — archive TCP_OFFSET 0.130 is invalidated.** Its justification ("pad faces close to 0.0415 m against a 0.0412 m cube, delta +0.3 mm — a true flat-pad parallel grip") is built on a cube that is really 0.048 m. Pads cannot close to 0.0415 around a 0.048 m cube. **Do not carry 0.130 over.** Concrete vindication of §14; worth a paragraph as a negative result. | archive grasp calibration rejected

2026-07-28 | Day 3 | 02_grasp_env | **Grasp-test prediction derivable now.** Interpolating our own face_gap column at the measured 0.0480 m cube: pads should stall at **q ≈ 0.69**. Later = crushing or slipping; earlier = wedging on the curved r1/l1 links. Written before the run. | prediction banked

2026-07-28 | Day 3 | 02_grasp_env | **Second wrong diagnosis of my own, caught.** `colour_gripper` reported "0 renderable prims" and its warning blamed a failed reference. `inspect_usd_geometry.py` showed the truth: all 10 finger meshes are USD **instances** (`/__Prototype_1..10`) and `Usd.PrimRange` does not descend into instance proxies. Confirmed the same for the DexCube (2 instances). | GUI check: **hand renders black** — the ancestor material binding already reaches the proxies, because it is authored outside the prototypes

2026-07-28 | Day 3 | 02_grasp_env | Removed the dead per-mesh `displayColor` loop rather than fixing it — instance proxies and prototypes are both READ-ONLY, and the root binding already works. Mesh count now taken through `TraverseInstanceProxies()`, so a zero really would mean a failed reference. | script corrected; no re-run needed

2026-07-28 | Day 3 | infra | **New landmine.** `Usd.PrimRange(prim)` silently skips instance proxies. Any traversal that authors or counts geometry on an imported asset will find nothing and report success. Both Isaac props and URDF-converted assets are instanced by default. | logged for `07_Troubleshooting.md`
