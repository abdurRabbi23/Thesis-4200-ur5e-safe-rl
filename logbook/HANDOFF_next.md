HANDOFF — UR5e Safe-RL Thesis · Module 02: SECOND GRIPPER, Robotiq 2F-85 (Day 5, 2026-07-30)

READ FIRST: logbook/00_INDEX.md, then logbook/02_grasp_env.md — the **Day 5** section, and
            in particular its DECISION RULES table. The rules outrank the commands below;
            three of them say STOP, and two of those are the correct outcome.

## GOAL OF THIS SESSION
Run `make_ur5e_robotiq_usd.py` and find out, by measurement, whether the Robotiq 2F-85 can be
mounted as ONE coupled articulation on Isaac Sim 5.0 with **all six finger joints driven** —
then return to the RH-P12-RN critical path.

## DONE MEANS
- `logbook/02_make_ur5e_robotiq.log` exists and PHASES A–F have been read **in order**
- PHASE A confirms the frozen stack (`Isaac/5.0/`) and a `Robotiq_2f_85` Gripper variant
- PHASE C's printed joint names are copied into `MIMIC` in `ur5e_robotiq_cfg.py` if they
  differ from the archive's — **or** the file is left alone because they match
- PHASE D reports which sign table it KEPT, and that table is the one in the cfg
- PHASE E's innermost-link ranking is recorded — pads or not, it is a finding either way
- PHASE F's open clear opening is written down next to Robotiq's published 85 mm
- **OR** the run stops at a decision-rule STOP and the 2F-85 is closed with a header banner
  as a documented negative result — that is a PASS for the session, not a failure
- `02_grasp_env.md` + `run_log.md` + `00_INDEX.md` updated; committed and pushed

## WHY IT MATTERS
The 2F-85 is what most published UR5 grasping work uses, so a cPPO-vs-PPO result on it is
directly comparable to the literature in a way an RH-P12-RN result is not. It is a **bonus**:
Layer 1 rides on the RH-P12-RN and must never wait on this. The reason it is worth one day at
all is that the previous attempt's failure on this gripper has now been traced to a specific,
avoidable mistake — five passive finger joints — rather than to the gripper itself. Either the
fix works, and the thesis gains a second benchmark; or it does not, and §9 is confirmed on its
own terms with evidence instead of inheritance. Both outcomes are publishable. Only an
untimeboxed third outcome is not.

## STATE — verified on disk 2026-07-30
- **Archive is mounted** at `~/Abdur_Rabbi_THESIS` — read-only, §14 applies.
- **Written this session, NONE RUN:**
  - `ur5_grasp/tools/make_ur5e_robotiq_usd.py` — PHASES A–F
  - `ur5_grasp/robots/ur5e_robotiq_cfg.py` — six DRIVEN finger joints, contact sensors ON
  - `ur5_grasp/robots/__init__.py` — `GRIPPERS = {"rhp12", "robotiq85"}`, default `rhp12`
- Checked offline only: all 12 joints matched by exactly one actuator group, no overlaps.
- **From the archive, all HYPOTHESES until PHASE A/C confirm them on Isaac 5.0** (the archive
  read the asset from **5.1**):
  - variant set `Gripper = [None, Robotiq_2f_85]`
  - merged asset = ONE articulation, 12 joints / 16 bodies
  - joints: `finger_joint`, `right_outer_knuckle_joint`, `left`/`right_inner_finger_joint`,
    `left`/`right_inner_finger_knuckle_joint`
  - drive stroke 0 = open, ~0.8 rad = closed
- **THE RH-P12-RN CRITICAL PATH IS STILL OPEN — AND RUN 7 HAS ALREADY RUN, TWICE, BOTH FAIL.**
  Caught by `ls`, not by the handoff. The Day 4 handoff and the first draft of this one both
  said "run 7 unrun". They were wrong. Two logs on disk:
  - `02_grasp_hold_test_run7_30mm.log` (14:21) — **FAIL, 2/9 checks**: stall q off the banked
    0.85; pads transmit no real normal force. Lift passed (+84.2 mm, slip 0.15 mm).
  - `02_grasp_hold_test_run7_depth.log` (14:26, **newest**) — **FAIL, 3/9 checks** on the
    48 mm cube: stall q measured **0.3063** against the banked 0.69 (error −0.3837); **peak pad
    force 0.00 N**; static hold failed at **+32.31 mm** drop. Passed: 4/4 finger prims resolved,
    4/4 joints found by name, cube square to the pads (0.00°), open pads clear the cube
    (0.1066 m vs 0.0480 m), TCP rose +84.2 mm, slip 0.12 mm.
  - **Read that stall q before anything else.** 0.31 against a predicted 0.69 is not a near
    miss — the gripper is stalling at roughly HALF the commanded stroke, which is a different
    contact than either the pad theory or the throat theory predicts.
  - Run 6's PHASE 0b conclusion remains WITHDRAWN as SUSPECT (AABBs around curved links), so
    the "throat captures first" explanation is still unproven, not disproven.

## RUNBOOK

