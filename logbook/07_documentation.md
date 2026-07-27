# Module 07 — The documentation system

**Status:** ✅ skeleton created (2026-07-27)
**Owner file for:** the logbook + Thesis_Documentation structure itself

---

## Goal

The documentation exists **from day one**, not retrofitted. In the previous attempt the docs were
written after the fact, which is the root cause of losing track across chats.

## What exists

- `logbook/00_INDEX.md` — front door, status, module table
- `logbook/01–06_*.md` — module stubs with goal / decision-rules / state / results sections
- `logbook/HANDOFF_next.md` — rolling session runbook
- `run_log.md` — dated timeline
- `Thesis_Documentation/00–10` — replication reference stubs
- `Thesis_Documentation/07_Troubleshooting.md` — **pre-filled** with landmines carried from the archive

## Conventions

- Work in a module → update that module file **and** `run_log.md`.
- Every doc change gets a dated line in `Thesis_Documentation/09_Changelog.md`.
- Every number in `06_Results_and_Experiments.md` names the script and flags that produced it.
- A correction must be chased through every file it propagated into.
- Stale "Next steps" sections are a bug.

## Next single action

Nothing — this module is maintenance-only. Update it if the doc structure itself changes.
