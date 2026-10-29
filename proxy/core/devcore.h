#pragma once
// Dev control: pure core (no Windows headers; host tests in proxy/tests/test_dev.cpp). Drivers: dev.cpp (state file, control
// channel, autostart, reset), luabridge.cpp (the engine's Lua side), timeline.cpp.
//   - UTC formatting and JSON escaping
//   - the phase timeline (one per launch: logs\timeline.json)
//   - the scene tracker (intro | frontend | loading | campaign | battle_deploy | battle | naval), fed by the Lua pumps, the battle
//     probe, load requests and the movie events; ported from empire-remastered rml_mod/src/devspeed.cpp ComputeScene
//   - the control channel grammar: request ids, verbs, autostart/reset targets, the result JSON
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

namespace wsp {

inline std::string TrimS2(const std::string& s) {
    size_t a = 0, b = s.size();
    while (a < b && (s[a] == ' ' || s[a] == '\t')) ++a;
    while (b > a && (s[b - 1] == ' ' || s[b - 1] == '\t')) --b;
    return s.substr(a, b - a);
}
inline std::vector<std::string> SplitBar(const std::string& s) {
    std::vector<std::string> v; std::string cur;
    for (char c : s) { if (c == '|') { if (!cur.empty()) v.push_back(cur); cur.clear(); } else cur += c; }
    if (!cur.empty()) v.push_back(cur);
    return v;
}

// ---- UTC and JSON ---------------------------------------------------------------------------------------------------------
inline void CivilFromDays(int64_t z, int& y, unsigned& m, unsigned& d) {   // Howard Hinnant's algorithm, days since 1970-01-01
    z += 719468;
    const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
    const unsigned doe = (unsigned)(z - era * 146097);
    const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    y = (int)(yoe + era * 400);
    const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    const unsigned mp = (5 * doy + 2) / 153;
    d = doy - (153 * mp + 2) / 5 + 1;
    m = mp < 10 ? mp + 3 : mp - 9;
    if (m <= 2) ++y;
}
inline std::string UtcIso(int64_t unixMs) {   // 2026-10-29T08:01:02.345Z
    if (unixMs < 0) return "";
    int64_t days = unixMs / 86400000; int64_t rem = unixMs % 86400000;
    int y; unsigned mo, d; CivilFromDays(days, y, mo, d);
    char b[40];
    snprintf(b, sizeof b, "%04d-%02u-%02uT%02d:%02d:%02d.%03dZ", y, mo, d, (int)(rem / 3600000), (int)(rem / 60000 % 60), (int)(rem / 1000 % 60), (int)(rem % 1000));
    return b;
}
inline std::string JsonEsc(const std::string& s) {
    std::string o; o.reserve(s.size() + 8);
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { o += '\\'; o += (char)c; }
        else if (c == '\n') o += "\\n";
        else if (c == '\r') o += "\\r";
        else if (c == '\t') o += "\\t";
        else if (c < 32) { char b[8]; snprintf(b, sizeof b, "\\u%04x", c); o += b; }
        else o += (char)c;
    }
    return o;
}
inline std::string JStr(const std::string& s) { return "\"" + JsonEsc(s) + "\""; }

// ---- phase timeline -------------------------------------------------------------------------------------------------------
struct PhaseMark { std::string phase, detail; int64_t utcMs; };
struct Timeline {
    std::string launchId;
    int64_t processStartMs = -1;   // from the OS (process creation time)
    std::vector<PhaseMark> marks;
    static const size_t kMax = 400;
    bool Add(const std::string& phase, const std::string& detail, int64_t utcMs) {
        if (marks.size() >= kMax) return false;
        marks.push_back({ phase, detail, utcMs });
        return true;
    }
    bool Has(const std::string& phase) const { for (const auto& m : marks) if (m.phase == phase) return true; return false; }
    std::string Json() const {
        std::string j = "{\n  \"launch_id\": " + JStr(launchId) + ",\n  \"process_start_utc\": " + JStr(UtcIso(processStartMs)) +
                        ",\n  \"phases\": [";
        for (size_t i = 0; i < marks.size(); ++i) {
            const auto& m = marks[i];
            char t[32]; snprintf(t, sizeof t, "%lld", (long long)(processStartMs >= 0 ? m.utcMs - processStartMs : -1));
            j += std::string(i ? ",\n" : "\n") + "    {\"phase\": " + JStr(m.phase) + ", \"utc\": " + JStr(UtcIso(m.utcMs)) + ", \"t_ms\": " + t +
                 (m.detail.empty() ? std::string() : ", \"detail\": " + JStr(m.detail)) + "}";
        }
        j += "\n  ]\n}\n";
        return j;
    }
};

// ---- scenes ---------------------------------------------------------------------------------------------------------------
inline const char* const* SceneNames() {
    static const char* const n[] = { "intro", "frontend", "loading", "campaign", "battle_deploy", "battle", "naval", nullptr };
    return n;
}
inline bool IsSceneName(const std::string& s) { for (const char* const* p = SceneNames(); *p; ++p) if (s == *p) return true; return false; }

