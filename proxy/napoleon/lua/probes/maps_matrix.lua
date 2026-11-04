-- probes/maps_matrix.lua - dev discovery (J46): every battle-map list the front end can enumerate, per type and all_maps flag
-- purpose: answer "is there a city siege map" and "why is the single-player historical list empty": for each battle type and each value of
--          EnumerateBattleMaps' second argument (and EnumerateNapoleonsBattleMaps if present) list count and Key:Name[siege/hist/naval flags]
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/maps_matrix.lua 30" in the front end
-- when: J46 siege-city and historical-cause probes; rerun after a game update
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local out = {}
local function flags(m)
	local s = ""
	if m.IsSiege then s = s .. "S" end
	if m.IsHistoric then s = s .. "H" end
	if m.IsNaval then s = s .. "N" end
	return s
end
local function list(label, fn, a, b)
	local ok, l = pcall(fn, a, b)
	if not ok then out[#out + 1] = label .. "=ERR " .. tostring(l); return end
	if type(l) ~= "table" then out[#out + 1] = label .. "=" .. type(l); return end
	local ks = {}
	for _, m in ipairs(l) do ks[#ks + 1] = tostring(m.Key) .. ":" .. tostring(m.Name) .. "[" .. flags(m) .. "]" end
	out[#out + 1] = label .. "(" .. #l .. ")=" .. table.concat(ks, ";")
end
for _, t in ipairs({ "classic", "naval", "siege", "historic", "historical", "settlement", "land", "city" }) do
	list(t .. ",false", FrontEnd.EnumerateBattleMaps, t, false)
	list(t .. ",true", FrontEnd.EnumerateBattleMaps, t, true)
end
if type(FrontEnd.EnumerateNapoleonsBattleMaps) == "function" then
	list("napoleons,false", FrontEnd.EnumerateNapoleonsBattleMaps, false)
	list("napoleons,true", FrontEnd.EnumerateNapoleonsBattleMaps, true)
end
return table.concat(out, " | ")
