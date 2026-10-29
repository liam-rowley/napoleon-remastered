-- probes/campaign_turn.lua - dev (J14): where the campaign is, read only
-- purpose: return the campaign's year, season and whether it is the player's turn and a save or an end turn is allowed: year|season|players_turn|can_save|can_end_turn
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/campaign_turn.lua" in a campaign (saves/README.md "Load ladder" polls it after an EndTurn)
-- when: to see that a loaded save is the expected turn, and to detect the next player turn after campaign_end_turn.lua
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local function call(f) local ok, v = pcall(f); return ok and tostring(v) or ("error " .. tostring(v)) end
return table.concat({ call(CampaignUI.CurrentYear), call(CampaignUI.CurrentSeasonString), call(CampaignUI.IsPlayersTurn),
	call(CampaignUI.CanSave), call(CampaignUI.CanEndTurn) }, "|")
