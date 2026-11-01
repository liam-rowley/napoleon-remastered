-- probes/api_surface.lua - the engine Lua API surface of the pumping context, enumerated without calling anything (J9).
-- purpose: log every name reachable by enumeration: the context's globals, one level into each global table, the metatables (and their __index tables) of globals, and every string-keyed table in the Lua registry (Lunar classes, Pointer<TYPE> method tables); lines "api <state> <owner> <name>:<type> ..." in proxy.log
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/api_surface.lua -- <state label>" in any context; discovery/core/engine_api.py reads the lines from the run's proxy.log
-- when: the engine API surface per screen and game phase (J9; again after a game update)
-- not-a-verb: runs inside the game's own Lua, not on a host
-- Probe-safe by construction: only pairs, type, getmetatable, rawget and debug.getregistry; never tostring on a value (a __tostring
-- metamethod is a call), never a string library call (fact napoleon.lua.string_find_stalls_pump), never a function call on the engine.
local id, ctx, wsp = ...
local args = wsp.dev_config("lua_args")
local state = (type(args) == "string" and args ~= "" and args) or tostring(ctx)
local env = getfenv(1)
local total, buf, owner_now = 0, {}, nil

local function flush()
	if #buf > 0 then wsp.log("api " .. state .. " " .. owner_now .. " " .. table.concat(buf, " ")); buf = {} end
end
local function emit(owner, k, v)
	local tk = type(k)
	if tk ~= "string" and tk ~= "number" then return end
	if owner ~= owner_now then flush(); owner_now = owner end
	buf[#buf + 1] = tostring(k) .. ":" .. type(v)
	total = total + 1
	if #buf >= 40 then flush() end
end
local function walk(owner, t, limit)
	local n = 0
	for k, v in pairs(t) do
		emit(owner, k, v)
		n = n + 1
		if n >= limit then emit(owner, "__cut", n) break end
	end
end
local function meta(owner, v)
	local mt = getmetatable(v)
	if type(mt) ~= "table" then return end
	walk(owner .. "#mt", mt, 400)
	local ix = rawget(mt, "__index")
	if type(ix) == "table" and ix ~= mt then walk(owner .. "#index", ix, 800) end
end

local STD = { _G = true, package = true, string = true, table = true, math = true, io = true, os = true, coroutine = true, debug = true }
walk("G", env, 4000)
for k, v in pairs(env) do
	if type(k) == "string" and not STD[k] then
		if type(v) == "table" then walk("G." .. k, v, 1500) end
		if type(v) == "table" or type(v) == "userdata" then meta("G." .. k, v) end
	end
end
local reg = (type(debug) == "table" and type(debug.getregistry) == "function") and debug.getregistry() or nil
if type(reg) == "table" then
	for k, v in pairs(reg) do
		if type(k) == "string" and type(v) == "table" and k ~= "_LOADED" then walk("R." .. k, v, 800) end
	end
else
	emit("R", "__no_registry", 0)
end
flush()
wsp.log("api " .. state .. " __end total=" .. total)
return total .. " names (" .. state .. ")"
