-- napoleon_remastered\lua\wsp.lua - dev only (J3). Loaded once per engine Lua state by the wrapper scripts of the dev pack:
-- purpose: the dev Lua bridge loader and pump: loads the proxy into the engine's Lua, runs a wrapped vanilla script unchanged, pumps control commands from its update callback, probes battles
-- usage: loaded by the dev pack's wrapper scripts only: dofile("napoleon_remastered/lua/wsp.lua").wrap(entry, ctx, getfenv(1))
-- when: whenever dev.lua_bridge=1 (scene tracking from Lua, `lua` commands, autostart, reset); never edited on the PC (kit-synced)
-- not-a-verb: runs inside the game's own Lua, not on a host
--   return dofile("napoleon_remastered/lua/wsp.lua").wrap("<pack entry>", "<context>", getfenv(1))
-- It loads the proxy's Lua bridge (proxy/core/luabridge.cpp), runs the VANILLA script of that entry unchanged in the wrapper's
-- environment, then wraps the script's update callback so every update also pumps the bridge: control commands (`lua <file>`) run
-- here, in the pumping script's environment, and their outcome goes back with wsp.result. In battle every 8th pump probes the
-- battle UI (naval, deployment panel, map) for the scene tracker.
-- Rules (empire-remastered PANEL_GUIDE): no string.find / string.sub / pattern functions (the engine replaces them); every engine
-- call in pcall; never error out of a pump.
local M = rawget(_G, "__wsp_lua")
if M then return M end
M = {}
rawset(_G, "__wsp_lua", M)

local function load_bridge()
	local sentinel, e1 = package.loadlib(".\\d3d9.dll", "wsp_sentinel")
	if not sentinel then return nil, "loadlib wsp_sentinel: " .. tostring(e1) end
	sentinel({})                                -- an empty table made by the ENGINE's VM (its dummynode)
	local open, e2 = package.loadlib(".\\d3d9.dll", "luaopen_wsp")
	if not open then return nil, "loadlib luaopen_wsp: " .. tostring(e2) end
	local t = open()
	if type(t) ~= "table" then return nil, "luaopen_wsp refused (see proxy.log)" end
	return t
end
local ok, wsp, err = pcall(load_bridge)
if not ok then err = wsp; wsp = nil end
M.wsp = wsp
M.error = err

local function tostr(v) if v == nil then return "" end return tostring(v) end

local function run(cmd, env, ctx)
	if cmd.verb ~= "lua" then wsp.result(cmd.id, false, "unknown verb " .. tostr(cmd.verb)) return end
	local f, lerr = loadfile(cmd.arg)
	if not f then wsp.result(cmd.id, false, "load " .. tostr(cmd.arg) .. ": " .. tostr(lerr)) return end
	setfenv(f, env)
	local okc, a, b, c = pcall(f, cmd.id, ctx, wsp)
	if okc then
		local text = tostr(a)
		if b ~= nil then text = text .. " | " .. tostr(b) end
		if c ~= nil then text = text .. " | " .. tostr(c) end
		wsp.result(cmd.id, true, text)
	else
		wsp.result(cmd.id, false, tostr(a))
	end
end

local function b2n(v) if v == nil then return -1 elseif v and v ~= 0 then return 1 else return 0 end end
local map_keys = { "Map", "MapName", "map", "map_name", "BattleMap", "MapKey", "Name", "Key", "File" }
local logged_details = false

local function probe(env)
	local B = env.BattleUI
	if type(B) ~= "table" then return end
	local naval, panel = -1, -1
	local okd, d = pcall(B.BattleDetails)
	if okd and type(d) == "table" then
		naval = b2n(d.NavalBattle or d.IsNaval or d.Naval)
		if not logged_details then   -- discovery: every plain field once, so the map field is found, not assumed
			logged_details = true
			local parts = {}
			for k, v in pairs(d) do
				local t = type(v)
				if t == "string" or t == "number" or t == "boolean" then parts[#parts + 1] = tostr(k) .. "=" .. tostr(v)
				elseif t == "table" then
					for k2, v2 in pairs(v) do
						local t2 = type(v2)
						if t2 == "string" or t2 == "number" or t2 == "boolean" then parts[#parts + 1] = tostr(k) .. "." .. tostr(k2) .. "=" .. tostr(v2) end
					end
				end
			end
			wsp.log("battle details: " .. table.concat(parts, ", "))
		end
		local m = nil
		for i = 1, #map_keys do
			local v = d[map_keys[i]]
			if type(v) == "string" and v ~= "" then m = v break end
			if type(v) == "table" then
				for j = 1, #map_keys do local w = v[map_keys[j]] if type(w) == "string" and w ~= "" then m = w break end end
				if m then break end
			end
		end
		if m then wsp.report("battle.map", m) end
	end
	local okp, vis = pcall(function()
		local root = env.UIComponent(env.Component.Root())
		local a = root:Find("deployment_end_sp", false)
		if a == nil then return -1 end
		return b2n(env.UIComponent(a):Visible())
	end)
	if okp then panel = vis end
	wsp.dev_state(naval, panel)
end

local ticks = {}
function M.pump(ctx, env)
	if not wsp then return end
	local cmds = wsp.poll(ctx)
	if cmds then
		for i = 1, #cmds do
			local okr, e = pcall(run, cmds[i], env, ctx)
			if not okr then wsp.result(cmds[i].id, false, "pump: " .. tostr(e)) end
		end
	end
	if ctx == "battle" then
		ticks[ctx] = (ticks[ctx] or 0) + 1
		if ticks[ctx] % 8 == 1 then pcall(probe, env) end
	end
end

-- The update callback the engine calls on this script; OnUpdate first (battle root has both: pumping once per frame is enough).
local callbacks = { "OnUpdate", "OnUpdatePulse" }
function M.hook(env, ctx)
	for i = 1, #callbacks do
		local name = callbacks[i]
		local orig = rawget(env, name)
		if type(orig) == "function" then
			env[name] = function(...)
				local a, b, c = orig(...)
				pcall(M.pump, ctx, env)
				return a, b, c
			end
			if wsp then wsp.log("wrapper: " .. ctx .. " pumps from " .. name) end
			return true
		end
	end
	if wsp then wsp.log("wrapper: " .. ctx .. ": no OnUpdate/OnUpdatePulse to pump from") end
	return false
end

function M.wrap(entry, ctx, env)
	if not wsp then error("wsp wrapper " .. entry .. ": the bridge did not load: " .. tostr(M.error)) end
	local bytes, verr = wsp.vanilla(entry)
	if not bytes then error("wsp wrapper " .. entry .. ": " .. tostr(verr)) end
	local chunk, lerr = loadstring(bytes, "=" .. entry)
	if not chunk then error("wsp wrapper " .. entry .. ": " .. tostr(lerr)) end
	setfenv(chunk, env)
	local r1, r2, r3 = chunk()
	M.hook(env, ctx)
	return r1, r2, r3
end

if wsp then wsp.log("wsp.lua loaded (" .. tostr(wsp.version()) .. ")") end
return M
