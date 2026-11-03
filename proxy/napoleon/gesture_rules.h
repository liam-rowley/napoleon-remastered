#pragma once
// gesture_rules.h - Napoleon's side of the gesture layer (J29; contract warscape-core docs/PROXY_GESTURES.md), the pure part: the scene
// map, the selected unit as the layer takes it, the frontage clamps, the order a target becomes, and the commit loop. No Windows types and
// no driver calls: adapter.cpp wires these to the core's drivers (OrdersSelection, OrdersUnit, CameraRead, OrdersGroundAt, OrdersMove)
// in the DLL build; tests/cpp/test_gesture_napoleon.cpp runs them on the host (tests/test_gesture_adapter.py builds and runs it).
// Facts (registries/engine_facts): napoleon.battle.camera_route (mode +8 position, +0x14 target, 70.0 degrees vertical),
// napoleon.battle.bearing_convention (0 = +z, 90 = +x, clockwise from above: the core's convention, so bearings pass unchanged),
// napoleon.battle.unit_layout (UNIT+0x310 the destination front centre, +0x324 the destination frontage: the order point is the front
// centre), napoleon.battle.frontage_ranks (no ranks field; depth derived as twice the centre-to-front distance),
// napoleon.battle.order_deployment (deployment orders do not walk: inert), napoleon.battle.ship_orders (ships are out of scope).
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>
#include "adapter.h"
#include "orders.h"

