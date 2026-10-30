-- ctl/cam_set.lua - dev (J43): set the battle camera to a pose through the proxy's engine call (wsp.cam_set, dev.camera)
-- purpose: the setter half of ctl.py cam: parse "x,y,z,yaw,pitch" from the lua args and call wsp.cam_set on the engine thread (the active
--          camera mode's own SetTargetAndPosition); the readback is ctl/cam_read.lua, run after the settle
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/ctl/cam_set.lua 20 -- <x>,<y>,<z>,<yaw>,<pitch>" in a battle; ctl.py cam runs it
-- when: every ctl cam; never in a scenario row or a script (poses are coordinates read back, rule 78)
-- not-a-verb: runs inside the game's own Lua, not on a host
-- Returns "cam_set ok" or "cam_set refused: <why>". gsub only (no string.find/sub/gmatch: fact napoleon.lua.string_find_stalls_pump).
local id, ctx, wsp = ...
if type(wsp.cam_set) ~= "function" then return "cam_set refused: this proxy has no wsp.cam_set (older build)" end
local v = {}
string.gsub(wsp.dev_config("lua_args"), "[^,]+", function(s) v[#v + 1] = tonumber(s) end)
if #v ~= 5 then return "cam_set refused: expected x,y,z,yaw,pitch (got " .. #v .. " numbers)" end
local ok, err = wsp.cam_set(v[1], v[2], v[3], v[4], v[5])
if ok then return "cam_set ok" end
return "cam_set refused: " .. tostring(err)
