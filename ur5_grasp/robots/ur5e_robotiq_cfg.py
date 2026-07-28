# Copyright (c) 2026, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e + Robotiq 2F-85 articulation configuration. Module 02, STEP 6 — the SECOND gripper.

THE RH-P12-RN IS THE LAYER 1 CRITICAL PATH. This gripper exists for literature
comparability — the 2F-85 is what most published UR5 grasping work uses, so a cPPO-vs-PPO
result on it is directly comparable. Nothing in Layer 1 may wait on this file.

The asset is `ur5_grasp/assets/ur5e_robotiq_2f85.usd`, built by
`ur5_grasp/tools/make_ur5e_robotiq_usd.py` (log: `logbook/02_make_ur5e_robotiq.log`).

======================================================================================
READ THIS BEFORE CHANGING ANY NUMBER BELOW
======================================================================================
The previous attempt built this same gripper and it failed. The failure is recorded in
`~/Abdur_Rabbi_THESIS/Thesis_Documentation/07_Troubleshooting.md`:

    "the 2f-85's passive pads transmit no normal force, so the gripper can't truly grip"
    "cube falls straight through a closed gripper ... raising finger stiffness (20 -> 400)
     / effort (50 -> 200) did not help"

and its fix was a **proximity weld** — latch the cube when CLOSE is commanded within 6 cm.
That is not a gripper. Every headline number in the previous thesis was measured with it.

WHY IT FAILED, PRECISELY. The archive drove `finger_joint` alone and set the other five
finger joints PASSIVE (stiffness 0, damping 0.5), on the reasoning that the mechanical
four-bar loop would carry them. Its own comment says so: *"Drive ONLY finger_joint; leave
the coupled joints PASSIVE so the mechanical loop makes them follow."*

