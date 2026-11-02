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
    "campaign.handler_gate_test", 2,         // cmp byte [edi + 0x54], 0  (113 of 168 acting handlers; set in a live campaign)
    gen::kConsoleNoOps, gen::kConsoleSystem };
// The battle camera setter (J43, static RE and probes in harness/runs/20261030_j43pc): every number is inside the named engine_sites
// row's stock bytes (proxy/tests/test_camera.cpp checks each against the generated table).
const CameraAdapter kCamera = {
    "battle.camera_chain_read", 1, 10, 16,   // mov eax, [owner global]; ...; mov eax, [eax + 0xf8]; mov eax, [eax + 0x281b8]
    "battle.camera_mode_read", 2,            // mov ecx, [esi + 0x800]  (the controller's active mode)
    "battle.camera_set_target_pos", 47,      // vtable slot 0xbc: SetTargetAndPosition(target*, pos*)
    100.0f };                                // target 100 m along the forward vector (any distance gives the same view)
// The battle unit control route (J28, static RE in harness/runs/20261101_j9pc/j28_candidates.md, PC runs in harness/runs/20261102_j28pc):
// every operand is inside the named engine_sites row's stock bytes (proxy/tests/test_orders.cpp in the core checks each against the
// generated table). Front centre and width have no engine accessor: UNIT+0x310 / +0x324 are proven by order readback (J28 run).
const OrdersAdapter kOrders = {
    "battle.ui_queue_site", 1, 9, 15,          // mov eax, [owner global]; push ecx; push esp; mov eax, [eax + 0xf8]; mov esi, [eax + 0x28048]
    "battle.selection_dispatch", 16, 28,       // mov eax, [ecx + 0x450] (holder); ...; add eax, 0x20 (the UI selection S)
    "battle.selection_add_unit", 30, 8, 0xc,   // lea ecx, [edi + 0x14] (loose units); vector count +8, data +0xc
    "battle.unit_entity_index", 2, 18,         // cmp [ecx + 0xae8], 0; ...; mov ecx, [ecx + eax*4 + 0xadc]
    "battle.entity_has_order", 2,              // cmp [ecx + 0x460], 0
    "battle.unit_position_get", 8, 14,         // mov ecx, [eax + 0xadc]; lea ecx, [ecx + 0x62c]
    "battle.position_xyz", 2,                  // lea eax, [ecx + 0xb0]
    "battle.world_position_copy", 2,           // mov eax, [ecx + 0x10]  (frame)
    "battle.unit_bearing_get", 19,             // movsx eax, word [eax + 0x64c]
    "battle.unit_men_get", 5,                  // push [ecx + 0x204]
    "battle.unit_army_list", 7, 13, 23,        // mov eax, [ecx + 0x1ec]; mov edx, [eax + 0xf0]; ...; mov eax, [eax + 0xf4]
    0x310, 0x324,                              // front centre, width (readback-proven)
    "battle.selection_ctor", "battle.order_move_ctor", "battle.order_move_push", "battle.command_dtor", "guard.engine_free",
    0x44, 0x74, { 0x10, 0x20, 0x30, 0x40 },    // Selection and move command sizes; the selection's four vector data pointers
    "battle.ground_chain", 25, 28,             // mov eax, [eax + 8]; mov ecx, [eax + 0xb4]
    "battle.ground_project" };
const DevAdapter kDev = { kIntroMovies, kFrontendMovies, kLuaRules, "napoleon_remastered\\lua\\", "data\\battleterrain\\presets\\", "data\\*.pack" };
}

const GameAdapter& Adapter() {
    static const GameAdapter a = { gen::kGameName, gen::kConfigFile, gen::kModDir, gen::kInstanceMutex, gen::kIdentity,
                                   gen::kSites, gen::kSiteCount, gen::kKeys, gen::kKeyCount, &kDev, &kConsole, &kCamera, &kOrders };
    return a;
}

} // namespace wsp
