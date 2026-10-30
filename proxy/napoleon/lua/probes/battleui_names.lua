-- probes/battleui_names.lua - dev (J4): the BattleUI table's function names matching a lua-args filter (comma separated, lower case substrings)
-- purpose: list BattleUI functions about the camera, speed, pause, orders and positions
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/battleui_names.lua -- camera,speed,pause,move,position" in a battle
-- when: J4 route probe; any search for a BattleUI call
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local filters = {}
string.gsub(wsp.dev_config("lua_args"), "[^,]+", function(f) filters[#filters + 1] = f end)   -- gsub, never gmatch/find (fact napoleon.lua.string_find_stalls_pump)
local out = {}
local bui = getfenv(1).BattleUI
out[1] = "n=" .. (type(bui) == "table" and "table" or type(bui)) .. " filters=" .. #filters
for k, v in pairs(bui) do
	local s = tostring(k):lower()
	for _, f in ipairs(filters) do if s:match(f) then out[#out + 1] = tostring(k); break end end
end
table.sort(out)
return table.concat(out, ",")
