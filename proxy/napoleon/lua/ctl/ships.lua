-- ctl/ships.lua - dev (J60): the battle ship control route's Lua half: list the player's fleet, read ships, push one ship order
-- purpose: the chunk ctl.py order runs in a naval battle, in the land chunk's protocol (ctl/orders.lua) so the verb reads ships as units:
--          "list" (every ship of the player's fleet), "state <ship>[,<ship>...]" (one line per ship), "move <ship> <x> <z> <heading|-> <width|-> <run>
--          [sail]" (wsp.ship_move: the engine's own ship move command, a heading as a queued facing order; width and run are land's and ignored),
--          "face <ship> <heading> [flag] [queue]" (wsp.ship_face), "halt <ship>" (wsp.ship_halt), "selection" (the UI's own selection S, its ships),
--          "seed <ship>" (cache the fleet from a 0x... pointer); <ship> = the ship's number in the player's fleet (1-based) or a 0x... pointer
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/ctl/ships.lua 20 -- list|state <ship>|move <ship> <x> <z> <heading|-> - 0 [sail]|face ..|halt <ship>|selection" in a naval battle
-- when: ctl order in a naval scene (the route block's naval entry names this chunk) and the J60 PC probes; never in a scenario row by itself
-- not-a-verb: runs inside the game's own Lua, not on a host
-- One "unit k=v ..." line per ship (facing = the heading; men, queued, width and the front are land's and absent), or "orders refused: <why>".
-- gsub/format only (no string.find/sub/gmatch: fact napoleon.lua.string_find_stalls_pump). Never call a BattleUI function with missing
-- arguments (run harness/runs/20261102_j28pc, b2). NOT run yet: the J60 PC slot proves it (harness/runs/20261103_j60re/PC_PLAN.md).
local id, ctx, wsp = ...
if type(wsp.ship_move) ~= "function" then return "orders refused: this proxy has no wsp.ship_move (older core, or not J60)" end
local env = getfenv(1)
local B = env.BattleUI
if type(B) ~= "table" then return "orders refused: no BattleUI (not a battle?)" end
local a = {}
string.gsub(wsp.dev_config("lua_args"), "%S+", function(s) a[#a + 1] = s end)
local function ref(s) local n = tonumber(s); if n and s ~= nil and string.format("%d", n) == s then return n end return s end
local function nan(v) return string.format("%.4f", v or 0/0) end
local function line(s)
	if s.why then return "unit ptr=" .. tostring(s.ptr) .. " why=" .. string.gsub(s.why, "%s", "_") end
	return string.format("unit id=%d ptr=%s x=%.4f y=%.4f z=%.4f facing=%.4f raw=%d moving=-1 sail=%s sail_level=%.4f surrendered=%d blocked=%d wind_x=%s wind_z=%s wind_angle=%s m02=%.5f m22=%.5f army=%s",
		s.id, s.ptr, s.x, s.y, s.z, s.heading, s.heading_raw, s.sail, s.sail_level, s.surrendered and 1 or 0, s.blocked and 1 or 0,
		nan(s.wind_x), nan(s.wind_z), nan(s.wind_angle), s.m02, s.m22, s.army)
end
-- the player's fleet: a ship named by pointer, else the UI's ship selection, else the battle UI's own lists (key names checked on the PC)
local verb = a[1] or "list"
local seed = nil
if verb == "seed" or (a[2] and string.gsub(a[2], "^0x%x+$", "") == "") then seed = a[2] end
if not seed then
	local s = wsp.ship_selection()
	if s and s.ships and s.ships[1] then seed = s.ships[1] end
end
if not seed then
	local ok, lists = pcall(B.UnitListForBattleIds)
	if ok and type(lists) == "table" then
		for _, k in ipairs({ "Naval", "Ships", "Ship", "Sea" }) do
			if type(lists[k]) == "table" and lists[k][1] then seed = lists[k][1]; break end
		end
	end
end
local list, why = wsp.ship_list(seed)
if not list then return "orders refused: " .. tostring(why) end
if verb == "list" or verb == "seed" then
	local out = {}
	for _, s in ipairs(list) do out[#out + 1] = line(s) end
	return table.concat(out, "\n")
elseif verb == "selection" then
	local s, w = wsp.ship_selection()
	if not s then return "orders refused: " .. tostring(w) end
	return "selection groups=" .. tostring(s.groups) .. " ships=" .. table.concat(s.ships, ",")
elseif verb == "state" then
	local out = {}
	string.gsub(a[2] or "", "[^,]+", function(r)
		local s, w = wsp.ship_state(ref(r))
		out[#out + 1] = s and line(s) or ("orders refused: " .. r .. ": " .. tostring(w))
	end)
	if #out == 0 then return "orders refused: state <ship>[,<ship>...]" end
	return table.concat(out, "\n")
elseif verb == "move" then
	if #a < 7 then return "orders refused: move <ship> <x> <z> <heading|-> <width|-> <run> [sail]" end
	local x, z = tonumber(a[3]), tonumber(a[4])
	if not x or not z then return "orders refused: x and z must be numbers" end
	local h = a[5] ~= "-" and tonumber(a[5]) or nil
	local t0 = B.WindowsTime and B.WindowsTime() or 0
	local okm, info = wsp.ship_move(ref(a[2]), x, z, h, a[8], false)
	if not okm then return "orders refused: " .. tostring(info) end
	local s = wsp.ship_state(ref(a[2]))
	return "pushed " .. string.gsub(tostring(info), "\n", " ") .. "\n" .. (s and line(s) or "unit unreadable after the push") .. "\nwt=" .. tostring(t0)
elseif verb == "face" then
	local h = tonumber(a[3] or "")
	if not h then return "orders refused: face <ship> <heading> [flag 0|1] [queue 0|1]" end
	local okf, info = wsp.ship_face(ref(a[2] or ""), h, a[4] == "1", a[5] == "1")
	if not okf then return "orders refused: " .. tostring(info) end
	return "pushed " .. tostring(info)
elseif verb == "halt" or verb == "command" then   -- "command <ship> <cmd>": the land verb's command form; ships know halt only
	local okh, info = wsp.ship_halt(ref(a[2] or ""))
	if not okh then return "orders refused: " .. tostring(info) end
	return "pushed " .. tostring(info)
end
return "orders refused: unknown verb " .. verb .. " (list, seed, selection, state, move, face, halt)"
