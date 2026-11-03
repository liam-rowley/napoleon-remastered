// test_gesture_napoleon.cpp - host tests for Napoleon's gesture rules (J29, proxy/napoleon/gesture_rules.h) against the core's gesture
// maths (warscape-core W6): the scene map, the selected unit (front centre, derived depth, clamps), the selection filter, the order a
// target becomes, the commit loop, a 20-unit line laid by the core's LineLayout checked against geometry computed here, the rotate pivot
// (with the core's 4 m depth floor pinned as a known gap), and the pick round trip with Napoleon's 70 degree camera.
// Built and run by tests/test_gesture_adapter.py (native g++, else Docker, in the tests gate).
#include "testkit.h"
#include "gesture_rules.h"
#include "gesture_plan.h"
#include <cmath>
#include <map>

using namespace wsp;
using namespace wsp::nap;

namespace {
const double kPi = 3.14159265358979323846;
UnitState Standing(uint32_t id, double cx, double cz, double bearing, double width, double depth, int men = 120) {
    UnitState s; s.ok = true; s.unit = id; s.men = men; s.x = (float)cx; s.y = 10.f; s.z = (float)cz;
    s.facing = bearing; s.hasWidth = true; s.width = (float)width;
    const double b = bearing * kPi / 180.0;
    s.hasFront = true; s.fx = (float)(cx + std::sin(b) * depth / 2); s.fy = 10.f; s.fz = (float)(cz + std::cos(b) * depth / 2);
    return s;
}
bool Near(double a, double b, double eps = 1e-4) { return std::fabs(a - b) <= eps; }
gest::Unit ToCore(const GestureUnitIn& a) {   // as gesture.cpp Selection() copies it
    gest::Unit u; u.id = a.id; u.x = a.x; u.y = a.y; u.z = a.z; u.bearing = a.bearing; u.width = a.width; u.depth = a.depth;
    u.minWidth = a.minWidth; u.maxWidth = a.maxWidth; u.frontRef = a.frontRef; return u;
}
GestureOrderOut ToOut(const gest::Unit& t) { return GestureOrderOut{ t.id, t.x, t.z, t.bearing, t.width }; }
}  // namespace

