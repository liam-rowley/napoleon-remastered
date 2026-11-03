-- probes/napoleon_battles.lua - dev discovery (J46): the "Napoleon's Battles" screen: each battle's icon state (lock/unlock/medal) and
--          EnumerateNapoleonsBattleMaps' fields
-- purpose: show why a single-player historical battle can or cannot be started from the front end on this PC
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/napoleon_battles.lua 30" in the front end
-- when: J46 historical cause; rerun after a profile or DLC change
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local out = {}
local r = UIComponent(Component.Root())
r:LuaCall("TransitionTo", "napoleon_battles")
local pg = UIComponent(r:Find("napoleon_battles"))
local mapp = UIComponent(pg:Find("map_panel"))
local list = FrontEnd.EnumerateNapoleonsBattleMaps()
for _, m in ipairs(list) do
	local f = {}
	for k, v in pairs(m) do
		if type(v) ~= "table" and type(v) ~= "userdata" then f[#f + 1] = tostring(k) .. "=" .. tostring(v) end
	end
	table.sort(f)
	local ic = mapp:Find(m.Key, false)
	out[#out + 1] = tostring(m.Key) .. " state=" .. tostring(ic and UIComponent(ic):CurrentState()) .. " {" .. table.concat(f, ",") .. "}"
end
pcall(function() r:LuaCall("TransitionTo", "main") end)
return table.concat(out, " | ")
