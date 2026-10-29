-- probes/campaign_end_turn.lua - dev (J14): STATE-CHANGING: ends the player's turn; the AI turn runs and the game autosaves
-- purpose: end the campaign turn through the End Turn button's own path (button_end_turn EndTurn: dismisses messages, then CampaignUI.EndTurn), else CampaignUI.EndTurn()
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/campaign_end_turn.lua" in a campaign; then poll campaign_turn.lua until the season changes and players_turn is true
-- when: load ladder C (a structural edit survives the AI pass) and to make saves of a later turn
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
if not CampaignUI.CanEndTurn() then error("CampaignUI.CanEndTurn() is false") end
local from = tostring(CampaignUI.CurrentYear()) .. " " .. tostring(CampaignUI.CurrentSeasonString())
local okb, b = pcall(function() return UIComponent(Component.Root()):Find("button_end_turn") end)
if not okb then b = nil end
if b ~= nil then
	local ok, err = pcall(function() UIComponent(b):LuaCall("EndTurn") end)
	if ok then return "end turn asked through button_end_turn at " .. from end
	wsp.report("end_turn.button_error", tostring(err))
end
CampaignUI.EndTurn()
return "end turn asked through CampaignUI.EndTurn at " .. from
