# Copyright (c) 2026, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Build + validate a single-articulation UR5e + Robotiq 2F-85 USD.  Module 02, STEP 6.

THE SECOND GRIPPER. The RH-P12-RN is the Layer 1 critical path; the 2F-85 is the
literature-comparability gripper. Nothing here may block Layer 1.

--------------------------------------------------------------------------------------
WHY THIS IS NOT A REPEAT OF THE ARCHIVE'S FAILURE
--------------------------------------------------------------------------------------
PROJECT_INSTRUCTIONS §9 rejects the 2F-85, and the previous attempt did fail on it. But
read WHAT failed, because it is specific and it is avoidable.

  §9's stated objection is against the URDF ROUTE. Each 2F-85 finger is a closed four-bar
  linkage. A URDF is a tree and cannot express a loop, so every public 2F-85 URDF breaks
  the loop and papers over it with <mimic> tags, which Isaac Lab 2.3 does not honour
  (issue #2424, discussion #2626). THIS SCRIPT DOES NOT TOUCH A URDF. It uses the
  NVIDIA-authored USD variant already inside `ur5e.usd`, where the loop is rigged in USD
  and has no tree restriction.

  The archive's actual failure was narrower and is recorded in its own
  `Thesis_Documentation/07_Troubleshooting.md`: it drove `finger_joint` alone and left the
  other five finger joints PASSIVE (stiffness 0), expecting the mechanical loop to carry
  them. The pads then transmitted no normal force and the cube fell straight through a
  visually closed gripper. Raising finger stiffness 20 -> 400 and effort 50 -> 200 did not
  help. It fell back to a proximity WELD — a fake gripper — and every headline number in
  that thesis was measured with it.

  The reason the passive approach cannot work is documented upstream: Isaac Sim resolves
  closed-loop kinematics automatically through USD schemas, but **Isaac Lab requires every
  mimic joint to be fully specified in the ArticulationCfg**. A joint Isaac Lab was never
  told about is not coupled — it is limp.

  So this build DRIVES ALL SIX finger joints from ONE scalar through an explicit sign
  table. That is not a new idea: it is exactly the pattern that already worked in THIS
  folder on the RH-P12-RN, where four coupled joints sharing one scalar target reproduced
  the ROBOTIS published 106.0 mm stroke to +0.4 mm (`logbook/02_make_ur5e_rhp12.log`).

--------------------------------------------------------------------------------------
WHAT THIS SCRIPT MEASURES, AND WHY IT MEASURES RATHER THAN ARGUES
--------------------------------------------------------------------------------------
Day 4's methodological result, in one line from `run_log.md`: *five geometric predictions,
all wrong, every one an inference from joint origins and a screenshot; the two things that
advanced the diagnosis were a control run and measuring the geometry directly.*

So nothing below is assumed:

  PHASE A  variant discovery      — does `ur5e.usd` on THIS Isaac Sim version carry a
                                    Gripper variant, and what is it called?
  PHASE B  build                  — author the wrapper USD, disable the nested root
  PHASE C  topology               — ONE articulation; joint and body names printed
  PHASE D  mimic sign table       — the six-joint coupling is TESTED, not assumed. Each
                                    candidate table is swept and scored on whether the
                                    pads actually converge.
  PHASE E  free-space link sweep  — closest approach of EVERY finger body to the
                                    centreline, at every q. This is the measurement whose
                                    absence cost Day 4 six runs on the RH-P12-RN, where
                                    the proximal links turned out to reach the object
                                    before the pads did. It is cheap. It runs first here.
  PHASE F  stroke check           — open clear opening against Robotiq's published 85 mm.

An external number is the point of PHASE F. Robotiq publishes for the 2F-85:
    Stroke              85 mm
    Gripping force      20 - 235 N
    Rated payload       5 kg
    Closing speed       20 - 150 mm/s
Source: https://robotiq.com/products/adaptive-grippers (2F-85 specifications)

--------------------------------------------------------------------------------------
WHAT A PASS HERE DOES AND DOES NOT MEAN
--------------------------------------------------------------------------------------
A PASS means the gripper is mounted, coupled, and sweeps the published stroke in FREE
SPACE. It says NOTHING about whether a grasp holds. The archive's gripper would have
passed every check in this file and still dropped the cube, because free-space geometry
cannot see contact force. `grasp_hold_test.py --gripper robotiq85` decides that, and the
§9 failure mode has a name there: pads visibly touching, contact force ~0 N.

--------------------------------------------------------------------------------------
RUN (lab PC, ~5 min)
--------------------------------------------------------------------------------------
    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_robotiq_usd.py --headless \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_make_ur5e_robotiq.log

CONFIRM FROM THE HEADER BEFORE LETTING IT RUN:
    ISAAC_NUCLEUS_DIR ends in `/Isaac/5.0/Isaac`   <- the frozen stack. The archive read
      this asset from 5.1. If the line says 5.1 the environment is not the frozen one and
      every number below belongs to a different asset release.
    PHASE A prints `Gripper` with a Robotiq option. If it does not, STOP — the variant
      route is gone on this version and the fallback is a different day's work.
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Build + validate the UR5e + Robotiq 2F-85 USD.")
parser.add_argument("--steps", type=int, default=25, help="sweep resolution over the stroke")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below needs the app running ---------------------------------------
import os  # noqa: E402

import torch  # noqa: E402
from pxr import PhysxSchema, Usd, UsdGeom, UsdPhysics  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.actuators import ImplicitActuatorCfg  # noqa: E402
from isaaclab.assets import Articulation, ArticulationCfg  # noqa: E402
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.normpath(os.path.join(HERE, ".."))
ROOT_DIR = os.path.normpath(os.path.join(PKG_DIR, ".."))
ASSETS_DIR = os.path.join(PKG_DIR, "assets")

OUT_USD = os.path.join(ASSETS_DIR, "ur5e_robotiq_2f85.usd")
REPORT_PATH = os.path.join(ROOT_DIR, "logbook", "02_make_ur5e_robotiq.log")

SRC_USD = f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd"

# Variant selections. The archive recorded `Gripper=[None, Robotiq_2f_85]` on Isaac 5.1;
# PHASE A re-reads them here because we are frozen on 5.0 and a renamed option must not be
# silently swallowed by a `if name in ...` guard.
WANT_VARIANTS = {"Physics": "PhysX", "Gripper": "Robotiq_2f_85", "Sensor": "None"}

# The gripper's OWN articulation root, which must be disabled so arm + gripper load as one.
GRIPPER_ROOT_NAME = "Robotiq_2F_85"

##
# Joint coupling.
#
# `finger_joint` is the single real actuator. The other five follow it through the linkage.
# The signs below are the standard 2F-85 mimic table (inner fingers counter-rotate to keep
# the pad faces parallel), but they are CANDIDATES, not facts — PHASE D sweeps each table
# and keeps whichever actually makes the pads converge. If the kept table is not
# CANDIDATE_TABLES[0], say so in the logbook: it means NVIDIA's joint axes differ from the
# ros-industrial URDF convention, which is worth a line in 07_Troubleshooting.md.
##

DRIVE_JOINT = "finger_joint"

CANDIDATE_TABLES = [
    # name, {joint: multiplier of the drive angle}
    (
        "standard-mimic",
        {
            "finger_joint": +1.0,
            "right_outer_knuckle_joint": +1.0,
            "left_inner_finger_knuckle_joint": +1.0,
            "right_inner_finger_knuckle_joint": +1.0,
            "left_inner_finger_joint": -1.0,
            "right_inner_finger_joint": -1.0,
        },
    ),
    (
        "mirrored-right",
        {
            "finger_joint": +1.0,
            "right_outer_knuckle_joint": -1.0,
            "left_inner_finger_knuckle_joint": +1.0,
            "right_inner_finger_knuckle_joint": -1.0,
            "left_inner_finger_joint": -1.0,
            "right_inner_finger_joint": +1.0,
        },
    ),
]

# Pad bodies — the surfaces that are SUPPOSED to do the gripping.
# Named here so PHASE E can prove or disprove it. On the RH-P12-RN this exact assumption
# was wrong and went unchecked for two days, so it is now a hypothesis with a test.
PAD_BODIES = ["left_inner_finger", "right_inner_finger"]

Q_OPEN = 0.0
Q_CLOSE = 0.8  # finger_joint travel: 0 = open, ~0.8 rad = closed

# Topology expected from the archive's build of the same variant (12 joints / 16 bodies).
# A MISMATCH IS NOT AUTOMATICALLY A FAILURE — it is an Isaac 5.0-vs-5.1 asset difference
# and must be recorded, not tuned away.
EXPECT_JOINTS = 12
EXPECT_BODIES = 16

DATASHEET_STROKE_M = 0.085
STROKE_TOL_M = 0.004

_FH = open(REPORT_PATH, "w")
_BOUNDS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {}


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


def find_prim_by_name(stage: Usd.Stage, root: str, name: str) -> Usd.Prim | None:
    """Depth-first search for a prim whose name matches exactly.

    Prim paths differ between asset releases, so searching by name is the only stable way
    to reach the gripper root. NOTE the landmine recorded on 2026-07-28: `Usd.PrimRange`
    silently skips instance proxies, so a traversal that finds nothing is not evidence the
    prim is absent. `Usd.TraverseInstanceProxies` is used for that reason.
    """
    start = stage.GetPrimAtPath(root)
    if not start or not start.IsValid():
        return None
    for prim in Usd.PrimRange(start, Usd.TraverseInstanceProxies()):
        if prim.GetName() == name:
            return prim
    return None


def rotate_into_body_frame(vec_w: torch.Tensor, quat_w: torch.Tensor) -> torch.Tensor:
    """Express a world-frame vector in a body's local frame.

    Written out rather than imported because the helper's name moved between Isaac Lab
    releases (quat_rotate_inverse -> quat_apply_inverse).
    """
    w = quat_w[0]
    u = quat_w[1:]
    t = torch.linalg.cross(u, vec_w)
    return vec_w - 2.0 * w * t + 2.0 * torch.linalg.cross(u, t)


def local_bounds(body: str):
    """Local-frame AABB (min, max) of a link's geometry, in the frame body_pos_w reports."""
    if body not in _BOUNDS:
        stage = Usd.Stage.Open(OUT_USD)
        prim = find_prim_by_name(stage, str(stage.GetDefaultPrim().GetPath()), body)
        if prim is None:
            return None
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
        rng = cache.ComputeUntransformedBound(prim).ComputeAlignedRange()
        mn, mx = rng.GetMin(), rng.GetMax()
        _BOUNDS[body] = ((mn[0], mn[1], mn[2]), (mx[0], mx[1], mx[2]))
    return _BOUNDS[body]


def support(direction_local: torch.Tensor, body: str) -> float:
    """How far the link's geometry reaches from its own origin along `direction_local`.

    The box SUPPORT in direction d: take each coordinate from the max corner where d is
    positive and the min corner where it is negative.

        s(d) = sum_i  d_i * (d_i > 0 ? max_i : min_i)

    NOT `size / 2` — that is the half-width, and is only the reach from the origin if the
    box is CENTRED on the origin, which a link origin sitting on a joint axis is not. That
    bug produced a 92.4 mm opening against a 106 mm datasheet on the RH-P12-RN.

    CAVEAT, and it is the one that withdrew a Day 4 conclusion: an AABB around a CURVED
    link reports its inner face at every height, including where the real link has swung
    outboard. Every number from this function is therefore an UPPER bound on reach, i.e. a
    LOWER bound on clearance. Safe for the OPEN gap (reads too small, conservative);
    optimistic for the CLOSED gap. Do not read a passing closed check as proof the pads
    meet — that is what contact force is for.
    """
    b = local_bounds(body)
    if b is None:
        return float("nan")
    mn, mx = b
    d = direction_local.cpu().tolist()
    return float(sum(d[i] * (mx[i] if d[i] > 0.0 else mn[i]) for i in range(3)))


# ---------------------------------------------------------------------------------
# PHASE A — variant discovery
# ---------------------------------------------------------------------------------
def discover_variants() -> dict[str, list[str]]:
    log("-" * 82)
    log("PHASE A — variant sets on the stock ur5e.usd")
    log("-" * 82)
    log(f"    source: {SRC_USD}")
    stage = Usd.Stage.Open(SRC_USD)
    if stage is None:
        log("    !! could not open the source stage — asset server unreachable. STOP.")
        return {}
    found: dict[str, list[str]] = {}
    for prim in stage.Traverse():
        vsets = prim.GetVariantSets()
        for vs_name in vsets.GetNames():
            options = list(vsets.GetVariantSet(vs_name).GetVariantNames())
            found[vs_name] = options
            log(f"    {prim.GetPath()}")
            log(f"        set '{vs_name}'  options={options}")
    if not found:
        log("    (no variant sets found on any prim)")
    log("")
    gripper_opts = found.get("Gripper", [])
    if not gripper_opts:
        log("    VERDICT: no Gripper variant set on this asset release. The variant route is")
        log("             CLOSED on Isaac Sim 5.0. Do not improvise — close the 2F-85 as a")
        log("             documented negative result and keep Layer 1 on the RH-P12-RN.")
    elif WANT_VARIANTS["Gripper"] not in gripper_opts:
        log(f"    VERDICT: Gripper variant exists but '{WANT_VARIANTS['Gripper']}' is not among")
        log(f"             {gripper_opts}. Update WANT_VARIANTS to the real name and re-run.")
        log("             ONE knob. Do not also change the sign table in the same run.")
    else:
        log(f"    VERDICT: '{WANT_VARIANTS['Gripper']}' is present. Proceeding to build.")
    return found


# ---------------------------------------------------------------------------------
# PHASE B — author the wrapper USD
# ---------------------------------------------------------------------------------
def build_usd() -> bool:
    """Reference ur5e.usd, select the gripper variant, disable the gripper's nested root.

    Isaac Lab requires exactly ONE articulation per robot. The stock asset declares an
    articulation root on the gripper next to the arm's own root, so it refuses to load.
    Removing the gripper's root lets PhysX fold the gripper bodies into the arm
    articulation across the existing fixed mount joint.
    """
    log("-" * 82)
    log("PHASE B — authoring the wrapper USD")
    log("-" * 82)
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if os.path.exists(OUT_USD):
        os.remove(OUT_USD)

    stage = Usd.Stage.CreateNew(OUT_USD)
    robot = UsdGeom.Xform.Define(stage, "/Robot").GetPrim()
    robot.GetReferences().AddReference(SRC_USD)
    stage.SetDefaultPrim(robot)

    vsets = robot.GetVariantSets()
    available = set(vsets.GetNames())
    for name, sel in WANT_VARIANTS.items():
        if name not in available:
            log(f"    variant {name:<8} -> NOT PRESENT on this asset (skipped)")
            continue
        vsets.GetVariantSet(name).SetVariantSelection(sel)
        log(f"    variant {name:<8} -> {sel}")

    grip = find_prim_by_name(stage, "/Robot", GRIPPER_ROOT_NAME)
    if grip is None:
        log(f"    !! gripper prim '{GRIPPER_ROOT_NAME}' not found under /Robot.")
        log("       The variant selection did not take, or the prim is named differently on")
        log("       this asset release. Aborting the build rather than writing a broken USD.")
        return False

    log(f"    gripper root prim: {grip.GetPath()}")
    removed = grip.RemoveAPI(UsdPhysics.ArticulationRootAPI)
    log(f"    removed UsdPhysics.ArticulationRootAPI: {removed}")
    # Belt and suspenders: some releases keep the PhysX schema alive independently.
    PhysxSchema.PhysxArticulationAPI.Apply(grip).CreateArticulationEnabledAttr(False)
    log("    set physxArticulation:articulationEnabled = False")

    stage.GetRootLayer().Save()
    log(f"    wrote {OUT_USD}")
    log("")
    return True


# ---------------------------------------------------------------------------------
# PHASES C-F — spawn and measure
# ---------------------------------------------------------------------------------
def validate() -> None:
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1.0 / 120.0, device=args_cli.device))
    sim_utils.GroundPlaneCfg().func("/World/ground", sim_utils.GroundPlaneCfg())
    sim_utils.DomeLightCfg(intensity=2000.0).func("/World/Light", sim_utils.DomeLightCfg(intensity=2000.0))

    robot = Articulation(
        ArticulationCfg(
            prim_path="/World/Robot",
            spawn=sim_utils.UsdFileCfg(usd_path=OUT_USD),
            # Blanket actuator ON PURPOSE. Every quantity below is a distance between two
            # bodies of the SAME robot, so arm droop under these gains cancels out. The
            # tuned per-group gains live in the ArticulationCfg and are not what this
            # script tests.
            actuators={
                "all": ImplicitActuatorCfg(
                    joint_names_expr=[".*"], stiffness=400.0, damping=40.0, armature=0.01
                )
            },
        )
    )
    sim.reset()

    # ---- PHASE C: topology ----
    log("-" * 82)
    log("PHASE C — topology")
    log("-" * 82)
    log(f"    num joints : {robot.num_joints}   (archive on Isaac 5.1 saw {EXPECT_JOINTS})")
    log(f"    joint names: {list(robot.joint_names)}")
    log(f"    num bodies : {robot.num_bodies}   (archive on Isaac 5.1 saw {EXPECT_BODIES})")
    log(f"    body names : {list(robot.body_names)}")
    topology_ok = robot.num_joints == EXPECT_JOINTS and robot.num_bodies == EXPECT_BODIES
    if not topology_ok:
        log("    NOTE: counts differ from the archive. That is an asset-release difference,")
        log("          NOT a defect to tune away. Record it and read the names below as the")
        log("          authoritative input to the ArticulationCfg.")
    log("")

    names = list(robot.joint_names)
    missing = [j for j in CANDIDATE_TABLES[0][1] if j not in names]
    if missing:
        log(f"    !! these expected finger joints are absent: {missing}")
        log("       The sign tables are written against the archive's names. Fix the names")
        log("       from the list above before reading PHASE D as evidence of anything.")
    body_names = list(robot.body_names)
    finger_bodies = [b for b in body_names if any(k in b for k in ("finger", "knuckle"))]
    log(f"    finger/knuckle bodies: {finger_bodies}")
    log(f"    PAD_BODIES hypothesis: {PAD_BODIES}  <- PHASE E tests this, it is not a fact")
    log("")

    def drive_to(table: dict[str, float], q: float) -> None:
        """Command every coupled joint from ONE scalar and settle."""
        targets = robot.data.joint_pos.clone()
        for jname, mult in table.items():
            if jname in names:
                targets[:, names.index(jname)] = mult * q
        for _ in range(60):
            robot.set_joint_position_target(targets)
            robot.write_data_to_sim()
            sim.step()
            robot.update(sim.get_physics_dt())

    def pad_origin_gap() -> float:
        i = [body_names.index(b) for b in PAD_BODIES if b in body_names]
        if len(i) != 2:
            return float("nan")
        p = robot.data.body_pos_w[0]
        return float(torch.linalg.norm(p[i[0]] - p[i[1]]))

    # ---- PHASE D: which sign table actually closes the gripper? ----
    log("-" * 82)
    log("PHASE D — mimic sign table, TESTED not assumed")
    log("-" * 82)
    log("    A table is correct only if the pads MOVE TOGETHER as q rises. A table that")
    log("    opens them, or moves them by ~nothing, is the linkage fighting itself.")
    log("")
    log(f"    {'table':<18} {'gap@open':>10} {'gap@close':>10} {'delta':>10}  verdict")

    best_name, best_table, best_delta = None, None, 0.0
    for tname, table in CANDIDATE_TABLES:
        drive_to(table, Q_OPEN)
        g_open = pad_origin_gap()
        drive_to(table, Q_CLOSE)
        g_close = pad_origin_gap()
        delta = g_open - g_close
        verdict = "closes" if delta > 0.005 else ("opens" if delta < -0.005 else "no motion")
        log(f"    {tname:<18} {g_open:>10.4f} {g_close:>10.4f} {delta:>10.4f}  {verdict}")
        if delta > best_delta:
            best_name, best_table, best_delta = tname, table, delta
    log("")

    if best_table is None:
        log("    RESULT: NO candidate table closes the gripper. STOP — do not tune gains.")
        log("            This is the §9 failure arriving at the kinematic level, and it is a")
        log("            legitimate negative result. Close the 2F-85 with a header banner.")
        log("")
        return
    log(f"    KEPT: '{best_name}' (pads converge by {best_delta * 1000:.1f} mm)")
    if best_name != CANDIDATE_TABLES[0][0]:
        log("    NOTE: this is NOT the ros-industrial convention. NVIDIA's joint axes differ.")
        log("          Worth a line in 07_Troubleshooting.md and in the methods chapter.")
    log("")

    # ---- PHASE E: free-space link geometry ----
    log("-" * 82)
    log("PHASE E — free space: how close does EVERY finger link come to the centreline?")
    log("-" * 82)
    log("    No cube, no contact. This is the measurement whose absence cost Day 4 six runs")
    log("    on the RH-P12-RN, where the PROXIMAL links reached the object before the pads.")
    log("    Smallest number in a row = the link a centred object meets FIRST at that q.")
    log("    All values are half-approach in metres; clear opening = 2 x the minimum.")
    log("")

    wrist_i = body_names.index("wrist_3_link") if "wrist_3_link" in body_names else 0
    probe_bodies = [b for b in finger_bodies if b in body_names]

    # Closing axis, measured: the line joining the two pad origins at full open.
    drive_to(best_table, Q_OPEN)
    pi = [body_names.index(b) for b in PAD_BODIES if b in body_names]
    if len(pi) != 2:
        log("    !! cannot resolve both PAD_BODIES — skipping PHASE E/F.")
        return
    p = robot.data.body_pos_w[0]
    axis_w = p[pi[1]] - p[pi[0]]
    axis_w = axis_w / torch.linalg.norm(axis_w)
    centre_w = 0.5 * (p[pi[0]] + p[pi[1]])
    log(f"    closing axis (world, at open): {[round(float(v), 4) for v in axis_w]}")
    log("")

    header = "    " + f"{'q':>6}" + "".join(f"{b[:13]:>15}" for b in probe_bodies)
    log(header)

    qs = [Q_OPEN + (Q_CLOSE - Q_OPEN) * k / (args_cli.steps - 1) for k in range(args_cli.steps)]
    rows = []
    for q in qs:
        drive_to(best_table, q)
        p = robot.data.body_pos_w[0]
        quat = robot.data.body_quat_w[0]
        centre = 0.5 * (p[pi[0]] + p[pi[1]])
        row = []
        for b in probe_bodies:
            bi = body_names.index(b)
            # Which side of the centreline is this link on? Point the support query INWARD.
            side = torch.dot(p[bi] - centre, axis_w)
            inward_w = -axis_w if side > 0 else axis_w
            inward_l = rotate_into_body_frame(inward_w, quat[bi])
            reach = support(inward_l, b)
            # Distance from the centreline plane to the link's innermost geometry.
            row.append(abs(float(side)) - reach)
        rows.append((q, row))
        log("    " + f"{q:>6.3f}" + "".join(f"{v:>15.4f}" for v in row))
    log("")

    # Which link is the innermost one, and where?
    inner_counts = {b: 0 for b in probe_bodies}
    for _, row in rows:
        vals = [(v, b) for v, b in zip(row, probe_bodies) if v == v]  # drop NaN
        if vals:
            inner_counts[min(vals)[1]] += 1
    ranked = sorted(inner_counts.items(), key=lambda kv: -kv[1])
    log(f"    innermost link, by count over the stroke: {ranked}")
    pads_lead = all(b in PAD_BODIES for b, c in ranked[:2] if c > 0)
    if pads_lead:
        log("    -> the PADS are the innermost surface. PAD_BODIES is confirmed by measurement.")
    else:
        log("    -> a NON-PAD link is innermost over part of the stroke. Any object wider than")
        log("       twice that link's clearance is captured by the THROAT, not the pads —")
        log("       exactly the RH-P12-RN result. Set the cube size from this table, and say")
        log("       so in the methods chapter: object size fixed by measured kinematics.")
    log("")

    # ---- PHASE F: stroke against the datasheet ----
    log("-" * 82)
    log("PHASE F — open clear opening vs Robotiq published 85 mm")
    log("-" * 82)
    pad_rows = [(q, [v for v, b in zip(row, probe_bodies) if b in PAD_BODIES]) for q, row in rows]
    open_clear = 2.0 * min(pad_rows[0][1]) if pad_rows[0][1] else float("nan")
    close_clear = 2.0 * min(pad_rows[-1][1]) if pad_rows[-1][1] else float("nan")
    log(f"    pad clear opening, q={Q_OPEN:.2f} : {open_clear:.4f} m  ({open_clear * 1000:.1f} mm)")
    log(f"    pad clear opening, q={Q_CLOSE:.2f} : {close_clear:.4f} m  ({close_clear * 1000:.1f} mm)")
    log(f"    Robotiq published stroke        : {DATASHEET_STROKE_M:.4f} m  (85.0 mm)")
    err = abs(open_clear - DATASHEET_STROKE_M)
    log(f"    error                           : {(open_clear - DATASHEET_STROKE_M) * 1000:+.1f} mm")
    log("")

    # ---- verdict ----
    monotonic = all(
        min(pad_rows[k][1]) >= min(pad_rows[k + 1][1]) - 1e-4 for k in range(len(pad_rows) - 1)
    )
    checks = [
        (topology_ok, f"topology matches the archive ({EXPECT_JOINTS} joints / {EXPECT_BODIES} bodies)"),
        (not missing, "every expected finger joint is present on the articulation"),
        (best_delta > 0.005, "a sign table exists that actually closes the gripper"),
        (monotonic, "pad clearance decreases monotonically over the stroke"),
        (close_clear < open_clear, "the gripper is narrower closed than open"),
        (err <= STROKE_TOL_M, f"open clear opening within {STROKE_TOL_M * 1000:.0f} mm of 85.0 mm"),
        (pads_lead, "the pads, not a proximal link, are the innermost surface"),
    ]
    log("-" * 82)
    log("VERDICT")
    log("-" * 82)
    for ok, label in checks:
        log(f"      [{'PASS' if ok else 'FAIL'}]  {label}")
    n_pass = sum(1 for ok, _ in checks if ok)
    log("")
    log(f"    {n_pass}/{len(checks)} PASS")
    if n_pass == len(checks):
        log("    RESULT: PASS — mounted, coupled, and sweeping the published stroke IN FREE")
        log("            SPACE. This is NOT a passed gripper. The archive's 2F-85 would have")
        log("            passed every line above and still dropped the cube, because free")
        log("            space cannot see contact force. Next: grasp_hold_test.py, and the")
        log("            failure to watch for is pads touching at ~0 N.")
    else:
        log("    RESULT: FAIL — see the failed lines. Change ONE knob and re-run. Never two.")
    log("")


def main() -> None:
    log("=" * 82)
    log("BUILD + VALIDATE  ur5e_robotiq_2f85.usd   (Module 02, STEP 6 — second gripper)")
    log("=" * 82)
    log(f"ISAAC_NUCLEUS_DIR : {ISAAC_NUCLEUS_DIR}")
    log("    ^ CONFIRM THIS SAYS 5.0. The archive read this asset from 5.1; a 5.1 path means")
    log("      the environment is not the frozen stack and these numbers are a different asset.")
    log(f"source USD        : {SRC_USD}")
    log(f"output USD        : {OUT_USD}")
    log("")

    variants = discover_variants()
    if "Gripper" not in variants or WANT_VARIANTS["Gripper"] not in variants.get("Gripper", []):
        log("STOPPING at PHASE A. See the verdict above.")
        return

    if not build_usd():
        log("STOPPING at PHASE B. See the message above.")
        return

    try:
        validate()
    except Exception:  # noqa: BLE001
        import traceback

        log("    !! validation FAILED — traceback below:")
        log(traceback.format_exc())

    log(f"[report saved to {REPORT_PATH}]")


if __name__ == "__main__":
    try:
        main()
    finally:
        _FH.close()
        simulation_app.close()
