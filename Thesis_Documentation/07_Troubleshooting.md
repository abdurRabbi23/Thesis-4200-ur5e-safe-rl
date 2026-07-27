# 07 — Troubleshooting

Every error hit, and what fixed it.

**Sections 1–4 are carried over from the previous attempt (`~/Abdur_Rabbi_THESIS`).** These are
lessons, not progress — they cost real days to find. Read them before starting each module.
Section 5 is where errors found in *this* attempt get added.

---

## 1. Simulator, assets and configuration

**`TiledCamera` hangs on Blackwell (RTX 5090, sm_120).**
Symptom: the sim starts and never progresses. Fix: use `Camera` instead — output is identical at
`num_envs=1`. Relevant to Layer 2 (IBVS) more than anywhere else.

**Isaac Lab ships no pre-built UR5 config.**
It has to be written from scratch, modelled on the UR10 pattern in
`isaaclab_assets/robots/universal_robots.py`. Budget time for this in Module 02.

**Robotiq 2F-85 is rejected for the critical path.**
Mimic joints / kinematic loops are an unresolved Isaac Lab problem (issue #2424, discussion #2626).
Approved alternatives: a simple two-finger prismatic gripper (Franka-hand style), or the ROBOTIS
RH-P12-RN. Escape hatch if contact modelling fights back: fixed-joint / surface grasp, documented
as an explicit abstraction rather than a hidden shortcut.

**`ArticulationRootAPI` error when attaching a gripper.**
Validate the **arm-only** `ArticulationCfg` in the GUI first, and only attach a gripper once it
loads clean. Build before attach.

**`isaaclab.sh` not found.**
It lives inside the `IsaacLab/` subdirectory, not the thesis root. Run training from
`cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab` with `-p ../ur5_grasp/scripts/train.py`.

**Warp `cuDeviceGetUuid` warning on driver 580.**
Harmless. A fallback path is active. Ignore it.

**`num_envs` throughput does not transfer between tasks.**
The 8192 default was calibrated on Franka Reach, which is far lighter than a UR5 grasping env.
Re-time it on the actual env before setting any training budget. Franka Reach reference:
4096 → 2.44 it/s, 8192 → 1.98 it/s, 16384 → 1.35 it/s. **⚠ Superseded 2026-07-27 — this machine
measures ~4.2 it/s at 4096 envs. See §5.**

---

## 2. Safe RL / cPPO — the expensive ones

**The silent failure mode.** A buggy Lagrangian cPPO trains perfectly normally while the safety
constraint does nothing at all. Nothing crashes; the curves look healthy; the result is worthless.
Review points, every time:

- loss combination and the **λ update sign convention**
- cost limit `d` defined **per-step vs per-episode**
- discount factor used for the cost GAE
- episode-boundary bootstrapping for the cost value head

**λ sitting at zero for a whole run means the benchmark is meaningless.**
Decide *before* launching what you will check in the first 100 iterations to confirm λ is doing
work. Finding out at iteration 1500 wastes the run.

**cPPO cannot cut violations that don't exist.**
Gate every cPPO run on its PPO baseline having a violation rate high enough to be reduced. If the
unconstrained baseline is already safe, stop — the comparison proves nothing. In the previous
attempt this cost a full run: a velocity-capped env drove violations to ~0.02%, leaving cPPO with
nothing to constrain.

**Velocity caps are a confound, not a control.**
A 1.0 rad/s arm ceiling drove singularity violations to zero *and* stopped the sparse lift reward
bootstrapping (lift 1.57 vs 13.84). Useful as an **ablation** — it shows the safety constraint isn't
trivially substitutable by slowing the arm — but useless as a benchmark environment.

**Experiment names collide and overwrite checkpoints.**
A new task variant registered against an existing runner cfg will dump its runs on top of earlier
results. Subclass the runner and set a distinct `experiment_name` **before** the first run.

**`Episode_Reward/*` per-term values ARE horizon-independent.**
`reward_manager.py:118` divides by `max_episode_length_s`. Only raw `Mean reward` scales with
episode length. An earlier note claiming otherwise was wrong and had to be chased through several
files — when correcting a doc claim, chase it everywhere.

**Never change two things at once.**
The previous attempt burned four days and produced three wrong diagnoses by pairing a velocity cap
with four "compensating" changes (episode length, gamma, entropy coefficient, curriculum pin). A
bisect eventually showed the cap was innocent. Write the decision rules before the run: one symptom,
one named knob.

---

## 3. Logging and results

**Relative `tee` paths bite.** A training log `tee`'d to a relative path landed under `IsaacLab/`
and looked lost. Always use an absolute path. (Real data survives in the TensorBoard event files.)

**Training logs carry no success scalar.** Success rate has to come from a separate eval script,
and that script's exact flags must be documented alongside the number in
`06_Results_and_Experiments.md`.

**Checkpoint directories get deleted.** A banked baseline checkpoint vanished while only its text
log survived, which broke a planned fallback. Never plan around a checkpoint you have not just
`ls`'d.

---

## 4. Infrastructure and remote access

**"Connection refused" vs hang/timeout.** Connection refused = the process is down, restart it.
Hang or timeout = network or firewall.

**Campus Wi-Fi blocks Tailscale coordination traffic.** On campus, use a phone hotspot, or connect
over the local LAN IP when physically in the department.

**Dropped NoMachine sessions kill training.** `tmux` is mandatory for every training run.

**Fresh NoMachine terminals start in `(base)`.** Always `conda activate isaaclab` first.

**`.git/index.lock` stuck.** `rm -f .git/index.lock` on the lab PC. Push from the lab PC — the SSH
key lives there. If a push is rejected as "behind": `git pull --rebase origin main`, then push.

**Isaac Sim 6.0 pairs only with Isaac Lab 3.0-beta.** Dependency conflicts and architectural
instability. The stack is frozen at Isaac Sim 5.0.0 + Isaac Lab 2.3.0. Do not upgrade.

---

## 5. This attempt

_Add every new error here as it is hit: symptom → cause → fix → date. Log the doc change in
`09_Changelog.md`._

| Date | Module | Symptom | Cause | Fix |
|---|---|---|---|---|
| 2026-07-27 | 01 | Kit logs and user config load from `omni/.../Kit/Isaac-Sim/**5.1**/` while `pip list` reports Isaac Sim **5.0.0.0** — looks like the 5.0/5.1 mix-up §7 forbids | The **5.1** is the Nucleus **asset library** / Kit data-directory version, not the simulator version. The archive's own logs contain the identical path in 26 places across runs that produced documented results | **Nothing to fix — benign.** `pip list \| grep -i isaacsim` is the authoritative check. Do not act on the log path. |

**Pin Isaac Lab to the TAG `v2.3.0`, never the `release/2.3.0` branch.**
The branch tip advanced to 2.3.1, which exact-pins URDF importer `2.4.31` while Isaac Sim 5.0.0
ships `2.4.19` → training crashes at startup. Carried over from the previous attempt (its Day 8
bug), and §7 of `PROJECT_INSTRUCTIONS.md` said "release/2.3.0" until 2026-07-27, when it was
corrected. Correct clone: `git checkout -b frozen/2.3.0 v2.3.0`, then confirm with
`git describe --tags`.

**Reusing an existing conda env can import code from the old thesis folder.**
`./isaaclab.sh -i` registers the five `isaaclab*` packages as **editable** — a name→path pointer,
one slot per name. An env built by a previous attempt still points at that attempt's folder, so
`import isaaclab` silently runs old code and nothing errors. Check with
`python -c "import isaaclab; print(isaaclab.__file__)"` and `pip list | grep isaaclab`; the paths
must contain the current working folder. Re-running `./isaaclab.sh -i` from the new clone
overwrites the pointers.

**Franka Reach throughput on this machine is ~4.2 it/s at 4096 envs, not 2.44.**
Measured 2026-07-27 (0.24 s/iter). The previous attempt's table (4096 → 2.44, 8192 → 1.98,
16384 → 1.35) reflects an older driver/env and must not be used for budgeting here. Re-time on the
actual target env in any case — `num_envs` throughput does not transfer between tasks.

