-- probes/campaign_turn.lua - dev (J14, J40): where the campaign is, read only
-- purpose: return the campaign's year, season, whether it is the player's turn and a save or an end turn is allowed, and the HUD date: year|season|players_turn|can_save|can_end_turn|date
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/campaign_turn.lua" in a campaign (saves/README.md "Load ladder" polls it after an EndTurn)
-- when: to see that a loaded save is the expected turn, and to detect the next player turn after campaign_end_turn.lua
-- not-a-verb: runs inside the game's own Lua, not on a host
-- The date field is the HUD's `date` text ("Late January 1805"): turns are two weeks, so year and season alone stay the same across a
-- turn (J40, run 20261031_j40pc: Early -> Late January 1805 is Winter both times). Compare the date to see a turn pass.
local id, ctx, wsp = ...
local function call(f) local ok, v = pcall(f); return ok and tostring(v) or ("error " .. tostring(v)) end
local function hud_date()
	local ok, t = pcall(function() return UIComponent(UIComponent(Component.Root()):Find("date")):GetStateText() end)
	if not ok or t == nil then return "error " .. tostring(t) end
	local a, b = string.match(tostring(t), "^(.-)%s*\n%s*(.*)$")   -- string.match only (fact napoleon.lua.string_find_stalls_pump)
	return a and (a .. " " .. b) or tostring(t)
end
return table.concat({ call(CampaignUI.CurrentYear), call(CampaignUI.CurrentSeasonString), call(CampaignUI.IsPlayersTurn),
	call(CampaignUI.CanSave), call(CampaignUI.CanEndTurn), hud_date() }, "|")
