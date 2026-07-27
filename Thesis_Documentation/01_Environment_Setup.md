# 01 — Environment setup

**Status:** ✅ complete (2026-07-27, Module 01).

Written so this stack can be rebuilt from nothing. Every command here was actually run; every
number was measured on the lab PC on 2026-07-27.

---

## Purpose

Get from a bare machine to "a stock Isaac Lab task trains correctly, in this folder". Nothing
UR5-specific happens here. The point is that when a later training bug appears, the install is
already ruled out as the cause.

---

## 1. The frozen stack

Do not upgrade any of these mid-thesis.

| Component | Version | Why it's pinned |
|---|---|---|
| Isaac Sim | **5.0.0** | 6.0 pairs only with Isaac Lab 3.0-beta — dependency conflicts |
| Isaac Lab | **tag `v2.3.0`** | see §3 — the *branch* is broken |
| Python | 3.11, conda env `isaaclab` | Isaac Sim requirement |
| PyTorch | 2.7.0 + cu128 | required for Blackwell `sm_120` (RTX 5090) |
| numpy | 1.26.0 | Isaac Sim expects the NumPy 1.x series |
| RL trainer | `rsl-rl-lib` 3.0.1 | shared by the PPO baseline and our cPPO — keeps the comparison fair |
| NVIDIA driver | 580.173.02 | 570+ required for Blackwell |

---

## 2. Verify the machine before installing anything

```bash
conda env list
conda activate isaaclab
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
python -c "import numpy; print(numpy.__version__)"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
```

**Measured 2026-07-27:** `2.7.0+cu128 12.8 True` · `1.26.0` · `NVIDIA GeForce RTX 5090,
580.173.02, 32607 MiB`.

Pass condition: no `sm_120 is not compatible` warning. If you see it, the torch build is not cu128
— reinstall with the CUDA 12.8 index URL.

> **Do not check the Isaac Sim version with `isaacsim.__version__`** — the pip build has no such
> attribute and it raises `AttributeError`. Use `pip list | grep -i isaacsim`; expect `5.0.0.0`.

---

## 3. Isaac Lab — pin the TAG, never the branch

```bash
cd ~/Abdur_Rabbi_Thesis_updated
git clone https://github.com/isaac-sim/IsaacLab.git IsaacLab
cd IsaacLab
git checkout -b frozen/2.3.0 v2.3.0
git describe --tags        # must print exactly: v2.3.0
```

> **The expensive mistake.** The `release/2.3.0` **branch** silently advanced to 2.3.1, which
> exact-pins URDF importer `2.4.31`; Isaac Sim 5.0.0 ships `2.4.19`. Result: training crashes at
> startup. The `v2.3.0` **tag** pins that importer to "any". This cost the previous attempt a day.

Then install Isaac Lab and let it pull the RL dependencies:

```bash
./isaaclab.sh -i        # installs Isaac Lab + rsl_rl 3.0.1
```

`_isaac_sim` symlink absent afterwards is **normal** for a pip Isaac Sim install. Not a fault.

---

## 4. Confirm the env points at THIS folder

This step exists because the `isaaclab` conda env was reused from the previous attempt.

```bash
python -c "import isaaclab; print(isaaclab.__file__)"
pip list | grep -iE "isaacsim|isaaclab|rsl"
```

**Why it matters:** `./isaaclab.sh -i` registers the five `isaaclab*` packages as **editable** —
a name→path pointer with one slot per name. An env built by an earlier attempt still points at that
attempt's folder, so `import isaaclab` runs old code and **nothing errors**. Re-running
`./isaaclab.sh -i` from the new clone overwrites the pointers.

**Measured 2026-07-27** — all five resolve into `~/Abdur_Rabbi_Thesis_updated/IsaacLab/source/`:
`isaaclab` 0.47.2 · `isaaclab_assets` 0.2.3 · `isaaclab_mimic` 1.0.15 · `isaaclab_rl` 0.4.4 ·
`isaaclab_tasks` 0.11.6 · `isaacsim` 5.0.0.0 (25 packages) · `rsl-rl-lib` 3.0.1.

---

## 5. Validate the RL loop — Test A: Cartpole

Balancing a pole on a cart: the cheapest possible proof that simulator, physics, trainer, GPU and
logging all work together. ~17 seconds. If Cartpole won't train, nothing will.

```bash
cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Cartpole-v0 --headless \
    2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/01_smoke_cartpole.log
```

| Pass condition | Measured 2026-07-27 |
|---|---|
| converges ~150 iterations | 150 |
| mean episode length reaches 300 (the cap) | 300.00 |
| `Episode_Termination/time_out` ≈ 0.999 | 0.9988 |
| `Episode_Termination/cart_out_of_bounds` ≈ 0.001 | 0.0012 |
| wall time ~17 s | 16 s |

> The **first ever** Isaac Sim launch sits silently for several minutes compiling shaders and
> caching assets. That is not a hang.

---

## 6. Validate the RL loop — Test B: Franka Reach at scale

An articulated arm reaching to a target, across thousands of parallel environments — the same shape
of problem as the thesis task, on a robot Isaac Lab already ships.

```bash
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Reach-Franka-v0 --headless --num_envs 4096 --max_iterations 100 \
    2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/01_smoke_franka_reach.log
```

| Pass condition | Measured 2026-07-27 |
|---|---|
| header confirms the right config | `FrankaReachEnvCfg` + `FrankaReachPPORunnerCfg` |
| `num_envs` = 4096 | 4096 (9,830,400 ÷ 100 iters ÷ 24 steps) |
| no NaNs | 0 occurrences (`grep -c -i nan`) |
| `Metrics/ee_pose/position_error` falling | 0.2702 → 0.2475 → 0.2366 → 0.1562 → **0.0919 m** |
| mean reward rising | −2.14 → −1.20 → −0.66 → **−0.49** |
| throughput | 0.24 s/iter = **~4.2 it/s** |

Mean reward is negative throughout and that is correct — the Reach reward is penalty-dominated, so
it climbs toward zero rather than going positive. `position_error` is the trustworthy signal.

**Throughput note.** ~4.2 it/s supersedes the previous attempt's 2.44 it/s for the same task and
env count. Budget off the new number, and re-time on the actual UR5e grasping env anyway —
throughput does not transfer between tasks.

---

## 7. TensorBoard from the laptop

```bash
tensorboard --logdir ~/Abdur_Rabbi_Thesis_updated/IsaacLab/logs --bind_all
```

Laptop browser → `100.109.10.66:6006` over Tailscale. Confirmed working 2026-07-27.

Diagnosing failures: **"connection refused"** = the TensorBoard process is down, restart it.
**Hang or timeout** = network — Tailscale or campus Wi-Fi; use a phone hotspot or the LAN IP.

---

## 8. Known false alarm — `Kit/Isaac-Sim/5.1`

Kit writes its user config and logs to `.../omni/data/Kit/Isaac-Sim/**5.1**/` while `pip list`
reports Isaac Sim **5.0.0.0**. This looks like the 5.0/5.1 mix-up the frozen stack forbids.

**It is benign.** The 5.1 is the Nucleus **asset library** / Kit data-directory version, not the
simulator. Confirmed by the previous attempt: its logs contain the identical path in 26 places
across runs that produced documented results. `pip list` is the authoritative check. Do not act on
the log path.
