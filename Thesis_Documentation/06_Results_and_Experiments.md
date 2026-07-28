# 06 — Results and experiments

**Rule: every number in this file names the script and the exact flags that produced it.**
A result without a reproducible command is not a result.

**Nothing has been measured in this attempt yet.** Numbers from the previous attempt
(`~/Abdur_Rabbi_THESIS`) do not belong here unless explicitly re-measured in this folder and
labelled as such.

---

## Benchmark table — Layer 1 (cPPO vs PPO)

| Agent | Seed | Task success % | Mean reward | Singularity viol % | Checkpoint | Command |
|---|---|---|---|---|---|---|
| PPO | | | | | | |
| cPPO | | | | | | |

_Multi-seed (42/43/44) mean±std expected — an examiner will ask._

## How each number was produced

_Script, flags, and log path for every row above._

## Figures

_Filename in `assets/`, what it shows, and the script that generated it._

---

# Module 02 — UR5e + RH-P12-RN geometry (measured 2026-07-28)

Every number below was measured in `~/Abdur_Rabbi_Thesis_updated`. None is carried from the
previous attempt. Run all commands from `IsaacLab/` with `conda activate isaaclab` first.

## Gripper stroke

Command: `./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_rhp12_usd.py --headless`
Log: `logbook/02_make_ur5e_rhp12.log`

| q (rad) | Pad gap, body origins (m) | Pad **face** gap (m) | TCP from wrist (m) |
|---|---|---|---|
| 0.00 | 0.1145 | 0.1064 | 0.0767 |
| 0.20 | 0.1012 | 0.0931 | 0.0859 |
| 0.40 | 0.0844 | 0.0763 | 0.0936 |
| 0.60 | 0.0656 | 0.0578 | 0.0993 |
| 0.80 | 0.0442 | 0.0363 | 0.1032 |
| 1.00 | 0.0216 | 0.0137 | 0.1049 |

Pad reach from body origin: **0.0041 m** (right) + **0.0040 m** (left) = **0.0081 m**.
TCP travel over the stroke: **0.0282 m** — the TCP is not a fixed point.

Topology: **10 joints / 12 bodies, one articulation.** PhysX returns the gripper joints as
`rh_l1, rh_p12_rn, rh_l2, rh_r2` — ordered by tree depth, not as requested.

## External validation against the manufacturer

| Quantity | Measured | Published | Error |
|---|---|---|---|
| Clear opening, fully open | **106.4 mm** | **106.0 mm** | **+0.4 mm** |

Source: <https://emanual.robotis.com/docs/en/platform/rh_p12_rn/> — stroke 0–106 mm, reduced
from 109 mm for units shipped from 2019-11-04 to improve fingertip durability.

This is the first geometry number in the thesis validated against a source outside the
project, and it is enforced as an automatic acceptance criterion in the build script rather
than left as a comment.

## DexCube edge

Command: `./isaaclab.sh -p ../ur5_grasp/tools/measure_dexcube_drop.py --headless`
Log: `logbook/02_measure_dexcube.log`

Method: drop on a ground plane at z = 0 and measure the resting centre height. For a cube
resting on a face, **edge = 2 × centre height**. This measures the *collision* geometry — what
the pads actually touch — and was used because USD introspection was ambiguous.

| Scale | Resting centre (m) | Edge (m) | Residual speed (m/s) |
|---|---|---|---|
| 1.0 (raw) | 0.03000 | **0.06000** | 0.00012 |
| 0.8 (env) | 0.02400 | **0.04800** | 0.00012 |

Scaling is exactly linear (−0.0 mm), confirming the collision shape rescales with the visual.

**Correction to the previous attempt.** Its value of 0.0412 m (implying a 0.0515 m raw cube)
is wrong by 8.5 mm raw. A prediction of 0.0515 m made during this session was also refuted.

**Consequence.** The archive's `TCP_OFFSET = 0.130` is invalidated: its justification — *"pad
faces close to 0.0415 m against a 0.0412 m cube, delta +0.3 mm, a true flat-pad parallel
grip"* — is arithmetically impossible against a 0.048 m cube. The archive's origin-gap table
does replicate here to 4 dp, so its geometry work was sound; the calibration against the cube
is what fails.

## Pre-registered prediction for the grasp test

Interpolating the face-gap column at the measured 0.0480 m cube: **the pads should stall at
q ≈ 0.69.** Stalling later indicates crushing or slipping; earlier indicates the cube wedged
on the curved proximal `r1`/`l1` links — the failure mode that survives a static hold test and
fails under lift accelerations.

## Caveat

The pad reach is derived from an axis-aligned box around a curved fingertip, so it
over-approximates. That biases the open gap small (conservative) and the closed gap small
(optimistic). The closed-gap check is the weakest of the seven acceptance criteria.
