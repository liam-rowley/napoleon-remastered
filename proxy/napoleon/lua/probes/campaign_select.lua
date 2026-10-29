-- probes/campaign_select.lua - dev (J15): select one of the player's characters and zoom to it
-- purpose: select the player's first agent (else first army) with CampaignUI.SelectAndZoomToCharacter(addr, -1) and return its list entry's scalar fields: kind|ok|key=value ...
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/campaign_select.lua" in a campaign; read the camera with campaign_camera.lua at least 5 s later (CameraTarget lies mid-zoom)
-- when: before console teleport_to / transport_to_region (they act on the selection), J15 units fit, J4 campaign scenarios
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local fid = CampaignUI.PlayerFactionId()
local kind, list = "agent", CampaignUI.RetrieveFactionAgentsList(fid) or {}
if not list[1] then kind, list = "army", CampaignUI.RetrieveFactionMilitaryForceLists(fid, true) or {} end
local e = list[1]
if not e then return "none|false|faction=" .. tostring(fid) end
local ks = {}
for k, v in pairs(e) do if type(v) ~= "table" and type(v) ~= "userdata" and type(v) ~= "function" then ks[#ks + 1] = k .. "=" .. tostring(v) end end
table.sort(ks)
local ok, err = pcall(CampaignUI.SelectAndZoomToCharacter, e.Address, -1)
return kind .. "|" .. tostring(ok) .. (ok and "" or (" " .. tostring(err))) .. "|" .. table.concat(ks, " "):sub(1, 600)
