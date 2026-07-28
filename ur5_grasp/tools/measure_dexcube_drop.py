# Copyright (c) 2026, Touhid — UR5e Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Settle the DexCube edge length by dropping it on a plane and measuring where it rests.

WHY A PHYSICAL TEST AND NOT MORE USD READING
--------------------------------------------
`inspect_usd_geometry.py --target cube` gave two agreeing answers and one that makes no
sense, so USD introspection alone cannot close this:

    purpose default (the visuals mesh, after transforms)   0.06000 m   <- agrees
    /DexCube/collisions extent attribute                   0.06000 m   <- agrees
    purpose guide  (the collisions prim, world bound)      0.00360 m   <- makes no sense

0.0036 = 0.06 x 0.06, which looks like a scale applied twice. A 3.6 mm collision box is not
credible for an asset the whole Isaac Lab lift task is built around, so that reading is
almost certainly an artefact of asking BBoxCache for `guide` purpose in isolation. But
"almost certainly" is not a measurement, and the cube edge is the number every grasp result
gets compared against.

So measure what PhysX actually simulates. Drop the cube on a ground plane at z=0 and read
the resting centre height. For a cube resting on a face:

    edge = 2 x resting centre height

This is unambiguous, it uses the COLLISION geometry (which is what the gripper pads will
touch, not the render mesh), and it produces a number with a reproducible command behind it.

THE DISAGREEMENT BEING SETTLED
------------------------------
    this rebuild's USD reading   raw 0.0600 m  ->  0.0480 m at scale 0.8
    previous attempt's number    raw 0.0515 m  ->  0.0412 m at scale 0.8

Both scales are dropped here so the raw edge and the env-scaled edge are both measured
rather than one being inferred from the other.

RUN (lab PC, isaaclab env):

    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/tools/measure_dexcube_drop.py --headless

