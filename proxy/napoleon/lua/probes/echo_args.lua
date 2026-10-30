-- probes/echo_args.lua - dev (J4): return the ctl lua request's arguments and the pumping context
-- purpose: check that `lua <file> -- <args>` reaches the chunk through wsp.dev_config("lua_args")
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/echo_args.lua -- a=1"
-- when: after a change to the lua verb or the bridge
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
return "args=[" .. tostring(wsp.dev_config("lua_args")) .. "] ctx=" .. tostring(ctx)
