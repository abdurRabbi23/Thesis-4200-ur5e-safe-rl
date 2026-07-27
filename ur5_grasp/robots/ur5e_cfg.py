"""UR5e articulation configuration — arm only, no gripper.

Isaac Lab 2.3.0 ships no UR5/UR5e config (verified by grep, 2026-07-27: `isaaclab_assets/
robots/universal_robots.py` defines UR10 and UR10e only). This file supplies it.

The asset is NOT invented — `ur5_grasp/scripts/probe_ur5e_asset.py` confirmed on 2026-07-27
that the Isaac Sim asset library carries a UR5e at:

    Assets/Isaac/5.1/Isaac/Robots/UniversalRobots/ur5e/ur5e.usd

alongside ur3, ur3e, ur5, ur10, ur10e, ur16e, ur20, ur30. Log: `logbook/02_probe_ur5e_asset.log`.

Modelled on `UR10e_CFG`, not `UR10_CFG` — same e-series generation, per-group actuator bands
rather than one blanket `.*` group, and the higher solver iteration count that contact-rich
grasping needs later. See `logbook/02_grasp_env.md` STEP 1 for the side-by-side.

Everything marked PROVISIONAL below is a starting value to be checked against measurement,
not a value to trust. Change one at a time (`02_grasp_env.md` decision rules).
"""

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

##
# Configuration
##

UR5E_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd",
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            # GRAVITY ON — deliberate, and it differs from UR10e_CFG (which disables it).
            # Rationale: UR10e_CFG and FRANKA_PANDA_HIGH_PD_CFG disable gravity because they
            # are driven by task-space / differential-IK controllers where gravity droop is a
            # nuisance. The task this module builds toward is an RL lift env with joint-position
            # actions — the direct analogue is FRANKA_PANDA_CFG, which keeps gravity ON.
            # It is also the honest choice for Layer 3: a policy trained without gravity has
            # learned a robot that does not exist.
            disable_gravity=False,
            max_depenetration_velocity=5.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            solver_position_iteration_count=16,
            solver_velocity_iteration_count=1,
        ),
        # Left False for now — contact sensing is a Module 03 concern (collision constraints
        # for cPPO). Build before attach: do not switch this on until something reads it.
        activate_contact_sensors=False,
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        # PROVISIONAL home pose — elbow up, arm reaching forward over the (not yet placed) table.
        # Deviates from UR10e_CFG in one value only: shoulder_pan is 0.0 here, not pi. UR10e's
        # pi points the arm away from the base's +x; there is no table behind the robot in this
        # thesis. Revisit once the table and object are placed in the lift env — check_ur5e.py
        # prints the resulting end-effector position so this is checked, not assumed.
        joint_pos={
            "shoulder_pan_joint": 0.0,
            "shoulder_lift_joint": -1.712,
            "elbow_joint": 1.712,
            "wrist_1_joint": -1.5707963267948966,
            "wrist_2_joint": -1.5707963267948966,
            "wrist_3_joint": 0.0,
        },
        pos=(0.0, 0.0, 0.0),
        rot=(1.0, 0.0, 0.0, 0.0),
    ),
    actuators={
        # PROVISIONAL gains — copied verbatim from UR10e_CFG. The UR5e is the lighter arm
        # (5 kg payload vs 12.5 kg), so these are very likely too stiff. They are NOT pre-tuned
        # here on purpose: guessing a scale factor would be changing a value without evidence.
        # Run check_ur5e.py first, read the measured drift, then change ONE number.
        #
        # effort limits are intentionally NOT set — the USD's own values apply, and
        # check_ur5e.py prints them. They get pinned explicitly once we can cite the source.
        "shoulder": ImplicitActuatorCfg(
            joint_names_expr=["shoulder_.*"],
            stiffness=1320.0,
            damping=72.6636085,
            friction=0.0,
            armature=0.0,
        ),
        # MEASURED CHANGE, 2026-07-27 — the only value moved from the UR10e reference.
        #
        # stiffness 600 -> 1320. Reason, from logbook/02_check_ur5e.log run 2:
        # the elbow showed 0.026703 rad (1.53 deg) of steady-state sag at the home pose
        # while every other joint was under 0.009 rad. Multiplying error by stiffness gives
        # the gravity torque each joint actually carries:
        #     shoulder_lift  0.008904 x 1320 = 11.8 N-m
        #     elbow          0.026703 x  600 = 16.0 N-m   <- largest load, weakest gain
        #     wrist_1        0.006379 x  216 =  1.4 N-m
        # The elbow carries the most gravity torque of any joint yet had less than half the
        # shoulder's stiffness. That is inherited from UR10e_CFG, tuned for a heavier robot
        # with different link masses — not a UR5e fact. All three are far below the USD's
        # 150 N-m limit, so effort limit was never the constraint.
        #
        # Damping deliberately NOT changed in the same edit (one knob per run). Note this
        # drops the damping ratio, so watch the step trace for ringing; steady-state error
        # is unaffected by damping, so the prediction below holds either way.
        # PREDICTION to check on re-run: err = 0.026703 x 600/1320 = 0.01214 rad (0.70 deg).
        # If the measurement lands far from that, the 1/k model is wrong and needs revisiting
        # before any further tuning.
        #
        # NOT taken from the archive: it used a single arm group at stiffness 800 / damping 40
        # and its own logbook proposed 800 -> 400. That recommendation targets bang-bang
        # motion under a 1.0 rad/s velocity clamp, not static accuracy — at 400 the predicted
        # droop here would be 0.040 rad, worse than the value being fixed.
        "elbow": ImplicitActuatorCfg(
            joint_names_expr=["elbow_joint"],
            stiffness=1320.0,
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
    },
)
"""UR5e 6-DOF arm, no gripper, implicit actuators. Gravity enabled."""
