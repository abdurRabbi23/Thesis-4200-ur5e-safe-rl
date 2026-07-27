# 10 — Command reference

Every command actually run, in order, with what it does. Appendix B at the bottom is the
quick-reference for commands used repeatedly.

**Absolute paths only for `tee`.** Relative paths land somewhere unexpected.

---

## Session start (every time)

    conda activate isaaclab                       # fresh NoMachine terminals start in (base)
    sudo cpupower frequency-set -g performance    # before any timed run
    tmux new -s train                             # mandatory for training runs

## 1. Environment setup

All run 2026-07-27 (Module 01). Full rationale and measured results in `01_Environment_Setup.md`.

```bash
# 1.1 — verify the machine against the frozen stack
conda env list
conda activate isaaclab
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
python -c "import numpy; print(numpy.__version__)"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
# -> 2.7.0+cu128 12.8 True | 1.26.0 | RTX 5090, 580.173.02, 32607 MiB

# 1.2 — clone Isaac Lab pinned to the TAG (never the release branch)
cd ~/Abdur_Rabbi_Thesis_updated
git clone https://github.com/isaac-sim/IsaacLab.git IsaacLab
cd IsaacLab && git checkout -b frozen/2.3.0 v2.3.0
git describe --tags          # -> v2.3.0   (HEAD 3c6e67bb5)
./isaaclab.sh -i             # installs Isaac Lab + rsl_rl 3.0.1

# 1.3 — which Isaac Sim, and does the env point at THIS folder?
pip list | grep -iE "isaacsim|isaaclab|rsl"
python -c "import isaaclab; print(isaaclab.__file__)"
# NOTE: isaacsim.__version__ does NOT exist in the pip build — AttributeError. Use pip list.

# 1.4 — Cartpole smoke test (~16 s)
cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Cartpole-v0 --headless \
    2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/01_smoke_cartpole.log

# 1.5 — Franka Reach at scale (~26 s for 100 iters)
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Reach-Franka-v0 --headless --num_envs 4096 --max_iterations 100 \
    2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/01_smoke_franka_reach.log

# 1.6 — TensorBoard, reachable from the laptop
tensorboard --logdir ~/Abdur_Rabbi_Thesis_updated/IsaacLab/logs --bind_all
# laptop browser: 100.109.10.66:6006

# 1.7 — verifying a run afterwards, from the tee'd log
grep -c -i nan logbook/01_smoke_franka_reach.log            # must be 0
grep -E "position_error:" logbook/01_smoke_franka_reach.log # must fall monotonically
```

## 2. Grasp environment

_To be filled in during Module 02._

## 3. Safety constraints and cPPO benchmark

_To be filled in during Module 03._

---

## Appendix A — planned, not yet run

- Module 02 onward. Module 01 is complete and its commands are in §1 above.

## Appendix B — quick reference

| What | Command |
|---|---|
| Activate env | `conda activate isaaclab` |
| TensorBoard | `tensorboard --logdir <thesis>/IsaacLab/logs --bind_all` (laptop: `100.109.10.66:6006`) |
| Attach to run | `tmux attach -t train` |
