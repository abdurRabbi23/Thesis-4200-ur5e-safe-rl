"""Probe: does Isaac Sim ship a usable Robotiq 2F-85, and does stock ur5e.usd carry gripper variants?

Module 02 / STEP 6 — the SECOND gripper. Same method that resolved the arm in STEP 2:
ask the asset server and the USD directly instead of guessing.

Why this probe exists. The Robotiq 2F-85 was rejected in PROJECT_INSTRUCTIONS §9 because each
finger is a closed four-bar linkage. A URDF is a tree and cannot hold a loop, so every public
2F-85 URDF breaks the loop and papers over it with `<mimic>` tags, which Isaac Lab 2.3 does not
honour usefully (issue #2424, discussion #2626). That is why the previous attempt fell back to a
proximity weld. BUT: a USD authored by NVIDIA does not have the URDF's tree restriction, and the
archive's build script referenced a `Gripper` VARIANT SET on the stock `ur5e.usd`. If that variant
set offers a Robotiq value, the coupling is already authored and the §9 objection does not apply
to that asset. This script finds out before we spend a day on it.

Run (from the IsaacLab clone, ~3 min):

    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/scripts/probe_gripper_assets.py \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_probe_gripper_assets.log

READ THE OUTPUT IN THIS ORDER:

  1. CONTROL — the ur10e path Isaac Lab itself ships. Must come back `on Nucleus`. If the
     control is MISSING the server is unreachable and every line below is noise, not evidence.
  2. PART A, VARIANTS on stock ur5e.usd — the cheapest possible win. A `Gripper` variant set
     listing a Robotiq value means the asset is already built and coupled.
  3. PART B, LISTING of the Nucleus gripper folders — ground truth on what standalone 2F-85
     assets exist.
  4. PART C, CANDIDATES — named guesses. Only meaningful read next to the listing.

A found asset is NOT yet a passed gripper. It only earns the right to the pad-force test.
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Probe for a shipped Robotiq 2F-85 USD and ur5e gripper variants.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
# no GUI needed — this only talks to the asset server and opens stages read-only
args_cli.headless = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below needs the app running (carb settings + omni.client) ---
import omni.client  # noqa: E402
from pxr import Usd  # noqa: E402

from isaaclab.utils.assets import (  # noqa: E402
    ISAAC_NUCLEUS_DIR,
    ISAACLAB_NUCLEUS_DIR,
    NUCLEUS_ASSET_ROOT_DIR,
    check_file_path,
)

STATUS = {0: "MISSING", 1: "local", 2: "on Nucleus"}

UR5E_USD = f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd"


def show(label: str, path: str) -> None:
    print(f"{label:<9} {STATUS[check_file_path(path)]:<11} {path}")


def listdir(url: str) -> list[str]:
    """List a Nucleus folder. Returns the entry names, or [] if it cannot be listed."""
    print(f"\n--- listing: {url}")
    result, entries = omni.client.list(url)
    if result != omni.client.Result.OK:
        print(f"    could not list  ({result})")
        return []
    names = sorted(e.relative_path for e in entries)
    for n in names:
        print(f"    {n}")
    if not names:
        print("    (empty)")
    return names


def show_variants(usd_path: str) -> None:
    """Open a USD read-only and print every variant set on every prim that has one."""
    print(f"\n--- variant sets in: {usd_path}")
    stage = Usd.Stage.Open(usd_path)
    if stage is None:
        print("    could not open stage")
        return
    found = False
    for prim in stage.Traverse():
        vsets = prim.GetVariantSets()
        names = vsets.GetNames()
        if not names:
            continue
        found = True
        for vs_name in names:
            vs = vsets.GetVariantSet(vs_name)
            options = vs.GetVariantNames()
            selected = vs.GetVariantSelection()
            print(f"    {prim.GetPath()}")
            print(f"        set '{vs_name}'  selected='{selected}'  options={options}")
    if not found:
        print("    (no variant sets on any prim)")


print("=" * 78)
print("GRIPPER ASSET PROBE  —  Module 02, STEP 6 (second gripper: Robotiq 2F-85)")
print("=" * 78)
print(f"NUCLEUS_ASSET_ROOT_DIR : {NUCLEUS_ASSET_ROOT_DIR}")
print(f"ISAAC_NUCLEUS_DIR      : {ISAAC_NUCLEUS_DIR}")
print(f"ISAACLAB_NUCLEUS_DIR   : {ISAACLAB_NUCLEUS_DIR}")
print()

# 0. CONTROL ------------------------------------------------------------------
# Taken verbatim from UR10e_CFG. MISSING here => server unreachable, stop reading.
show("CONTROL", f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur10e/ur10e.usd")
show("UR5E", UR5E_USD)

# PART A — the cheapest possible win -------------------------------------------
print()
print("-" * 78)
print("PART A — does stock ur5e.usd already carry a Gripper variant set?")
print("-" * 78)
show_variants(UR5E_USD)

# PART B — ground truth on standalone gripper assets ---------------------------
print()
print("-" * 78)
print("PART B — what gripper assets does the library actually contain?")
print("-" * 78)
for root in (f"{ISAAC_NUCLEUS_DIR}/Robots/", f"{ISAACLAB_NUCLEUS_DIR}/Robots/"):
    for name in listdir(root):
        if any(k in name.lower() for k in ("robotiq", "gripper", "endeffector", "end_effector")):
            listdir(f"{root}{name}/")

# PART C — named guesses -------------------------------------------------------
print()
print("-" * 78)
print("PART C — candidates (only meaningful next to PART B)")
print("-" * 78)
candidates = [
    f"{ISAAC_NUCLEUS_DIR}/Robots/Robotiq/2F-85/Robotiq_2F_85.usd",
    f"{ISAAC_NUCLEUS_DIR}/Robots/Robotiq/2F-85/Robotiq_2F_85_base_link.usd",
    f"{ISAAC_NUCLEUS_DIR}/Robots/Robotiq/2F-85/2f85_instanceable.usd",
    f"{ISAAC_NUCLEUS_DIR}/Robots/Robotiq/2F-140/Robotiq_2F_140.usd",
    f"{ISAACLAB_NUCLEUS_DIR}/Robots/Robotiq/2F-85/Robotiq_2F_85.usd",
]
for path in candidates:
    show("CAND", path)

# Any candidate that exists: report its variants too — a coupled asset may expose them.
print()
for path in candidates:
    if check_file_path(path) != 0:
        show_variants(path)

print()
print("=" * 78)
print("DECIDES the 2F-85 fidelity route:")
print("  ur5e.usd Gripper variant lists a Robotiq value")
print("      -> BEST. Coupling already authored by NVIDIA. Spawn with variants={'Gripper': ...}.")
print("  standalone 2F-85 USD found, no variant on ur5e.usd")
print("      -> GOOD. Mount it the same way as the RH-P12-RN, then run the pad-force test.")
print("  nothing found")
print("      -> FALL BACK to coupled-tree drive: import the URDF, break the loop, and drive all")
print("         finger joints from ONE command through the real transmission ratio.")
print()
print("NONE of these outcomes is a passing gripper. The pad-force test decides that:")
print("  close on the 0.0480 m DexCube and MEASURE pad separation + contact force.")
print("  (0.0480 m = 0.06000 m raw x env scale 0.8, MEASURED by drop test 2026-07-28,")
print("   logbook/02_measure_dexcube.log. The archive's 0.0412 m is wrong by 8.5 mm raw.)")
print("  Timebox for the whole 2F-85 attempt: ONE day. Failure closes it as a negative result.")
print("=" * 78)

simulation_app.close()
