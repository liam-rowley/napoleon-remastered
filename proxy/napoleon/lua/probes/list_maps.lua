-- probes/list_maps.lua - dev discovery (J3): log every custom-battle map the front end offers per battle type (Key, Name, File,
-- purpose: log every custom-battle map the front end offers per battle type (Key, Name, File, naval)
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/list_maps.lua" in the front end
-- when: to pick or check a battle preset's map key
-- not-a-verb: runs inside the game's own Lua, not on a host
-- IsNaval). Run in the front end:  ctl `lua napoleon_remastered/lua/probes/list_maps.lua`. Result: counts; the maps go to proxy.log.
local id, ctx, wsp = ...
local out = {}
for _, t in ipairs({ "classic", "naval", "siege" }) do
	local ok, list = pcall(FrontEnd.EnumerateBattleMaps, t, false)
	if ok and type(list) == "table" then
		out[#out + 1] = t .. "=" .. #list
		for i = 1, #list do
			local m = list[i]
			wsp.log("map " .. t .. " | " .. tostring(m.Key) .. " | " .. tostring(m.Name) .. " | " .. tostring(m.File) .. " | naval " .. tostring(m.IsNaval) .. " | players " .. tostring(m.TotalPlayers))
		end
	else
		out[#out + 1] = t .. "=error " .. tostring(list)
	end
end
return table.concat(out, ", ")