// Times are seconds on one monotonic clock. Not thread-safe: the driver holds a lock.
struct SceneTracker {
    static constexpr double kPumpFresh = 1.5;     // a context whose pumps stopped for longer reads as not live
    static constexpr double kBattleFresh = 3.0;   // battle probe reports older than this are ignored
    std::string ctx;                              // last pumping context: frontend | campaign | battle ("" = no Lua seen)
    double lastPump = -1, ctxSince = -1;
    bool frontendSeen = false;                    // a front-end pump, or the front-end background movie opened
    bool frontendMovieOpen = false, frontendMovieSeen = false;
    std::string loadTarget;                       // a requested load (autostart, reset) not reached yet: "" none
    int naval = -1, deployPanel = -1; double battleT = -1;
    std::string scene = "intro"; double sceneSince = 0;

    void OnPump(const std::string& c, double now) {
        if (c != ctx) { ctx = c; ctxSince = now; }
        lastPump = now;
        if (c == "frontend") frontendSeen = true;
        if (!loadTarget.empty() && (loadTarget == c)) loadTarget.clear();
    }
    // The front end's background movie opening means the front end is up, whatever pumped last (after a battle the front end may
    // come back on a screen that does not pump: run 20261029_j3pc).
    void OnFrontendMovie(bool open, double) {
        frontendMovieOpen = open;
        if (!open) return;
        frontendMovieSeen = true; frontendSeen = true;
        if (ctx != "frontend") { ctx = "frontend"; lastPump = -1; }
        if (loadTarget == "frontend") loadTarget.clear();
    }
    void OnLoadRequested(const std::string& targetCtx) { loadTarget = targetCtx; }
    void OnBattleState(int nav, int deploy, double now) { naval = nav; deployPanel = deploy; battleT = now; }

    std::string Compute(double now) const {
        if (!frontendSeen) return "intro";
        const bool fresh = lastPump >= 0 && now - lastPump < kPumpFresh;
        if (fresh && loadTarget.empty()) {
            if (ctx == "battle") {
                if (battleT >= 0 && now - battleT < kBattleFresh) {
                    if (naval == 1) return "naval";
                    if (deployPanel == 1) return "battle_deploy";
                }
                return "battle";
            }
            if (ctx == "campaign" || ctx == "frontend") return ctx;
        }
        if (fresh && !loadTarget.empty() && ctx != loadTarget && ctx == "frontend") return "loading";   // asked to leave the front end
        if (!loadTarget.empty()) return "loading";
        if (ctx == "campaign" || ctx == "battle") return "loading";
        if (ctx.empty() || ctx == "frontend") {
            // no live pump: the front end's sub-screens do not pump; the background movie closing means the front end is gone
            if (frontendMovieSeen && !frontendMovieOpen) return "loading";
            return "frontend";
        }
        return "loading";
    }
    // returns true when the scene changed (the driver logs and timelines it)
    bool Update(double now, std::string* from = nullptr) {
        const std::string s = Compute(now);
        if (s == scene) return false;
        if (from) *from = scene;
        scene = s; sceneSince = now;
        return true;
    }
};

// ---- control channel --------------------------------------------------------------------------------------------------------
// Request <dir>\<id>.cmd (one line: verb and arguments, UTF-8/ASCII); result <dir>\<id>.done (JSON, written last). Ids: 1-64 of
// [A-Za-z0-9._-], not starting with '.' or '_', never reused (the proxy refuses an id it has seen or whose .done exists).
inline bool ValidCtlId(const std::string& id) {
    if (id.empty() || id.size() > 64 || id[0] == '.' || id[0] == '_') return false;
    for (char c : id) if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-')) return false;
    return true;
}

