-- probes/battle_route.lua - dev (J4): where does the battle script API (empire_battle, battle_manager, camera) live relative to the pumping UI script?
-- purpose: try the routes to the battle script objects from the UI environment: globals, require of the game's Scripting_Library, other tables
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/battle_route.lua" in a battle
-- when: deliverable 1 of J4 (route probe)
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local out = {}
local function add(k, v) out[#out + 1] = k .. "=" .. tostring(v) end
local env = getfenv(1)
local hits = {}
for k, v in pairs(env) do
	local s = tostring(k):lower()
	if s:match("battle") or s:match("camera") or s:match("empire") or s:match("script") or s:match("vector") or s:match("alliance") then   -- match, never find (fact napoleon.lua.string_find_stalls_pump) hits[#hits + 1] = tostring(k) .. ":" .. type(v) end
end
table.sort(hits); add("globals_matching", table.concat(hits, ","))
add("G_same_as_env", env == _G)
local ok, e = pcall(require, "Scripting_Library"); add("require_Scripting_Library", ok and "ok" or e)
add("empire_battle_after", type(empire_battle)); add("battle_manager_after", type(battle_manager))
add("package_path", package and package.path or "nil")
local loaded = {}
if package and package.loaded then for k, _ in pairs(package.loaded) do loaded[#loaded + 1] = tostring(k) end end
table.sort(loaded); add("package_loaded", table.concat(loaded, ","))
for _, name in ipairs({ "BattleUI", "Battle", "BattleScript", "battle_ui", "CampaignUI" }) do
	local t = env[name]
	if type(t) == "table" then
		local ks = {}; for k, _ in pairs(t) do ks[#ks + 1] = tostring(k) end
		table.sort(ks); add(name, table.concat(ks, ","))
	else add(name, type(t)) end
end
return table.concat(out, " | ")