namespace wsp {
namespace nap {

// ---- the camera (napoleon.battle.camera_route, verified 2026-10-30, run 20261030_j43pc) -------------------------------------------
const int kCamPosOff = 0x8;          // the camera mode's eye (3 floats)
const int kCamTargetOff = 0x14;      // the camera mode's look-at target (3 floats)
const double kFovYDeg = 70.0;        // the pinhole fit's vertical field of view (to 0.001 px over 27 points)

// ---- the bindings and thresholds (registries/hotkeys: mod.gesture.move, mod.gesture.rotate; the core's modifier bits) ------------
const unsigned kModAlt = 1, kModCtrl = 2, kModShift = 4;
const unsigned kMoveMods = kModAlt;                 // Alt+LeftDrag
const unsigned kRotateMods = kModAlt | kModCtrl;    // Ctrl+Alt+LeftDrag
const int kDragPx = 6;               // a press becomes a drag beyond 6 client px (the core's default)
const double kShortDragM = 3.0;      // a move line under 3 m keeps the widths and moves the block's centre to the press point
const double kPivotFwdM = 0.0;       // the rotate pivot: in place (J29 brief; Liam may change it at sign-off: open question 2)
const double kRotGain = 225.0;       // degrees per 1000 px at a 3840-wide client (the provenance's v5 gain)
const int kRotSign = 1;              // mouse right turns clockwise from above

// ---- the selected unit ---------------------------------------------------------------------------------------------------------------
// A unit's frontage clamps. PROVISIONAL until J29's PC step (b) measures the engine's accepted min and max width with `ctl.py order`
// on land_40 and records a fact: the C++ side reads no unit class, so the measured rule is keyed by men alive. Until then: a floor a
// little over CheckMove's 0.5 m refusal and no ceiling (0 = none), so the layout never plans a width the order route refuses.
struct ClampRow { int menMin, menMax; double minWidth, maxWidth; };
const ClampRow kClamps[] = { { 1, 1000000, 1.0, 0.0 } };   // PROVISIONAL (see above)
inline void FrontageClamps(int men, double& minWidth, double& maxWidth) {
    minWidth = 0; maxWidth = 0;
    for (const ClampRow& r : kClamps) if (men >= r.menMin && men <= r.menMax) { minWidth = r.minWidth; maxWidth = r.maxWidth; return; }
}

// The depth used when a unit is not standing at its last destination (walking, or pushed off it): J28's 120-man default line
// (31.9 m wide, 1.75 m deep, derived; napoleon.battle.frontage_ranks).
const double kFallbackDepthM = 1.75;
// A unit stands at its destination when its destination front centre lies ahead of its live centre along its facing by 0.1 to 15 m and
// within 1 m sideways: then the front centre is the order point and twice the ahead distance is its depth.
const double kAheadMinM = 0.1, kAheadMaxM = 15.0, kSideMaxM = 1.0;

// UnitState (OrdersUnit) -> the layer's unit. The order point is the front centre (frontRef), because the engine's move order names the
// formation's front centre (napoleon.battle.unit_layout). Refuses a unit the order route would not order or whose frontage is unknown.
inline bool UnitIn(const UnitState& s, GestureUnitIn& u, std::string& why) {
    if (!UnitOrderable(s, why)) return false;
    if (!s.hasWidth || !std::isfinite(s.width) || s.width <= 0.5f) { why = "the unit's frontage is not readable"; return false; }
    const double b = s.facing * 3.14159265358979323846 / 180.0, fx = std::sin(b), fz = std::cos(b);
    u = GestureUnitIn{};
    u.id = s.unit; u.y = s.y; u.bearing = s.facing; u.width = s.width; u.frontRef = true;
    FrontageClamps(s.men, u.minWidth, u.maxWidth);
    bool atDest = false;
    if (s.hasFront && std::isfinite(s.fx) && std::isfinite(s.fz)) {
        const double dx = s.fx - s.x, dz = s.fz - s.z, ahead = dx * fx + dz * fz, side = std::fabs(dx * fz - dz * fx);
        if (ahead >= kAheadMinM && ahead <= kAheadMaxM && side <= kSideMaxM) { atDest = true; u.x = s.fx; u.z = s.fz; u.depth = 2.0 * ahead; }
    }
    if (!atDest) { u.depth = kFallbackDepthM; u.x = s.x + fx * kFallbackDepthM / 2; u.z = s.z + fz * kFallbackDepthM / 2; }
    return true;
}

// The selection: every loose unit of the UI's own selection that UnitIn takes, in the selection's order. sel(loose, groups, why) and
// unit(ptr, state, why) are the drivers (OrdersSelection, OrdersUnit) or a test's fakes. Units that cannot be taken are skipped; none
// left = false with the reason (the layer then passes the press). A grouped selection's groups are not read (J29 open question 6).
template <class Sel, class Read>
bool Selection(Sel sel, Read unit, std::vector<GestureUnitIn>& out, std::string& why) {
    out.clear();
    std::vector<uint32_t> loose; int groups = 0;
    if (!sel(loose, groups, why)) { if (why.empty()) why = "the selection is not readable"; return false; }
    std::string skip;
    for (uint32_t p : loose) {
        UnitState s; std::string w;
        if (!unit(p, s, w)) { if (skip.empty()) skip = w; continue; }
        GestureUnitIn u;
        if (!UnitIn(s, u, w)) { if (skip.empty()) skip = w; continue; }
        out.push_back(u);
    }
    if (!out.empty()) { why.clear(); return true; }
    if (loose.empty()) why = groups > 0 ? "only grouped units are selected (groups are not read: J29 open question 6)" : "empty selection";
    else why = "no selected unit can be ordered: " + skip;
    return false;
}

// ---- the scene (the core's scene tracker, fed by the battle probe in the Lua bridge) ------------------------------------------------
// land and siege battles are "battle"; the deployment phase is "battle_deploy"; "naval", the campaign, the front end and loading are not
// gesture scenes. "" = the tracker is off (no dev key: the orders route is a dev key too, J29 open question 3).
inline GestureScene SceneOf(const std::string& scene, std::string& why) {
    if (scene == "battle") { why = "land or siege battle"; return GestureScene::Eligible; }
    if (scene == "battle_deploy") { why = "the deployment phase (orders there do not walk: napoleon.battle.order_deployment)"; return GestureScene::Deployment; }
    if (scene == "naval") { why = "naval battle (ship orders are J60's)"; return GestureScene::Ineligible; }
    if (scene.empty()) { why = "the scene tracker is off (no dev key)"; return GestureScene::Ineligible; }
    why = "scene " + scene;
    return GestureScene::Ineligible;
}

// ---- orders --------------------------------------------------------------------------------------------------------------------------
// A planned target as the move order takes it: the front centre, the facing in [0, 360) and the width, walking, not queued.
inline MoveArgs MoveOf(const GestureOrderOut& o) {
    MoveArgs a;
    a.x = (float)o.x; a.z = (float)o.z;
    double f = std::fmod(o.bearing, 360.0); if (f < 0) f += 360.0;
    a.hasFacing = true; a.facing = f;
    a.hasWidth = true; a.width = (float)o.width;
    a.run = false; a.queue = false;
    return a;
}
// placeable: the order route's own argument check (finite, inside +-100 km, width in (0.5, 1000] m). The ground check (no ground =
// refused) is the core's, through groundAt; an off-map point the ground projector still places is J29 PC plan item 2.
inline bool Placeable(const GestureOrderOut& o, std::string& why) { return CheckMove(MoveOf(o), why); }

// commit: one move order per target, in order; send(unit, args, info, why) is OrdersMove or a test's fake. Returns the orders sent; why
// names the first refusal and how many there were.
template <class Send>
int Commit(const GestureOrderOut* o, size_t n, Send send, std::string& why) {
    int sent = 0, refused = 0; std::string first;
    for (size_t i = 0; i < n; ++i) {
        std::string info, w;
        if (send(o[i].id, MoveOf(o[i]), info, w)) ++sent;
        else { ++refused; if (first.empty()) first = w.empty() ? "refused" : w; }
    }
    why = refused ? std::to_string(refused) + " refused, first: " + first : std::string();
    return sent;
}

}  // namespace nap
}  // namespace wsp