struct Target {   // autostart / reset target
    std::string kind;           // frontend | campaign | battle
    std::string mode;           // campaign: new | continue | save; battle: the preset name
    std::string campaign, faction, save, preset;
    std::string error;
    std::string Ctx() const { return kind; }   // the Lua context that means "arrived"
};
inline std::vector<std::string> SplitColon(const std::string& s) {
    std::vector<std::string> v; std::string cur;
    for (char c : s) { if (c == ':') { v.push_back(cur); cur.clear(); } else cur += c; }
    v.push_back(cur);
    return v;
}
inline bool SafeToken(const std::string& s) {   // names that go into Lua strings and file names
    if (s.empty() || s.size() > 80) return false;
    for (char c : s) if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.' || c == ' ')) return false;
    return s[0] != '.' && s[0] != ' ';
}
//   frontend | campaign:new:<campaign>:<faction> | campaign:continue | campaign:<save> | battle:<preset>
inline Target ParseTarget(const std::string& t) {
    Target r;
    const std::vector<std::string> p = SplitColon(t);
    if (t == "frontend") { r.kind = "frontend"; return r; }
    if (p[0] == "campaign") {
        r.kind = "campaign";
        if (p.size() == 4 && p[1] == "new") {
            r.mode = "new"; r.campaign = p[2]; r.faction = p[3];
            if (!SafeToken(r.campaign) || !SafeToken(r.faction)) r.error = "campaign:new:<campaign>:<faction> needs two plain names";
            return r;
        }
        if (p.size() == 2 && p[1] == "continue") { r.mode = "continue"; return r; }
        if (p.size() == 2 && p[1] != "new") { r.mode = "save"; r.save = p[1]; if (!SafeToken(r.save)) r.error = "bad save name '" + p[1] + "'"; return r; }
        r.error = "campaign target is campaign:new:<campaign>:<faction>, campaign:continue or campaign:<save>";
        return r;
    }
    if (p[0] == "battle") {
        r.kind = "battle";
        if (p.size() == 2 && SafeToken(p[1])) { r.mode = r.preset = p[1]; return r; }
        r.error = "battle target is battle:<preset>";
        return r;
    }
    r.error = "unknown target '" + t + "' (frontend | campaign:... | battle:<preset>)";
    return r;
}

struct CtlRequest {
    std::string verb, arg;     // arg = the rest of the line (log text, file, scenes, target)
    double timeoutS = 0;       // 0 = the verb's default
    std::string error;         // set = refuse with this reason
    Target target;             // autostart / reset
    std::vector<std::string> scenes;   // waitfor
};
inline const char* CtlVerbs() { return "ping, state, log <text>, lua <file> [timeout_s], waitfor <scene>[|<scene>] [timeout_s], autostart <target> [timeout_s], reset <target> [timeout_s], console <line>|status|on|off, exit"; }
inline double CtlDefaultTimeout(const std::string& verb) {
    return verb == "lua" || verb == "console" ? 30 : verb == "waitfor" ? 180 : (verb == "autostart" || verb == "reset") ? 240 : 10;
}

inline bool ParseTrailingTimeout(std::string& rest, double& t) {   // "x y 30" -> rest "x y", t 30; false when no number at the end
    const size_t sp = rest.find_last_of(' ');
    if (sp == std::string::npos) return false;
    const std::string tail = rest.substr(sp + 1);
    if (tail.empty()) return false;
    for (char c : tail) if (!((c >= '0' && c <= '9') || c == '.')) return false;
    t = atof(tail.c_str());
    rest = TrimS2(rest.substr(0, sp));
    return true;
}

inline CtlRequest ParseCtl(const std::string& lineIn) {
    CtlRequest r;
    std::string line = lineIn;
    const size_t nl = line.find_first_of("\r\n"); if (nl != std::string::npos) line = line.substr(0, nl);
    if (line.size() >= 3 && (unsigned char)line[0] == 0xEF && (unsigned char)line[1] == 0xBB && (unsigned char)line[2] == 0xBF) line = line.substr(3);
    line = TrimS2(line);
    const size_t sp = line.find(' ');
    r.verb = line.substr(0, sp);
    r.arg = sp == std::string::npos ? "" : TrimS2(line.substr(sp + 1));
    const std::string& v = r.verb;
    if (v.empty()) { r.error = "empty request (verbs: " + std::string(CtlVerbs()) + ")"; return r; }
    if (v == "ping" || v == "state" || v == "exit") { if (!r.arg.empty()) r.error = v + " takes no argument"; return r; }
    if (v == "log") { if (r.arg.empty()) r.error = "log needs a text"; return r; }
    if (v == "lua") {
        ParseTrailingTimeout(r.arg, r.timeoutS);
        if (r.arg.empty()) r.error = "lua needs a file (relative to the game folder or absolute)";
        else if (r.arg.find('"') != std::string::npos || r.arg.find('\n') != std::string::npos) r.error = "bad file name";
        return r;
    }
    if (v == "waitfor") {
        ParseTrailingTimeout(r.arg, r.timeoutS);
        for (const std::string& s : SplitBar(r.arg)) {
            if (!IsSceneName(s)) { r.error = "waitfor: unknown scene '" + s + "' (intro frontend loading campaign battle_deploy battle naval)"; return r; }
            r.scenes.push_back(s);
        }
        if (r.scenes.empty()) r.error = "waitfor needs a scene";
        return r;
    }
    if (v == "autostart" || v == "reset") {
        ParseTrailingTimeout(r.arg, r.timeoutS);
        r.target = ParseTarget(r.arg);
        if (!r.target.error.empty()) r.error = v + ": " + r.target.error;
        return r;
    }
    if (v == "console") {   // the line itself is checked by ParseConsoleLine (console.h); no trailing timeout: numbers are arguments
        if (r.arg.empty()) r.error = "console needs a command line or status|on|off";
        return r;
    }
    r.error = "unknown verb '" + v + "' (verbs: " + std::string(CtlVerbs()) + ")";
    return r;
}


} // namespace wsp
