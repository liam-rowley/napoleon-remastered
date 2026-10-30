-- ctl/speed.lua - dev (J43): set the battle speed or pause through the battle root's own RequestSpeed, and read the battle clock
-- purpose: the setter and the readback of ctl.py pause and speed: RequestSpeed(<slow|play|fwd|ffwd|pause>) in the pumping battle root
--          environment (it calls BattleUI.Slow/Play/Fwd/Ffwd/Pause and updates the HUD), then the battle clock and the tick period
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/ctl/speed.lua 20 -- <slow|play|fwd|ffwd|pause|read>" in a battle; ctl.py runs it
-- when: every ctl pause and speed (twice: set, then read after a measured wall-clock interval)
-- not-a-verb: runs inside the game's own Lua, not on a host
-- Returns "speed ebt=<battle s> wt=<windows s> tick=<period> conflict=<bool>"; ebt runs only after deployment (IsConflict true).
local id, ctx, wsp = ...
local env = getfenv(1)
local B = env.BattleUI
if type(B) ~= "table" then return "speed none: no BattleUI (not a battle?)" end
local a = wsp.dev_config("lua_args")
local said = ""
if a ~= "read" and a ~= "" then
	if a ~= "slow" and a ~= "play" and a ~= "fwd" and a ~= "ffwd" and a ~= "pause" then return "speed refused: " .. a .. " is not slow, play, fwd, ffwd, pause or read" end
	if type(env.RequestSpeed) ~= "function" then return "speed refused: the battle root has no RequestSpeed" end
	local ok, e = pcall(env.RequestSpeed, a)
	if not ok then return "speed refused: RequestSpeed(" .. a .. "): " .. tostring(e) end
	said = "set=" .. a .. " "
end
local function v(n) local ok, r = pcall(B[n]); if ok then return tostring(r) end return "?" end
return "speed " .. said .. "ebt=" .. v("ElapsedBattleTime") .. " wt=" .. v("WindowsTime") .. " tick=" .. v("TickPeriod") .. " conflict=" .. v("IsConflict")
