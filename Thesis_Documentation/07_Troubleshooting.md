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
4096 → 2.44 it/s, 8192 → 1.98 it/s, 16384 → 1.35 it/s.

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
| | | | | |
