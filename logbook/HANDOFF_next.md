HANDOFF — UR5e Safe-RL Thesis · Module 01: ENVIRONMENT SETUP (Day 1, TBD)

READ FIRST: logbook/00_INDEX.md, then PROJECT_INSTRUCTIONS.md (§7 frozen stack, §9 landmines),
            then logbook/01_env_setup.md.


## GOAL OF THIS SESSION

Verify the machine still matches the frozen stack, clone Isaac Lab release/2.3.0 fresh into
this folder, and get a stock Isaac Lab task training end to end.

## DONE MEANS

- `conda activate isaaclab` works; torch reports 2.7.0+cu128 and `cuda.is_available() == True`
- `IsaacLab/` cloned at release/2.3.0 and built
- One stock task (e.g. Franka Reach) trains headless for a few hundred iterations without NaNs
- TensorBoard reachable from the laptop over Tailscale
- `01_env_setup.md` and `run_log.md` updated; first push done

## WHY IT MATTERS

Everything downstream assumes this stack. Every hour spent proving it works now is an hour not
spent misdiagnosing a training bug that was really an install bug.

## STATE — what is already done

Nothing. This folder contains only the skeleton. `IsaacLab/` does not exist yet.

## RUNBOOK

### STEP 0 — verify the machine before cloning anything

    conda env list
    conda activate isaaclab
    python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
    python -c "import numpy; print(numpy.__version__)"

CONFIRM: torch 2.7.0, cuda 12.8, True, RTX 5090, driver 580.x, numpy 1.26.0.
If any of these differ from PROJECT_INSTRUCTIONS.md §7 — STOP and fix that first.

### STEP 1 — clone Isaac Lab (fresh)

    cd ~/Abdur_Rabbi_Thesis_updated
    git clone --branch release/2.3.0 https://github.com/isaac-sim/IsaacLab.git IsaacLab

Then follow the Isaac Lab source-install steps for Isaac Sim 5.0.0.

### STEP 2 — smoke test on a stock task

    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    tmux new -s smoke
    conda activate isaaclab
    ./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
        --task Isaac-Reach-Franka-v0 --headless --num_envs 4096 --max_iterations 100 \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/01_smoke_franka_reach.log

CONFIRM FROM THE HEADER: task name, num_envs, and that a log directory is created.
WATCHING FOR: no NaNs, mean reward rising, it/s in the expected range.

### STEP 3 — TensorBoard over Tailscale

    tensorboard --logdir ~/Abdur_Rabbi_Thesis_updated/IsaacLab/logs --bind_all

Reachable from the laptop at 100.109.10.66:6006.

## DECISION RULES

| Symptom | Single knob | Action |
|---|---|---|
| `cuda.is_available()` False | driver / torch build | Stop. Do not proceed until True. |
| Build fails on numpy | numpy version | Pin back to 1.26.0. Do NOT bump. |
| TensorBoard "connection refused" | the process | Process is down — restart it. |
| TensorBoard hangs / times out | network | Tailscale or campus Wi-Fi — use hotspot or LAN IP. |
| Warp `cuDeviceGetUuid` warning | none | Harmless. Ignore. |

## END OF SESSION

Update `01_env_setup.md`, add a line to `run_log.md`, refresh `00_INDEX.md` status,
rewrite this file for Module 02, then commit and push from the lab PC.
