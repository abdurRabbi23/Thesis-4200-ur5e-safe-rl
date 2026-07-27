# Module 01 — Environment setup

**Status:** ✅ COMPLETE (2026-07-27, Day 1)
**Owner file for:** Isaac Lab clone, conda env, stack verification, stock reaching task validation

---

## Goal

Prove the frozen stack works end to end in the new working folder, before any UR5-specific code
exists. Concretely: the `isaaclab` env resolves to code **in this folder**, and a stock Isaac Lab
task trains to its documented convergence criterion.

**Result: met.** All six gates green.

## Decision rules

_Written before the run._

| Symptom | Single knob to change | Threshold to act |
|---|---|---|
| `cuda.is_available()` False | driver / torch build | Stop. Do not proceed until True. |
| Build fails on numpy | numpy version | Pin back to 1.26.0. Never bump. |
| URDF importer version crash at startup | Isaac Lab git ref | Check out tag `v2.3.0`, not the branch |
| `import isaaclab` resolves to `~/Abdur_Rabbi_THESIS` | editable install path | Re-run `./isaaclab.sh -i` from this folder |
| TensorBoard "connection refused" | the process | Process is down — restart it |
| TensorBoard hangs / times out | network | Tailscale or campus Wi-Fi — hotspot or LAN IP |
| Warp `cuDeviceGetUuid` warning | none | Harmless. Ignore. |

## State — what is actually done

Verified on disk, not assumed.

| Item | Verified value | How checked |
|---|---|---|
| conda env | `isaaclab` at `~/miniconda3/envs/isaaclab` (pre-existing, reused) | `conda env list` |
| PyTorch | 2.7.0+cu128, CUDA 12.8, `is_available()` True | `python -c "import torch; ..."` |
| numpy | 1.26.0 | `python -c "import numpy; ..."` |
| GPU | RTX 5090, 32607 MiB | `nvidia-smi --query-gpu=...` |
| NVIDIA driver | **580.173.02** (drift from the recorded 580.159.03) | `nvidia-smi` |
| Isaac Sim | 5.0.0.0 across all 25 `isaacsim-*` packages | `pip list \| grep -i isaacsim` |
| Isaac Lab | tag **`v2.3.0`**, branch `frozen/2.3.0`, HEAD `3c6e67bb5` | `git describe --tags` |
| Isaac Lab packages | all five editable, resolving to **this** folder | `pip list \| grep isaaclab` |
| RL trainer | `rsl-rl-lib` 3.0.1 | `pip list \| grep rsl` |
| `IsaacLab/` gitignored | yes (`.gitignore:2`) | `git check-ignore -v IsaacLab` |

Isaac Lab clone HEAD `3c6e67bb5` is byte-identical to the archive's clone — same tag, same commit.

`_isaac_sim` symlink is **absent**, which is normal for a pip Isaac Sim install (archive
`10_Command_Reference.md` §11.2). Not a fault.

## What was run

```bash
# Gate 1 — stack verification
conda activate isaaclab
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
python -c "import numpy; print(numpy.__version__)"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

# Gate 2 — Isaac Lab clone, pinned to the TAG
cd ~/Abdur_Rabbi_Thesis_updated
git clone https://github.com/isaac-sim/IsaacLab.git IsaacLab
cd IsaacLab && git checkout -b frozen/2.3.0 v2.3.0
git describe --tags        # -> v2.3.0

# Gate 3 — where does the env resolve to?
pip list | grep -iE "isaacsim|isaaclab|rsl"

# Gate 4 — Cartpole smoke test
cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Cartpole-v0 --headless \
    2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/01_smoke_cartpole.log

# Gate 5 — Franka Reach at scale
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Reach-Franka-v0 --headless --num_envs 4096 --max_iterations 100 \
    2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/01_smoke_franka_reach.log

# Gate 6 — TensorBoard
tensorboard --logdir ~/Abdur_Rabbi_Thesis_updated/IsaacLab/logs --bind_all
# laptop: 100.109.10.66:6006
```

Note: `./isaaclab.sh -i` was run after the clone (evidenced by `rsl-rl-lib` 3.0.1 present and all
five `isaaclab*` editable paths pointing at this folder). No separate log was tee'd for it.

## Results

**Cartpole** (`01_smoke_cartpole.log`) — matches the archive's documented convergence exactly:

| Metric | Expected | Measured |
|---|---|---|
| Iterations | ~150 | 150 |
| Mean episode length | 300 (cap) | 300.00 |
| `Episode_Termination/time_out` | ≈0.999 | 0.9988 |
| `Episode_Termination/cart_out_of_bounds` | ≈0.001 | 0.0012 |
| Wall time | ~17 s | 16 s |

**Franka Reach, 4096 envs, 100 iterations** (`01_smoke_franka_reach.log`):

| Metric | Measured |
|---|---|
| NaN occurrences in log | **0** (`grep -c -i nan`) |
| `num_envs` confirmed | 4096 (9,830,400 timesteps ÷ 100 iters ÷ 24 steps) |
| `Metrics/ee_pose/position_error` | 0.2702 → 0.2475 → 0.2366 → 0.1562 → **0.0919 m**, monotonic |
| Mean reward | −2.14 (it 20) → −1.20 → −0.66 → **−0.49**, rising |
| Config loaded | `FrankaReachEnvCfg` + `FrankaReachPPORunnerCfg` |
| Iteration time | 0.24 s → **~4.2 it/s** |

**Throughput supersedes the archive.** The archive recorded 2.44 it/s for Franka Reach at 4096
envs. This machine measures **~4.2 it/s** — roughly 1.7× faster. The archive's throughput table
(4096 → 2.44, 8192 → 1.98, 16384 → 1.35) must not be used for budgeting in this attempt. Re-time
on the actual UR5e grasping env in Module 02 regardless (`num_envs` does not transfer across tasks).

Negative mean reward is expected on Reach — the reward is penalty-dominated, so it climbs toward
zero. `position_error` is the honest signal.

**TensorBoard** reachable from the laptop at `100.109.10.66:6006`; both runs' curves render.

## Open problems

**None blocking.** One resolved false alarm worth remembering:

- Kit writes its config and log directories under `omni/.../Kit/Isaac-Sim/**5.1**/` while
  `pip list` reports Isaac Sim **5.0.0.0**. This looks like the 5.0/5.1 mix-up §7 warns about.
  It is not. Settled by evidence in the archive: the archive's own logs contain the same
  `Kit/Isaac-Sim/5.1` path in 26 places across runs that produced documented results, and
  archive `logbook/01_env_setup.md:21` records *"Nucleus asset library is version 5.1 (assets),
  stack sim is 5.0 — fine."* `pip list` is authoritative. Now logged in
  `Thesis_Documentation/07_Troubleshooting.md` §5 so it costs nobody a second look.

Two doc corrections made as a result of this module — see `09_Changelog.md`.

## Next single action

Module 02: write the UR5e `ArticulationCfg`, modelled on the UR10 pattern in
`isaaclab_assets/robots/universal_robots.py`. Validate the **arm alone** in the GUI (no
`ArticulationRootAPI` error) before attaching any gripper. Build before attach.
