# CLAUDE.md — read this before doing anything

This folder is the **working directory** for the UR5 Safe-RL thesis. All work happens here.

## Start here (for any new chat)

1. Read `logbook/00_INDEX.md` — the front door: current status, module map, how work is tracked across chats.
2. Read `PROJECT_INSTRUCTIONS.md` — role, working principles, frozen stack, formatting rules, known landmines.
3. Read the specific `logbook/NN_*.md` for whatever we're working on.
4. If a handoff was pasted, still **verify state on disk** before trusting it (`ls`, `git status`, `git log`).

## Tracking convention

- `run_log.md` — the daily timeline. Add a dated line whenever something happens.
- `logbook/NN_*.md` — per-module deep context: goals, decisions, files, next steps.
- `logbook/HANDOFF_next.md` — rolling runbook for the next session, rewritten at the end of each one.
- **When work happens in a module: update that module file AND add a line to `run_log.md`.** Both.

## The other folder

`~/Abdur_Rabbi_THESIS` is the **previous attempt — read-only archive**. Never write to it. Mine it deliberately per §14 of `PROJECT_INSTRUCTIONS.md`: read the docs freely, but never copy code or results wholesale without asking.

## Non-negotiables

- Times New Roman 12, justified, 1.25 spacing, full page width. Figures and captions centred.
- Frozen stack: Isaac Sim 5.0.0 + Isaac Lab 2.3.0 + Python 3.11 + PyTorch 2.7.0/cu128. Do not upgrade.
- `git push` at the end of every session.
- Write failure decision rules *before* a run, not after. One knob per symptom. Never two changes at once.
