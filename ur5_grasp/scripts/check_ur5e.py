"""Validate the UR5e ArticulationCfg — arm only, no gripper. Module 02, STEP 4.

Checks the four things `HANDOFF_next.md` calls "DONE MEANS", and says PASS or FAIL for each
rather than leaving it to the eye:

  1. the arm loads with no ArticulationRootAPI error
  2. exactly 6 joints, found and named in the expected order
  3. joint limits print and are sensible
  4. the arm holds its commanded home pose without drifting or exploding

Run (GUI, so you can look at it — this is the point of the step):

    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/scripts/check_ur5e.py \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_check_ur5e.log

Add --headless to skip the window.

CONFIRM FROM THE HEADER before trusting anything below it:
    "usd_path" ends in .../UniversalRobots/ur5e/ur5e.usd   <- the right robot loaded
    "gravity disabled : False"                             <- the cfg you think you edited

WATCHING FOR: max drift should settle in the millirad range and stop growing. A drift that
climbs steadily is a stiffness/damping problem; a drift that explodes is an effort limit.
One knob at a time — see the decision-rule table in logbook/02_grasp_env.md.
"""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

# Isaac Sim can die inside simulation_app.close(), and Python's stdout is block-buffered when
# piped through tee — which silently ate this script's entire output on 2026-07-27 (run 1 of
# probe_ur5e_asset.py). Line buffering makes the script self-defending regardless of how it
# is invoked. See Thesis_Documentation/07_Troubleshooting.md.
sys.stdout.reconfigure(line_buffering=True)

parser = argparse.ArgumentParser(description="Validate the UR5e arm-only ArticulationCfg.")
parser.add_argument("--steps", type=int, default=300, help="physics steps to hold the home pose")
parser.add_argument(
    "--drift-tol", type=float, default=0.02, help="max allowed |q - q_home| in rad for a PASS"
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below needs the app running ---
import torch  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.assets import Articulation  # noqa: E402
from isaaclab.sim import SimulationContext  # noqa: E402

# the thesis root, so `ur5_grasp` imports as a package regardless of cwd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from ur5_grasp.robots import UR5E_CFG  # noqa: E402

EXPECTED_JOINTS = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]

results: dict[str, bool] = {}


def verdict(name: str, ok: bool, detail: str = "") -> None:
    results[name] = ok
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{('  — ' + detail) if detail else ''}")


