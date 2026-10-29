-- probes/campaign_camera.lua - dev (J15): the campaign camera's target, read only
-- purpose: return CampaignUI.CameraTarget()'s values: a|b|c|d (the camera target, which follows a selected character only after its zoom settles)
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/campaign_camera.lua" in a campaign, at least 5 s after a SelectAndZoomToCharacter
-- when: J15 teleport_to units fit (camera units against console units); any check of where the camera or a selected character is
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local ok, a, b, c, d = pcall(CampaignUI.CameraTarget)
if not ok then return "error " .. tostring(a) end
return tostring(a) .. "|" .. tostring(b) .. "|" .. tostring(c) .. "|" .. tostring(d)
