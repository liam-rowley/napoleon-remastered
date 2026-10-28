#pragma once
// The game adapter contract: everything game-specific the core needs, supplied by proxy/<game>/adapter.cpp (identity pin, engine
// sites, config keys, names and folders). proxy/core never names a game, a path inside a game or an address (it moves to
// warscape-core at the end of phase 1).
#include <cstddef>
#include "guard.h"
#include "patch_engine.h"
#include "config.h"

namespace wsp {

struct GameAdapter {
    const char*    gameName;        // shown in the log and the notice
    const wchar_t* configFile;      // file name next to the exe
    const wchar_t* modDir;          // folder name next to the exe (logs, dumps, dxvk, the notice)
    const wchar_t* instanceMutex;   // named mutex: one live log per game
    Identity       identity;        // generated from proxy/<game>/identity.json
    const SiteDef* sites; size_t nSites;     // generated from the engine_sites registry
    const KeySpec* keys;  size_t nKeys;      // generated from the config_keys registry
};

const GameAdapter& Adapter();   // defined by the game's adapter.cpp

} // namespace wsp
