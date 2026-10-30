-- probes/require_sl.lua - dev (J43): require the game's Scripting_Library alone, nothing else, so its effect on the battle pump is isolated
-- purpose: one require "Scripting_Library" in the pumping battle UI environment and the globals it adds (type only, no pattern functions)
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/require_sl.lua" in a battle, then watch pump_age_s in ctl state
-- when: J43 deliverable 1 (the pump stall)
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local env = getfenv(1)
local before = {}
for k, _ in pairs(env) do before[k] = true end
local ok, e = pcall(require, "Scripting_Library")
local added = {}
for k, v in pairs(env) do if not before[k] then added[#added + 1] = tostring(k) .. ":" .. type(v) end end
table.sort(added)
return "require=" .. (ok and "ok" or tostring(e)) .. " | added=" .. table.concat(added, ",")
