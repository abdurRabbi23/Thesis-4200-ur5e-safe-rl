# 00 — Start here

This folder is the **replication reference**: enough for someone who has never seen the project to
rebuild it from an empty machine. It is written *as the work happens*, not afterwards.

Read in this order:

| File | What it answers |
|---|---|
| `01_Environment_Setup.md` | How do I get the stack running? |
| `02_Grasp_Environment.md` | How is the UR5e lift task built? |
| `03_Safety_and_cPPO_Benchmark.md` | What are the safety constraints, and how does cPPO work here? |
| `04_Layer2_IBVS.md` | How does the visual servoing loop work? |
| `05_Layer3_SimToReal.md` | How does this reach the physical robot? |
| `06_Results_and_Experiments.md` | What are the numbers, and what command produced each one? |
| `07_Troubleshooting.md` | It broke. What now? |
| `08_Glossary.md` | What does that term mean? |
| `09_Changelog.md` | What changed in these docs, and when? |
| `10_Command_Reference.md` | What is the exact command? |

For day-to-day project state (status, what's next, decisions), see `logbook/00_INDEX.md` instead.
This folder is the *manual*; the logbook is the *diary*.

## Rules

- Every number in `06_` names the script and flags that produced it. No command, no result.
- Every doc change gets a dated line in `09_`.
- A correction gets chased through every file it propagated into.
- Stale "Next steps" sections are a bug.
