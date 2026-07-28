"""Robot articulation configurations."""

from .ur5e_cfg import UR5E_CFG
from .ur5e_rhp12_cfg import (
    ARM_JOINT_NAMES,
    GRIPPER_CLOSED_Q,
    GRIPPER_DISTAL_JOINTS,
    GRIPPER_EFFORT_LIMIT,
    GRIPPER_JOINT_NAMES,
    GRIPPER_OPEN_Q,
    GRIPPER_PROXIMAL_JOINTS,
    UR5E_RHP12_CFG,
    UR5E_RHP12_USD,
)
from .ur5e_robotiq_cfg import UR5E_ROBOTIQ_CFG, UR5E_ROBOTIQ_USD

##
# Gripper registry — selected at run time by `--gripper`, as planned in
# logbook/02_grasp_env.md. Each entry must keep its OWN experiment_name downstream: §9
# records that new task variants registered against an existing runner cfg dump
# checkpoints on top of earlier results.
#
# `rhp12` is the Layer 1 critical path. `robotiq85` is the literature-comparability
# gripper and nothing in Layer 1 is gated on it — see `ur5e_robotiq_cfg.py` for why the
# previous attempt failed on it and what is done differently here.
#
# Only the two cfg objects are re-exported flat. The per-gripper constants
# (GRIPPER_OPEN_Q, PAD_BODIES, MIMIC, ...) share names across the two modules, so reach
# them through the module — `from ur5_grasp.robots import ur5e_robotiq_cfg` — rather than
# flattening them here and silently shadowing one gripper's values with the other's.
##

GRIPPERS = {
    "rhp12": UR5E_RHP12_CFG,
    "robotiq85": UR5E_ROBOTIQ_CFG,
}

DEFAULT_GRIPPER = "rhp12"

__all__ = [
    "UR5E_CFG",
    "UR5E_RHP12_CFG",
    "UR5E_RHP12_USD",
    "UR5E_ROBOTIQ_CFG",
    "UR5E_ROBOTIQ_USD",
    "GRIPPERS",
    "DEFAULT_GRIPPER",
    "ARM_JOINT_NAMES",
    "GRIPPER_JOINT_NAMES",
    "GRIPPER_PROXIMAL_JOINTS",
    "GRIPPER_DISTAL_JOINTS",
    "GRIPPER_OPEN_Q",
    "GRIPPER_CLOSED_Q",
    "GRIPPER_EFFORT_LIMIT",
]
