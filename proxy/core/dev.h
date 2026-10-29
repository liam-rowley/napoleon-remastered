#pragma once
// Internal interface between the dev-side drivers (dev.cpp, files.cpp, luabridge.cpp). Game-agnostic: the game's specifics come
// from Adapter().dev. Everything here is inert unless DevActive(): a dev key is on AND the guard's plan allows engine hooks.
#include "runtime.h"
#include "devcore.h"
#include "filerules.h"

namespace wsp {

struct DevKeys {
    bool timeline = false, logFiles = false, skipIntro = false, stateJson = false, luaBridge = false, ctl = false;
    std::wstring fileRules, ctlDir;
    std::string autostart;
    int autostartDelayMs = 1500;
    bool Any() const { return timeline || logFiles || skipIntro || stateJson || luaBridge || ctl || !fileRules.empty() || !autostart.empty(); }
};
DevKeys& Dk();
bool DevActive();

// dev.cpp
void TlMark(const char* phase, const std::string& detail = std::string());
void TlMarkOnce(const char* phase, const std::string& detail = std::string());
void DevPump(const std::string& ctx);                 // the engine's Lua thread, every wrapped OnUpdate/OnUpdatePulse
void DevBattleState(int naval, int deployPanel);
void DevFrontendMovie(bool open);
void DevReport(const std::string& key, const std::string& value);   // wsp.report(): facts the Lua side sees (map, campaign, ...)
std::string DevConfigValue(const std::string& key);   // wsp.dev_config(): target.*, preset.*, lua_dir
void DevPresent();                                    // the render thread, every Present

// files.cpp
void FilesInit(std::vector<FileRule> rules);          // installs the exe's IAT hooks the rules and keys need
bool FilesVanillaEntry(const std::string& lowerPath, std::string& bytes, std::string& err);   // newest real pack holding it
int  FilesMoviesSkipped();
int  FilesMoviesOpened();
void FilesOnDirect3DCreate();                         // binkw32 is loaded by then

// luabridge.cpp
struct LuaCmd { std::string id, verb, arg, ctx; };   // ctx: only a pump of this context takes it ("" = any)
void BridgeQueue(const LuaCmd& c);
bool BridgeTakeResult(const std::string& id, bool& ok, std::string& text);
void BridgeDrop(const std::string& id);               // a timed-out command: forget its result if it ever arrives
bool BridgeLoaded();                                  // luaopen ran on an engine state
double BridgeLastPumpS();                             // MonoS of the last pump (-1 none)
std::string BridgeLastCtx();

} // namespace wsp
