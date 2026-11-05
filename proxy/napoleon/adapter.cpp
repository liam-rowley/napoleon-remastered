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
    .slotSite = "console.handler_slot_test", .slotOperand = 2,          // cmp dword [slot], 0
    .slotCallSite = "console.handler_slot_call",             // mov ecx, [slot]; ... call [eax]  (vfunc0(&name, &stream), bool)
    .ownerSite = "campaign.owner_global_read", .ownerOperand = 2, .ownerCampaignOff = 0x9fc,  // mov ecx, [owner global]; ... mov ecx, [ecx + 0x9fc]
    .wiringSite = "campaign.owner_selection_wiring", .ownerSelectionOff = 0xf4, .selectionVtblOperand = 8, .campaignSelectionOff = 0x28,   // lea ecx, [ebx + 0xf4]; mov [ecx], <selection vtable>; ... mov [eax + 0x28], ecx
    .ctorSite = "campaign.cli_ctor",
    .ctorTailSite = "campaign.cli_ctor_tail", .cliVtblOperand = 13,            // mov [esi], <CampaignCLI vtable>
    .cliCtxOff = 0x28, .cliSize = 0x2c,                              // this + 0x28 = *ctx; operator new(0x2c) in the CLI registration
    .executeSite = "campaign.cli_execute", .executeSlot = 7,
    .gateSite = "campaign.handler_gate_test", .gateOperand = 2,         // cmp byte [edi + 0x54], 0  (113 of 168 acting handlers; set in a live campaign)
    .noOps = gen::kConsoleNoOps, .systemNames = gen::kConsoleSystem };
// The battle camera setter (J43, static RE and probes in harness/runs/20261030_j43pc): every number is inside the named engine_sites
// row's stock bytes (proxy/tests/test_camera.cpp checks each against the generated table).
const CameraAdapter kCamera = {
    .chainSite = "battle.camera_chain_read", .globalOperand = 1, .battleOffOperand = 10, .controllerOffOperand = 16,   // mov eax, [owner global]; ...; mov eax, [eax + 0xf8]; mov eax, [eax + 0x281b8]
    .modeSite = "battle.camera_mode_read", .modeOffOperand = 2,            // mov ecx, [esi + 0x800]  (the controller's active mode)
    .setSite = "battle.camera_set_target_pos", .setSlot = 47,      // vtable slot 0xbc: SetTargetAndPosition(target*, pos*)
    .targetDistance = 100.0f };                                // target 100 m along the forward vector (any distance gives the same view)
// The battle unit control route (J28, static RE in harness/runs/20261101_j9pc/j28_candidates.md, PC runs in harness/runs/20261102_j28pc):
// every operand is inside the named engine_sites row's stock bytes (proxy/tests/test_orders.cpp in the core checks each against the
// generated table). Front centre and width have no engine accessor: UNIT+0x310 / +0x324 are proven by order readback (J28 run).
const OrdersAdapter kOrders = {
    .queueSite = "battle.ui_queue_site", .globalOperand = 1, .battleOperand = 9, .queueOperand = 15,          // mov eax, [owner global]; push ecx; push esp; mov eax, [eax + 0xf8]; mov esi, [eax + 0x28048]
    .uiSelectionSite = "battle.selection_dispatch", .holderOperand = 16, .selOperand8 = 28,       // mov eax, [ecx + 0x450] (holder); ...; add eax, 0x20 (the UI selection S)
    .selAddSite = "battle.selection_add_unit", .selVecOperand8 = 30, .vecCountOff = 8, .vecDataOff = 0xc,   // lea ecx, [edi + 0x14] (loose units); vector count +8, data +0xc
    .entitySite = "battle.unit_entity_index", .activeIdxOperand = 2, .entitiesOperand = 18,         // cmp [ecx + 0xae8], 0; ...; mov ecx, [ecx + eax*4 + 0xadc]
    .entityOrdersSite = "battle.entity_has_order", .orderCountOperand = 2,              // cmp [ecx + 0x460], 0
    .positionSite = "battle.unit_position_get", .posEntityOperand = 8, .posBlockOperand = 14,         // mov ecx, [eax + 0xadc]; lea ecx, [ecx + 0x62c]
    .positionXyzSite = "battle.position_xyz", .xyzOperand = 2,                  // lea eax, [ecx + 0xb0]
    .frameSite = "battle.world_position_copy", .frameOperand8 = 2,           // mov eax, [ecx + 0x10]  (frame)
    .bearingSite = "battle.unit_bearing_get", .bearingOperand = 19,             // movsx eax, word [eax + 0x64c]
    .menSite = "battle.unit_men_get", .menOperand = 5,                  // push [ecx + 0x204]
    .armySite = "battle.unit_army_list", .armyOperand = 7, .armyCountOperand = 13, .armyListOperand = 23,        // mov eax, [ecx + 0x1ec]; mov edx, [eax + 0xf0]; ...; mov eax, [eax + 0xf4]
    .frontOff = 0x310, .widthOff = 0x324,                              // front centre, width (readback-proven)
    .selCtorSite = "battle.selection_ctor", .moveCtorSite = "battle.order_move_ctor", .movePushSite = "battle.order_move_push",
    .cmdDtorSite = "battle.command_dtor", .freeSite = "guard.engine_free",
    .selBytes = 0x44, .cmdBytes = 0x74, .selDataOffs = { 0x10, 0x20, 0x30, 0x40 },    // Selection and move command sizes; the selection's four vector data pointers
    .groundChainSite = "battle.ground_chain", .groundAOperand8 = 25, .groundBOperand = 28,             // mov eax, [eax + 8]; mov ecx, [eax + 0xb4]
    .groundFnSite = "battle.ground_project",
    .cmdCellSite = "battle.selection_dispatch_b", .cmdCellOperand = 12,         // add ecx, 0x454  (the dispatcher's this: a cell holding the battle)
    .cmdSite = "battle.selection_command" };              // dispatcher(sel*, cmd, float, flag): halt, formation toggles (codes in ctl/orders.lua's route)
const DevAdapter kDev = { .introMovies = kIntroMovies, .frontendMovies = kFrontendMovies, .luaRules = kLuaRules, .luaDir = "napoleon_remastered\\lua\\",
                          .mapProbe = "data\\battleterrain\\presets\\", .packGlob = "data\\*.pack" };
}

const GameAdapter& Adapter() {
    static const GameAdapter a = { .gameName = gen::kGameName, .configFile = gen::kConfigFile, .modDir = gen::kModDir, .instanceMutex = gen::kInstanceMutex,
                                   .identity = gen::kIdentity, .sites = gen::kSites, .nSites = gen::kSiteCount, .keys = gen::kKeys, .nKeys = gen::kKeyCount,
                                   .dev = &kDev, .console = &kConsole, .camera = &kCamera, .orders = &kOrders, .gesture = nullptr };
    return a;
}

} // namespace wsp