int main(int argc, char** argv) {
    tk::Args(argc, argv);

    // ---- constants: the bindings and thresholds the hotkeys rows and the brief name
    CHECK_EQ(kMoveMods, 1u); CHECK_EQ(kRotateMods, 3u); CHECK(kMoveMods != kRotateMods);
    CHECK_EQ(kDragPx, 6); CHECK(Near(kShortDragM, 3.0)); CHECK(Near(kPivotFwdM, 0.0)); CHECK(Near(kRotGain, 225.0)); CHECK_EQ(kRotSign, 1);
    CHECK_EQ(kCamPosOff, 8); CHECK_EQ(kCamTargetOff, 0x14); CHECK(Near(kFovYDeg, 70.0));

    // ---- the scene map
    {
        std::string w;
        CHECK(SceneOf("battle", w) == GestureScene::Eligible);
        CHECK(SceneOf("battle_deploy", w) == GestureScene::Deployment); CHECK(w.find("deployment") != std::string::npos);
        CHECK(SceneOf("naval", w) == GestureScene::Ineligible); CHECK(w.find("naval") != std::string::npos);
        for (const char* sc : { "campaign", "frontend", "loading", "intro" }) { CHECK(SceneOf(sc, w) == GestureScene::Ineligible); CHECK(w.find(sc) != std::string::npos); }
        CHECK(SceneOf("", w) == GestureScene::Ineligible); CHECK(w.find("tracker is off") != std::string::npos);
    }

    // ---- the selected unit
    {
        GestureUnitIn u; std::string w;
        UnitState s = Standing(7, 100, 200, 90, 31.9, 1.75);
        CHECK(UnitIn(s, u, w));
        CHECK_EQ(u.id, 7u); CHECK(u.frontRef); CHECK(Near(u.bearing, 90)); CHECK(Near(u.width, 31.9, 1e-4)); CHECK(Near(u.y, 10));
        CHECK(Near(u.x, 100.875, 1e-4)); CHECK(Near(u.z, 200, 1e-4)); CHECK(Near(u.depth, 1.75, 1e-4));   // the front centre, twice the ahead distance
        CHECK(Near(u.minWidth, 1.0)); CHECK(Near(u.maxWidth, 0.0));                                           // provisional clamps
        // walking (the destination is 40 m away): the live centre plus half the fallback depth ahead
        s = Standing(8, 0, 0, 0, 31.9, 1.75); s.fz = 40.f;
        CHECK(UnitIn(s, u, w)); CHECK(Near(u.depth, kFallbackDepthM)); CHECK(Near(u.x, 0)); CHECK(Near(u.z, kFallbackDepthM / 2));
        // pushed sideways off the destination (more than 1 m): fallback too
        s = Standing(9, 0, 0, 0, 31.9, 1.75); s.fx = 3.f;
        CHECK(UnitIn(s, u, w)); CHECK(Near(u.depth, kFallbackDepthM));
        // the destination behind the unit (turned since): fallback
        s = Standing(10, 0, 0, 180, 31.9, 1.75); s.fz = 0.875f;
        CHECK(UnitIn(s, u, w)); CHECK(Near(u.depth, kFallbackDepthM)); CHECK(Near(u.z, -kFallbackDepthM / 2));
        // refusals
        s = Standing(11, 0, 0, 0, 31.9, 1.75); s.men = 0;
        CHECK(!UnitIn(s, u, w)); CHECK(w.find("no men") != std::string::npos);
        s = Standing(12, 0, 0, 0, 31.9, 1.75); s.ok = false; s.why = "the unit is on a moving frame (a ship or a building): out of scope";
        CHECK(!UnitIn(s, u, w)); CHECK(w.find("moving frame") != std::string::npos);
        s = Standing(13, 0, 0, 0, 0.3, 1.75);
        CHECK(!UnitIn(s, u, w)); CHECK(w.find("frontage") != std::string::npos);
        s = Standing(14, 0, 0, 0, 31.9, 1.75); s.hasWidth = false;
        CHECK(!UnitIn(s, u, w));
        double mn = -1, mx = -1; FrontageClamps(0, mn, mx); CHECK(Near(mn, 0)); CHECK(Near(mx, 0));   // no row: no clamps
    }

    // ---- the selection filter
    {
        std::map<uint32_t, UnitState> mem;
        mem[1] = Standing(1, 0, 0, 0, 30, 1.75); mem[2] = Standing(2, 30, 0, 0, 30, 1.75); mem[2].men = 0; mem[3] = Standing(3, 60, 0, 0, 30, 1.75);
        std::vector<uint32_t> loose; int groups = 0; bool selOk = true;
        auto sel = [&](std::vector<uint32_t>& l, int& g, std::string& w) { if (!selOk) { w = "no battle"; return false; } l = loose; g = groups; return true; };
        auto rd = [&](uint32_t p, UnitState& s, std::string& w) { auto it = mem.find(p); if (it == mem.end()) { w = "not a unit"; return false; } s = it->second; return true; };
        std::vector<GestureUnitIn> out; std::string why;
        CHECK(!Selection(sel, rd, out, why)); CHECK_EQ(why, std::string("empty selection"));
        groups = 2; CHECK(!Selection(sel, rd, out, why)); CHECK(why.find("grouped") != std::string::npos); groups = 0;
        loose = { 1, 2, 3, 99 };
        CHECK(Selection(sel, rd, out, why)); CHECK_EQ(out.size(), (size_t)2); CHECK_EQ(out[0].id, 1u); CHECK_EQ(out[1].id, 3u); CHECK(why.empty());
        loose = { 2, 99 };
        CHECK(!Selection(sel, rd, out, why)); CHECK(out.empty()); CHECK(why.find("no selected unit can be ordered: the unit has no men") == 0);
        selOk = false; CHECK(!Selection(sel, rd, out, why)); CHECK_EQ(why, std::string("no battle"));
    }

    // ---- the order a target becomes, the placeable check, the commit loop
    {
        MoveArgs a = MoveOf(GestureOrderOut{ 5, 1.5, -2.5, -90, 12 });
        CHECK(Near(a.x, 1.5)); CHECK(Near(a.z, -2.5)); CHECK(a.hasFacing); CHECK(Near(a.facing, 270)); CHECK(a.hasWidth); CHECK(Near(a.width, 12));
        CHECK(!a.run); CHECK(!a.queue);
        CHECK(Near(MoveOf(GestureOrderOut{ 5, 0, 0, 450, 12 }).facing, 90));
        CHECK(Near(MoveOf(GestureOrderOut{ 5, 0, 0, 360, 12 }).facing, 0));
        std::string w;
        CHECK(Placeable(GestureOrderOut{ 1, 10, 10, 0, 30 }, w));
        CHECK(!Placeable(GestureOrderOut{ 1, 10, 10, 0, 0.4 }, w)); CHECK(w.find("width") != std::string::npos);
        CHECK(!Placeable(GestureOrderOut{ 1, std::nan(""), 10, 0, 30 }, w));
        CHECK(!Placeable(GestureOrderOut{ 1, 2e5, 10, 0, 30 }, w));
        const GestureOrderOut o[3] = { { 1, 0, 0, 0, 30 }, { 2, 5, 0, 0, 30 }, { 3, 10, 0, 0, 30 } };
        std::vector<uint32_t> got;
        auto send = [&](uint32_t id, const MoveArgs& m, std::string& info, std::string& ww) {
            got.push_back(id); info = "pushed"; if (id == 2) { ww = "the engine refused the unit"; return false; } return m.hasFacing && m.hasWidth; };
        std::string why;
        CHECK_EQ(Commit(o, 3, send, why), 2); CHECK_EQ(got.size(), (size_t)3); CHECK(why.find("1 refused, first: the engine refused") == 0);
        got.clear(); CHECK_EQ(Commit(o, 0, send, why), 0); CHECK(got.empty()); CHECK(why.empty());
    }

    // ---- a 20-unit line through the core's LineLayout (brief deliverable 3: the planned rectangles equal the geometry computed here)
    {
        std::vector<gest::Unit> sel;
        for (int i = 0; i < 20; ++i) {   // standing in a line along x facing +z, fronts at z = 0, 35 m apart, in reverse id order
            GestureUnitIn u; std::string w;
            CHECK(UnitIn(Standing((uint32_t)(100 + i), 35.0 * (19 - i), -0.875, 0, 31.9, 1.75), u, w));
            sel.push_back(ToCore(u));
        }
        const gest::V2 a{ -30, 50 }, b{ 30, 50 };   // a 60 m line, 50 m ahead
        const gest::Layout L = gest::LineLayout(sel, a, b, kShortDragM);
        CHECK(!L.shortDrag); CHECK(Near(L.length, 60)); CHECK(Near(L.bearing, 0, 1e-9));
        auto flat = [](double, double, double* y) { *y = 10; return true; };
        auto check = [](const gest::Unit& t, std::string& w) { return Placeable(ToOut(t), w); };
        const std::vector<gest::UnitPlan> plan = gest::MakePlan(L.t, flat, check);
        CHECK_EQ(gest::RefusedCount(plan), (size_t)0);
        const std::vector<gest::Order> ord = gest::OrdersOf(plan);
        CHECK_EQ(ord.size(), (size_t)20);
        // left to right across +z is +x: the unit standing furthest left (id 119, x = 0) takes the first 3 m share
        for (const gest::Order& o : ord) {
            const int k = 119 - (int)o.id;   // its rank from the left
            const MoveArgs m = MoveOf(GestureOrderOut{ o.id, o.x, o.z, o.bearing, o.width });
            CHECK(Near(m.x, -30 + 3.0 * k + 1.5, 1e-4)); CHECK(Near(m.z, 50, 1e-4));   // front centre on the drawn line
            CHECK(Near(m.facing, 0, 1e-9)); CHECK(Near(m.width, 3.0, 1e-5));
        }
        // the clamp floor packs a line too short for the minimums: 20 units on a 10 m line stand 1 m wide, edge to edge, centred
        const gest::Layout P = gest::LineLayout(sel, gest::V2{ -5, 50 }, gest::V2{ 5, 50 }, kShortDragM);
        double lo = 1e9, hi = -1e9;
        for (const gest::Unit& t : P.t) { CHECK(Near(t.width, 1.0)); lo = std::fmin(lo, t.x - 0.5); hi = std::fmax(hi, t.x + 0.5); CHECK(Near(t.z, 50)); }
        CHECK(Near(lo, -10, 1e-6)); CHECK(Near(hi, 10, 1e-6));
        // a refused target is drawn red and skipped: no ground under the right half
        auto half = [](double x, double, double* y) { *y = 10; return x < 0.5; };
        const std::vector<gest::UnitPlan> hp = gest::MakePlan(L.t, half, check);
        CHECK_EQ(gest::RefusedCount(hp), (size_t)10); CHECK_EQ(gest::OrdersOf(hp).size(), (size_t)10);
    }

    // ---- the rotate pivot. KNOWN GAP (core): gesture_math.h FootDepth floors every depth at 4 m and UnitCentre uses it, so a front-
    // referenced unit's centre is taken 2 m behind its front when Napoleon's real line is 0.875 m: the pivot sits 1.125 m behind the true
    // centre and a quarter turn moves the true block centre 1.59 m (J29 walk (b) asks for 0.6). Deep blocks (4 m or more) are exact.
    // This check flips when the core changes the rule: then re-check walk (b)'s expectation (J29 PC plan).
    {
        auto drift = [](double depth) {
            std::vector<gest::Unit> sel;
            for (int i = 0; i < 20; ++i) { GestureUnitIn u; std::string w; UnitIn(Standing((uint32_t)i, 35.0 * i, 0, 0, 31.9, depth), u, w); sel.push_back(ToCore(u)); }
            const std::vector<gest::Unit> t = gest::OrbitPose(sel, gest::RotatePivotFwd(sel, kPivotFwdM), 90.0);
            double bx = 0, bz = 0, ax = 0, az = 0;
            for (size_t i = 0; i < sel.size(); ++i) {
                const gest::V2 f0 = gest::Facing(sel[i].bearing), f1 = gest::Facing(t[i].bearing);
                bx += sel[i].x - f0.x * depth / 2; bz += sel[i].z - f0.z * depth / 2;   // true centres: half the real depth behind the front
                ax += t[i].x - f1.x * depth / 2; az += t[i].z - f1.z * depth / 2;
                CHECK(Near(gest::Wrap180(t[i].bearing - sel[i].bearing), 90, 1e-9));
            }
            return std::hypot(ax - bx, az - bz) / (double)sel.size();
        };
        const double d1 = drift(1.75);
        CHECK(Near(d1, (4.0 - 1.75) / 2 * std::sqrt(2.0), 1e-6)); CHECK(d1 > 0.6);
        CHECK(drift(5.3) < 1e-6);
    }

    // ---- the pick with Napoleon's camera (70 degrees vertical, 1920x1080): picked point projects back onto the cursor; draped on a slope
    {
        gest::Camera c; c.pos = gest::V3{ 0, 40, -60 }; c.target = gest::V3{ 0, 0, 40 }; c.fovYDeg = kFovYDeg; c.w = 1920; c.h = 1080;
        double vp[16]; CHECK(gest::CameraVP(c, vp));
        auto slope = [](double x, double z, double* y) { *y = 0.087 * z + 0.02 * x; return true; };
        double worst = 0; int n = 0;
        for (int py = 490; py <= 1060; py += 190) for (int px = 20; px <= 1900; px += 470) {
            gest::V3 hit; double res = 0;
            if (!gest::PickGround(px, py, 0.0, vp, 1920, 1080, slope, 12, &hit, &res)) continue;
            double sx = 0, sy = 0; CHECK(gest::WorldToScreen(hit, vp, 1920, 1080, &sx, &sy));
            worst = std::fmax(worst, std::hypot(sx - px, sy - py)); ++n;
            double gy = 0; slope(hit.x, hit.z, &gy); CHECK(std::fabs(gy - hit.y) < 0.05);
        }
        CHECK(n >= 15); CHECK(worst < 1e-6);
    }
    return tk::Done("test_gesture_napoleon");
}