That reasoning is wrong in Isaac Lab specifically. Isaac Sim resolves closed-loop
kinematics automatically through USD schemas; **Isaac Lab requires every mimic joint to be
fully specified in the ArticulationCfg** (IsaacLab issue #2424, discussions #2626, #2665).
A coupled joint Isaac Lab was never told about is not coupled — it is limp. Limp joints
bend away under contact instead of transmitting it, which is exactly "pads touch, force
~0 N", which is exactly the §9 failure mode.

WHAT IS DONE DIFFERENTLY HERE. All six finger joints are DRIVEN from one scalar through an
explicit sign table (`MIMIC` below). No joint is passive. This is not a new idea — it is
the pattern that already worked in THIS folder on the RH-P12-RN, where four coupled joints
sharing one scalar target reproduced the ROBOTIS published 106.0 mm stroke to +0.4 mm.

Consequence worth stating plainly: if the pads STILL read ~0 N with all six driven, the §9
rejection is confirmed on its own terms and the 2F-85 closes as a documented negative
result. That outcome is a paragraph in the thesis, not a failure of the session. Do not
tune gains to escape it — the archive already tried that and it did not work.

======================================================================================
KNOWN UPSTREAM ISSUE TO WATCH FOR
======================================================================================
IsaacLab discussion #3385: grasping with the 2F-85 induces a consistent rotation of the
whole 6-DOF arm, and it gets faster and more violent as finger PD gains rise. If the arm
visibly twists when the gripper closes, that is this issue, NOT a bug in your reward. The
reported workaround is a virtual-target delta-position controller on the arm. Note it and
move on — do not spend the timebox on it.

======================================================================================
STATUS OF THE NUMBERS IN THIS FILE
======================================================================================
Arm gains      MEASURED (Day 2, carried from ur5e_cfg.py). Trustworthy.
MIMIC table    CANDIDATE until PHASE D of the build tool reports which table it kept.
Stroke q       CANDIDATE (archive value). Confirm against PHASE F.
Effort limit   PROVISIONAL. Calibrate against Robotiq's published force, see below.

Run the build tool before trusting anything here:

    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_robotiq_usd.py --headless \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_make_ur5e_robotiq.log
"""

import os

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg

##
# Asset path — absolute, resolved from this file, so the cfg works from any cwd.
# (Training runs from inside `IsaacLab/`, not the thesis root. A relative path would break.)
##

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
UR5E_ROBOTIQ_USD = os.path.abspath(os.path.join(_THIS_DIR, "..", "assets", "ur5e_robotiq_2f85.usd"))

##
# Joint names — from the archive's build of this same variant. VERIFY against the build
# tool's PHASE C output; Isaac Sim 5.0 may name them differently from the 5.1 the archive
# read. Anything that indexes joints by position instead of by name is a bug waiting for a
# re-import.
##

ARM_JOINT_NAMES = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]

GRIPPER_DRIVE_JOINT = "finger_joint"  # the one real actuator on the hardware

##
# THE MIMIC TABLE — the whole point of this file.
#
# Every finger joint's angle as a multiple of the drive angle. The inner fingers
# counter-rotate (-1) to keep the pad faces parallel through the stroke; that is what makes
# a 2F-85 a parallel gripper rather than a pinching one.
#
# These are the ros-industrial / standard convention signs. They are a HYPOTHESIS until
# PHASE D of `make_ur5e_robotiq_usd.py` sweeps both candidate tables and reports which one
# actually converges the pads. If PHASE D keeps `mirrored-right` instead, copy that table
# here and record the discrepancy in 07_Troubleshooting.md — it would mean NVIDIA's joint
# axes differ from the URDF convention, which is worth knowing and worth citing.
##

MIMIC = {
    "finger_joint": +1.0,
    "right_outer_knuckle_joint": +1.0,
    "left_inner_finger_knuckle_joint": +1.0,
    "right_inner_finger_knuckle_joint": +1.0,
    "left_inner_finger_joint": -1.0,
    "right_inner_finger_joint": -1.0,
}

GRIPPER_JOINT_NAMES = list(MIMIC)

# The bodies that are supposed to do the gripping. HYPOTHESIS, not fact — PHASE E of the
# build tool measures which link is actually innermost. On the RH-P12-RN this same
# assumption was wrong and went unchecked for two days.
PAD_BODIES = ["left_inner_finger", "right_inner_finger"]

# Stroke of the drive joint. 0 = open, ~0.8 rad = closed (archive value; confirm in PHASE F).
GRIPPER_OPEN_Q = 0.0
GRIPPER_CLOSED_Q = 0.8

##
# Open / close commands for `BinaryJointPositionAction`.
#
# The sign table lives HERE, in the command, not in the actuator group — the six joints
# share one set of gains but not one target. Isaac Lab's binary action takes a joint-name
# list and a dict of per-joint values, so the coupling is imposed at the action layer and
# the policy still sees a single scalar. Same action space as the RH-P12-RN, so the two
# grippers stay benchmark-comparable.
##

GRIPPER_OPEN_COMMAND = {j: m * GRIPPER_OPEN_Q for j, m in MIMIC.items()}
GRIPPER_CLOSE_COMMAND = {j: m * GRIPPER_CLOSED_Q for j, m in MIMIC.items()}

##
# Grip force.
#
# Robotiq publishes for the 2F-85:
#     Stroke                85 mm
#     Gripping force        20 - 235 N   (adjustable)
#     Rated payload          5 kg
#     Closing speed         20 - 150 mm/s
# Source: https://robotiq.com/products/adaptive-grippers  (2F-85 specifications)
#
# Converting a pad force to a joint effort needs the moment arm from the knuckle axis to
# the contact point. Taking it as roughly 0.05 m at the top of the published range:
#     tau = 235 N x 0.05 m = 11.75 N-m  ->  12.0 N-m below.
#
# TREAT 12.0 AS PROVISIONAL AND CALIBRATE IT AGAINST THE MEASURED FORCE, not the torque.
# The grasp test prints achieved pad contact force; the acceptance check is that it lands
# inside the published 20-235 N band. If it comes back at, say, 600 N, scale this by
# 235/600 and re-run. ONE knob, aimed at a target external to this project — the same move
# that made the RH-P12-RN's 106.4 mm check worth something.
#
# Do NOT reach for the archive's 200.0. That number was chosen while chasing a cube that
# fell through a limp linkage; it is roughly 17x the datasheet and is a number about PhysX,
# not about a gripper.
##

GRIPPER_EFFORT_LIMIT = 12.0  # N-m, PROVISIONAL — calibrate against 20-235 N (see above)

##
# Configuration
##

UR5E_ROBOTIQ_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=UR5E_ROBOTIQ_USD,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,  # same reasoning as ur5e_cfg.py — an honest robot for Layer 3
            max_depenetration_velocity=5.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            # OFF. The 2F-85 has many closely-packed finger bodies; self-collision at high
            # num_envs blows up the GPU contact-pair buffer and hangs physics init. This
            # matches Isaac Lab's own manipulation-env convention and the archive's choice.
            enabled_self_collisions=False,
            # 32, matching the RH-P12-RN cfg and for the same reason: this articulation is
            # meant to press two pads into a rigid cube and hold it against gravity.
            # Under-iterated contact solves look like the object sinking into the fingers
            # or jittering out of them — which is the signal the grasp test reads. A
            # closed-loop linkage needs the iterations more, not less.
            solver_position_iteration_count=32,
            solver_velocity_iteration_count=1,
        ),
        # ON. §9 names "pads touch, contact force ~0" as the failure that killed this
        # gripper. A config that cannot see contact force cannot detect it — and the
        # archive shipped with this set to False, which is part of why it took so long to
        # find. This is the single most important line in the file.
        activate_contact_sensors=True,
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        joint_pos={
            # Arm: the Day 2 home pose, identical to ur5e_rhp12_cfg.py so the two grippers
            # start from the same arm state and the benchmark compares grippers, not poses.
            "shoulder_pan_joint": 0.0,
            "shoulder_lift_joint": -1.712,
            "elbow_joint": 1.712,
            "wrist_1_joint": -1.5707963267948966,
            "wrist_2_joint": -1.5707963267948966,
            "wrist_3_joint": 0.0,
            # Gripper fully open. Listed per joint, not by regex: at q=0 every multiple of
            # q is 0 anyway, but writing it out keeps the joint list in one place so a
            # rename caught in PHASE C fails loudly here instead of silently matching.
            **{j: 0.0 for j in MIMIC},
        },
        pos=(0.0, 0.0, 0.0),
        rot=(1.0, 0.0, 0.0, 0.0),
    ),
    actuators={
        # ---- ARM: copied from the MEASURED ur5e_cfg.py. Do not edit here. ----------------
        # If you ever find yourself changing arm gains in THIS file, stop: change them in
        # ur5e_cfg.py and copy across, so the configs cannot drift apart.
        #
        # The archive used ONE blanket arm group at stiffness 800 / damping 40. Using that
        # would silently discard Day 2's finding that the elbow carries the most gravity
        # torque of any joint (16.0 N-m) while inheriting UR10e's weakest gain (600).
        "shoulder": ImplicitActuatorCfg(
            joint_names_expr=["shoulder_.*"],
            stiffness=1320.0,
            damping=72.6636085,
            friction=0.0,
            armature=0.0,
        ),
        "elbow": ImplicitActuatorCfg(
            joint_names_expr=["elbow_joint"],
            stiffness=1320.0,  # MEASURED Day 2: elbow carries 16.0 N-m, the largest load
            damping=34.64101615,
            friction=0.0,
            armature=0.0,
        ),
        "wrist": ImplicitActuatorCfg(
            joint_names_expr=["wrist_.*"],
            stiffness=216.0,
            damping=29.39387691,
            friction=0.0,
            armature=0.0,
        ),
        # ---- GRIPPER: ONE group, all SIX joints, none passive ----------------------------
        #
        # THIS IS THE LINE THE ARCHIVE GOT WRONG. It split the fingers into
        # `gripper_drive` (finger_joint, stiffness 400) and `gripper_passive` (the other
        # five, stiffness 0). Stiffness 0 means Isaac Lab holds no target on those joints,
        # so under contact they fold instead of transmitting force. Result: a visibly
        # closed gripper that grips nothing.
        #
        # Here all six are driven. The differing SIGNS live in GRIPPER_OPEN_COMMAND /
        # GRIPPER_CLOSE_COMMAND above, not in the gains — a joint that must rotate the
        # other way still needs the same stiffness to hold its side of the linkage.
        #
        # Gains set only how the fingers APPROACH the target. Grip force is
        # `effort_limit_sim`: once the pads stall on the cube the position error grows, the
        # PD demand saturates, and torque sits at the limit. Sizing check: stalling with
        # ~0.3 rad of error gives a demand of 100 x 0.3 = 30 N-m against a 12 N-m cap —
        # comfortably saturated, which is what makes the limit (and therefore the
        # datasheet) the thing that sets the force.
        #
        # Damping is deliberately high relative to stiffness. A closed four-bar can pump
        # energy round the loop when the solver disagrees with itself between substeps; the
        # archive's `damping=0.5` on the passive side was an attempt to bleed exactly that.
        # Driving every joint removes the mechanism, but the margin costs nothing.
        "gripper": ImplicitActuatorCfg(
            joint_names_expr=[
                "finger_joint",
                ".*_outer_knuckle_joint",
                ".*_inner_finger_joint",
                ".*_inner_finger_knuckle_joint",
            ],
            stiffness=100.0,
            damping=5.0,
            effort_limit_sim=GRIPPER_EFFORT_LIMIT,
            velocity_limit_sim=2.0,
            friction=0.0,
            armature=0.01,  # effective inertia — the finger bodies are light and the loop
            #                 is stiff; a little armature keeps the solver well-conditioned
        ),
    },
)
"""UR5e + Robotiq 2F-85, implicit actuators, gravity on, contact sensing enabled.

All six finger joints are DRIVEN from one scalar through `MIMIC`. None is passive — that
is the difference between this config and the one that failed in the previous attempt.
"""