def main() -> None:
    sim = SimulationContext(sim_utils.SimulationCfg(device=args_cli.device))
    sim.set_camera_view([1.8, 1.8, 1.2], [0.0, 0.0, 0.4])

    ground_cfg = sim_utils.GroundPlaneCfg()
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)
    light_cfg = sim_utils.DomeLightCfg(intensity=3000.0, color=(0.75, 0.75, 0.75))
    light_cfg.func("/World/Light", light_cfg)

    print("\n" + "=" * 78)
    print("UR5e ARM-ONLY VALIDATION  —  Module 02, STEP 4")
    print("=" * 78)
    print(f"usd_path         : {UR5E_CFG.spawn.usd_path}")
    print(f"gravity disabled : {UR5E_CFG.spawn.rigid_props.disable_gravity}")
    print(f"solver pos iters : {UR5E_CFG.spawn.articulation_props.solver_position_iteration_count}")
    print(f"actuator groups  : {list(UR5E_CFG.actuators.keys())}")
    print("=" * 78)

    # ---- CHECK 1: does it load at all? -------------------------------------------------
    # An ArticulationRootAPI problem surfaces here, as an exception or as is_fixed_base
    # coming back wrong on a robot that is bolted to the floor.
    robot_cfg = UR5E_CFG.copy()
    robot_cfg.prim_path = "/World/Robot"
    robot = Articulation(cfg=robot_cfg)

    sim.reset()
    print("\n--- 1. articulation loaded ---")
    verdict("loads without ArticulationRootAPI error", True, "sim.reset() returned")
    verdict(
        "fixed base (arm is bolted down, not floating)",
        bool(robot.is_fixed_base),
        f"is_fixed_base={robot.is_fixed_base}",
    )
    print(f"  bodies ({len(robot.body_names)}): {robot.body_names}")

    # ---- CHECK 2: joint count and order ------------------------------------------------
    print("\n--- 2. joints ---")
    names = list(robot.joint_names)
    verdict("exactly 6 joints", robot.num_joints == 6, f"num_joints={robot.num_joints}")
    verdict("joint names match the UR convention, in order", names == EXPECTED_JOINTS, str(names))
    if names != EXPECTED_JOINTS:
        print(f"       expected: {EXPECTED_JOINTS}")

    # ---- CHECK 3: limits ---------------------------------------------------------------
    print("\n--- 3. joint limits (env 0) ---")
    pos_lim = robot.data.joint_pos_limits[0]
    eff_lim = robot.data.joint_effort_limits[0]
    vel_lim = robot.data.joint_vel_limits[0]
    home = robot.data.default_joint_pos[0]
    print(f"  {'joint':<22}{'lower':>10}{'upper':>10}{'effort':>10}{'vel':>10}{'home':>10}")
    for i, n in enumerate(names):
        print(
            f"  {n:<22}{pos_lim[i, 0]:>10.3f}{pos_lim[i, 1]:>10.3f}"
            f"{eff_lim[i]:>10.1f}{vel_lim[i]:>10.3f}{home[i]:>10.3f}"
        )
    finite = bool(torch.isfinite(pos_lim).all() and torch.isfinite(eff_lim).all())
    ordered = bool((pos_lim[:, 0] < pos_lim[:, 1]).all())
    in_range = bool(((home >= pos_lim[:, 0]) & (home <= pos_lim[:, 1])).all())
    verdict("limits finite and lower < upper", finite and ordered)
    verdict("home pose lies inside the joint limits", in_range)

    # ---- CHECK 4: hold the home pose ---------------------------------------------------
    print(f"\n--- 4. holding home pose for {args_cli.steps} steps ---")
    target = robot.data.default_joint_pos.clone()
    robot.write_joint_state_to_sim(target, torch.zeros_like(target))
    robot.reset()

    sim_dt = sim.get_physics_dt()
    max_drift = 0.0
    trace: list[tuple[int, float]] = []
    err = torch.zeros_like(target[0])
    for step in range(args_cli.steps):
        robot.set_joint_position_target(target)
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim_dt)
        err = (robot.data.joint_pos - target)[0]
        drift = float(err.abs().max())
        max_drift = max(max_drift, drift)
        if step % 50 == 0 or step == args_cli.steps - 1:
            trace.append((step, drift))

    print(f"  {'step':>8}{'max |q - q_home| (rad)':>26}")
    for step, drift in trace:
        print(f"  {step:>8}{drift:>26.6f}")

    # WHICH joint sagged, and which actuator group owns it. Without this the max-drift
    # number above names a symptom but not a knob — and there are three arm groups with
    # three different stiffnesses. Never guess which one.
    def group_of(joint: str) -> str:
        if joint.startswith("shoulder_"):
            return "shoulder"
        if joint == "elbow_joint":
            return "elbow"
        return "wrist"

    print(f"\n  per-joint steady-state error at step {args_cli.steps - 1}:")
    print(f"  {'joint':<22}{'group':>10}{'stiffness':>12}{'err (rad)':>12}{'err (deg)':>12}")
    for i, n in enumerate(names):
        g = group_of(n)
        k = UR5E_CFG.actuators[g].stiffness
        e = float(err[i])
        print(f"  {n:<22}{g:>10}{k:>12.1f}{e:>12.6f}{torch.rad2deg(err[i]):>12.3f}")
    worst = int(err.abs().argmax())
    print(f"\n  worst joint: {names[worst]}  (group '{group_of(names[worst])}')")
    print(f"  -> if this needs fixing, that group's stiffness is the ONE knob to move.")

    settled = trace[-1][1]
    exploded = not torch.isfinite(robot.data.joint_pos).all() or max_drift > 1.0
    verdict("did not explode (finite, drift < 1 rad)", not exploded, f"peak {max_drift:.6f} rad")
    verdict(
        f"settled within tolerance ({args_cli.drift_tol} rad)",
        settled <= args_cli.drift_tol,
        f"final {settled:.6f} rad",
    )
    verdict("drift is not still growing", settled <= max_drift + 1e-9, f"peak {max_drift:.6f} rad")

    # ---- end-effector position, for placing the table later -----------------------------
    ee_idx = len(robot.body_names) - 1
    ee = robot.data.body_pos_w[0, ee_idx]
    print(f"\n  end-effector body : {robot.body_names[ee_idx]}")
    print(f"  position (world)  : x={ee[0]:+.3f}  y={ee[1]:+.3f}  z={ee[2]:+.3f}  m")
    print("  (not a pass/fail — this is what decides where the table goes in the lift env)")

    # ---- summary ------------------------------------------------------------------------
    print("\n" + "=" * 78)
    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"RESULT: FAIL — {len(failed)} of {len(results)} checks failed")
        for k in failed:
            print(f"  - {k}")
        print("\nLook up the symptom in the decision-rule table in logbook/02_grasp_env.md.")
        print("Change ONE knob. Re-run. Never two at once.")
    else:
        print(f"RESULT: PASS — all {len(results)} checks green. Arm is signed off.")
        print("Next: the gripper decision (Robotiq 2F-85 is rejected — see PROJECT_INSTRUCTIONS §9).")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
    simulation_app.close()
