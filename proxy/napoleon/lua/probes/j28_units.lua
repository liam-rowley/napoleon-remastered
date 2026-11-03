-- probes/j28_units.lua - dev (J28): read-only look at the orders route: install state, threads, the UI selection S, the army listing,
-- and what the battle UI's own unit functions hand out (UnitListForBattleIds, the cards), to pick the unit id scheme
-- purpose: one battle-time read of everything the orders route reads, before any order is pushed
-- usage: job.sh ctl <owner> "lua <abs path>/probes/j28_units.lua 30 -- [select]" in a battle (select: BattleUI.SelectAllInfantry first)
-- when: J28 PC step b (read-only first)
-- not-a-verb: runs inside the game's own Lua, not on a host
-- gsub/format only (no string.find/sub/gmatch: fact napoleon.lua.string_find_stalls_pump).
local id, ctx, wsp = ...
local out = {}
local function add(s) out[#out + 1] = s end
local env = getfenv(1)
local B = env.BattleUI
add("info " .. tostring(wsp.orders_info and wsp.orders_info()))
if type(B) ~= "table" then return table.concat(out, "\n") .. "\nno BattleUI" end
local arg = wsp.dev_config("lua_args")
if arg == "select" then
	local ok, e = pcall(B.SelectAllInfantry); add("SelectAllInfantry " .. tostring(ok) .. " " .. tostring(e))
end
local function desc(v)
	local t = type(v)
	if t == "table" then
		local n, ks = 0, {}
		for k, x in pairs(v) do n = n + 1; if n <= 6 then ks[#ks + 1] = tostring(k) .. "=" .. type(x) .. ":" .. tostring(x) end end
		return "table(" .. n .. ") " .. table.concat(ks, ",")
	end
	return t .. ":" .. tostring(v)
end
for _, name in ipairs({ "UnitListForBattleIds" }) do   -- never SquadInfoByPointer() without its argument: its Lua error stopped the battle UI pump (run 20261102_j28pc b2)
	local f = B[name]
	if type(f) == "function" then
		local ok, r1, r2 = pcall(f); add(name .. "() " .. tostring(ok) .. " " .. desc(r1) .. " | " .. desc(r2))
		if ok and type(r1) == "table" and type(r1.Land) == "table" then
			local n = 0
			for k, v in pairs(r1.Land) do
				n = n + 1
				if n <= 4 then
					add("  Land[" .. tostring(k) .. "] " .. desc(v))
					if type(v) == "table" then for k2, v2 in pairs(v) do add("    [" .. tostring(k2) .. "] " .. desc(v2)) end end
				end
			end
			add("  Land entries " .. n)
		end
	end
end
local sel, why = wsp.selection()
local first = nil
if sel then
	add("selection groups=" .. tostring(sel.groups) .. " units=" .. #sel.units .. " " .. table.concat(sel.units, ","))
	first = sel.units[1]
else add("selection refused: " .. tostring(why)) end
local function line(u)
	if u.why then return "  " .. tostring(u.ptr) .. " why=" .. u.why end
	return string.format("  #%d %s pos=(%.3f,%.3f,%.3f) facing=%.3f raw=%d men=%d queued=%d front=(%s,%s,%s) width=%s army=%s n=%d",
		u.id, u.ptr, u.x, u.y, u.z, u.facing, u.facing_raw, u.men, u.queued, tostring(u.front_x), tostring(u.front_y), tostring(u.front_z),
		tostring(u.width), u.army, u.army_count)
end
local list, lwhy = wsp.unit_list(first)
if list then
	add("army list " .. #list)
	for _, u in ipairs(list) do add(line(u)) end
	if list[1] and list[1].ptr then
		local hex = wsp.peek(list[1].ptr, 64); add("peek unit+0 " .. tostring(hex))
	end
else add("unit_list refused: " .. tostring(lwhy)) end
return table.concat(out, "\n")
