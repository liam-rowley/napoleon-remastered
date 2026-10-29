-- probes/campaign_keys.lua - dev discovery (J3): the campaign keys the main menu's campaign buttons carry
-- purpose: log and return the campaign_key property of every single-player campaign button (grand, episodic, spain) and whether
--          FrontEnd reports the Spanish campaign and saves, without opening any campaign (OpenMapDataFile on a bad key is an AV)
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/campaign_keys.lua" on the main menu
-- when: to pick or check the <campaign> of an autostart target campaign:new:<campaign>:<faction>
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local r = UIComponent(Component.Root())
local out = {}
for _, name in ipairs({ "grand_campaign", "episodic_campaign", "spain_campaign", "continue_campaign" }) do
	local a = r:Find(name)
	if a == nil then
		out[#out + 1] = name .. "=absent"
	else
		local c = UIComponent(a)
		local ok, key = pcall(function() return c:GetProperty("campaign_key") end)
		out[#out + 1] = name .. "=" .. (ok and tostring(key) or ("error " .. tostring(key))) .. " (" .. tostring(c:CurrentState()) .. ")"
	end
end
local okS, spain = pcall(FrontEnd.SpanishCampaignEnabled)
local okV, saves = pcall(FrontEnd.CampaignSavesExist)
out[#out + 1] = "spain_enabled=" .. tostring(okS and spain) .. " saves_exist=" .. tostring(okV and saves)
for i = 1, #out do wsp.log("campaign_keys: " .. out[i]) end
return table.concat(out, ", ")
