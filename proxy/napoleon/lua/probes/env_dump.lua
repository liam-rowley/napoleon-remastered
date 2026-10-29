-- probes/env_dump.lua - dev discovery (J3): log the globals of the pumping script's environment (functions and tables by name) and
-- purpose: log the pumping script's environment and the FrontEnd / CampaignUI / BattleUI function names
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/env_dump.lua" in any context
-- when: discovery of the engine Lua API available to a context (J3; later the engine API surface job)
-- not-a-verb: runs inside the game's own Lua, not on a host
-- the FrontEnd / CampaignUI / BattleUI function names reachable from it. ctl `lua napoleon_remastered/lua/probes/env_dump.lua`.
local id, ctx, wsp = ...
local env = getfenv(1)
local names = {}
for k, v in pairs(env) do names[#names + 1] = tostring(k) .. ":" .. type(v) end
table.sort(names)
wsp.log("env " .. tostring(ctx) .. ": " .. table.concat(names, " "))
for _, lib in ipairs({ "FrontEnd", "CampaignUI", "BattleUI" }) do
	local t = env[lib]
	if type(t) == "table" then
		local f = {}
		for k, v in pairs(t) do f[#f + 1] = tostring(k) end
		table.sort(f)
		wsp.log(lib .. ": " .. table.concat(f, " "))
	end
end
return #names .. " names"
