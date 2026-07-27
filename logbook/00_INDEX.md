# Thesis Logbook — INDEX (read this first)

Front door for the UR5 Safe RL Grasping thesis. **Any new chat starts here.**

## How I work across chats

Each Cowork chat is a separate session, but they all share **this folder** as memory.
To start a new chat with full context:

1. Open the chat inside the thesis project.
2. Connect this folder (`Abdur_Rabbi_Thesis_updated`).
3. Say: *"Read `logbook/00_INDEX.md` and `logbook/<module>.md`, then continue with X."*

Three layers of memory:

- **`run_log.md`** — the daily timeline (what happened each day, chronological).
- **`logbook/NN_*.md`** — one file per work-stream (deep context: goals, decisions, files, next steps). Use these for "how / why did I do X".
- **`logbook/HANDOFF_next.md`** — the runbook for the *next* session. Rewritten at the end of every session.

Rule of thumb: work happens in a module → update that module file **and** add a dated line to `run_log.md`.

## Project one-liner

Safe Adaptive IBVS with constrained RL (cPPO) for precision grasping on a UR5e, sim → real.
Three layers: **L1** safe-RL grasping in sim (must-pass), **L2** IBVS visual loop (stretch),
**L3** sim-to-real on the physical UR5e (optional). See `PROJECT_INSTRUCTIONS.md`.

## Current status (updated 2026-07-27, Day 0 — CLEAN RESTART)

**The thesis has been restarted from zero in a new folder.** The previous attempt is archived
read-only at `~/Abdur_Rabbi_THESIS` and must not be written to. Nothing in this folder has been
built or measured yet — only this skeleton exists.

**Module 01 is next.** Fresh clone of Isaac Lab `release/2.3.0` into `IsaacLab/`, verify the
frozen stack against `PROJECT_INSTRUCTIONS.md` §7, then validate the RL loop on a stock reaching
task before touching anything UR5-specific.

**Carried over from the archive:** the working method, the documentation system, the frozen stack,
and the landmine list in `Thesis_Documentation/07_Troubleshooting.md`. **No code, no configs and
no results were carried over.** Any number that enters this thesis must be re-measured here.

**Before the first command:** confirm the machine still matches §7 (`conda env list`, torch version
+ CUDA availability, `nvidia-smi` driver). If anything has drifted, fix that before cloning.

## Modules

| File | Work-stream | Status |
|---|---|---|
| `01_env_setup.md` | Stack install, Isaac validation, reaching tasks | ▶ NEXT |
| `02_grasp_env.md` | UR5e lift env, grasp, PPO baseline | ◻ not started |
| `03_cppo_benchmark.md` | Safety constraints + cPPO vs PPO (**Layer 1 deliverable**) | ◻ not started |
| `04_layer2_ibvs.md` | IBVS visual loop, RL-tuned image Jacobian (Layer 2) | ◻ not started |
| `05_layer3_sim2real.md` | Real gripper + ROS 2 transfer (Layer 3) | ◻ not started |
| `06_writing.md` | Thesis chapters, figures, defence prep | ◻ ongoing |
| `07_documentation.md` | The documentation system itself | ✅ skeleton created |

## Roadmap

| Weeks | Work | Module |
|---|---|---|
| 1–4 | Environment setup; validate RL loop on a stock reaching task | `01` |
| 5–8 | Grasping task with privileged pose info | `02` |
| 9–10 | Safety constraints + cPPO vs PPO benchmark → **Layer 1 done** | `03` |
| 11–13 | Layer 2 (IBVS); Layer 3 if time allows | `04`, `05` |
| 14–16 | Results, writing, defence prep | `06` |
