# Copyright (c) 2026, Touhid — UR5e Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Build and validate a single-articulation UR5e + ROBOTIS RH-P12-RN USD.

WHY THIS GRIPPER
----------------
The Robotiq 2F-85 is a closed-loop 4-bar. PhysX articulations are trees, so the loop is
never closed: the pad-carrying joints stay passive and no normal force reaches the contact
surfaces. See PROJECT_INSTRUCTIONS §9 — it is rejected for the critical path.

The RH-P12-RN URDF is a pure TREE. Verified by reading the copied URDF on 2026-07-28
(`ur5_grasp/assets/rh_p12_rn/rh_p12_rn.urdf`), not taken on trust:

    rh_p12_rn_base
      |-- rh_p12_rn  axis +x, limit 0.0 .. 1.1  --> rh_p12_rn_r1
      |     `-- rh_r2  axis -x, limit 0.0 .. 1.0  --> rh_p12_rn_r2
      |-- rh_l1      axis -x, limit 0.0 .. 1.1  --> rh_p12_rn_l1
            `-- rh_l2  axis +x, limit 0.0 .. 1.0  --> rh_p12_rn_l2

Four revolute joints, no loop, so every joint is directly drivable and there is a real
force path to the pads. The opposed axis signs mean all four take the SAME scalar target
and the pads stay parallel; r1/l1 allow 1.1 rad but r2/l2 only 1.0, so the common usable
stroke is q in [0, 1.0].

WHAT THIS SCRIPT DOES
---------------------
  1. Converts the URDF to USD with CONVEX DECOMPOSITION colliders. Not the default. A
     convex hull spans the gap between the pad faces and turns each finger into a solid
     blob with no flat gripping surface.
  2. Authors the merged USD: references the stock ur5e.usd with variant Gripper=None,
     references the converted gripper beneath it, STRIPS the gripper's nested articulation
     root, and adds a fixed mount joint wrist_3_link -> rh_p12_rn_base.
  3. Validates: confirms ONE articulation, prints joints and bodies, spawns a DexCube to
     measure against, then sweeps the gripper open -> closed and MEASURES pad separation.

DELIBERATE DEPARTURES FROM THE ARCHIVE SCRIPT (§14 — rebuild the what, reuse the how)
-------------------------------------------------------------------------------------
  a. NO calibrated number is imported. The archive's TCP offset 0.130, its pad-gap table
     and its ~0.0078 m pad half-thickness were measured on the previous attempt's build.
     This script measures all of them here or it does not report them.
  b. The cube edge is MEASURED from the spawned prim's bounds, not hardcoded. The archive
     compared against a literal 0.0412 m.
  c. The acceptance criterion is written INTO the script and evaluated as PASS / FAIL. The
     archive printed a table and left the judgement to the reader — which is how offsets
     0.100-0.120 all passed a static test while the cube was actually wedged on the curved
     proximal r1/l1 links.
  d. The report goes to `logbook/02_make_ur5e_rhp12.log`, matching the module-log
     convention, not to `tools/`.

WHAT THIS SCRIPT DOES *NOT* PROVE
---------------------------------
A free-space stroke sweep shows the pads CAN close to a given separation. It does not show
a grasp holds. The wedge failure mode above survives every check in this file. Proving the
grasp needs a separate script that closes on the cube and lifts it. Do not let a PASS here
be read as a working gripper.

RUN (lab PC, isaaclab env):

    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_rhp12_usd.py --headless

Drop --headless for the visual check. Add --mount_pos "0 0 0.005" / --mount_rpy "0 0 0.7854"
to nudge the flange mount if the gripper is clocked or sunk into the wrist.

