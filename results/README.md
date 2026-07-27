# results/

Outputs, organised per experiment.

| Path | Contents |
|---|---|
| `tb_csv/` | TensorBoard scalars exported to CSV — the durable form of a run's numbers |
| `scripts/` | Plotting and export scripts used to turn logs into figures |
| `<experiment>/` | One directory per experiment (e.g. `layer1_ppo_vs_cppo/`): MP4s, figures, tables |

**Checkpoints are NOT stored here** — they live under `IsaacLab/logs/` and are gitignored.
A checkpoint directory has disappeared before; never plan a fallback around one you have not
just `ls`'d. The CSV exports here are what survives.

Every figure and number must be traceable to the command that produced it — see
`Thesis_Documentation/06_Results_and_Experiments.md`.