**A script's log ends mid-startup with none of the script's own output.**
Symptom: the log shows the Isaac Sim GPU banner and then simply stops; the shell prompt has
returned; no Python traceback anywhere. It looks like a truncated or hung run. It is neither.
Two things combine:
1. Isaac Sim can die hard inside `simulation_app.close()`. A native crash never unwinds, so
   Python's buffers are discarded rather than flushed.
2. Python's `stdout` is **block-buffered** (~4 KB) when piped — as it always is under `| tee`.
   Everything the script printed is still sitting in that buffer when the process dies.
The Isaac Sim banner survives because it comes from carb's C++ logger, which writes directly.
That is exactly what makes the log look truncated instead of lost.
Ruling it out is cheap: a Python *exception* would still print, because `stderr` is not
block-buffered. No traceback + no output = native crash, not a Python error.
Fix, both applied in this project: `PYTHONUNBUFFERED=1` on the command line, and
`sys.stdout.reconfigure(line_buffering=True)` at the top of every script so it defends itself
regardless of how it is invoked.
Related trap in the same command: after a pipe, `$?` reports **tee's** exit status, which is
always 0. A segfaulting script looks successful. Use `${PIPESTATUS[0]}`.
First hit 2026-07-27, Module 02 (`probe_ur5e_asset.py` run 1).

**Isaac Lab 2.3.0 ships no UR5 or UR5e configuration — but the USD asset exists.**
`isaaclab_assets/robots/universal_robots.py` defines UR10 and UR10e only, and
`grep -rni "ur5" IsaacLab/source/` returns two hits, both in a 2022 changelog line. The
articulation config must be written. The *asset* does not: the Nucleus library carries
`Robots/UniversalRobots/ur5e/ur5e.usd` (alongside ur3, ur3e, ur5, ur10, ur10e, ur16e, ur20,
ur30). Do not import a URDF for the arm. Verify with `ur5_grasp/scripts/probe_ur5e_asset.py`,
which lists the folder and includes the shipped UR10e path as a **control** — without that
control an unreachable asset server is indistinguishable from a missing asset, and the wrong
conclusion costs an afternoon of URDF conversion.

**Steady-state joint sag is not drift, and stiffness is the knob — but only after you know which joint.**
A held pose settling to a *constant* non-zero error is a P-controller balancing gravity:
`err = τ_gravity / k`. It is not instability. Diagnose it by multiplying each joint's error by
its own stiffness — that recovers the gravity torque each joint actually carries, and names the
one to change. A max-over-joints number alone names a symptom, not a knob.
Sanity check that validates the whole measurement: `shoulder_pan` error must be ≈ 0, because its
axis is vertical and gravity has no leverage about it. If it isn't, distrust the rest.
Measured here 2026-07-27: elbow carried the largest torque (16.0 N·m) on the *weakest* gain
(600 vs shoulder 1320) because `UR10e_CFG` was tuned for a heavier arm. Raising elbow stiffness
600 → 1320 moved the error 0.026703 → 0.011847 rad against 0.01214 predicted (−2.4%, explained
by τ falling to 15.64 N·m as the arm sags less). `τ = k · err` is a calibrated way to set an arm
gain from a measured torque.
Caution: raising `k` alone lowers the damping ratio. Steady-state error does not care, so the
prediction holds — but watch the step trace for ringing, and treat damping as the *next* single
knob, never the same edit.
