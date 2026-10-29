-- probes/battle_api.lua - dev (J4): is the battle script API reachable from ctl lua, and which calls work? (read only, no orders)
-- purpose: report whether empire_battle / battle_manager exist in the pumping environment, and what camera:position(), battle speed and a unit controller answer
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/battle_api.lua" in a land battle, a siege and a naval battle (and with "-- move=1" to also move the camera once)
-- when: deliverable 1 of J4 (the route probe); rerun after a game or proxy change that touches the Lua environment
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local out = {}
local function add(k, v) out[#out + 1] = k .. "=" .. tostring(v) end
add("ctx", ctx)
add("empire_battle", type(empire_battle))
add("battle_manager", type(battle_manager))
add("battle_g", type(battle))
add("bm_g", type(bm))
local function methods(o)   -- the object's method names, from its metatable (userdata) or itself (table)
	local names = {}
	local okm, mt = pcall(getmetatable, o)
	local src = (okm and type(mt) == "table") and (type(mt.__index) == "table" and mt.__index or mt) or (type(o) == "table" and o or {})
	for k, _ in pairs(src) do names[#names + 1] = tostring(k) end
	table.sort(names)
	return table.concat(names, ",")
end
local ok, b = pcall(function() return empire_battle:new() end)
add("new_ok", ok); add("new_type", type(b))
if not ok then add("new_err", b) else
	local ok2, cam = pcall(function() return b:camera() end)
	add("camera_ok", ok2); add("camera_type", type(cam))
	if ok2 and cam then
		local ok3, p = pcall(function() return cam:position() end)
		add("position_ok", ok3)
		if ok3 and p then
			local ok4, x, y, z = pcall(function() return p:get_x(), p:get_y(), p:get_z() end)
			add("position", ok4 and (x .. "," .. y .. "," .. z) or ("methods:" .. tostring(x)))
		else add("position_err", p) end
		local args = wsp.dev_config("lua_args")
		if args == "move=1" then
			local ok5, e = pcall(function() cam:move_to(p, p, 0) end)
			add("move_to_same_ok", ok5); if not ok5 then add("move_to_err", e) end
		end
	end
	local ok6, e6 = pcall(function() b:modify_battle_speed(1.0) end)
	add("speed_ok", ok6); if not ok6 then add("speed_err", e6) end
	local ok7, alliances = pcall(function() return b:alliances() end)
	add("alliances_ok", ok7); if not ok7 then add("alliances_err", alliances) end
	if ok2 and cam then add("camera_methods", methods(cam)) end
	add("battle_methods", methods(b))
	if ok7 and alliances then
		local ok8, r = pcall(function()
			local army = alliances:item(1):armies():item(1)
			local units = army:units()
			local ctl = army:create_unit_controller()
			local u = units:item(1)
			return "units=" .. units:count() .. " unit_methods=" .. methods(u) .. " controller_methods=" .. methods(ctl)
		end)
		add("controller_ok", ok8); add("controller_info", r)
	end
end
return table.concat(out, " | ")
