"""UR5e + ROBOTIS RH-P12-RN articulation configuration. Module 02, Day 4.

The asset is `ur5_grasp/assets/ur5e_rhp12.usd`, built and validated on 2026-07-28 by
`ur5_grasp/tools/make_ur5e_rhp12_usd.py` (7/7 PASS, log `logbook/02_make_ur5e_rhp12.log`):
10 joints / 12 bodies, ONE articulation, nested root stripped, open clear opening 106.4 mm
against the ROBOTIS published 106.0 mm.

WHAT IS CARRIED OVER FROM `ur5e_cfg.py`, AND WHY IT MATTERS
The three arm actuator groups below are the MEASURED ones — shoulder 1320, elbow 1320,
wrist 216 — not a blanket `.*` group. The archive used one arm group at stiffness 800 /
damping 40. Using that here would silently discard Day 2's finding that the elbow carries the
most gravity torque of any joint (16.0 N-m) while inheriting UR10e's weakest gain (600).
If you ever find yourself editing arm gains in THIS file, stop: change them in `ur5e_cfg.py`
and copy across, so the two configs cannot drift apart.

WHAT IS NEW HERE
1. `activate_contact_sensors=True`. `ur5e_cfg.py` leaves this False on purpose ("build before
   attach"). It is switched on now because something finally reads it: the grasp test measures
   pad-to-cube contact force, and PROJECT_INSTRUCTIONS §9 names "pads touch, contact force
   approximately zero" as the failure mode that killed the Robotiq 2F-85. A grasp test that
   cannot see contact force cannot detect that failure.
2. One `gripper` actuator group covering all four finger joints (see below).
3. `effort_limit_sim` set from the ROBOTIS datasheet rather than left at the URDF value.

Run the grasp test before trusting any number in here:

    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/scripts/grasp_hold_test.py --headless \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_grasp_hold_test.log
"""

import os

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg

##
# Asset path — absolute, resolved from this file, so the cfg works from any cwd.
# (Training is run from inside `IsaacLab/`, not the thesis root. A relative path would break.)
##

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
UR5E_RHP12_USD = os.path.abspath(os.path.join(_THIS_DIR, "..", "assets", "ur5e_rhp12.usd"))

##
# Joint names — read off the articulation, never assumed.
#
# PhysX returns the gripper joints in TREE-DEPTH order, which is NOT the order the URDF
# declares them: ['rh_l1', 'rh_p12_rn', 'rh_l2', 'rh_r2'] (logbook/02_make_ur5e_rhp12.log).
# Anything that indexes gripper joints by position instead of by name is a bug waiting for a
# re-import. These constants exist so that lookup is by name everywhere.
##

ARM_JOINT_NAMES = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]

# Proximal (driven directly off the base) and distal (carried by the proximal link).
GRIPPER_PROXIMAL_JOINTS = ["rh_p12_rn", "rh_l1"]   # URDF limit 0 .. 1.1 rad
GRIPPER_DISTAL_JOINTS = ["rh_r2", "rh_l2"]         # URDF limit 0 .. 1.0 rad
GRIPPER_JOINT_NAMES = GRIPPER_PROXIMAL_JOINTS + GRIPPER_DISTAL_JOINTS

# Usable stroke for the SINGLE scalar that drives all four joints.
# Capped at 1.0, not 1.1, because r2/l2 stop there — commanding 1.1 would ask the distal
# joints to exceed their limit and desynchronise the four-bar.
GRIPPER_OPEN_Q = 0.0
GRIPPER_CLOSED_Q = 1.0

##
# Grip force.
#
# The URDF ships effort="1000" on every finger joint. That is not a specification, it is the
# usual "large enough not to interfere" placeholder. At a ~0.06 m lever arm it corresponds to
# roughly 17 kN at the pad — the gripper would pass through the cube rather than hold it, and
# any "stall width" measured under it would be a number about PhysX, not about a gripper.
#
# ROBOTIS publishes, for the RH-P12-RN:
#     Maximum Gripping Force  170 N
#     Recommended Payload       5 kg
#     Max Closing Speed        75 mm/s
#     Weight                  500 g
# Source: https://emanual.robotis.com/docs/en/platform/rh_p12_rn/  (specifications table)
#
# Converting 170 N at the pad to a joint effort needs the moment arm from the joint axis to
# the contact point. Taking it as roughly 0.06 m for the proximal joint gives
#     tau = 170 N x 0.06 m = 10.2 N-m  ->  10.0 N-m below.
#
# TREAT 10.0 AS PROVISIONAL AND CALIBRATE IT. The 0.06 m is an estimate off the URDF link
# origins, not a measurement, so the FORCE is the thing to check, not the torque. The grasp
# test prints the achieved pad contact force; the acceptance check is that it lands in the
# same order as 170 N. If the measured force comes back at, say, 400 N, scale this number by
# 170/400 and re-run. That is one knob, and the target it is aimed at is external to this
# project — the same move that made the 106.4 mm stroke check worth something.
##

