-- probes/console_nodll.lua - dev (J15): what the engine's own CliExecute does with no DLL help
-- purpose: call the Lua global CliExecute with a system command (here_kitty_kitty), a campaign command (teleport_to 0 0) and an unknown name, and return each pcall result: CliExecute=<type>|<line>=<ok>,<ret1>,<ret2>|...
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/console_nodll.lua" in a campaign, with dev.log_files=1 (the executor's fopen of a name it did not find shows in logs\files.log)
-- when: J15 deliverable 1 (no-DLL probe); again after a game update, before relying on the console route
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local out = { "CliExecute=" .. type(CliExecute) }
if type(CliExecute) ~= "function" then return table.concat(out, "|") end
for _, line in ipairs({ "here_kitty_kitty", "teleport_to 0 0", "j15_probe_unknown_name" }) do
	local ok, a, b = pcall(CliExecute, line)
	out[#out + 1] = line .. "=" .. tostring(ok) .. "," .. tostring(a) .. "," .. tostring(b)
end
return table.concat(out, "|")
