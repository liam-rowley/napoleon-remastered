#pragma once
// In-process shared state and services of the proxy core (Windows only; the pure parts live in pe.h, sha1.h, guard.h,
// patch_engine.h and config.h). One Runtime per process, filled by dllmain.cpp Init.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <string>
#include "adapter.h"

namespace wsp {

enum class LogLevel : int { Debug = 0, Info = 1, Warn = 2, Error = 3 };

struct Runtime {
    std::wstring gameDir;      // folder of the exe, with a trailing backslash
    std::wstring modDir;       // gameDir + adapter modDir + "\"
    std::wstring configPath;   // gameDir + adapter configFile
    std::string  launchId;     // "20261028T195944Z-p1234": names the log header and every dump of this launch
    Config       cfg;
    bool         enabled = false;     // proxy.enabled and not a second instance
    bool         engineOk = false;    // exe-identity guard verdict (false until it ran)
    EnginePlan   plan;                // PlanEngine(enabled, engineOk): the only switch engine-side code asks
};
Runtime& Rt();

// log.cpp
void LogOpen(const std::wstring& dir, const std::wstring& baseName, LogLevel minLevel);   // rotates <base>.log -> <base>.prev.log
void LogWrite(LogLevel lvl, const char* fmt, ...);
std::wstring LogPath();
#define LOGD(...) ::wsp::LogWrite(::wsp::LogLevel::Debug, __VA_ARGS__)
#define LOGI(...) ::wsp::LogWrite(::wsp::LogLevel::Info, __VA_ARGS__)
#define LOGW(...) ::wsp::LogWrite(::wsp::LogLevel::Warn, __VA_ARGS__)
#define LOGE(...) ::wsp::LogWrite(::wsp::LogLevel::Error, __VA_ARGS__)

// crash.cpp
void CrashInstall(int mode);   // 0 off, 1 unhandled exceptions (default), 2 also the first fatal first-chance exception

// guard_driver.cpp
void GuardRun();               // sets Rt().engineOk and writes or removes the notice

// patch_driver.cpp
void PatchesRun();             // only when Rt().plan.patches

// backend.cpp
bool BackendEnsure();          // loads the configured backend once (never from DllMain); false = no d3d9 at all
const char* BackendName();

std::string Narrow(const std::wstring& w);

} // namespace wsp
