# ur5_grasp — what this package is

All custom thesis code lives here. **Nothing goes inside the `IsaacLab/` clone** — that folder is a
gitignored dependency and gets wiped on a reinstall.

| Directory | Contains |
|---|---|
| `robots/` | UR5e `ArticulationCfg` and gripper configs. Isaac Lab has no pre-built UR5 — model it on the UR10 pattern in `isaaclab_assets/robots/universal_robots.py`. |
| `assets/` | USD files and meshes. |
| `tasks/` | Environment cfgs, reward/cost terms, task registration (`Isaac-Lift-Cube-UR5e-<variant>-v0`), and agent runner cfgs. |
| `safe_rl/` | PPO-Lagrangian (cPPO): cost-aware actor-critic, cost rollout storage, Lagrangian runner, training logic. |
| `scripts/` | `train.py`, eval scripts, geometry checks. |
| `tools/` | One-off utilities. |

## Rules

- **Distinct `experiment_name` per task variant.** A new variant registered against an existing
  runner cfg will overwrite earlier checkpoints. Subclass the runner first.
- Training is launched from the Isaac Lab directory:
  `cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab && ./isaaclab.sh -p ../ur5_grasp/scripts/train.py ...`
- Before touching `safe_rl/`, re-read the cPPO silent-failure checklist in
  `Thesis_Documentation/07_Troubleshooting.md` §2. That class of bug does not announce itself.
