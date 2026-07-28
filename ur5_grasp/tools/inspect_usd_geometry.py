# Copyright (c) 2026, Touhid — UR5e Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Inspect what geometry a USD actually contains, and how it is reachable.

WHY THIS EXISTS
---------------
Two open problems from `make_ur5e_rhp12_usd.py`, and one script answers both because they
share a root cause — USD instancing.

  1. CUBE EDGE (Step 2). `measure_cube_edge` reported a 0.060 m raw DexCube, giving 0.048 m
     at scale 0.8. The previous attempt used 0.0412 m, implying a 0.0515 m raw cube. That is
     a 17% disagreement on the number every grasp measurement is compared against, and it
     sets the predicted stall point for the grasp test. It has to be settled from the asset,
     not from either party's memory.

  2. GRIPPER COLOUR (Step 3). `colour_gripper` reported "0 renderable prims" while the
     gripper had plainly loaded (12 bodies, mount joint found). The warning text in that
     script blamed a failed reference — a wrong diagnosis, written by me. The suspected real
     cause is that `Usd.PrimRange(prim)` does NOT descend into INSTANCE PROXIES by default,
     so the traversal never reaches the meshes at all.

Both are traversal questions. So this script traverses twice — once with the default
predicate, once with `Usd.TraverseInstanceProxies()` — and prints the difference. If the
counts differ, instancing is confirmed as the cause of (2).

WHAT IT MEASURES FOR THE CUBE
-----------------------------
Four different numbers that could each be called "the cube size", printed side by side:

  * bbox per PURPOSE (default / render / proxy / guide) — a render proxy larger than the
    real mesh is one way a 0.0515 m cube reports as 0.060 m
  * the authored `extent` attribute — a hint, and hints can be stale or padded
  * the actual MESH POINTS min/max — ground truth, the vertices themselves
  * the world bbox — points after any scale op authored inside the asset

The number a grasp cares about is the COLLISION geometry, because that is what the pads
touch. Where collision and render disagree, collision wins.

RUN (lab PC, isaaclab env):

    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/tools/inspect_usd_geometry.py --headless --target cube
    ./isaaclab.sh -p ../ur5_grasp/tools/inspect_usd_geometry.py --headless --target gripper