STEP 0 — session start (~1 min)
    conda activate isaaclab                      # fresh NoMachine terminals start in (base)
    sudo cpupower frequency-set -g performance
    cd ~/Abdur_Rabbi_Thesis_updated
    git status                                   # must be clean
    ls ur5_grasp/robots/ ur5_grasp/tools/        # confirm the three new files exist

STEP 1 — build + validate the 2F-85 (~5 min, headless)
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_robotiq_usd.py --headless \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_make_ur5e_robotiq.log

  CONFIRM FROM THE HEADER, BEFORE LETTING IT RUN:
    - `ISAAC_NUCLEUS_DIR` contains **`/Isaac/5.0/`**. If it says 5.1 the environment is not
      the frozen stack and every number below belongs to a different asset release. STOP.
    - PHASE A prints a `Gripper` variant set with a Robotiq option. No Gripper set = the
      variant route is closed on 5.0. STOP, and close the track as a negative result.

  WATCHING FOR, phase by phase:
    PHASE C — the joint names. These are AUTHORITATIVE. The counts (12/16) are not; a
              mismatch there is a 5.0-vs-5.1 asset difference to record, not to tune away.
    PHASE D — which table it KEPT, and by how many mm the pads converged. `no motion` on
              both tables is the linkage fighting itself: STOP, do not touch gains.
    PHASE E — the "innermost link, by count" line. If a non-pad link leads, the 2F-85 has
              the same throat-capture geometry as the RH-P12-RN and the cube size must be
              set from that table. Prediction (low confidence): the pads lead, because a
              2F-85 is a designed parallel gripper and the RH-P12-RN is an adaptive one.
    PHASE F — open clear opening vs 85.0 mm. Sign of the error matters: the AABB makes the
              open gap read TOO SMALL, so a small negative error is expected and benign.

STEP 2 — reconcile the cfg with what was measured (~10 min)
  Only these edits, and only from the log:
    - `MIMIC` keys  <- PHASE C names, if they differ
    - `MIMIC` signs <- PHASE D's kept table, if it is not `standard-mimic`
    - `GRIPPER_CLOSED_Q` <- only if PHASE F says the stroke is wrong
  One knob at a time. If two things look wrong, fix one and re-run STEP 1.

STEP 3 — the only test that decides the gripper (~10 min)
    PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/scripts/grasp_hold_test.py \
        --gripper robotiq85 --headless \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_grasp_hold_robotiq.log

  NOTE: `grasp_hold_test.py` does not yet take `--gripper`. Adding that flag is part of this
  step and is the ONLY change permitted to that script — do not refactor it while the
  RH-P12-RN runs are still mid-diagnosis.

  WATCHING FOR: pad contact force in the same order as Robotiq's published **20–235 N**.
  **Pads visibly touching at ≈ 0 N is the §9 failure reproducing with all six joints driven.**
  That is the answer, not a bug. STOP and log it.

STEP 4 — CLOSE THE TIMEBOX AND GO BACK (mandatory)
  Whatever happened above, the 2F-85 gets ONE day. Then back to the RH-P12-RN, where run 7
  has already FAILED twice and the open question is the measured **stall q = 0.3063** against
  a banked 0.69. Do NOT re-run run 7 unchanged and do NOT start tuning grip force — read the
  `depth` column in `02_grasp_hold_test_run7_depth.log` first and establish WHERE the loaded
  contact sits along the tool axis. That column was added precisely so this question stops
  being argued from geometry. **That is Layer 1. The 2F-85 is not.**

## DECISION RULES — written BEFORE the run, one knob per symptom
Full table in `logbook/02_grasp_env.md`, Day 5. The ones that end the session early:

| Symptom | Action |
|---|---|
| `ISAAC_NUCLEUS_DIR` says 5.1 | **STOP.** Not the frozen stack. Fix the env first. |
| No `Gripper` variant set on Isaac 5.0 | **STOP.** Negative result. Do NOT improvise a URDF import — that is the route §9 actually rejects. |
| Neither sign table closes the gripper | **STOP.** §9 at the kinematic level. Do NOT touch gains. |
| Pads touch, force ≈ 0 N | **STOP.** §9 confirmed on its own terms. Header banner, negative result. The archive already proved tuning does not fix this. |
| Arm twists when the gripper closes | IsaacLab #3385, not your reward. Note it, move on. |

## OPEN QUESTIONS CARRIED
- Is `PAD_BODIES = [left_inner_finger, right_inner_finger]` right? PHASE E decides. The same
  assumption was wrong on the RH-P12-RN and went unchecked for two days.
- Does the 12/16 topology hold on Isaac 5.0, or did the asset change between 5.1 and 5.0?
- **RH-P12-RN, unresolved and more important than any of the above: why does the gripper stall
  at q = 0.3063 when 0.69 was predicted and the pads read 0.00 N?** Run 7 has failed twice on
  this. The `depth` column exists to answer it without another geometric argument.
- Method note earned this session: the Day 4 handoff said run 7 was unrun; `ls` said otherwise.
  §5's rule held. **Verify state on disk before trusting any handoff, including this one.**
