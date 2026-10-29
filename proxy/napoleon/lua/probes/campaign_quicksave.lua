-- probes/campaign_quicksave.lua - dev (J14): STATE-WRITING: the game writes its quick save into save_games
-- purpose: call CampaignUI.QuickSave() when CampaignUI.CanSave() allows it and return year|season of the saved turn
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/campaign_quicksave.lua" in a campaign, then stage_save.py keep <the quick save's name>
-- when: load ladder B and C (re-parse the state the engine wrote) and to make base saves of other turns
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
if not CampaignUI.CanSave() then error("CampaignUI.CanSave() is false (not the player's turn, or a battle or popup is pending)") end
CampaignUI.QuickSave()
return "quicksave asked at " .. tostring(CampaignUI.CurrentYear()) .. " " .. tostring(CampaignUI.CurrentSeasonString())
