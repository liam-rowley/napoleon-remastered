# Napoleon.exe UI-facing Lua C functions: addresses and static argument counts (J9)

Static read of `Napoleon.exe` sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`, ImageBase 0x400000, 2026-11-01. Nothing was run, launched or edited. Machine-readable twin: `lua_cfuncs.json`. Regenerate (intermediates go to a temp folder `$LUA_TMP`): `<re venv python> -I py/lua_scan.py $LUA_TMP/lua_scan_raw.json`; from the napoleon-remastered checkout `python3 -I py/lua_vanilla_counts.py $LUA_TMP/lua_vanilla_counts.json` and `python3 -I py/lua_vanilla_all.py $LUA_TMP/lua_vanilla_all.json`; then `LUA_TMP=... python3 py/lua_final.py` and `python3 py/lua_md.py` (about 15 s in all). Every address is a candidate until an engine_sites row with anchor bytes is checked on the PC.

## Method

1. **Lua core.** I took masked byte signatures (relocated dwords and rel32 targets wildcarded) of Empire's known lapi/lauxlib functions (`empire-remastered/.../lua_api/lapi_map.py`) and searched Napoleon's .text: 39 of 39 hit uniquely. The whole block sits at Empire + 0xE1B70 and is linked in alphabetical order, so I named the other lapi/lauxlib functions from that order plus their callees (for example `lua_next` calls luaH_next, `lua_rawgeti` calls luaH_getnum, `lua_remove` follows `lua_rawseti`). `lua_core` in the JSON lists 85; the 39 signature hits are certain, the rest are named from layout and shape.
2. **Bindings.** CampaignUI / BattleUI / FrontEnd are static registrars: `push doc; push name; push func; mov ecx,<static>; call <registrar>` with registrar 0x998c50 = CampaignUI (339), 0x59eb40 = BattleUI (218), 0x4587a0 = FrontEnd (118), the same shape as Empire. The doc strings are copied into the JSON. Other tables: `luaL_Reg` arrays (Component at 0x13f1a38, filled by its own loop; UniChar, out, Keyboard via `luaL_register`); Lunar classes (8-byte {name, member fn}, 24-byte {name, 0, member pointer}, or 16-byte tables filled at start-up by `mov [entry+8], fn`), each named from the `luaL_typerror` class string in its dispatch thunk; Lunar constructors (the closure stored as both `new` and `__call`); stack-built arrays for DirectoryUtils and Localisation. I skipped the battle script classes (battle.unit etc., 0x1451400..0x1452000, ui_component, empire_battle), because another agent maps them. The Lunar thunk calls `lua_remove(L, 1)` before the method, so method counts exclude `self` and compare directly with J6's method signatures.
3. **Argument model (important).** Engine bindings do not read `lua_to*(L, n)`. They fetch an argument stream with `0x1058750(L)` and read it with operator>> helpers. Each helper reads index **-1** and then pops it (`lua_settop(L,-2)`): 0x1055760 string, 0x1055840 bool, 0x1055700 number (0x10556d0 = number to int), 0x44d320 / 0x10557e0 pointer, and 0x10558b0 opens a table on top. **Arguments are consumed from the last one backwards**. A binding that reads N values and is called with more than N reads the *trailing* arguments, which puts every value in the wrong slot, unless it branches on `lua_gettop` or on the type of the top value (both are flagged per entry). Called with fewer, it reads past the frame: the reader's type check fails and later reads are skipped.
4. **Counting.** A reader op is a function that reads index -1 and pops without building a table. For each binding I walk its CFG once per acyclic path (back edges ignored) and track the Lua stack level: the counted value is the lowest level reached, so a getfield/read/pop field read nets 0. Callee contributions count only for wrappers of 80 instructions or fewer, or for callees that fetch the argument stream themselves. `static_args` is the maximum over paths. `static_args_min` is the minimum over paths that fetched the stream: a lower value there means optional arguments. It is **null** in these cases: a read sits inside a loop, the function forwards arguments with `lua_pcall` and a computed count, it reads by a computed index inside a loop, or most vanilla call sites disagree (see validation). Functions of four instructions or fewer that touch no argument are `stub` (count 0, extras ignored). Plain `lua_CFunction`s that read constant indices are reported as `index`.

## Counts per table

| table | kind | entries | with static count | null |
|---|---|---:|---:|---:|
| FrontEnd | registrar | 118 | 115 | 3 |
| BattleUI | registrar | 218 | 215 | 3 |
| CampaignUI | registrar | 339 | 336 | 3 |
| Keyboard | luaL_register | 3 | 3 | 0 |
| Component | luaL_Reg (own registration loop at 0x1027200) | 28 | 25 | 3 |
| UniChar | luaL_register | 2 | 2 | 0 |
| out | luaL_register | 6 | 6 | 0 |
| UIHistoricBattleSetup | lunar | 3 | 3 | 0 |
| UIMPInterface | lunar | 30 | 30 | 0 |
| ChatRoomInterface | lunar | 6 | 6 | 0 |
| BattleUnit | lunar | 7 | 7 | 0 |
| BattleShip | lunar | 6 | 6 | 0 |
| GAME | lunar | 95 | 95 | 0 |
| CampaignCharacter | lunar | 4 | 4 | 0 |
| CampaignSettlement | lunar | 5 | 5 | 0 |
| UIDiplomacyNegotiation | lunar | 21 | 21 | 0 |
| UIPrefsInterface | lunar | 29 | 28 | 1 |
| MPAvatar | lunar | 4 | 4 | 0 |
| MultiplayerPlayerInterface | lunar | 5 | 5 | 0 |
| Cursor | lunar | 6 | 6 | 0 |
| UIComponent | lunar | 77 | 69 | 8 |
| UIComponentImageMetrics | lunar | 5 | 5 | 0 |
| UICardManager | lunar | 21 | 15 | 6 |
| UIPaletisedImage | lunar | 6 | 6 | 0 |
| UIImage | lunar | 6 | 6 | 0 |
| UISelectionManager | lunar | 7 | 7 | 0 |
| UIBattleSetup | lunar+runtime_init | 5 | 5 | 0 |
| UIFEDropInInterface | lunar+runtime_init | 5 | 5 | 0 |
| UIMPDropInInterface | lunar+runtime_init | 9 | 9 | 0 |
| ChatManager | lunar+runtime_init | 3 | 3 | 0 |
| BlockedPlayers | lunar | 1 | 1 | 0 |
| UIComponentState | lunar | 1 | 1 | 0 |
| Localisation | stack_luaL_Reg | 1 | 1 | 0 |
| DirectoryUtils | stack_luaL_Reg | 2 | 2 | 0 |
| **total** | | **1084** | **1057** | **27** |

Basis: auto 1013, stub 38, null 26, manual 4, index 3. "UIComponent" is the Lunar class behind `UIComponent(address)` objects (component methods). GAME is the campaign episodic-scripting class (not UI, included because it was met).

## Validation against vanilla call sites

I compared each static range [min if the binding checks gettop or the top type, else max .. max] with every non-open call site in Napoleon's vanilla `ui/*.luac`, using J6's inventory with open `f(...)` calls marked. For table functions the match is by Table.name; for methods, only by method names that are unique across the classes. **10015 call sites fall inside the range and 460 outside.** 15 bindings had at least half of their call sites outside the range, so their count is withheld (null). Some are model misses: a value read through an indirect call, or a variadic reader such as `Component.CallByAddress`, `UIComponent:SequentialFind`, `UIComponent:SetGlobal` or `Component.SetProperty`. Others have one or two sites each and may be real script mistakes:

| binding | va | static range | vanilla counts outside | inside |
|---|---|---|---|---:|
| FrontEnd.LoadBattleSetup | 0x4709f0 | 0..0 | 1 x3 | 0 |
| FrontEnd.MPLogOn | 0x475450 | 1..1 | 0 x1 | 1 |
| FrontEnd.SaveBattleSetup | 0x478100 | 1..2 | 3 x4 | 0 |
| BattleUI.CameraZoomToSelection | 0x5cebc0 | 2..2 | 1 x1 | 0 |
| BattleUI.CreateUnitGroup | 0x5cf230 | 2..2 | 1 x1 | 0 |
| BattleUI.SelectUnitBasedOnUnitType | 0x5d3370 | 2..2 | 1 x1 | 0 |
| CampaignUI.DemolishBuilding | 0x9e2380 | 1..1 | 2 x1 | 1 |
| CampaignUI.UpdateRadarView | 0x9fae60 | 0..0 | 1 x1 | 0 |
| Component.SetProperty | 0x1016a00 | 1..1 | 2 x20 | 0 |
| Component.CallByAddress | 0x1018300 | 1..1 | 2 x7, 3 x24, 4 x14, 5 x11, 9 x2 | 0 |
| UIPrefsInterface.SetAudioOptions | 0xda1740 | 2..2 | 1 x1 | 0 |
| UIComponent.Adopt | 0x1014580 | 4..5 | 1 x12, 2 x2 | 0 |
| UIComponent.Divorce | 0x1014610 | 4..4 | 1 x41 | 0 |
| UIComponent.SequentialFind | 0x1015060 | 1..1 | 2 x6, 3 x1 | 0 |
| UIComponent.SetGlobal | 0x1015b10 | 1..1 | 2 x306 | 0 |

## J6's 38 argument-count drifts

Vanilla counts were recomputed with J6's own inventory (`discovery/core/lua_api.py`). J6 recorded only the drift flag, not the counts. `...` means an open call (`f(x, g())` / `f(...)`), whose count cannot be known statically; J6 shows these as one `expr`. The Empire counts come from Empire's `engine_api.json`.

| J6 name | binding (va) | static | gettop | Napoleon vanilla {count: sites} | Empire {count: sites} | verdict |
|---|---|---|---|---|---|---|
| `calls:CampaignUI.InitialiseUnitDetails` | CampaignUI.InitialiseUnitDetails (0x9eb470) | 0..5 | y | {'1': 1, '5': 1} | {'1': 1, '4': 1} | real engine change: when lua_gettop()>1 it first reads four trailing strings (a nil is popped instead), then the unit pointer or id string, so 1 or 5 args; Napoleon vanilla uses 1 and 5, Empire used 1 and 4 |
| `calls:CampaignUI.PromoteUnits` | CampaignUI.PromoteUnits (0x9ef360) | 2 |  | {'2': 1} | {'1': 1} | real engine change: reads two pointers (commander/force); Napoleon vanilla passes 2, Empire passed one table |
| `calls:CampaignUI.TheatreList` | CampaignUI.TheatreList (0x9f96c0) | 0..1 | y | {'0': 3, '1': 2} | {'1': 2} | not a real difference: optional bool (read only if the top is a boolean); () and (bool) both fit |
| `calls:ChatManager` | ChatManager.__call (0xdb5940) | 3 | y | {'3': 1} | {'2': 1} | real engine change: the ChatManager constructor reads 3 (bool, pointer, pointer); Napoleon vanilla passes 3, Empire passed 2 |
| `calls:Component.CreateFromLayout` | Component.CreateFromLayout (0x1016bd0) | 3..7 | y | {'...': 3, '3': 13, '4': 4, '5': 29, '6': 1} | {'1': 3, '3': 9, '4': 4, '5': 21} | not a real difference: 3 required + type-checked optional trailing (2 numbers, array table, dict table); every Napoleon and Empire shape fits 3..7 (the 1-arg rows are open f(...) calls) |
| `calls:FrontEnd.CampaignDetails` | FrontEnd.CampaignDetails (0x46bcc0) | 2 | y | {'2': 2} | {'1': 2} | real engine change: reads key and a bool; Napoleon vanilla passes 2, Empire passed 1 |
| `calls:FrontEnd.GenerateRegionOwnershipMaps` | FrontEnd.GenerateRegionOwnershipMaps (0x46f990) | 3..5 | y | {'3': 1, '5': 1} | {'2': 1, '3': 1} | real engine change: 3..5 by lua_gettop (5th = int, 4th = optional second faction); Napoleon vanilla uses 3 and 5, Empire used 2 and 3 |
| `calls:FrontEnd.MPHostCampaign` | FrontEnd.MPHostCampaign (0x473650) | 5 |  | {'5': 1} | {'4': 1} | real engine change: fixed 5; Napoleon vanilla passes 5, Empire passed 4 |
| `calls:FrontEnd.MPQuickBattleStart` | FrontEnd.MPQuickBattleStart (0x475660) | 4 |  | {'4': 1} | {'1': 1} | real engine change: fixed 4 bools; Napoleon vanilla passes 4, Empire passed 1 (the exe doc string still describes one bool) |
| `calls:FrontEnd.RecruitableUnits` | FrontEnd.RecruitableUnits (0x475b00) | 7 | y | {'7': 1} | {'5': 1} | real engine change: fixed 7 (doc string lists 4); Napoleon vanilla passes 7, Empire passed 5 |
| `calls:FrontEnd.StartBattle` | FrontEnd.StartBattle (0x4783e0) | 4..5 | y | {'4': 3, '5': 1} | {'3': 2} | real engine change: 4 or 5 (lua_gettop()==5 adds a bool); Napoleon vanilla uses 4 and 5, Empire used 3 |
| `calls:out.tom` | out.tom (0x461180) | 0 |  | {'...': 10, '1': 63, '10': 3, '2': 23, '3': 4, '4': 7, '5': 3, '6': 2, '7': 1} | {'1': 51, '2': 17, '3': 5, '4': 4, '5': 1, '6': 2} | not a real difference: out.* (shane, dylan, tom, kostas, ting, design) all point at one stub 0x461180 that reads nothing |
| `methods:AddAiBot` | UIMPInterface.AddAiBot (0x44b260) | 2 | y | {'...': 1, '2': 1} | {'1': 2} | real engine change: reads 2 (string + number); Napoleon vanilla passes 2 (one open call), Empire passed 1 |
| `methods:JoinTeam` | UIMPInterface.JoinTeam (0x44b330) | 2 |  | {'2': 1} | {'1': 3} | real engine change: reads 2 numbers; Napoleon vanilla passes 2, Empire passed 1 |
| `methods:LuaCall` | UIComponent.LuaCall (0x1014110) | variadic | y | {'...': 80, '1': 568, '11': 1, '2': 624, '3': 154, '4': 77, '5': 57, '6': 12, '7': 16, '8': 3, '9': 4} | {'1': 594, '10': 1, '2': 550, '3': 123, '4': 79, '5': 57, '6': 14, '7': 10, '8': 2, '9': 4} | not a real difference: variadic forwarder (name at index 1, the rest passed to the script function); counts are per call site |
| `methods:SetImageRotation` | UIComponent.SetImageRotation (0x1015570) | 2..4 | y | {'...': 1, '2': 34, '4': 1} | {'2': 33, '4': 2} | not a real difference: 2 or 4 by lua_gettop()>2; both games use 2 and 4 (the Napoleon 1-arg row is an open f(...) call) |
| `calls:AddPlayerToTeam` | script global | - | | {'9': 1} | {'7': 1} | not an engine function: a Lua global defined in vanilla scripts (mp_battle3.main_panel.luac, mp_battle3_scenario.luac); the drift is a script-side signature change, no exe count applies |
| `calls:BuildTooltip` | script global | - | | {'...': 4, '2': 1} | {'1': 5} | not an engine function: a Lua global defined in vanilla scripts (region_details.luac, template.buildingframe.luac, template.tech_icon.luac +1); the drift is a script-side signature change, no exe count applies |
| `calls:CloseEndTurnFlagsDisplay` | script global | - | | {'1': 1} | {'0': 1} | not an engine function: a Lua global defined in vanilla scripts (layout.root.luac); the drift is a script-side signature change, no exe count applies |
| `calls:Filtered` | script global | - | | {'2': 1, '5': 1} | {'2': 1, '4': 1} | not an engine function: a Lua global defined in vanilla scripts (campaigns.luac, custom_battles.luac); the drift is a script-side signature change, no exe count applies |
| `calls:GenerateUnitCards` | script global | - | | {'...': 2, '3': 1} | {'1': 2} | not an engine function: a Lua global defined in vanilla scripts (units_panel.luac, popup_pre_battle.luac); the drift is a script-side signature change, no exe count applies |
| `calls:InitialiseFromDetails` | script global | - | | {'2': 1} | {'1': 1} | not an engine function: a Lua global defined in vanilla scripts (region_details.luac); the drift is a script-side signature change, no exe count applies |
| `calls:MultiplayerSetButtonTimer` | script global | - | | {'...': 5, '1': 1, '2': 13} | {'1': 6, '2': 11, '3': 1} | not an engine function: a Lua global defined in vanilla scripts (diplomacy_panel.luac, duel challenge received.luac, popup_pre_battle.luac); the drift is a script-side signature change, no exe count applies |
| `calls:OnPlayerJoined` | script global | - | | {'10': 4, '4': 1, '8': 1} | {'4': 1, '8': 3} | not an engine function: a Lua global defined in vanilla scripts (mp_battle3.main_panel.luac, main_panel.luac); the drift is a script-side signature change, no exe count applies |
| `calls:Selected` | script global | - | | {'...': 1, '0': 4} | {'0': 4} | not an engine function: a Lua global defined in vanilla scripts (land_hud_melee.luac, land_hud_move_speed.luac, land_hud_special_ability_button.luac +13); the drift is a script-side signature change, no exe count applies |
| `calls:SelectionUpdate` | script global | - | | {'1': 2} | {'0': 2, '1': 1} | not an engine function: a Lua global defined in vanilla scripts (card_window.luac, prisoners_naval_battle.luac, units_panel.luac); the drift is a script-side signature change, no exe count applies |
| `calls:SendOffString` | script global | - | | {'2': 1} | {'1': 1, '2': 2} | not an engine function: a Lua global defined in vanilla scripts (multiplayer_chat.luac); the drift is a script-side signature change, no exe count applies |
| `calls:SetInProgress` | script global | - | | {'1': 1, '3': 1} | {'0': 2, '1': 1, '2': 1} | not an engine function: a Lua global defined in vanilla scripts (template.tech_icon.luac); the drift is a script-side signature change, no exe count applies |
| `calls:SetTechnologyAsBeingResearched` | script global | - | | {'4': 1} | {'3': 1} | not an engine function: a Lua global defined in vanilla scripts (technology_researching.luac); the drift is a script-side signature change, no exe count applies |
| `calls:SetTechnologyInProgress` | script global | - | | {'4': 1, '5': 1} | {'3': 1, '4': 1} | not an engine function: a Lua global defined in vanilla scripts (technology_common.luac, technology_researching.luac, technology_stealing.luac); the drift is a script-side signature change, no exe count applies |
| `calls:ShowEffectEntries` | script global | - | | {'5': 1} | {'4': 1} | not an engine function: a Lua global defined in vanilla scripts (building_information.luac); the drift is a script-side signature change, no exe count applies |
| `calls:ShowMessageBox` | script global | - | | {'...': 1, '3': 1} | {'3': 1} | not an engine function: a Lua global defined in vanilla scripts (root.luac); the drift is a script-side signature change, no exe count applies |
| `calls:ShowRecruitmentEffectEntries` | script global | - | | {'7': 1} | {'8': 1} | not an engine function: a Lua global defined in vanilla scripts (building_information.luac); the drift is a script-side signature change, no exe count applies |
| `calls:ShowTabSheet` | script global | - | | {'2': 9} | {'1': 2, '2': 9} | not an engine function: a Lua global defined in vanilla scripts (technology_common.luac, technology_researching.luac, technology_stealing.luac); the drift is a script-side signature change, no exe count applies |
| `calls:ShowTradeWindow` | script global | - | | {'4': 2} | {'5': 2} | not an engine function: a Lua global defined in vanilla scripts (government_screens.luac); the drift is a script-side signature change, no exe count applies |
| `calls:ShowUnitInfo` | script global | - | | {'0': 2, '1': 1} | {'1': 1} | not an engine function: a Lua global defined in vanilla scripts (root.luac, layout.root.luac, army_setup_card.luac +1); the drift is a script-side signature change, no exe count applies |
| `calls:SortByColumn` | script global | - | | {'1': 1, '2': 1} | {'1': 2} | not an engine function: a Lua global defined in vanilla scripts (template.building_browser_sortable_list.luac, template.sortable_list.luac); the drift is a script-side signature change, no exe count applies |
| `calls:TransitionTo` | script global | - | | {'1': 6, '2': 1, '3': 3, '5': 2} | {'1': 2, '2': 1, '3': 3, '4': 2} | not an engine function: a Lua global defined in vanilla scripts (root.luac); the drift is a script-side signature change, no exe count applies |

**Summary:** 22 of the 38 are Lua functions defined in the vanilla scripts. The drift there is a script change, not an engine fact. Of the 16 engine functions, **11 are real engine signature changes** (Napoleon's exe reads what Napoleon's scripts pass): CampaignUI.InitialiseUnitDetails, CampaignUI.PromoteUnits, the ChatManager constructor, FrontEnd.CampaignDetails / GenerateRegionOwnershipMaps / MPHostCampaign / MPQuickBattleStart / RecruitableUnits / StartBattle, and UIMPInterface:AddAiBot / JoinTeam. Because of the last-argument-first stream, an Empire-shaped call to these reads the wrong slots. **5 are not real differences**: CampaignUI.TheatreList and SetImageRotation have optional arguments that both games' counts fit; Component.CreateFromLayout has type-checked optional trailing arguments; LuaCall is a variadic forwarder; out.tom is a no-op stub. No vanilla Napoleon call to the 16 falls outside the exe's range.

## Not found, and limits

- **Script names the exe does not register.** These J6 table names are absent from Napoleon.exe's strings, so they are dead calls in vanilla scripts: CampaignUI CanDisembark, CanEmbark, EmbarkOrDisembark, ExecuteCaptives, HideBattleDetails, ImprisonCaptives, PreBattlePlayerSurrenderDecision; BattleUI CurrentSelectionBreakGroup/Group/Halt/Runs/Walks, Current_Selection_Start/Stop_Firing_At_Will, DestroyBattleChat, SelectUnitCard, Shot_Standard, UnitCardAddToGroup, UnitCardBeginsDrag, UnitCardGroupID, UnitCardUngroup, UnselectUnitCard; FrontEnd IsModifier, MPBaseInterface, MPHostLandBattle, MPHostNavalBattle, ModifierHeld, StartDefaultCampaign, StartDefaultFortBattle, StartDefaultLandBattle, StartDefaultSeaBattle. Component methods absent: IsVisible, SetPayRansom, BlockPlayerID, SetDetails, SetFromSetup, SyncProgress (close/read/seek/write are the io library's file methods).
- **Model misses** (why some counts are null or withheld): reads through an indirect (virtual) call; values read with a computed index or with `lua_settop` to a computed level; table helpers above 80 instructions that do not fetch the stream themselves. The full walk, which counts all callees, is kept in `evidence` whenever it differs.
- `lua_gettop` / top-type checks are flags, not proof of optional arguments. `static_args_min` is the path minimum and can include error paths.
- Not in scope: battle script luaL_Reg tables and battle order functions (other J9 agent).
- The runtime check would be the J9 api_surface probe: call each binding with N-1 / N / N+1 arguments on a scratch screen. Not done here (static only).
