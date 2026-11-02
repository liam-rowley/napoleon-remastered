-- ctl/orders.lua - dev (J28): the battle unit control route's Lua half: list the player's army, read one unit, push one move order
-- purpose: the chunk ctl.py order runs: "list" (every unit of the player's army: the first Land unit of BattleUI.UnitListForBattleIds),
--          "state <unit>" (one unit), "move <unit> <x> <z> <facing|-> <width|-> <run 0|1>" (wsp.order_move: the engine's own command
--          path, one unit per command), "selection" (the UI's own selection S); <unit> = the unit's number in the player's army (1-based,
--          the army list order: stable across launches of a scenario) or a 0x... pointer
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/ctl/orders.lua 20 -- list|state <unit>|move <unit> <x> <z> <facing|-> <width|-> <run>|selection" in a battle; ctl.py order runs it
-- when: every ctl order; never in a scenario row or a script by itself (ctl.py checks each order by readback, rule 77)
-- not-a-verb: runs inside the game's own Lua, not on a host
-- One "unit k=v ..." line per unit, or "orders refused: <why>". gsub/format only (no string.find/sub/gmatch: fact
-- napoleon.lua.string_find_stalls_pump). Never call a BattleUI function with missing arguments: an engine Lua error stopped the
-- battle UI pump (run harness/runs/20261102_j28pc, b2).
local id, ctx, wsp = ...
if type(wsp.order_move) ~= "function" then return "orders refused: this proxy has no wsp.order_move (older build, or not J28)" end
local env = getfenv(1)
local B = env.BattleUI
if type(B) ~= "table" then return "orders refused: no BattleUI (not a battle?)" end
local a = {}
string.gsub(wsp.dev_config("lua_args"), "%S+", function(s) a[#a + 1] = s end)
local function ref(s) local n = tonumber(s); if n and s ~= nil and string.format("%d", n) == s then return n end return s end
-- the player's army: cache it from the battle UI's own unit list (Land[1] is the player's first unit)
local ok, lists = pcall(B.UnitListForBattleIds)
local seed = ok and type(lists) == "table" and type(lists.Land) == "table" and lists.Land[1] or nil
local function line(u)
	if u.why then return "unit ptr=" .. tostring(u.ptr) .. " why=" .. string.gsub(u.why, "%s", "_") end
	return string.format("unit id=%d ptr=%s x=%.4f y=%.4f z=%.4f facing=%.4f raw=%d men=%d queued=%d fx=%s fy=%s fz=%s width=%s army=%s",
		u.id, u.ptr, u.x, u.y, u.z, u.facing, u.facing_raw, u.men, u.queued, string.format("%.4f", u.front_x or 0/0),
		string.format("%.4f", u.front_y or 0/0), string.format("%.4f", u.front_z or 0/0), string.format("%.4f", u.width or 0/0), u.army)
end
local list, why = wsp.unit_list(seed)
if not list then return "orders refused: " .. tostring(why) end
local verb = a[1] or "list"
if verb == "list" then
	local out = {}
	for _, u in ipairs(list) do out[#out + 1] = line(u) end
	return table.concat(out, "\n")
elseif verb == "selection" then
	local s, w = wsp.selection()
	if not s then return "orders refused: " .. tostring(w) end
	return "selection groups=" .. tostring(s.groups) .. " units=" .. table.concat(s.units, ",")
elseif verb == "state" then
	local u, w = wsp.unit_state(ref(a[2] or ""))
	if not u then return "orders refused: " .. tostring(w) end
	return line(u)
elseif verb == "move" then
	if #a < 7 then return "orders refused: move <unit> <x> <z> <facing|-> <width|-> <run>" end
	local x, z = tonumber(a[3]), tonumber(a[4])
	if not x or not z then return "orders refused: x and z must be numbers" end
	local f = a[5] ~= "-" and tonumber(a[5]) or nil
	local w = a[6] ~= "-" and tonumber(a[6]) or nil
	local t0 = B.WindowsTime and B.WindowsTime() or 0
	local okm, info = wsp.order_move(ref(a[2]), x, z, f, w, a[7] == "1", false)
	if not okm then return "orders refused: " .. tostring(info) end
	local u = wsp.unit_state(ref(a[2]))
	return "pushed " .. string.gsub(tostring(info), "\n", " ") .. "\n" .. (u and line(u) or "unit unreadable after the push") .. "\nwt=" .. tostring(t0)
end
return "orders refused: unknown verb " .. verb .. " (list, selection, state, move)"