Output: logbook/02_inspect_<target>.log
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Inspect the geometry inside a USD asset.")
parser.add_argument(
    "--target",
    type=str,
    default="cube",
    help="'cube', 'gripper', 'merged', or an explicit USD path / URL",
)
parser.add_argument(
    "--scale",
    type=float,
    default=0.8,
    help="uniform scale the env will apply — used only to report the effective size",
)
parser.add_argument(
    "--max_rows",
    type=int,
    default=40,
    help="cap on how many prims to list, so the log stays readable",
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below needs the app running ---------------------------------------
import os

from pxr import Usd, UsdGeom, UsdPhysics

from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.normpath(os.path.join(HERE, ".."))
ROOT_DIR = os.path.normpath(os.path.join(PKG_DIR, ".."))
ASSETS_DIR = os.path.join(PKG_DIR, "assets")

TARGETS = {
    "cube": f"{ISAAC_NUCLEUS_DIR}/Props/Blocks/DexCube/dex_cube_instanceable.usd",
    "gripper": os.path.join(ASSETS_DIR, "rh_p12_rn.usd"),
    "merged": os.path.join(ASSETS_DIR, "ur5e_rhp12.usd"),
}

USD_PATH = TARGETS.get(args_cli.target, args_cli.target)
LABEL = args_cli.target if args_cli.target in TARGETS else "custom"
REPORT_PATH = os.path.join(ROOT_DIR, "logbook", f"02_inspect_{LABEL}.log")

PURPOSES = {
    "default": UsdGeom.Tokens.default_,
    "render": UsdGeom.Tokens.render,
    "proxy": UsdGeom.Tokens.proxy,
    "guide": UsdGeom.Tokens.guide,
}

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
_FH = open(REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


def fmt_range(rng) -> str:
    if rng.IsEmpty():
        return "EMPTY"
    s = rng.GetSize()
    return f"{s[0]:.5f} x {s[1]:.5f} x {s[2]:.5f}"


def walk(root: Usd.Prim, with_proxies: bool):
    """Traverse a subtree, optionally descending into instance proxies."""
    if with_proxies:
        return list(Usd.PrimRange(root, Usd.TraverseInstanceProxies()))
    return list(Usd.PrimRange(root))


def points_bounds(prim: Usd.Prim):
    """Min/max of a Mesh's actual vertices — ground truth, ignoring extent hints."""
    if not prim.IsA(UsdGeom.Mesh):
        return None
    pts = UsdGeom.Mesh(prim).GetPointsAttr().Get()
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    return (
        (min(xs), min(ys), min(zs)),
        (max(xs), max(ys), max(zs)),
        len(pts),
    )


def main() -> None:
    log("=" * 78)
    log(f"INSPECT USD GEOMETRY   target={args_cli.target}")
    log("=" * 78)
    log(f"usd    : {USD_PATH}")
    log(f"report : {REPORT_PATH}")
    log("")

    stage = Usd.Stage.Open(USD_PATH)
    if stage is None:
        log("!! could not open the stage — check the path or the Nucleus connection.")
        return
    root = stage.GetDefaultPrim()
    if not root or not root.IsValid():
        log("!! stage has no default prim.")
        return
    log(f"default prim : {root.GetPath()}  (type {root.GetTypeName()})")
    log("")

    # --- 1. TRAVERSAL: does instancing hide the geometry? --------------------------
    log("--- 1. Traversal comparison (this is the colour-bug diagnosis) ---")
    plain = walk(root, with_proxies=False)
    proxied = walk(root, with_proxies=True)
    gprim_plain = [p for p in plain if p.IsA(UsdGeom.Gprim)]
    gprim_proxied = [p for p in proxied if p.IsA(UsdGeom.Gprim)]
    mesh_proxied = [p for p in proxied if p.IsA(UsdGeom.Mesh)]

    log(f"    prims  without instance proxies : {len(plain)}")
    log(f"    prims  WITH    instance proxies : {len(proxied)}")
    log(f"    Gprims without instance proxies : {len(gprim_plain)}")
    log(f"    Gprims WITH    instance proxies : {len(gprim_proxied)}")
    log(f"    Meshes WITH    instance proxies : {len(mesh_proxied)}")

    instanceable = [p for p in plain if p.IsInstanceable()]
    instances = [p for p in plain if p.IsInstance()]
    log(f"    prims marked instanceable       : {len(instanceable)}")
    log(f"    prims that ARE instances        : {len(instances)}")
    for p in instances[: args_cli.max_rows]:
        proto = p.GetPrototype()
        log(f"      instance {p.GetPath()}  -> prototype {proto.GetPath() if proto else 'NONE'}")

    log("")
    if len(gprim_plain) == 0 and len(gprim_proxied) > 0:
        log("    CONFIRMED: the geometry is reachable ONLY through instance proxies.")
        log("    This is why colour_gripper() found 0 renderable prims. Note that instance")
        log("    proxies are READ-ONLY — you cannot author a displayColor or a material")
        log("    binding on them. The fix is to author on the PROTOTYPE, or to clear the")
        log("    instanceable flag on the referencing prims before editing.")
    elif len(gprim_plain) > 0:
        log("    Geometry IS reachable without instance proxies, so instancing is NOT the")
        log("    cause of the colour failure. Look at the Gprim type check instead.")
    else:
        log("    No Gprims found either way — the geometry is somewhere this walk misses.")

    # --- 2. BOUNDS BY PURPOSE ------------------------------------------------------
    log("")
    log("--- 2. Whole-asset bounds, by purpose ---")
    for name, tok in PURPOSES.items():
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [tok])
        rng = cache.ComputeWorldBound(root).ComputeAlignedRange()
        log(f"    purpose {name:8s} : {fmt_range(rng)}")

    cache_both = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
    )
    rng_both = cache_both.ComputeWorldBound(root).ComputeAlignedRange()
    log(f"    default+render     : {fmt_range(rng_both)}   <- what make_ur5e_rhp12_usd.py used")

    # --- 3. PER-PRIM DETAIL --------------------------------------------------------
    log("")
    log("--- 3. Per-prim geometry (points are ground truth; extent is only a hint) ---")
    shown = 0
    for prim in proxied:
        if not prim.IsA(UsdGeom.Gprim):
            continue
        if shown >= args_cli.max_rows:
            log(f"    ... {len(gprim_proxied) - shown} more Gprims not shown")
            break
        shown += 1
        purpose = UsdGeom.Imageable(prim).ComputePurpose()
        flags = []
        if prim.IsInstanceProxy():
            flags.append("instance-proxy")
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            flags.append("CollisionAPI")
        log(f"    {prim.GetPath()}")
        log(f"      type={prim.GetTypeName()}  purpose={purpose}  {' '.join(flags)}")

        ext = UsdGeom.Boundable(prim).GetExtentAttr().Get()
        if ext:
            size = [ext[1][i] - ext[0][i] for i in range(3)]
            log(f"      extent attr  : {size[0]:.5f} x {size[1]:.5f} x {size[2]:.5f}")

        pb = points_bounds(prim)
        if pb:
            mn, mx, n = pb
            size = [mx[i] - mn[i] for i in range(3)]
            log(f"      MESH POINTS  : {size[0]:.5f} x {size[1]:.5f} x {size[2]:.5f}   ({n} verts)")

    # --- 4. THE VERDICT FOR THE CUBE ----------------------------------------------
    if LABEL == "cube":
        log("")
        log("--- 4. Cube edge verdict ---")
        candidates = {}
        for name, tok in PURPOSES.items():
            cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [tok])
            rng = cache.ComputeWorldBound(root).ComputeAlignedRange()
            if not rng.IsEmpty():
                candidates[f"bbox[{name}]"] = max(rng.GetSize())
        for prim in mesh_proxied:
            pb = points_bounds(prim)
            if pb:
                mn, mx, _ = pb
                candidates[f"points[{prim.GetName()}]"] = max(mx[i] - mn[i] for i in range(3))

        log(f"    {'source':28s} {'raw edge (m)':>14s} {'x scale ' + str(args_cli.scale):>16s}")
        for name, raw in candidates.items():
            log(f"    {name:28s} {raw:14.5f} {raw * args_cli.scale:16.5f}")

        log("")
        log("    HOW TO READ THIS:")
        log("      * If every source agrees, the cube really is that size and the previous")
        log("        attempt's 0.0412 m was wrong. Use the measured value and say so.")
        log("      * If the MESH POINTS are smaller than the bbox, something above the mesh")
        log("        inflates it — a scale op, or a larger render proxy. The points win for")
        log("        geometry; but check which prim carries CollisionAPI, because the pads")
        log("        contact the COLLISION mesh, not the render mesh.")
        log("      * A raw 0.0515 m here would vindicate the previous attempt's 0.0412 m.")

    log("")
    log(f"[report saved to {REPORT_PATH}]")


if __name__ == "__main__":
    try:
        main()
    finally:
        _FH.close()
        simulation_app.close()
