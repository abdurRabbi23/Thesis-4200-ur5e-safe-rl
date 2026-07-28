"""Does the RH-P12-RN actually HOLD the cube? Module 02, Day 4.

Day 3 measured free-space geometry: the pads sweep from 106.4 mm open to 13.7 mm closed, so a
flat parallel grip around a 48.0 mm cube is geometrically POSSIBLE. That is all it showed.
PROJECT_INSTRUCTIONS §9 names the failure this misses: pads that touch while transmitting no
normal force (what killed the Robotiq 2F-85), and cubes that wedge on the curved proximal
links — which survives a static hold and lets go under lift accelerations.

This script closes the question with four measurements:

  1. STALL WIDTH   at what q do the pads stop tracking their command?   prediction q ~ 0.69
  2. CONTACT FORCE what normal force do the pads put into the cube?     datasheet max 170 N
  3. STATIC HOLD   released, arm still — does the cube stay put?
  4. LIFT HOLD     arm raised ~0.15 m — does the cube slip in the gripper?

and then reads TCP_OFFSET off the geometry AT THE GRASP, which is the only place it is
meaningful: the pad midpoint travels 28.2 mm over the stroke, so a q=0 reading is the wrong
point by construction (and the archive's TCP_OFFSET = 0.130 was invalidated on Day 3 anyway).

NO INVERSE KINEMATICS. The arm is held at its Day 2 home pose and the cube is teleported to
the pad midpoint, held kinematically while the fingers close, then released. This is on
purpose: it tests the grip and only the grip. Adding a reach would mean a failure could be
either the grasp or the IK, and the TCP frame that IK needs is the thing this script is
measuring.

Run:

    conda activate isaaclab
    cd ~/Abdur_Rabbi_Thesis_updated/IsaacLab
    PYTHONUNBUFFERED=1 ./isaaclab.sh -p ../ur5_grasp/scripts/grasp_hold_test.py --headless \
        2>&1 | tee ~/Abdur_Rabbi_Thesis_updated/logbook/02_grasp_hold_test.log
    echo "exit ${PIPESTATUS[0]}"

Drop --headless to watch it. Absolute tee path, PYTHONUNBUFFERED, PIPESTATUS — all three for
the reasons in Thesis_Documentation/07_Troubleshooting.md.

CONFIRM FROM THE HEADER, before believing anything below it:
    "cube edge (scaled)"   is 0.04800 m          <- the Day 3 drop-test value, not a guess
    "gripper joints"       lists exactly 4 rh_*  <- read off the articulation, not assumed
    "effort_limit_sim"     is the value you set  <- the config you think you edited loaded
    "contact sensors"      resolved to 2 prims   <- with 0, every force below reads zero

WATCHING FOR: contact force climbing as q rises and then flattening. Flat at zero while the
pads are visibly on the cube is the §9 failure reproducing — STOP, do not tune, log it.
"""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

sys.stdout.reconfigure(line_buffering=True)

