// adapter.cpp - Napoleon's adapter for the proxy core: identity pin, engine sites, config keys and names (generated from
// identity.json and the registries: generated/tables.h) and the dev side's game specifics (J3, below).
#include "generated/tables.h"
#include "generated/console_table.h"

namespace wsp {
namespace {
// Start-up movies, from movies.pack's index (media.pack, 2026-10-29) and the file survey (proxy/runs/20261029_j3pc).
const char* const kIntroMovies[] = { "movies\\sega_logo_sting_hd.bik", "movies\\corei7_intro.bik", "movies\\ntw_intro.bik",
                                     "movies\\low_res\\ntw_intro_lowres.bik", nullptr };
// The front end's background movie (scene "frontend" before any Lua pump; closing it means the front end is gone).
const char* const kFrontendMovies[] = { "movies\\frontend.bik", "movies\\frontend2.bik", nullptr };
// dev.lua_bridge: the wrapper scripts reach the engine as a virtual movie-type pack listed in data\ (zero-touch: the file stays in
// napoleon_remastered\packs\); the wrappers then load the bridge files from napoleon_remastered\lua\ with dofile.
const char* const kLuaRules[] = { "add data\\zz_napoleon_remastered_dev.pack -> napoleon_remastered\\packs\\zz_napoleon_remastered_dev.pack", nullptr };
// While a battle loads, the engine probes loose copies of its map's preset folder (run 20261029_j3pc): the map check reads them.
// The campaign console (J15, static RE in proxy/runs/20261029_j15re): every number below is inside the named engine_sites row's
// stock bytes (proxy/tests/test_console.cpp checks each against the generated table).
const ConsoleAdapter kConsole = {
    "console.handler_slot_test", 2,          // cmp dword [slot], 0
    "console.handler_slot_call",             // mov ecx, [slot]; ... call [eax]  (vfunc0(&name, &stream), bool)
    "campaign.owner_global_read", 2, 0x9fc,  // mov ecx, [owner global]; ... mov ecx, [ecx + 0x9fc]
    "campaign.owner_selection_wiring", 0xf4, 8, 0x28,   // lea ecx, [ebx + 0xf4]; mov [ecx], <selection vtable>; ... mov [eax + 0x28], ecx
    "campaign.cli_ctor",
    "campaign.cli_ctor_tail", 13,            // mov [esi], <CampaignCLI vtable>
    0x28, 0x2c,                              // this + 0x28 = *ctx; operator new(0x2c) in the CLI registration
    "campaign.cli_execute", 7,
    "campaign.handler_gate_test", 2,         // cmp byte [edi + 0x54], 0  (113 of 168 acting handlers; retail leaves it 0)
    gen::kConsoleNoOps, gen::kConsoleSystem };
const DevAdapter kDev = { kIntroMovies, kFrontendMovies, kLuaRules, "napoleon_remastered\\lua\\", "data\\battleterrain\\presets\\", "data\\*.pack" };
}

const GameAdapter& Adapter() {
    static const GameAdapter a = { gen::kGameName, gen::kConfigFile, gen::kModDir, gen::kInstanceMutex, gen::kIdentity,
                                   gen::kSites, gen::kSiteCount, gen::kKeys, gen::kKeyCount, &kDev, &kConsole };
    return a;
}

} // namespace wsp