Output: ur5_grasp/assets/ur5e_rhp12.usd  +  logbook/02_make_ur5e_rhp12.log
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Build + validate the UR5e + RH-P12-RN USD.")
parser.add_argument(
    "--mount_pos",
    type=str,
    default="0 0 0",
    help="gripper base position in the wrist_3_link frame, 'x y z' in metres (default: flange origin)",
)
parser.add_argument(
    "--mount_rpy",
    type=str,
    default="0 0 0",
    help="gripper base orientation in the wrist_3_link frame, 'r p y' in radians",
)
parser.add_argument(
    "--skip_convert",
    action="store_true",
    help="reuse an existing assets/rh_p12_rn.usd instead of re-running the URDF conversion",
)
parser.add_argument(
    "--gripper_color",
    type=str,
    default="0.02 0.02 0.02",
    help="linear RGB for the gripper visual material, 'r g b' in 0..1 (default: near-black)",
)
parser.add_argument(
    "--cube_scale",
    type=float,
    default=0.8,
    help="uniform scale applied to the DexCube — must match the value the lift env will use",
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below needs the app running ---------------------------------------
import math
import os

import torch
from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.sim.converters import UrdfConverter, UrdfConverterCfg
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.normpath(os.path.join(HERE, ".."))
ROOT_DIR = os.path.normpath(os.path.join(PKG_DIR, ".."))
ASSETS_DIR = os.path.join(PKG_DIR, "assets")

URDF_PATH = os.path.join(ASSETS_DIR, "rh_p12_rn", "rh_p12_rn.urdf")
GRIPPER_USD = os.path.join(ASSETS_DIR, "rh_p12_rn.usd")
OUT_USD = os.path.join(ASSETS_DIR, "ur5e_rhp12.usd")
REPORT_PATH = os.path.join(ROOT_DIR, "logbook", "02_make_ur5e_rhp12.log")

# Same arm asset as ur5_grasp/robots/ur5e_cfg.py — confirmed present by probe_ur5e_asset.py.
SRC_USD = f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd"
CUBE_USD = f"{ISAAC_NUCLEUS_DIR}/Props/Blocks/DexCube/dex_cube_instanceable.usd"

GRIPPER_JOINTS = ["rh_p12_rn", "rh_r2", "rh_l1", "rh_l2"]
PAD_BODIES = ["rh_p12_rn_r2", "rh_p12_rn_l2"]
Q_OPEN = 0.0
Q_CLOSE = 1.0

# Expected topology after the mount: 6 arm + 4 gripper joints, 7 arm + 5 gripper bodies.
# Arm counts are MEASURED — check_ur5e.py reported 6 joints / 7 bodies on 2026-07-27.
# Gripper counts are read off the URDF above.
EXPECT_JOINTS = 10
EXPECT_BODIES = 12

# ROBOTIS RH-P12-RN published stroke: 0-106 mm. Reduced from 109 mm for units shipped from
# 2019-11-04 onward, to improve fingertip durability.
# Source: https://emanual.robotis.com/docs/en/platform/rh_p12_rn/
#
# This is the ONE external ground truth available for the geometry, so it is used as an
# acceptance check rather than a comment. Tolerance is 3 mm: the pad reach is bounded by an
# axis-aligned box around a curved fingertip, so a few mm of over-approximation is expected
# and is not evidence of a bug. A miss of 10 mm or more IS.
DATASHEET_STROKE_M = 0.106
STROKE_TOL_M = 0.003

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
_FH = open(REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


def find_prim_by_name(stage: Usd.Stage, root: str, name: str) -> Usd.Prim | None:
    """Depth-first search for a prim whose name matches exactly.

    Prim paths differ between the stock UR5e USD and whatever the URDF importer authors,
    so searching by name is the only stable way to reach the two mount bodies.
    """
    start = stage.GetPrimAtPath(root)
    if not start or not start.IsValid():
        return None
    for prim in Usd.PrimRange(start):
        if prim.GetName() == name:
            return prim
    return None


def rotate_into_body_frame(vec_w: torch.Tensor, quat_w: torch.Tensor) -> torch.Tensor:
    """Express a world-frame vector in a body's local frame.

    Written out rather than imported because the helper's name moved between Isaac Lab
    releases (quat_rotate_inverse -> quat_apply_inverse) and a wrong import here would fail
    at the one line the acceptance test depends on.

    For a unit quaternion q = (w, u): rotating by q is  v + 2w(u x v) + 2u x (u x v).
    Rotating by q^-1 = (w, -u) flips only the middle term, since (-u) x ((-u) x v) = u x (u x v).
    """
    w = quat_w[0]
    u = quat_w[1:]
    t = torch.linalg.cross(u, vec_w)
    return vec_w - 2.0 * w * t + 2.0 * torch.linalg.cross(u, t)


# ---------------------------------------------------------------------------------
# 1. URDF -> USD
# ---------------------------------------------------------------------------------
def convert_gripper() -> None:
    cfg = UrdfConverterCfg(
        asset_path=URDF_PATH,
        usd_dir=ASSETS_DIR,
        usd_file_name="rh_p12_rn.usd",
        force_usd_conversion=True,
        # The base link bolts to the UR5e flange, so it must NOT be world-fixed.
        fix_base=False,
        root_link_name="rh_p12_rn_base",
        # The URDF has no fixed joints to merge, and merging risks renaming bodies that
        # the env cfg and this script's measurements refer to by name.
        merge_fixed_joints=False,
        # THE important line. See the module docstring.
        collider_type="convex_decomposition",
        # The fingers are close-packed and never need to collide with each other. Leaving
        # this on costs contact pairs at 4096 envs for no benefit.
        self_collision=False,
        joint_drive=UrdfConverterCfg.JointDriveCfg(
            drive_type="force",
            target_type="position",
            # PROVISIONAL. These are the USD-authored drive gains; the ArticulationCfg
            # written later overrides them. Not tuned here — tuning before the geometry is
            # measured would be changing a value without evidence.
            gains=UrdfConverterCfg.JointDriveCfg.PDGainsCfg(stiffness=200.0, damping=20.0),
        ),
    )
    converter = UrdfConverter(cfg)
    log(f"    converted -> {converter.usd_path}")


# ---------------------------------------------------------------------------------
# 2. Author the merged USD
# ---------------------------------------------------------------------------------
def colour_gripper(stage: Usd.Stage, root: str, rgb: list[float]) -> tuple[int, list[str]]:
    """Force a flat colour onto every renderable prim under `root`.

    Cosmetic, but it is what makes the GUI check possible: the RH-P12-RN and the UR5e both
    import light grey, so the hand vanishes into the wrist and you cannot see whether the
    fingers are open or closed.

    Binding a material on each MESH is NOT enough. USD resolves bindings by strength, and a
    binding authored on an ANCESTOR with `strongerThanDescendants` beats everything below
    it — which is exactly what the URDF importer authors. So: bind once at the subtree root,
    also `strongerThanDescendants`.

    MEASURED 2026-07-28 — this function used to also write `displayColor` on every Gprim it
    walked, and warn when it found none. It always found none, and the warning text blamed a
    failed reference. That was a WRONG diagnosis. `inspect_usd_geometry.py --target gripper`
    showed the real structure: all 10 finger meshes are USD INSTANCES pointing at
    `/__Prototype_1..10`, and `Usd.PrimRange` does not descend into instance proxies by
    default. So the loop never saw them.

    The per-mesh loop is now gone rather than fixed, because fixing it is impossible and
    unnecessary: instance proxies are READ-ONLY (so is a prototype), and the root binding
    below already works — confirmed visually in the GUI on 2026-07-28, the hand renders
    black. The binding wins because it is authored OUTSIDE the prototypes, so it is
    inherited by the proxies at render time.

    Returns (instanced meshes found, material bindings displaced).
    """
    mat = UsdShade.Material.Define(stage, "/Robot/Looks/GripperColour")
    shader = UsdShade.Shader.Define(stage, "/Robot/Looks/GripperColour/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

    displaced: list[str] = []
    start = stage.GetPrimAtPath(root)

    # Directly-authored bindings only — anything inside a prototype is out of reach and does
    # not need clearing, since the root binding below outranks it.
    for prim in Usd.PrimRange(start):
        if prim.HasAPI(UsdShade.MaterialBindingAPI) and prim.GetPath() != start.GetPath():
            binding = UsdShade.MaterialBindingAPI(prim)
            if binding.GetDirectBinding().GetMaterial():
                displaced.append(str(prim.GetPath()))
            binding.UnbindAllBindings()

    root_binding = UsdShade.MaterialBindingAPI.Apply(start)
    root_binding.Bind(mat, UsdShade.Tokens.strongerThanDescendants)

    # Count through instance proxies — read-only, but it proves the geometry is present.
    # A zero here really would mean the reference failed to resolve.
    n = sum(1 for p in Usd.PrimRange(start, Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Mesh))
    return n, displaced


def build_usd() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if os.path.exists(OUT_USD):
        os.remove(OUT_USD)

    mount_pos = [float(v) for v in args_cli.mount_pos.split()]
    mount_rpy = [float(v) for v in args_cli.mount_rpy.split()]
    log(f"    mount pos={mount_pos}  rpy={mount_rpy}  (in the wrist_3_link frame)")

    stage = Usd.Stage.CreateNew(OUT_USD)
    robot = UsdGeom.Xform.Define(stage, "/Robot").GetPrim()
    robot.GetReferences().AddReference(SRC_USD)
    stage.SetDefaultPrim(robot)

    # Bare arm. Gripper=None because we bolt our own on below; leaving the stock Robotiq
    # in would give two grippers and a joint-name collision.
    vsets = robot.GetVariantSets()
    for name, sel in {"Physics": "PhysX", "Gripper": "None", "Sensor": "None"}.items():
        if name in vsets.GetNames():
            vsets.GetVariantSet(name).SetVariantSelection(sel)
            log(f"    variant {name} -> {sel}")
        else:
            log(f"    variant {name} not present on this asset — skipped")

    grip_root = UsdGeom.Xform.Define(stage, "/Robot/RHP12").GetPrim()
    grip_root.GetReferences().AddReference(GRIPPER_USD)

    # ONE articulation. The converted gripper carries its own articulation root; leaving it
    # gives PhysX two articulations and the ArticulationRootAPI error from §9. Stripping it
    # lets PhysX fold the gripper bodies into the arm across the fixed mount joint below.
    stripped = 0
    for prim in Usd.PrimRange(grip_root):
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            prim.RemoveAPI(UsdPhysics.ArticulationRootAPI)
            PhysxSchema.PhysxArticulationAPI.Apply(prim).CreateArticulationEnabledAttr(False)
            log(f"    disabled nested articulation root at {prim.GetPath()}")
            stripped += 1
    if stripped == 0:
        log("    !! WARNING: found no nested articulation root to strip. Either the")
        log("       converter stopped authoring one, or the reference did not resolve.")
        log("       Check the joint/body counts in section 3 before trusting this build.")

    wrist = find_prim_by_name(stage, "/Robot", "wrist_3_link")
    base = find_prim_by_name(stage, "/Robot/RHP12", "rh_p12_rn_base")
    if wrist is None or base is None:
        log(f"    !! mount FAILED — wrist_3_link={wrist}, rh_p12_rn_base={base}. Aborting build.")
        return
    log(f"    wrist prim : {wrist.GetPath()}")
    log(f"    base  prim : {base.GetPath()}")

    joint = UsdPhysics.FixedJoint.Define(stage, "/Robot/rhp12_mount_joint")
    joint.CreateBody0Rel().SetTargets([wrist.GetPath()])
    joint.CreateBody1Rel().SetTargets([base.GetPath()])
    joint.CreateLocalPos0Attr().Set(Gf.Vec3f(*mount_pos))
    joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
    r, p, y = mount_rpy
    q = (
        Gf.Rotation(Gf.Vec3d(0, 0, 1), math.degrees(y))
        * Gf.Rotation(Gf.Vec3d(0, 1, 0), math.degrees(p))
        * Gf.Rotation(Gf.Vec3d(1, 0, 0), math.degrees(r))
    ).GetQuat()
    joint.CreateLocalRot0Attr().Set(Gf.Quatf(q))
    joint.CreateLocalRot1Attr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    log("    added fixed joint /Robot/rhp12_mount_joint  (wrist_3_link -> rh_p12_rn_base)")

    rgb = [float(v) for v in args_cli.gripper_color.split()]
    n, displaced = colour_gripper(stage, "/Robot/RHP12", rgb)
    log(f"    bound /Robot/Looks/GripperColour rgb={rgb} at /Robot/RHP12 "
        f"(strongerThanDescendants); {n} instanced meshes beneath it")
    if displaced:
        log(f"    removed {len(displaced)} competing material binding(s):")
        for d in displaced[:12]:
            log(f"      - {d}")
    if n == 0:
        log("    !! WARNING: no meshes found under /Robot/RHP12 even through instance")
        log("       proxies. THIS one really does mean the gripper reference did not")
        log("       resolve — check the joint and body counts in section 3.")

    stage.GetRootLayer().Save()
    log(f"    wrote {OUT_USD}")


# ---------------------------------------------------------------------------------
# 3. Validate, measure, judge
# ---------------------------------------------------------------------------------
def measure_cube_edge() -> float:
    """Measure the DexCube's edge length from its own USD, scaled as the env will scale it.

    Measured rather than hardcoded so the number is defensible in the thesis: it names the
    asset and the scale that produced it. The archive compared against a literal 0.0412 m
    with no traceable source.
    """
    cube_stage = Usd.Stage.Open(CUBE_USD)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    bound = cache.ComputeWorldBound(cube_stage.GetDefaultPrim()).ComputeAlignedRange()
    size = bound.GetSize()
    edges = [size[0], size[1], size[2]]
    log(f"    DexCube raw bounds (m): {edges[0]:.5f} x {edges[1]:.5f} x {edges[2]:.5f}")
    if max(edges) - min(edges) > 1e-4:
        log("    !! the DexCube is not cubic on this asset — using the LARGEST edge, which is")
        log("       the conservative choice for a gripper-opening check.")
    return max(edges) * args_cli.cube_scale


_PAD_BOUNDS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {}


def pad_local_bounds(body: str) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Local-frame AABB (min, max) of a pad link's geometry. Cached — the bounds are static."""
    if body not in _PAD_BOUNDS:
        stage = Usd.Stage.Open(GRIPPER_USD)
        prim = find_prim_by_name(stage, str(stage.GetDefaultPrim().GetPath()), body)
        if prim is None:
            return None
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
        # Untransformed: the link's own geometry in the link's own frame — the same frame
        # whose origin body_pos_w reports.
        rng = cache.ComputeUntransformedBound(prim).ComputeAlignedRange()
        mn, mx = rng.GetMin(), rng.GetMax()
        _PAD_BOUNDS[body] = ((mn[0], mn[1], mn[2]), (mx[0], mx[1], mx[2]))
    return _PAD_BOUNDS[body]


def measure_pad_reach(direction_local: torch.Tensor, body: str) -> float:
    """How far the pad's geometry reaches FROM THE BODY ORIGIN along `direction_local`.

    CORRECTED 2026-07-28 — the first version of this function was wrong.

    It computed `size / 2` and projected that, which is the AABB's half-width. That is only
    the reach from the origin if the box is CENTRED on the origin. It is not: the body origin
    sits on the joint axis, not at the pad centre. The error produced a 92.4 mm open clear
    opening against a 106 mm datasheet stroke, and an impossible NEGATIVE gap (-0.0004 m) at
    full close — two pad faces cannot pass through each other.

    The correct quantity is the box SUPPORT in direction d: take each coordinate from the max
    corner where d is positive and the min corner where it is negative.

        s(d) = sum_i  d_i * (d_i > 0 ? max_i : min_i)

    Still an over-approximation for a curved pad — an AABB bounds the curve, so the reported
    reach is at least the true one. Note which way that biases each check: it makes the OPEN
    gap read too small (conservative, safe) but the CLOSED gap read too small as well
    (optimistic — it makes the closed-gap check easier to pass). Do not read a passing closed
    check as proof the pads meet.
    """
    bounds = pad_local_bounds(body)
    if bounds is None:
        return float("nan")
    mn, mx = bounds
    d = direction_local.cpu().tolist()
    return float(sum(d[i] * (mx[i] if d[i] > 0.0 else mn[i]) for i in range(3)))


def validate_usd() -> None:
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1.0 / 120.0, device=args_cli.device))
    sim_utils.GroundPlaneCfg().func("/World/ground", sim_utils.GroundPlaneCfg())
    sim_utils.DomeLightCfg(intensity=2000.0).func("/World/Light", sim_utils.DomeLightCfg(intensity=2000.0))

    robot = Articulation(
        ArticulationCfg(
            prim_path="/World/Robot",
            spawn=sim_utils.UsdFileCfg(usd_path=OUT_USD),
            # A blanket actuator on purpose. This is a GEOMETRY measurement: every quantity
            # below is a distance between two bodies of the same robot, so arm droop under
            # these gains cancels out. The tuned per-group gains live in the ArticulationCfg
            # and are not what this script is testing.
            actuators={
                "all": ImplicitActuatorCfg(
                    joint_names_expr=[".*"], stiffness=400.0, damping=40.0, armature=0.01
                )
            },
        )
    )
    sim.reset()

    log("    loaded as a single articulation.")
    log(f"    num joints : {robot.num_joints}   (expected {EXPECT_JOINTS})")
    log(f"    joint names: {list(robot.joint_names)}")
    log(f"    num bodies : {robot.num_bodies}   (expected {EXPECT_BODIES})")
    log(f"    body names : {list(robot.body_names)}")

    topology_ok = robot.num_joints == EXPECT_JOINTS and robot.num_bodies == EXPECT_BODIES
    if not topology_ok:
        log("    !! TOPOLOGY MISMATCH. Counts other than 10/12 mean the mount did not fold")
        log("       the two bodies into one articulation. Fix that before reading any")
        log("       distance below — they would be measured on the wrong robot.")

    missing = [j for j in GRIPPER_JOINTS if j not in robot.joint_names]
    if missing:
        log(f"    !! gripper joints missing: {missing}. Stop here and fix the mount.")
        return

    cube_edge = measure_cube_edge()
    log(f"    DexCube edge at scale {args_cli.cube_scale}: {cube_edge:.5f} m")

    gid, _ = robot.find_joints(GRIPPER_JOINTS)
    r2 = robot.find_bodies(PAD_BODIES[0])[0][0]
    l2 = robot.find_bodies(PAD_BODIES[1])[0][0]
    wid = robot.find_bodies("wrist_3_link")[0][0]

    log("")
    log("    --- gripper stroke sweep ---")
    log("      q(rad)   origin_gap(m)   reach_r(m)   reach_l(m)   face_gap(m)   tcp_from_wrist(m)")

    targets = robot.data.default_joint_pos.clone()
    rows = []
    for i in range(11):
        q = Q_OPEN + i * (Q_CLOSE - Q_OPEN) / 10.0
        targets[:, gid] = q
        for _ in range(60):  # let the drives settle before measuring
            robot.set_joint_position_target(targets)
            robot.write_data_to_sim()
            sim.step()
            robot.update(1.0 / 120.0)

        pr = robot.data.body_pos_w[0, r2]
        pl = robot.data.body_pos_w[0, l2]
        pw = robot.data.body_pos_w[0, wid]
        qr = robot.data.body_quat_w[0, r2]
        ql = robot.data.body_quat_w[0, l2]

        delta = pr - pl
        origin_gap = float(torch.norm(delta))
        # The closing direction is derived from the pads themselves rather than assumed to
        # be a URDF axis — the mount rotation would invalidate any assumed axis.
        # n_world points from the LEFT pad toward the RIGHT pad.
        n_world = delta / (torch.norm(delta) + 1e-12)
        # Each pad's inner face lies toward the OTHER pad, so the two reaches are measured
        # in OPPOSITE directions: -n for the right pad, +n for the left.
        reach_r = measure_pad_reach(rotate_into_body_frame(-n_world, qr), PAD_BODIES[0])
        reach_l = measure_pad_reach(rotate_into_body_frame(n_world, ql), PAD_BODIES[1])
        face_gap = origin_gap - (reach_r + reach_l)

        tcp = float(torch.norm((pr + pl) / 2.0 - pw))
        rows.append((q, origin_gap, face_gap, tcp))
        log(
            f"      {q:5.2f}    {origin_gap:9.4f}   {reach_r:9.4f}   {reach_l:9.4f}"
            f"   {face_gap:9.4f}   {tcp:13.4f}"
        )

    log("")
    log("    --- acceptance criteria (written before the run) ---")

    open_face = rows[0][2]
    closed_face = rows[-1][2]
    gaps = [r[1] for r in rows]
    monotonic = all(gaps[i + 1] <= gaps[i] + 1e-4 for i in range(len(gaps) - 1))
    moved = (gaps[0] - gaps[-1]) > 0.01

    checks = [
        ("topology is 10 joints / 12 bodies", topology_ok),
        ("the pads actually move over the stroke (>10 mm change)", moved),
        ("separation shrinks monotonically — no jump or bounce", monotonic),
        (f"open face gap clears the cube ({open_face:.4f} > {cube_edge:.4f} m)", open_face > cube_edge),
        (f"closed face gap is under the cube ({closed_face:.4f} < {cube_edge:.4f} m)", closed_face < cube_edge),
        (
            f"open face gap matches the datasheet stroke "
            f"({open_face:.4f} vs {DATASHEET_STROKE_M:.4f} +/- {STROKE_TOL_M:.3f} m, "
            f"error {1000.0 * (open_face - DATASHEET_STROKE_M):+.1f} mm)",
            abs(open_face - DATASHEET_STROKE_M) <= STROKE_TOL_M,
        ),
        (f"closed face gap is physically possible (>= 0, got {closed_face:.4f} m)", closed_face >= -1e-4),
    ]
    for label, ok in checks:
        log(f"      [{'PASS' if ok else 'FAIL'}]  {label}")

    log("")
    if all(ok for _, ok in checks):
        log("    RESULT: PASS — the pads sweep from clear of the cube to closed past it, so a")
        log("    flat parallel grip is geometrically possible.")
    else:
        log("    RESULT: FAIL — see the failed lines above. Change ONE knob and re-run.")

    log("")
    log("    WHAT THIS DOES NOT SHOW")
    log("    A free-space sweep says nothing about whether a grasp HOLDS. The known failure")
    log("    mode is the cube wedging on the curved proximal r1/l1 links: that survives a")
    log("    static hold test and fails under lift accelerations. The next script has to")
    log("    close on the cube and check the pads stall at the cube width, not wider.")
    log("")
    log("    TCP OFFSET: read tcp_from_wrist at q=0.00 above as the STARTING value for the")
    log("    env's ee_frame OffsetCfg. It is a starting value, not the answer — the pad")
    log(f"    midpoint travels {abs(rows[-1][3] - rows[0][3]):.4f} m over the stroke, so the")
    log("    TCP is not a fixed point. Calibrate it against a real grasp before trusting it.")


def main() -> None:
    log("=" * 78)
    log("BUILD + VALIDATE   ur5e_rhp12.usd    (UR5e + ROBOTIS RH-P12-RN)")
    log("=" * 78)
    log(f"urdf        : {URDF_PATH}")
    log(f"arm USD     : {SRC_USD}")
    log(f"cube USD    : {CUBE_USD}")
    log(f"output USD  : {OUT_USD}")
    log("")

    log("--- 1. Converting URDF -> USD ---")
    if args_cli.skip_convert and os.path.exists(GRIPPER_USD):
        log(f"    skipped (reusing {GRIPPER_USD})")
    else:
        try:
            convert_gripper()
        except Exception:  # noqa: BLE001
            import traceback

            log("    !! conversion FAILED — traceback below:")
            log(traceback.format_exc())

    log("")
    log("--- 2. Authoring the merged USD ---")
    build_usd()

    log("")
    log("--- 3. Validating + measuring ---")
    try:
        validate_usd()
    except Exception:  # noqa: BLE001
        import traceback

        log("    !! validation FAILED — traceback below:")
        log(traceback.format_exc())

    log("")
    log(f"[report saved to {REPORT_PATH}]")


if __name__ == "__main__":
    try:
        main()
    finally:
        _FH.close()
        simulation_app.close()
