-- getters.lua - J9 fix round: call the committed probe-safe getters once each and log a sample of what they return.
-- Run: job.sh ctl <owner> "lua <abs path>/getters.lua -- <abs path>/probe_safe_list.lua"; lines "sample <state> G.<table> <name> <type> <value>"
-- (state = the pumping context) for discovery/core/engine_api.py. The list (discovery/napoleon/probe_safe.json, generated) holds only C
-- bindings that read no argument and are named as getters; each call is wrapped in pcall. No string library call (the engine replaces
-- it: fact napoleon.lua.string_find_stalls_pump); tostring on returned values only.
local id, ctx, wsp = ...
local path = wsp.dev_config("lua_args")
local list = dofile(path)
local state = tostring(ctx)
local n, ok_n = 0, 0
local function show(v)
	local t = type(v)
	if t == "table" then
		local c, keys = 0, {}
		for k, x in pairs(v) do
			c = c + 1
			if #keys < 6 then keys[#keys + 1] = tostring(k) .. "=" .. type(x) end
		end
		return "table", "n=" .. c .. " " .. table.concat(keys, ",")
	elseif t == "userdata" or t == "function" then
		return t, ""
	end
	return t, tostring(v)
end
local OWN = { frontend = "FrontEnd", campaign = "CampaignUI", battle = "BattleUI" }   -- only the context's own table is called
local function one(tbl, name)
	local T = _G[tbl] or getfenv(1)[tbl]
	local f = type(T) == "table" and T[name] or nil
	n = n + 1
	if type(f) ~= "function" then
		wsp.log("sample " .. state .. " G." .. tbl .. " " .. name .. " error absent")
		return
	end
	local ok, a, b, c = pcall(f)
	if not ok then
		wsp.log("sample " .. state .. " G." .. tbl .. " " .. name .. " error " .. tostring(a))
		return
	end
	ok_n = ok_n + 1
	local ta, va = show(a)
	local extra = (b ~= nil) and (" | " .. tostring(b) .. ((c ~= nil) and (" | " .. tostring(c)) or "")) or ""
	wsp.log("sample " .. state .. " G." .. tbl .. " " .. name .. " " .. ta .. " " .. va .. extra)
end
for _, e in ipairs(list) do
	if e[1] == OWN[state] then one(e[1], e[2]) end
end
return ok_n .. " of " .. n .. " getters returned (" .. state .. ")"