GRIPPER_EFFORT_LIMIT = 10.0  # N-m, PROVISIONAL — calibrate against 170 N (see above)

##
# Configuration
##

UR5E_RHP12_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=UR5E_RHP12_USD,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,  # same reasoning as ur5e_cfg.py — an honest robot for Layer 3
            max_depenetration_velocity=5.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            # 16 -> 32. The arm alone never touched anything; this articulation is meant to
            # press two pads into a rigid cube and hold it against gravity. Under-iterated
            # contact solves show up as the object sinking into the fingers or jittering out
            # of them, which is exactly the signal the grasp test is trying to read.
            solver_position_iteration_count=32,
            solver_velocity_iteration_count=1,
        ),
        # Switched ON here, unlike ur5e_cfg.py — the grasp test reads pad contact force.
        activate_contact_sensors=True,
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        joint_pos={
            # Arm: the Day 2 home pose, unchanged. Measured EE at x=0.433 y=0.133 z=0.473 m.
            "shoulder_pan_joint": 0.0,
            "shoulder_lift_joint": -1.712,
            "elbow_joint": 1.712,
            "wrist_1_joint": -1.5707963267948966,
            "wrist_2_joint": -1.5707963267948966,
            "wrist_3_joint": 0.0,
            # Gripper: fully open. Regex covers all four finger joints in one entry.
            "rh_.*": 0.0,
        },
        pos=(0.0, 0.0, 0.0),
        rot=(1.0, 0.0, 0.0, 0.0),
    ),
    actuators={
        # ---- ARM: copied from the MEASURED ur5e_cfg.py. Do not edit here. ----------------
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
        # ---- GRIPPER: ONE group, all four joints, one target ------------------------------
        #
        # This is the answer to the open question logged on Day 3 ("the URDF gives 4 drivable
        # joints, the hardware is 1-DOF — what does a Layer 3 claim mean?").
        #
        # DECISION: the four joints are treated as ONE degree of freedom. They share an
        # actuator group and always receive the same scalar target.
        #
        # Why this and not four independent joints:
        #   - The real RH-P12-RN has ONE Dynamixel. Its fingers are mechanically coupled; a
        #     controller cannot command r2 independently of r1 because no such command exists.
        #     A policy trained on 4 free joints would learn grasps the hardware cannot execute,
        #     and Layer 3 would be transferring a robot that does not exist.
        #   - There is evidence the same-q coupling is the RIGHT one, not merely convenient:
        #     the Day 3 stroke sweep drove all four to the same q and produced a 106.4 mm open
        #     opening against the published 106.0 mm. Had the real coupling been q2 = f(q1) for
        #     some other f, that agreement would not have appeared.
        #   - It costs nothing. Isaac Lab's BinaryJointPositionAction takes a joint-name list
        #     and one open/close pair, so the action space is a single scalar either way.
        #
        # What is given up: nothing the hardware could have done. The URDF is a pure tree with
        # ZERO mimic tags (grep-verified Day 3), which is why the RH-P12-RN was chosen over the
        # Robotiq 2F-85 — every joint is directly drivable, so the coupling can be IMPOSED in
        # the controller instead of being fought in the physics. This group is where it is
        # imposed.
        #
        # Gains: stiffness and damping set only how the fingers APPROACH the target. The grip
        # force is `effort_limit_sim` — once the pads stall on the cube, the position error
        # grows, the PD demand saturates, and the torque sits at the limit. Sizing check:
        # stalling at q~0.69 against a commanded 1.0 leaves ~0.31 rad of error, so the demand
        # is 100 x 0.31 = 31 N-m against a 10 N-m cap — comfortably saturated, which is what
        # makes the limit (and therefore the datasheet) the thing that sets the force.
        "gripper": ImplicitActuatorCfg(
            joint_names_expr=["rh_.*"],
            stiffness=100.0,
            damping=5.0,  # overdamped for the ~0.09 kg finger chain; no closing bounce
            effort_limit_sim=GRIPPER_EFFORT_LIMIT,
            velocity_limit_sim=6.5,  # URDF value; datasheet 75 mm/s is the real ceiling
            friction=0.0,
            armature=0.0,
        ),
    },
)
"""UR5e + RH-P12-RN, implicit actuators, gravity on, contact sensing enabled.

The four finger joints are ONE degree of freedom by construction — see the `gripper` group.
"""
