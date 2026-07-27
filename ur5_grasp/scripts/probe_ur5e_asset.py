"""Probe: does a UR5e USD exist in the Nucleus asset library?

Module 02 / STEP 2. Isaac Lab 2.3.0 ships no UR5 or UR5e config and contains no UR5
asset reference anywhere in `source/` (verified by grep, 2026-07-27). So the arm must
come from somewhere else. This script asks the asset server directly instead of guessing.

Run (from the IsaacLab clone, ~2 min):

    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/scripts/probe_ur5e_asset.py \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_probe_ur5e_asset.log

READ THE OUTPUT IN THIS ORDER:

  1. CONTROL — a path Isaac Lab itself ships and uses (the UR10e cfg). It must come back
     `on Nucleus`. If the control is MISSING, the server is simply unreachable and every
     other line below is noise, not evidence.
  2. LISTING — the ground truth: what is actually in the UniversalRobots folders.
  3. CANDIDATES — named guesses. Only meaningful read next to the listing.

The listing decides STEP 2. The candidates are a convenience, not the answer.
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Probe the Nucleus asset library for a UR5e USD.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
# no GUI needed — this only talks to the asset server
args_cli.headless = True

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below needs the app running (carb settings + omni.client) ---
import omni.client  # noqa: E402

from isaaclab.utils.assets import (  # noqa: E402
    ISAAC_NUCLEUS_DIR,
    ISAACLAB_NUCLEUS_DIR,
    NUCLEUS_ASSET_ROOT_DIR,
    check_file_path,
)

STATUS = {0: "MISSING", 1: "local", 2: "on Nucleus"}


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


print("=" * 78)
print("UR5e ASSET PROBE  —  Module 02, STEP 2")
print("=" * 78)
print(f"NUCLEUS_ASSET_ROOT_DIR : {NUCLEUS_ASSET_ROOT_DIR}")
print(f"ISAAC_NUCLEUS_DIR      : {ISAAC_NUCLEUS_DIR}")
print(f"ISAACLAB_NUCLEUS_DIR   : {ISAACLAB_NUCLEUS_DIR}")
print()

# 1. CONTROL ------------------------------------------------------------------
# Taken verbatim from UR10e_CFG in isaaclab_assets/robots/universal_robots.py.
# If this is MISSING, stop reading — the server is unreachable, not the asset absent.
show("CONTROL", f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur10e/ur10e.usd")

# 2. GROUND TRUTH -------------------------------------------------------------
roots = [
    f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/",
    f"{ISAACLAB_NUCLEUS_DIR}/Robots/UniversalRobots/",
]
for root in roots:
    for name in listdir(root):
        # if anything looks like a UR5, open it up — one round trip, not two
        if "5" in name.lower() and "ur" in name.lower():
            listdir(f"{root}{name}/")

# 3. CANDIDATES ---------------------------------------------------------------
print()
candidates = [
    f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd",
    f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5/ur5.usd",
    f"{ISAAC_NUCLEUS_DIR}/Robots/UR5e/ur5e.usd",
    f"{ISAACLAB_NUCLEUS_DIR}/Robots/UniversalRobots/UR5e/ur5e_instanceable.usd",
    f"{ISAACLAB_NUCLEUS_DIR}/Robots/UniversalRobots/UR5/ur5_instanceable.usd",
]
for path in candidates:
    show("CAND", path)

print()
print("=" * 78)
print("DECIDES: a UR5e path found here -> STEP 3 writes ur5e_cfg.py against it.")
print("         nothing found          -> fall back to importing the official UR5e URDF")
print("                                   with IsaacLab/scripts/tools/convert_urdf.py.")
print("=" * 78)

simulation_app.close()
