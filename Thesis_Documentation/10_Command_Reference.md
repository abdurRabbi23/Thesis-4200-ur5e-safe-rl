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

_To be filled in during Module 01._

## 2. Grasp environment

_To be filled in during Module 02._

## 3. Safety constraints and cPPO benchmark

_To be filled in during Module 03._

---

## Appendix A — planned, not yet run

- Everything. This attempt has not started.

## Appendix B — quick reference

| What | Command |
|---|---|
| Activate env | `conda activate isaaclab` |
| TensorBoard | `tensorboard --logdir <thesis>/IsaacLab/logs --bind_all` (laptop: `100.109.10.66:6006`) |
| Attach to run | `tmux attach -t train` |