Output: logbook/02_measure_dexcube.log
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Measure the DexCube edge by a drop test.")
parser.add_argument(
    "--env_scale",
    type=float,
    default=0.8,
    help="the scale the lift env will apply to the cube",
)
parser.add_argument(
    "--drop_height",
    type=float,
    default=0.15,
    help="centre height to release from (m). Low on purpose — less bounce, faster settle.",
)
parser.add_argument(
    "--settle_steps",
    type=int,
    default=600,
    help="physics steps to settle before measuring (600 @ 1/120 s = 5 s)",
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below needs the app running ---------------------------------------
import os

import torch

import isaaclab.sim as sim_utils
from isaaclab.assets import RigidObject, RigidObjectCfg
from isaaclab.sim.schemas.schemas_cfg import RigidBodyPropertiesCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
REPORT_PATH = os.path.join(ROOT_DIR, "logbook", "02_measure_dexcube.log")

CUBE_USD = f"{ISAAC_NUCLEUS_DIR}/Props/Blocks/DexCube/dex_cube_instanceable.usd"

# The two competing claims, stated before the run so the log is falsifiable.
CLAIM_THIS_REBUILD = 0.0600
CLAIM_PREV_ATTEMPT = 0.0515
TOL = 0.0015  # 1.5 mm — generous enough for settle noise, tight enough to separate the two

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
_FH = open(REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


def make_cube(name: str, scale: float, x: float) -> RigidObject:
    return RigidObject(
        RigidObjectCfg(
            prim_path=f"/World/{name}",
            init_state=RigidObjectCfg.InitialStateCfg(
                pos=(x, 0.0, args_cli.drop_height), rot=(1.0, 0.0, 0.0, 0.0)
            ),
            spawn=UsdFileCfg(
                usd_path=CUBE_USD,
                scale=(scale, scale, scale),
                rigid_props=RigidBodyPropertiesCfg(
                    solver_position_iteration_count=16,
                    solver_velocity_iteration_count=1,
                    max_depenetration_velocity=5.0,
                    disable_gravity=False,
                ),
            ),
        )
    )


def main() -> None:
    log("=" * 78)
    log("MEASURE DexCube EDGE BY DROP TEST")
    log("=" * 78)
    log(f"cube USD     : {CUBE_USD}")
    log(f"drop height  : {args_cli.drop_height} m")
    log(f"settle steps : {args_cli.settle_steps}")
    log("")
    log("PREDICTIONS (written before the run):")
    log(f"  if this rebuild's USD reading is right : raw edge {CLAIM_THIS_REBUILD:.4f} m,")
    log(f"       resting centre {CLAIM_THIS_REBUILD / 2:.4f} m")
    log(f"  if the previous attempt was right      : raw edge {CLAIM_PREV_ATTEMPT:.4f} m,")
    log(f"       resting centre {CLAIM_PREV_ATTEMPT / 2:.4f} m")
    log("")

    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1.0 / 120.0, device=args_cli.device))
    # Ground plane at EXACTLY z=0 — the whole measurement depends on this.
    sim_utils.GroundPlaneCfg().func("/World/ground", sim_utils.GroundPlaneCfg())
    sim_utils.DomeLightCfg(intensity=2000.0).func("/World/Light", sim_utils.DomeLightCfg(intensity=2000.0))

    cubes = {
        "raw (scale 1.0)": make_cube("CubeRaw", 1.0, 0.0),
        f"env (scale {args_cli.env_scale})": make_cube("CubeEnv", args_cli.env_scale, 0.5),
    }
    sim.reset()

    for _ in range(args_cli.settle_steps):
        for c in cubes.values():
            c.write_data_to_sim()
        sim.step()
        for c in cubes.values():
            c.update(1.0 / 120.0)

    log("--- measured at rest ---")
    log(f"    {'cube':22s} {'centre z (m)':>13s} {'|vel| (m/s)':>12s} {'-> edge (m)':>13s}")
    results = {}
    for name, c in cubes.items():
        z = float(c.data.root_pos_w[0, 2])
        v = float(torch.norm(c.data.root_lin_vel_w[0]))
        edge = 2.0 * z
        results[name] = (z, v, edge)
        log(f"    {name:22s} {z:13.5f} {v:12.5f} {edge:13.5f}")

    log("")
    at_rest = all(v < 1e-3 for _, v, _ in results.values())
    if not at_rest:
        log("    !! NOT AT REST — a cube is still moving, so these heights are not a")
        log("       measurement. Raise --settle_steps and re-run. Change nothing else.")
        return

    raw_edge = results["raw (scale 1.0)"][2]
    env_edge = results[f"env (scale {args_cli.env_scale})"][2]

    log("--- verdict ---")
    matches_rebuild = abs(raw_edge - CLAIM_THIS_REBUILD) <= TOL
    matches_prev = abs(raw_edge - CLAIM_PREV_ATTEMPT) <= TOL
    log(f"    raw edge measured           : {raw_edge:.5f} m")
    log(f"    vs this rebuild ({CLAIM_THIS_REBUILD:.4f})     : {'MATCH' if matches_rebuild else 'no'}"
        f"   (err {1000 * (raw_edge - CLAIM_THIS_REBUILD):+.1f} mm)")
    log(f"    vs previous attempt ({CLAIM_PREV_ATTEMPT:.4f}) : {'MATCH' if matches_prev else 'no'}"
        f"   (err {1000 * (raw_edge - CLAIM_PREV_ATTEMPT):+.1f} mm)")
    log("")

    if matches_rebuild and not matches_prev:
        log("    RESULT: the USD reading in this rebuild is correct. The previous attempt's")
        log("    0.0412 m was wrong, and any archive number derived from it is suspect.")
    elif matches_prev and not matches_rebuild:
        log("    RESULT: the previous attempt was right and this rebuild's USD reading is")
        log("    inflated. Fix measure_cube_edge() before using any gap comparison.")
    else:
        log("    RESULT: INCONCLUSIVE — matches both or neither. Do not proceed on this")
        log("    number. Check the cube is resting on a FACE and not a corner or edge.")

    # Internal consistency: scaling should be exactly linear.
    expected = raw_edge * args_cli.env_scale
    log("")
    log(f"    consistency: raw x {args_cli.env_scale} = {expected:.5f} vs measured "
        f"{env_edge:.5f}  (err {1000 * (env_edge - expected):+.1f} mm)")
    if abs(env_edge - expected) > TOL:
        log("    !! scaling is NOT linear. That points at the collision shape not being")
        log("       rescaled with the visual — a real problem for grasping. Investigate")
        log("       before writing the env cfg.")

    log("")
    log("    USE THIS NUMBER: the env-scale edge above is what the gripper must close on.")
    log("    Quote it with this command in Thesis_Documentation/06_Results_and_Experiments.md.")


if __name__ == "__main__":
    try:
        main()
    finally:
        _FH.close()
        simulation_app.close()