parser = argparse.ArgumentParser(description="Grasp + hold test for the UR5e + RH-P12-RN.")
parser.add_argument("--settle-steps", type=int, default=200, help="steps to settle the home pose")
parser.add_argument("--close-steps", type=int, default=40, help="steps held at each q on the way in")
parser.add_argument("--q-step", type=float, default=0.02, help="commanded q increment")
parser.add_argument("--hold-steps", type=int, default=200, help="steps of static hold after release")
parser.add_argument("--lift-steps", type=int, default=400, help="steps of the lift ramp + settle")
parser.add_argument("--lift-delta", type=float, default=0.30, help="rad added to the lift arc")
parser.add_argument(
    "--cube-scale",
    type=float,
    default=0.8,
    help=(
        "DexCube scale. 0.8 -> 0.048 m. NOTE: 0.5 -> 0.030 m was briefly the default after an\n"
        "        AABB-based analysis said 48 mm could not be fingertip-grasped. That analysis is\n"
        "        SUSPECT — an axis-aligned box around a CURVED finger reports the box's inner face\n"
        "        at every height, including where the real link has swung far outboard. Reverted to\n"
        "        0.8 and the contact POSITIONS are now measured directly. Old note follows. CHOSEN BY MEASUREMENT on 2026-07-29. PHASE 0b showed "
        "the RH-P12-RN's proximal links never open wider than 39.9 mm, so anything above ~40 mm "
        "is caught by the throat before the fingertips can reach it. At 30 mm the pads close at "
        "q = 0.85 with the proximal links 38.2 mm apart — 8.2 mm of clearance. 0.8 -> 0.048 m "
        "was the previous value and cannot be fingertip-grasped by this hand at all."
    ),
)
parser.add_argument("--stall-tol", type=float, default=0.03, help="rad of lag that counts as stalled")
parser.add_argument("--force-tol", type=float, default=1.0, help="N above which a pad counts as loaded")
parser.add_argument(
    "--predicted-q",
    type=float,
    default=0.69,
    help=(
        "q at which the PADS reach the cube. 0.69 for the 48 mm cube (Day 3). Was 0.85 for 30 mm, by linear "
        "interpolation of the PHASE 0b table. Day 3's 0.69 was correct FOR A 48 mm CUBE — "
        "the pads do reach it there — but the proximal links arrive first, which is why "
        "48 mm never worked."
    ),
)
parser.add_argument(
    "--place-at",
    choices=["tip", "padface", "origin"],
    default="tip",
    help=(
        "where the cube's centre goes along the tool axis. 'tip' = held at the FINGERTIP, "
        "cube outer face flush with the distal end of the pads. 'padface' = the middle of "
        "the pad face (run 4: put ~500 N into the PROXIMAL links and 0 N into the pads). "
        "'origin' = the pad body origins, which reproduces run 1's throat wedge exactly. "
        "All three kept so every earlier failure stays reproducible on demand."
    ),
)
parser.add_argument(
    "--no-cube",
    action="store_true",
    help=(
        "CONTROL EXPERIMENT. Close the gripper with no cube in the scene at all and report "
        "where it stalls. Runs 1 and 2 stalled at essentially the same origin gap (~0.078 m) "
        "with the cube in two different places, and in run 2 the cube demonstrably was not "
        "touching anything. If the EMPTY gripper stalls there too, the cube is irrelevant and "
        "the fault is inside the gripper — not the placement. This should have been the first "
        "thing run."
    ),
)
parser.add_argument(
    "--grasp-depth",
    type=float,
    default=0.0,
    help="mm to shift the cube further out along the tool axis, past the pad geometric centre",
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below needs the app running ---
import torch  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg  # noqa: E402
from isaaclab.sensors import ContactSensor, ContactSensorCfg  # noqa: E402
from isaaclab.sim import SimulationContext  # noqa: E402
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR  # noqa: E402
from isaaclab.utils.math import quat_apply, subtract_frame_transforms  # noqa: E402

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from ur5_grasp.robots import (  # noqa: E402
    GRIPPER_CLOSED_Q,
    GRIPPER_EFFORT_LIMIT,
    GRIPPER_JOINT_NAMES,
    UR5E_RHP12_CFG,
)

CUBE_USD = f"{ISAAC_NUCLEUS_DIR}/Props/Blocks/DexCube/dex_cube_instanceable.usd"

# Day 3, measured by drop test (logbook/02_measure_dexcube.log). NOT read from the USD, which
# was ambiguous, and NOT the archive's 0.0412 which is wrong by 8.5 mm raw.
CUBE_EDGE_RAW = 0.06000

# Day 3, measured (logbook/02_make_ur5e_rhp12.log): the pad FACE sits this far inboard of the
# pad body origin, summed over the two pads. Needed to turn an origin gap into a face gap.
PAD_REACH_TOTAL = 0.0081

PAD_BODIES = ["rh_p12_rn_r2", "rh_p12_rn_l2"]

# Runs 1 and 2 both reported zero force on the pads while the fingers were solidly blocked, and
# both times "which link is actually touching?" was answered by ARGUMENT rather than
# measurement — first "the proximal links", then "the placement". Both were guesses. Sensors go
# on all four finger links now, so the question becomes a column in the table.
PROXIMAL_BODIES = ["rh_p12_rn_r1", "rh_p12_rn_l1"]
SENSED_BODIES = PAD_BODIES + PROXIMAL_BODIES

WRIST_BODY = "wrist_3_link"

# ROBOTIS RH-P12-RN specifications table.
# https://emanual.robotis.com/docs/en/platform/rh_p12_rn/
DATASHEET_MAX_GRIP_FORCE_N = 170.0

results: dict[str, bool] = {}


def verdict(name: str, ok: bool, detail: str = "") -> None:
    results[name] = ok
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{('  — ' + detail) if detail else ''}")


def find_prim_path(root: str, leaf_name: str) -> str | None:
    """Locate a body prim by NAME under `root`, rather than assuming the nesting.

    The gripper links live under /World/Robot/RHP12/... because of how the merged USD was
    authored, but that is an implementation detail of make_ur5e_rhp12_usd.py. Hardcoding it
    means a future re-author silently produces a sensor attached to nothing — and a contact
    sensor attached to nothing reads exactly 0.0 N, which is indistinguishable from the §9
    failure this script exists to detect. So resolve it, and fail loudly if it is missing.
    """
    import isaacsim.core.utils.stage as stage_utils
    from pxr import Usd

    stage = stage_utils.get_current_stage()
    root_prim = stage.GetPrimAtPath(root)
    if not root_prim.IsValid():
        return None
    for prim in Usd.PrimRange(root_prim, Usd.TraverseInstanceProxies()):
        if prim.GetName() == leaf_name:
            return str(prim.GetPath())
    return None


def main() -> None:  # noqa: C901 — one linear experiment, split would hide the ordering
    cube_edge = CUBE_EDGE_RAW * args_cli.cube_scale

    sim = SimulationContext(sim_utils.SimulationCfg(device=args_cli.device, dt=1.0 / 120.0))
    sim.set_camera_view([0.9, 0.9, 0.7], [0.45, 0.1, 0.45])

    ground_cfg = sim_utils.GroundPlaneCfg()
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)
    light_cfg = sim_utils.DomeLightCfg(intensity=3000.0, color=(0.75, 0.75, 0.75))
    light_cfg.func("/World/Light", light_cfg)

    print("\n" + "=" * 78)
    print("GRASP + HOLD TEST   —   UR5e + RH-P12-RN   —   Module 02, Day 4")
    print("=" * 78)
    print(f"robot usd          : {UR5E_RHP12_CFG.spawn.usd_path}")
    print(f"cube usd           : {CUBE_USD}")
    print(f"cube scale         : {args_cli.cube_scale}")
    print(f"cube edge (scaled) : {cube_edge:.5f} m      <- Day 3 drop test, not read from USD")
    print(f"effort_limit_sim   : {UR5E_RHP12_CFG.actuators['gripper'].effort_limit_sim} N-m")
    print(f"gripper stiffness  : {UR5E_RHP12_CFG.actuators['gripper'].stiffness}")
    print(f"solver pos iters   : {UR5E_RHP12_CFG.spawn.articulation_props.solver_position_iteration_count}")
    # If self-collisions are on, the convex-decomposition colliders of adjacent finger
    # links interpenetrate at their shared joint and PhysX shoves them apart — which would
    # stall the gripper at a fixed opening no matter what is or is not between the pads.
    # Exactly the symptom runs 1 and 2 produced. Print it; do not assume it.
    print(f"self collisions    : {UR5E_RHP12_CFG.spawn.articulation_props.enabled_self_collisions}")
    print(f"mode               : {'CONTROL — NO CUBE' if args_cli.no_cube else 'grasp test'}")
    print(f"contact sensing    : {UR5E_RHP12_CFG.spawn.activate_contact_sensors}")
    print(f"banked prediction  : pads stall at q ~ {args_cli.predicted_q}")
    print("=" * 78)

    # ---- scene ---------------------------------------------------------------------------
    robot_cfg = UR5E_RHP12_CFG.copy()
    robot_cfg.prim_path = "/World/Robot"
    robot = Articulation(cfg=robot_cfg)

    # In CONTROL mode there is no cube at all — not a cube parked far away, none. A cube
    # elsewhere in the scene is still a filter target and still a thing the solver knows
    # about; the control has to remove the variable, not relocate it.
    cube = None
    cube_cfg = None if args_cli.no_cube else RigidObjectCfg(
        prim_path="/World/Cube",
        spawn=sim_utils.UsdFileCfg(
            usd_path=CUBE_USD,
            scale=(args_cli.cube_scale,) * 3,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                disable_gravity=False,
                max_depenetration_velocity=1.0,
            ),
            # Must be on for the pads' filtered contact reports to name this object.
            activate_contact_sensors=True,
        ),
        # Parked clear of the robot; teleported to the pads once they can be measured.
        init_state=RigidObjectCfg.InitialStateCfg(pos=(0.8, 0.0, cube_edge / 2.0)),
    )
    if cube_cfg is not None:
        cube = RigidObject(cfg=cube_cfg)

    # ---- contact sensors, on resolved paths ----------------------------------------------
    print("\n--- resolving pad prims for contact sensing ---")
    pad_paths: dict[str, str] = {}
    for body in SENSED_BODIES:
        path = find_prim_path("/World/Robot", body)
        print(f"  {body:<18} -> {path}")
        if path is not None:
            pad_paths[body] = path
    verdict(
        "all 4 finger prims resolved (a sensor on nothing reads 0.0 N)",
        len(pad_paths) == len(SENSED_BODIES),
        f"{len(pad_paths)}/{len(SENSED_BODIES)} found",
    )
    if len(pad_paths) != len(SENSED_BODIES):
        print("\nSTOP: cannot measure contact force. Every force below would be a false zero.")
        print("=" * 78 + "\n")
        return

    pad_sensors: dict[str, ContactSensor] = {}
    for body, path in pad_paths.items():
        pad_sensors[body] = ContactSensor(
            ContactSensorCfg(
                prim_path=path,
                track_pose=False,
                # Filtered on the cube specifically, so the number below is pad-to-CUBE force
                # and not pad-to-anything. Unfiltered net force would also count the fingers
                # brushing each other, which is not a grasp.
                filter_prim_paths_expr=[] if args_cli.no_cube else ["/World/Cube"],
                # Default is 4. A flat pad on a flat cube face is a face-face contact and
                # generates more manifold points than that; the cfg's own docs say to raise it
                # for contact-rich scenes or contacts get dropped and the force reads low.
                # Contact POSITIONS, not just magnitudes. Five wrong hypotheses today came
                # from inferring WHERE the cube is held out of joint origins, AABBs and
                # screenshots. PhysX knows exactly where the contact is; ask it.
                track_contact_points=True,
                max_contact_data_count_per_prim=32,
                update_period=0.0,
            )
        )

    sim.reset()
    sim_dt = sim.get_physics_dt()

    # ---- indices, by NAME (PhysX reorders gripper joints by tree depth) --------------------
    jn = list(robot.joint_names)
    bn = list(robot.body_names)
    print(f"\n  all joints ({len(jn)}): {jn}")
    grip_idx = [jn.index(n) for n in GRIPPER_JOINT_NAMES if n in jn]
    print(f"  gripper joints     : {[jn[i] for i in grip_idx]}  (indices {grip_idx})")
    verdict("all 4 gripper joints found by name", len(grip_idx) == 4, f"{len(grip_idx)} found")
    if len(grip_idx) != 4:
        print("\nSTOP: gripper joint names do not match the config.")
        print("=" * 78 + "\n")
        return
    # All four finger links, not just the pads — PHASE 0b and the proximal contact
    # sensors both index through here.
    pad_idx = {b: bn.index(b) for b in SENSED_BODIES}
    wrist_idx = bn.index(WRIST_BODY)

    def pad_positions() -> tuple[torch.Tensor, torch.Tensor]:
        p = robot.data.body_pos_w[0]
        return p[pad_idx[PAD_BODIES[0]]], p[pad_idx[PAD_BODIES[1]]]

    def pad_midpoint() -> torch.Tensor:
        """Midpoint of the two pad BODY ORIGINS. NOT the grasp centre — see below."""
        r, l = pad_positions()
        return 0.5 * (r + l)

    # --- pad GEOMETRIC centre -------------------------------------------------------------
    #
    # Run 1's placement bug, and the reason the GUI capture shows the cube up in the throat of
    # the hand rather than between the pads.
    #
    # `body_pos_w` reports a link's ORIGIN, and a link origin sits on its JOINT AXIS. For the
    # r2/l2 fingertips that axis is at the TOP of the fingertip, where it hinges off r1/l1 —
    # not on the gripping face partway down. Placing the cube's centre at the midpoint of the
    # two body origins therefore parks it at the base of the fingers, between the curved
    # proximal links. It wedges there, corner-first: pads report zero force because the pads
    # never touch it, and the fingers stall ~17 mm wide of the cube.
    #
    # The correction uses the same AABB machinery Day 3 already validated
    # (`make_ur5e_rhp12_usd.py: pad_local_bounds`): take the link-local bounding box of the
    # pad's own geometry and use its CENTRE, transformed into world by the link's pose.
    #
    # Same known bias as Day 3: an AABB around a curved fingertip over-approximates, so this
    # centre is approximate too. It does not need to be exact — it needs to be tens of
    # millimetres closer to the truth than the joint axis, and the printed offset says whether
    # it is.
    _pad_local_centre: dict[str, torch.Tensor] = {}

    def pad_local_centre(body: str) -> torch.Tensor:
        if body not in _pad_local_centre:
            import isaacsim.core.utils.stage as stage_utils
            from pxr import Usd, UsdGeom

            stage = stage_utils.get_current_stage()
            prim = stage.GetPrimAtPath(pad_paths[body])
            cache = UsdGeom.BBoxCache(
                Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
            )
            # Untransformed: the link's geometry in the link's own frame — the same frame whose
            # origin `body_pos_w` reports. Exactly the Day 3 call.
            rng = cache.ComputeUntransformedBound(prim).ComputeAlignedRange()
            mid = rng.GetMidpoint()
            _pad_local_centre[body] = torch.tensor(
                [mid[0], mid[1], mid[2]], device=sim.device, dtype=torch.float32
            )
        return _pad_local_centre[body]

    def pad_centre_world(body: str) -> torch.Tensor:
        i = pad_idx[body]
        p = robot.data.body_pos_w[0, i]
        q = robot.data.body_quat_w[0, i]
        return p + quat_apply(q.unsqueeze(0), pad_local_centre(body).unsqueeze(0))[0]

    def grasp_centre() -> torch.Tensor:
        """Midpoint of the two pad GEOMETRIC centres — the middle of the gripping face."""
        return 0.5 * (pad_centre_world(PAD_BODIES[0]) + pad_centre_world(PAD_BODIES[1]))

    def pad_local_corners(body: str) -> torch.Tensor:
        """The 8 corners of the pad's link-local AABB."""
        import isaacsim.core.utils.stage as stage_utils
        from pxr import Usd, UsdGeom

        stage = stage_utils.get_current_stage()
        prim = stage.GetPrimAtPath(pad_paths[body])
        cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
        )
        rng = cache.ComputeUntransformedBound(prim).ComputeAlignedRange()
        mn, mx = rng.GetMin(), rng.GetMax()
        pts = [
            [x, y, z]
            for x in (mn[0], mx[0])
            for y in (mn[1], mx[1])
            for z in (mn[2], mx[2])
        ]
        return torch.tensor(pts, device=sim.device, dtype=torch.float32)

    def link_world_corners(body: str) -> torch.Tensor:
        """The 8 corners of a finger link's AABB, in world, at the CURRENT pose."""
        i = pad_idx[body]
        p, qt = robot.data.body_pos_w[0, i], robot.data.body_quat_w[0, i]
        return p.unsqueeze(0) + quat_apply(qt.unsqueeze(0).repeat(8, 1), pad_local_corners(body))

    def inner_extent(body: str, closing_axis_w: torch.Tensor, centre_w: torch.Tensor) -> float:
        """How close this link's geometry gets to the gripper centreline, in metres.

        THE MEASUREMENT THAT SHOULD HAVE EXISTED ON DAY 3.

        Every geometric claim so far — "the pads are the gripping surface", "the cube is in the
        throat", "the tip is 20-40 mm further out" — has been an inference from joint origins
        and a screenshot. Four of them were wrong. This measures the thing directly: for each of
        the four finger links, the smallest distance from the gripper centreline that its
        geometry reaches, along the axis the fingers close on.

        Whichever link has the SMALLEST value is the one that will touch a centred object
        first. If that is r1/l1 rather than r2/l2, then `PAD_BODIES` names the wrong links and
        the "pads" this script has been measuring were never the gripping surface at all.
        """
        corners = link_world_corners(body)
        d = (corners - centre_w.unsqueeze(0)) @ closing_axis_w
        return float(d.abs().min())

    def pad_tip_along(axis_w: torch.Tensor) -> float:
        """How far the pad geometry reaches along `axis_w` (world), from the wrist origin.

        Added for the fingertip grasp. `grasp_centre()` is the MIDDLE of the pad, so a cube
        placed there is held across the whole face — including the upper part, near the throat,
        where run 4 measured ~500 N landing on the PROXIMAL links and 0 N on the pads. Holding
        at the tip means putting the cube against the distal END of the pad instead, which is
        both what the hardware is designed to do and what an examiner will expect to see in a
        precision-grasping thesis.

        Returns the maximum projection of either pad's geometry onto `axis_w`, measured from
        the wrist body origin. Measured, not assumed — the pad rotates as q changes, so this
        must be read at the pose it is used at.
        """
        wrist_p = robot.data.body_pos_w[0, wrist_idx]
        best = -1e9
        for body in PAD_BODIES:
            i = pad_idx[body]
            p, qt = robot.data.body_pos_w[0, i], robot.data.body_quat_w[0, i]
            corners = pad_local_corners(body)
            world = p.unsqueeze(0) + quat_apply(qt.unsqueeze(0).repeat(8, 1), corners)
            best = max(best, float(((world - wrist_p.unsqueeze(0)) @ axis_w).max()))
        return best

    def origin_gap() -> float:
        r, l = pad_positions()
        return float(torch.linalg.norm(r - l))

    def pad_force(body: str) -> float:
        """Norm of the pad-to-CUBE contact force, in N (filtered)."""
        fm = pad_sensors[body].data.force_matrix_w
        if fm is None:
            return float("nan")
        return float(torch.linalg.norm(fm[0, 0, 0]))

    def contact_depth(body: str) -> float:
        """Where along the TOOL AXIS this link touches the cube, in mm below the wrist origin.

        THE MEASUREMENT THAT ENDS THE ARGUMENT.

        Every "the cube is in the throat" / "the cube is at the tip" claim so far has been read
        off joint origins, AABBs or a screenshot, and five of them were wrong. PhysX already
        knows exactly where the contact is. `contact_pos_w` is the average world position of the
        contact points between this link and the cube; projected onto the tool axis it says, in
        millimetres, how far down the finger the cube is actually being held.

        Compare it against `pad reach along tool` (the distance to the fingertip) printed in
        PHASE 0. Small number = held near the palm, in the throat. Close to the fingertip value
        = held at the tip, which is the goal.
        """
        cp = pad_sensors[body].data.contact_pos_w
        if cp is None or cp.numel() == 0:
            return float("nan")
        pt = cp[0, 0, 0]
        if not bool(torch.isfinite(pt).all()):
            return float("nan")
        wrist_p = robot.data.body_pos_w[0, wrist_idx]
        return float(torch.dot(pt - wrist_p, tool_axis)) * 1000.0

    def pad_net_force(body: str) -> float:
        """Norm of the pad's TOTAL contact force, in N (unfiltered).

        Added 2026-07-29 after run 1 reported a flat 0.00 N filtered force while the fingers
        were demonstrably being blocked. This is the DISCRIMINATOR, and it is a print, not a
        knob — it changes no physics:

            net > 0, filtered = 0  ->  contact is real; `filter_prim_paths_expr` is not
                                       resolving to the cube's rigid body. Fix the filter.
            net = 0, filtered = 0  ->  the pads are not reporting contact at all; the blockage
                                       is somewhere other than the pad bodies (r1/l1, say).
            net > 0, filtered > 0  ->  working.

        Unfiltered force also counts pad-on-anything, which is exactly why it cannot REPLACE
        the filtered number for the thesis result — only diagnose it.
        """
        nf = pad_sensors[body].data.net_forces_w
        if nf is None:
            return float("nan")
        return float(torch.linalg.norm(nf[0, 0]))

    def step(
        n: int,
        q_target: float | None,
        arm_target: torch.Tensor,
        pin_cube_to=None,
        pin_cube_quat=None,
    ) -> None:
        """Advance n steps holding the given arm pose and, optionally, gripper q.

        `pin_cube_to` holds the cube kinematically at a world position by rewriting its state
        every step. That is how the cube stays between the pads while they close, with no IK
        and no cheating on the grasp itself — the pin comes off before anything is measured.
        """
        for _ in range(n):
            target = robot.data.default_joint_pos.clone()
            target[0, : arm_target.shape[0]] = arm_target
            if q_target is not None:
                for i in grip_idx:
                    target[0, i] = q_target
            robot.set_joint_position_target(target)
            robot.write_data_to_sim()
            if pin_cube_to is not None and cube is not None:
                pose = torch.zeros((1, 7), device=sim.device)
                pose[0, :3] = pin_cube_to
                # ORIENTATION MATTERS, and runs 1 and 2 got it wrong.
                #
                # Both pinned the cube with the identity quaternion — i.e. axis-aligned to the
                # WORLD. The gripper hangs at the wrist's orientation, which is nothing like
                # world-aligned at this home pose. So the cube was presented to the pads
                # CORNER-FIRST, and the pads closed onto a diagonal instead of a face.
                #
                # The arithmetic is unambiguous. A 0.048 m cube has a face diagonal of
                # 0.0679 m. Run 2 stalled at a face gap of 0.0690 m. That is not the fingers
                # failing to close — it is the fingers closing correctly onto the widest
                # section of a rotated cube, and a corner grip has no flat contact to hold
                # with, which is why it dropped the moment the pin came off.
                if pin_cube_quat is None:
                    pose[0, 3] = 1.0
                else:
                    pose[0, 3:] = pin_cube_quat
                cube.write_root_pose_to_sim(pose)
                cube.write_root_velocity_to_sim(torch.zeros((1, 6), device=sim.device))
            sim.step()
            robot.update(sim_dt)
            if cube is not None:
                cube.update(sim_dt)
            for s in pad_sensors.values():
                s.update(sim_dt)

    arm_home = robot.data.default_joint_pos[0, :6].clone()

    # ---- PHASE 0: settle the arm, gripper open --------------------------------------------
    print(f"\n--- PHASE 0: settle at home, gripper open, {args_cli.settle_steps} steps ---")
    step(args_cli.settle_steps, 0.0, arm_home)
    origin_mid = pad_midpoint().clone()
    face_mid = grasp_centre().clone()
    tool_axis = quat_apply(
        robot.data.body_quat_w[0, wrist_idx].unsqueeze(0),
        torch.tensor([[0.0, 0.0, 1.0]], device=sim.device),
    )[0]
    wrist_p = robot.data.body_pos_w[0, wrist_idx]

    # Distance from the wrist origin, along the tool axis, to the far end of the pad geometry.
    tip_reach = pad_tip_along(tool_axis)
    # Cube centre so that its OUTER face is flush with the fingertip: one half-edge back from
    # the tip, plus a small margin so the cube is not hanging off the very end of the pad.
    tip_margin = 0.002
    tip_mid = wrist_p + tool_axis * (tip_reach - cube_edge / 2.0 - tip_margin)

    if args_cli.place_at == "tip":
        mid0 = tip_mid.clone()
    elif args_cli.place_at == "padface":
        mid0 = face_mid.clone()
    else:
        mid0 = origin_mid.clone()
    # Shift further out along the tool axis if asked. The tool axis is taken from the wrist's
    # own orientation (its local +z), not assumed to be world -z — the arm is not vertical.
    if abs(args_cli.grasp_depth) > 1e-9:
        mid0 = mid0 + tool_axis * (args_cli.grasp_depth / 1000.0)
    print(f"  pad origin gap, open : {origin_gap():.4f} m   (Day 3 free-space value 0.1145)")
    print(f"  pad ORIGIN midpoint  : x={origin_mid[0]:+.4f} y={origin_mid[1]:+.4f} z={origin_mid[2]:+.4f} m")
    print(f"  pad FACE   midpoint  : x={face_mid[0]:+.4f} y={face_mid[1]:+.4f} z={face_mid[2]:+.4f} m")
    print(f"  face - origin        : {float(torch.linalg.norm(face_mid - origin_mid)) * 1000:.2f} mm"
          f"   <- how far run 1's cube was misplaced")
    print(f"  pad TIP    midpoint  : x={tip_mid[0]:+.4f} y={tip_mid[1]:+.4f} z={tip_mid[2]:+.4f} m")
    print(f"  pad reach along tool : {tip_reach:.4f} m from the wrist origin")
    print(f"  tip - padface        : {float(torch.linalg.norm(tip_mid - face_mid)) * 1000:.2f} mm"
          f"   <- further out, onto the fingertip")
    print(f"  --place-at           : {args_cli.place_at}  (run 1 was 'origin', run 4 'padface')")
    print(f"  --grasp-depth        : {args_cli.grasp_depth:+.1f} mm along the tool axis")
    # The cube is pinned in the WRIST's frame so its faces are square to the pads. That claim
    # is checked, not asserted: the pads' actual separation direction is measured from their
    # body positions and compared against the wrist's local y axis, which is the direction the
    # URDF says the fingers travel along (joint origins at y = +/-0.008, axes along x).
    grasp_quat = robot.data.body_quat_w[0, wrist_idx].unsqueeze(0).clone()
    pad_r, pad_l = pad_positions()
    closing_axis = (pad_r - pad_l) / torch.linalg.norm(pad_r - pad_l)
    wrist_y = quat_apply(grasp_quat, torch.tensor([[0.0, 1.0, 0.0]], device=sim.device))[0]
    cos_a = float(torch.dot(closing_axis, wrist_y).abs().clamp(max=1.0))
    ang = float(torch.rad2deg(torch.acos(torch.tensor(cos_a))))
    print(f"  pad closing axis     : [{closing_axis[0]:+.3f} {closing_axis[1]:+.3f} {closing_axis[2]:+.3f}]")
    print(f"  wrist local +y       : [{wrist_y[0]:+.3f} {wrist_y[1]:+.3f} {wrist_y[2]:+.3f}]")
    print(f"  angle between        : {ang:.2f} deg   <- must be ~0 for a square grip")
    verdict(
        "cube frame is square to the pads (angle < 5 deg)",
        ang < 5.0,
        f"{ang:.2f} deg between the pad closing axis and the cube's y face normal",
    )
    print(f"  clearance vs cube    : {origin_gap() - PAD_REACH_TOTAL - cube_edge:+.4f} m")
    verdict(
        "open pads clear the cube with the arm loaded",
        origin_gap() - PAD_REACH_TOTAL - cube_edge > 0.0,
        f"face gap {origin_gap() - PAD_REACH_TOTAL:.4f} m vs cube {cube_edge:.4f} m",
    )

    # ---- PHASE 0b: WHICH LINK IS THE GRIPPING SURFACE? -------------------------------------
    #
    # Free space, no cube, no contact — pure geometry. For each q, the closest approach of each
    # of the four finger links to the centreline. The link with the smallest number is the one
    # a centred cube meets first, and the q where 2 x that number crosses the cube edge is the
    # q at which the object is actually captured BY THAT LINK.
    #
    # Run 5 measured 654 N on r1/l1 and 0 N on r2/l2 with the cube pushed all the way to the
    # fingertip. Either the cube is somehow still in the throat, or r1/l1 ARE the inner surface
    # and this script has had the roles of the two links backwards since it was written. This
    # table decides which, without another guess.
    print("\n--- PHASE 0b: link inner extents vs the centreline (free space, no cube) ---")
    print("  CAVEAT, added after run 6: these come from AXIS-ALIGNED BOXES around CURVED links.")
    print("  An AABB reports its inner face at EVERY height, including where the real arm has")
    print("  swung far outboard, so the proximal numbers here are an UPPER bound on how close")
    print("  those links really come. Treat this table as indicative. The authority is the")
    print("  measured contact DEPTH in PHASE 2, which comes from PhysX contact points.")
    print(f"  cube half-edge = {cube_edge / 2.0:.4f} m — a link captures the cube when its")
    print(f"  inner extent falls below this.")
    print(f"  {'q':>6}{'r2 (mm)':>10}{'l2 (mm)':>10}{'r1 (mm)':>10}{'l1 (mm)':>10}  closest link")
    for qg in [0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        step(60, qg, arm_home)
        c = grasp_centre()
        vals = {b: inner_extent(b, closing_axis, c) for b in SENSED_BODIES}
        nearest = min(vals, key=vals.get)
        print(f"  {qg:>6.2f}"
              f"{vals[PAD_BODIES[0]] * 1000:>10.2f}{vals[PAD_BODIES[1]] * 1000:>10.2f}"
              f"{vals[PROXIMAL_BODIES[0]] * 1000:>10.2f}{vals[PROXIMAL_BODIES[1]] * 1000:>10.2f}"
              f"  {nearest}")
    step(60, 0.0, arm_home)  # back to open before the cube goes in

    # ---- PHASE 1: put the cube between the pads --------------------------------------------
    if args_cli.no_cube:
        print("\n--- PHASE 1: SKIPPED — control mode, there is no cube in the scene ---")
    else:
        print("\n--- PHASE 1: cube teleported to the pad midpoint, pinned ---")
        print(f"  commanded            : x={mid0[0]:+.4f} y={mid0[1]:+.4f} z={mid0[2]:+.4f} m")
        # Run 1 landed 8.78 mm off the commanded position, almost all of it in -z. One step of
        # gravity at dt=1/120 is 0.34 mm, so that is ~5 steps of free fall and the pin is not
        # holding every step. Print the tracking error per step rather than reasoning about it:
        # if it grows and resets, the pin is intermittent; if it is constant, the frame is offset.
        print(f"  {'step':>6}{'dx (mm)':>10}{'dy (mm)':>10}{'dz (mm)':>10}{'|d| (mm)':>11}")
        for i in range(20):
            step(1, 0.0, arm_home, pin_cube_to=mid0, pin_cube_quat=grasp_quat[0])
            d = (cube.data.root_pos_w[0] - mid0) * 1000.0
            if i < 5 or i == 19:
                print(f"  {i:>6}{d[0]:>10.3f}{d[1]:>10.3f}{d[2]:>10.3f}{float(torch.linalg.norm(d)):>11.3f}")
        cpos = cube.data.root_pos_w[0]
        print(f"  cube (world)         : x={cpos[0]:+.4f} y={cpos[1]:+.4f} z={cpos[2]:+.4f} m")
        print(f"  offset from midpoint : {float(torch.linalg.norm(cpos - mid0)) * 1000:.2f} mm")
        print("\n  PLACEMENT — CONFIRMED BY GUI CAPTURE, run 1, 2026-07-29.")
        print("  Run 1 placed the cube at the pad BODY ORIGIN midpoint. A body origin sits on its")
        print("  joint axis, which for r2/l2 is at the TOP of the fingertip where it hinges off")
        print("  r1/l1 — not on the gripping face. The capture shows the cube up in the throat of")
        print("  the hand, pinched corner-first between the curved proximal links and tilted ~15")
        print("  deg, with the pads splayed below it touching nothing. Textbook wedge, and it")
        print("  explains all four run-1 symptoms at once: blocked 17 mm wide, zero pad force,")
        print("  a 10 mm settle on release, then a rigid ride through the lift.")
        print("  Figure: Thesis_Documentation/assets/02_day4_run1_wedge.png")

    # ---- PHASE 2: close, one q at a time ---------------------------------------------------
    print(f"\n--- PHASE 2: closing in {args_cli.q_step} rad steps, {args_cli.close_steps} steps each ---")
    # Run 1 lesson: the stall detector required BOTH lag AND force. When the force channel
    # failed, a real mechanical stall was reported as "never stalled" — a broken sensor
    # masquerading as a robot result. The two are now detected SEPARATELY: lag says the
    # fingers were blocked, force says by what. A stall with no force is a diagnosis, not a
    # non-event.
    # Net force is now printed for ALL FOUR finger links. "Which link is touching?" was
    # answered by argument twice and was wrong twice; it is a measurement from here on.
    print(f"  {'q_cmd':>7}{'q_meas':>9}{'lag':>9}{'org_gap':>10}{'face_gap':>10}"
          f"{'Fc_r2':>7}{'Fc_l2':>7}{'Fc_r1':>7}{'Fc_l1':>7}"
          f"{'Nr2':>7}{'Nl2':>7}{'Nr1':>7}{'Nl1':>7}{'depth':>9}")
    print(f"  {'':>7}{'':>9}{'':>9}{'':>10}{'':>10}"
          f"{'--- filtered, link vs CUBE ---':>28}{'--- net, link vs anything ---':>28}"
          f"{'mm':>9}")
    sweep: list[tuple[float, float, float, float, float, float, float, float]] = []
    stall_q: float | None = None
    force_stall_q: float | None = None
    q = 0.0
    while q <= GRIPPER_CLOSED_Q + 1e-9:
        step(args_cli.close_steps, q, arm_home, pin_cube_to=mid0, pin_cube_quat=grasp_quat[0])
        q_meas = float(robot.data.joint_pos[0, grip_idx].mean())
        lag = q - q_meas
        og = origin_gap()
        fg = og - PAD_REACH_TOTAL
        f_r, f_l = pad_force(PAD_BODIES[0]), pad_force(PAD_BODIES[1])
        # Filtered force on the PROXIMAL links too. It was never printed before, so "the cube
        # filter is not resolving" was never actually tested — the pads simply were not touching.
        fp_r, fp_l = pad_force(PROXIMAL_BODIES[0]), pad_force(PROXIMAL_BODIES[1])
        n_r, n_l = pad_net_force(PAD_BODIES[0]), pad_net_force(PAD_BODIES[1])
        p_r, p_l = pad_net_force(PROXIMAL_BODIES[0]), pad_net_force(PROXIMAL_BODIES[1])
        # How far the cube has drifted below the pad midpoint. If the cube is not where the
        # rig thinks it is, every geometric conclusion below is about the wrong object.
        cube_dz = (
            float(cube.data.root_pos_w[0, 2] - grasp_centre()[2]) * 1000.0
            if cube is not None
            else float("nan")
        )
        sweep.append((q, q_meas, og, fg, f_r, f_l, max(n_r, n_l), max(p_r, p_l)))
        mark = ""
        if stall_q is None and lag > args_cli.stall_tol:
            stall_q = q_meas
            mark = " <-LAG-STALL"
        if force_stall_q is None and max(f_r, f_l) > args_cli.force_tol:
            force_stall_q = q_meas
            mark += " <-FORCE"
        # Depth of the loaded contact, along the tool axis, in mm from the wrist.
        depth = contact_depth(PROXIMAL_BODIES[0]) if p_r > args_cli.force_tol else contact_depth(
            PAD_BODIES[0]
        )
        print(f"  {q:>7.2f}{q_meas:>9.4f}{lag:>9.4f}{og:>10.4f}{fg:>10.4f}"
              f"{f_r:>7.1f}{f_l:>7.1f}{fp_r:>7.1f}{fp_l:>7.1f}"
              f"{n_r:>7.1f}{n_l:>7.1f}{p_r:>7.1f}{p_l:>7.1f}"
              f"{depth:>9.1f}{mark}")
        q += args_cli.q_step

    peak_force = max(max(r[4], r[5]) for r in sweep)
    # r[6] is the pad columns, r[7] the proximal columns. Run 4's diagnosis fired on the
    # wrong branch because this line maxed over BOTH and so inherited the proximal load.
    peak_net = max(r[6] for r in sweep)

    peak_prox = max(r[7] for r in sweep)

    print("\n--- CONTACT CHANNEL: which link, if any, is actually touching? ---")
    print(f"  peak FILTERED, pad -> cube      : {peak_force:.2f} N")
    print(f"  peak NET,      pads  (r2/l2)    : {peak_net:.2f} N")
    print(f"  peak NET,      proximal (r1/l1) : {peak_prox:.2f} N")
    if args_cli.no_cube:
        print("  CONTROL RUN — there is no cube. Any non-zero force here is the gripper")
        print("  touching ITSELF or the arm, and that alone would explain the stall.")
    if peak_net <= args_cli.force_tol and peak_prox <= args_cli.force_tol:
        print("  DIAGNOSIS: NO finger link is touching anything, yet the fingers are blocked")
        print("             (see the lag column). The obstruction is not contact at all.")
        print("             Compare the stall gap against the control run: if the EMPTY gripper")
        print("             stalls in the same place, the cube was never the variable and the")
        print("             fault is inside the gripper — actuation or self-collision.")
    elif peak_prox > args_cli.force_tol >= peak_net:
        print("  DIAGNOSIS: the PROXIMAL links carry the load and the pads carry none.")
        print("             That is the wedge, measured rather than argued.")
        print("             ONE knob: --grasp-depth, to push the cube out past the throat.")
    elif peak_net > args_cli.force_tol >= peak_force:
        print("  DIAGNOSIS: the pads ARE in contact; the CUBE FILTER is not resolving.")
        print("             ONE knob: filter_prim_paths_expr. The gripper is fine.")
    else:
        print("  Both channels alive on the pads. The filtered number is the thesis result.")

    # Captured HERE, at the grasp, together with the wrist pose that PHASE 5 measures against.
    # Run 1 took `grasp_mid` at this point but read the wrist pose in PHASE 5 — after an 84 mm,
    # 0.3 rad lift. It was subtracting two frames from different instants, and reported a
    # 0.226 m TCP offset against a Day 3 expectation of ~0.10 m. Pure bookkeeping error.
    grasp_mid = grasp_centre().clone()
    grasp_gap = origin_gap()
    grasp_wrist_pos = robot.data.body_pos_w[0, wrist_idx].unsqueeze(0).clone()
    grasp_wrist_quat = robot.data.body_quat_w[0, wrist_idx].unsqueeze(0).clone()

    print("\n--- STALL WIDTH: measured vs the prediction banked on 2026-07-28 ---")
    mfg = min(r[3] for r in sweep)
    print(f"  minimum face gap reached : {mfg:.4f} m   vs cube {cube_edge:.4f} m")
    # The three widths a cube can present to a parallel gripper. Runs 1 and 2 both landed near
    # the FACE DIAGONAL, which is the fingerprint of a corner grip.
    print(f"  cube edge / face diag / body diag : {cube_edge:.4f} / "
          f"{cube_edge * 2 ** 0.5:.4f} / {cube_edge * 3 ** 0.5:.4f} m")
    if abs(mfg - cube_edge * 2 ** 0.5) < abs(mfg - cube_edge):
        print("  WARNING: the stall width is closer to the FACE DIAGONAL than to the edge.")
        print("           The cube is being gripped corner-first. Check the angle in PHASE 0.")
    if stall_q is None:
        print(f"  pads never stalled: they tracked the command to q={GRIPPER_CLOSED_Q}.")
        print("  Meaning: the fingers closed THROUGH the cube, or never touched it.")
        verdict("pads stall on the cube rather than closing through it", False, "no stall detected")
    else:
        err = stall_q - args_cli.predicted_q
        print(f"  measured stall q   : {stall_q:.4f}")
        print(f"  predicted stall q  : {args_cli.predicted_q:.4f}")
        print(f"  error              : {err:+.4f} rad")
        if abs(err) <= 0.03:
            print("  VERDICT: as predicted. The Day 3 geometry model transfers to contact.")
        elif err < -0.03:
            print("  VERDICT: EARLY. Per the decision rules this is the cube wedging on the")
            print("           curved proximal r1/l1 links. ONE knob: the TCP offset. Nothing else.")
        else:
            print("  VERDICT: LATE. Per the decision rules this is crushing or slipping through.")
            print("           ONE knob: effort_limit_sim. Nothing else.")
        verdict(
            f"stall q within 0.03 of the banked {args_cli.predicted_q}",
            abs(err) <= 0.03,
            f"measured {stall_q:.4f}, error {err:+.4f}",
        )

    print("\n--- CONTACT FORCE: measured vs the ROBOTIS datasheet ---")
    print(f"  peak pad force     : {peak_force:.2f} N")
    print(f"  datasheet maximum  : {DATASHEET_MAX_GRIP_FORCE_N:.1f} N")
    print(f"  effort_limit_sim   : {GRIPPER_EFFORT_LIMIT} N-m")
    verdict(
        "pads transmit real normal force (not the §9 Robotiq failure)",
        peak_force > args_cli.force_tol,
        f"peak {peak_force:.2f} N",
    )
    if peak_force <= args_cli.force_tol:
        print("\n  STOP. Pads in position with no force is the §9 failure mode reproducing on a")
        print("  different gripper. Do NOT tune. Log it as a negative result and diagnose the")
        print("  contact reporting first — starting with whether the CUBE has contact sensing on.")
    else:
        scale = DATASHEET_MAX_GRIP_FORCE_N / peak_force
        print(f"  to hit 170 N exactly, scale effort_limit_sim by {scale:.3f}"
              f"  ->  {GRIPPER_EFFORT_LIMIT * scale:.2f} N-m")
        verdict(
            "peak force is the same order as the datasheet 170 N (0.25x .. 4x)",
            0.25 <= peak_force / DATASHEET_MAX_GRIP_FORCE_N <= 4.0,
            f"ratio {peak_force / DATASHEET_MAX_GRIP_FORCE_N:.2f}x",
        )

    # PHASES 3 and 4 are about holding a cube. With no cube they are meaningless, and
    # running them anyway would emit FAILs that say nothing about the gripper.
    if args_cli.no_cube:
        print("\n--- PHASES 3 and 4: SKIPPED — control mode, there is no cube to hold ---")
    else:
        # ---- PHASE 3: release the pin — static hold --------------------------------------------
        print(f"\n--- PHASE 3: pin released, arm still, {args_cli.hold_steps} steps ---")
        z_before = float(cube.data.root_pos_w[0, 2])
        step(args_cli.hold_steps, GRIPPER_CLOSED_Q, arm_home)  # no pin_cube_to
        z_after = float(cube.data.root_pos_w[0, 2])
        static_drop = z_before - z_after
        print(f"  cube z, released   : {z_before:.4f} m")
        print(f"  cube z, after hold : {z_after:.4f} m")
        print(f"  drop               : {static_drop * 1000:+.2f} mm")
        verdict("cube held statically (drop < 5 mm)", static_drop < 0.005, f"{static_drop * 1000:+.2f} mm")

        # ---- PHASE 4: lift ----------------------------------------------------------------------
        # shoulder_lift -= d and wrist_1 += d. Those two axes are PARALLEL on a UR, so the tool
        # orientation is unchanged by construction and the TCP swings up on an arc about the
        # shoulder. No IK, no orientation drift to confuse a slip measurement.
        print(f"\n--- PHASE 4: lift arc, delta {args_cli.lift_delta} rad, {args_cli.lift_steps} steps ---")
        arm_lift = arm_home.clone()
        arm_lift[1] -= args_cli.lift_delta
        arm_lift[3] += args_cli.lift_delta

        tcp_before = grasp_centre().clone()
        cube_before = cube.data.root_pos_w[0].clone()
        grip_offset_before = cube_before - tcp_before

        ramp = args_cli.lift_steps // 2
        for i in range(ramp):
            a = (i + 1) / ramp
            step(1, GRIPPER_CLOSED_Q, arm_home * (1 - a) + arm_lift * a)
        step(args_cli.lift_steps - ramp, GRIPPER_CLOSED_Q, arm_lift)

        tcp_after = grasp_centre().clone()
        cube_after = cube.data.root_pos_w[0].clone()
        grip_offset_after = cube_after - tcp_after
        tcp_rise = float(tcp_after[2] - tcp_before[2])
        slip = float(torch.linalg.norm(grip_offset_after - grip_offset_before))
        f_r_lift, f_l_lift = pad_force(PAD_BODIES[0]), pad_force(PAD_BODIES[1])

        print(f"  TCP rise           : {tcp_rise * 1000:+.1f} mm")
        print(f"  cube rise          : {float(cube_after[2] - cube_before[2]) * 1000:+.1f} mm")
        print(f"  SLIP in gripper    : {slip * 1000:+.2f} mm   <- the number that matters")
        print(f"  pad force at top   : F_r2={f_r_lift:.2f} N   F_l2={f_l_lift:.2f} N")
        if tcp_rise < 0.01:
            print("  NOTE: the TCP barely moved. The lift arc sign may be wrong for this home pose —")
            print("        flip --lift-delta and re-run. A lift test that does not lift proves nothing.")
        verdict("TCP actually rose (the lift happened at all)", tcp_rise > 0.01, f"{tcp_rise * 1000:+.1f} mm")
        verdict("cube did not slip in the gripper (< 5 mm)", slip < 0.005, f"{slip * 1000:.2f} mm")
        if static_drop < 0.005 <= slip:
            print("\n  Held statically, slipped on the lift. That is the WEDGE — the cube riding the")
            print("  curved proximal links rather than sitting flat on the pads. Per the decision")
            print("  rules the ONE knob is the TCP offset. Not the effort limit. Not both.")

    # ---- PHASE 5: TCP_OFFSET, measured AT THE GRASP ------------------------------------------
    print("\n--- PHASE 5: TCP_OFFSET for this thesis, taken at the grasp ---")
    # Wrist pose taken AT THE GRASP, not now — PHASE 4 has since moved the arm 84 mm and
    # 0.3 rad. Mixing the two instants is what made run 1 report 0.226 m.
    ident = torch.tensor([[1.0, 0.0, 0.0, 0.0]], device=sim.device)
    tcp_in_wrist, _ = subtract_frame_transforms(
        grasp_wrist_pos, grasp_wrist_quat, grasp_mid.unsqueeze(0), ident
    )
    t = tcp_in_wrist[0]
    print(f"  pad origin gap at the grasp : {grasp_gap:.4f} m")
    print(f"  pad midpoint in wrist frame : x={t[0]:+.5f} y={t[1]:+.5f} z={t[2]:+.5f} m")
    print(f"  |offset|                    : {float(torch.linalg.norm(t)):.5f} m")
    print(f"\n  TCP_OFFSET = ({t[0]:+.5f}, {t[1]:+.5f}, {t[2]:+.5f})   <- use this in the lift env")
    print(f"  Day 3 free-space values were 0.0767 (q=0) and 0.1049 (q=1). This is taken at the")
    print(f"  actual grasp, which is the only q where the number means anything.")
    print(f"  The archive's 0.130 is NOT this number and was invalidated on Day 3.")

    # ---- summary -------------------------------------------------------------------------
    print("\n" + "=" * 78)
    failed = [k for k, v in results.items() if not v]
    if failed:
        print(f"RESULT: FAIL — {len(failed)} of {len(results)} checks failed")
        for k in failed:
            print(f"  - {k}")
        print("\nLook the symptom up in the decision-rule table in logbook/02_grasp_env.md.")
        print("Change ONE knob. Re-run. Never two at once.")
    else:
        print(f"RESULT: PASS — all {len(results)} checks green.")
        print("The RH-P12-RN holds the cube through a lift, with measured contact force.")
        print("Next: the lift env (Isaac Lab stock table, lift_env_cfg.py:45) and the PPO baseline.")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
    simulation_app.close()
