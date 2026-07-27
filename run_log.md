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
