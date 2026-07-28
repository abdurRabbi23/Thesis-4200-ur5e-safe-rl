# 09 — Changelog

One dated entry per documentation change. This is a convention, not optional.

Format: `YYYY-MM-DD — file(s) — what changed and why`

---

2026-07-27 — all — Clean restart. Documentation skeleton created in the new working folder
(`~/Abdur_Rabbi_Thesis_updated`). `07_Troubleshooting.md` pre-filled with the landmine list carried
over from the previous attempt; every other file is an empty stub. No results, code or configs
carried over.

2026-07-27 — `PROJECT_INSTRUCTIONS.md` §7 — **corrected two wrong values.** (a) Isaac Lab ref changed
from "release/2.3.0" to **tag `v2.3.0`**. The branch tip advanced to 2.3.1 and exact-pins a URDF
importer Isaac Sim 5.0.0 does not ship — the previous attempt's Day 8 startup crash. §7 had carried
the branch name forward, and it propagated into `logbook/HANDOFF_next.md` STEP 1, which would have
reproduced the bug. Caught before the clone. (b) NVIDIA driver changed from 580.159.03 to
**580.173.02**, measured on the lab PC. Also updated the §10 project-structure comment.

2026-07-27 — `Thesis_Documentation/07_Troubleshooting.md` §5 — three entries added from Module 01:
the benign `Kit/Isaac-Sim/5.1` vs pip `5.0.0.0` false alarm; the tag-not-branch rule; and the
editable-install trap when reusing a conda env from the previous attempt. Also annotated the §1
Franka Reach throughput table as superseded.

2026-07-27 — `PROJECT_INSTRUCTIONS.md` §5 (Git) — corrected. §5 claimed an SSH remote; the repo was
actually created with `https://`, which fails outright since GitHub removed git password auth. The
remote URL, the one-time `git remote set-url` fix, and the `ssh -T git@github.com` check are now
recorded explicitly instead of assumed.

2026-07-27 — `logbook/01_env_setup.md`, `run_log.md`, `logbook/00_INDEX.md`,
`Thesis_Documentation/01_Environment_Setup.md`, `10_Command_Reference.md` — Module 01 written up:
all six verification gates, measured values, and the commands that produced them.

2026-07-27 — `Thesis_Documentation/07_Troubleshooting.md` — three entries added from Module 02:
the block-buffered-stdout trap that makes a crashed Isaac Sim script look truncated (plus the
`$?`-reports-tee trap); the "no UR5 config but the USD exists" finding and why the probe needs a
reachability control; and the steady-state-sag diagnosis method (`τ = k · err`) with the
`shoulder_pan ≈ 0` sanity check.

2026-07-27 — `logbook/02_grasp_env.md`, `run_log.md`, `logbook/00_INDEX.md`,
`logbook/HANDOFF_next.md` — Module 02 arm sign-off written up: the asset probe result, the UR10e
-vs-UR10 pattern decision, the gravity-on decision and its rationale, the single elbow-stiffness
change with its pre-registered prediction and measured outcome, and the archive inspection.

2026-07-27 — archive inspection recorded in `logbook/02_grasp_env.md` STEP 2b. Correction to a
working assumption: the lift-env **table is Isaac Lab stock** (`lift_env_cfg.py:45`,
SeattleLabTable at `[0.5, 0, 0]`), not previous-attempt work — it is inherited by subclassing
`LiftEnvCfg` and requires no import. Also recorded that the archive's Layer 1 headline numbers
were measured with a proximity weld, not a working gripper, per its own `00_INDEX.md` Day 17.

2026-07-28 — `logbook/02_grasp_env.md`, `run_log.md`, `logbook/00_INDEX.md`,
`logbook/HANDOFF_next.md`, `06_Results_and_Experiments.md`, `07_Troubleshooting.md`,
`10_Command_Reference.md` — Day 3 written up: RH-P12-RN mounted as one articulation, stroke
measured, DexCube edge settled by drop test.

Two corrections propagated through every file that carried them:

1. **The DexCube edge is 0.06000 m raw / 0.04800 m at env scale 0.8**, measured by drop test
   (resting centre height × 2). The previous attempt's 0.0412 m is wrong by 8.5 mm raw. A
   prediction of 0.0515 m made *in this session* was also refuted — recorded rather than
   quietly dropped.
2. **The archive's `TCP_OFFSET = 0.130` is invalidated.** Its justification ("pad faces close
   to 0.0415 m against a 0.0412 m cube, delta +0.3 mm") is arithmetically impossible against a
   0.048 m cube. Its *origin-gap table* replicates here to 4 dp, so the geometry work was
   sound; it is the calibration against the cube that fails. Method reusable, constants not.

Two new landmines added to `07_Troubleshooting.md`: `Usd.PrimRange` skipping instance proxies,
and AABB half-size being mistaken for reach from a body origin. Both were wrong diagnoses made
and caught within this session; both are recorded with the symptom that exposed them.
