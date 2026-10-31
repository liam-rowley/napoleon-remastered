-- probes/campaign_modal_close.lua - dev (J40): STATE-CHANGING: declines an AI diplomacy proposal and closes a turn-start event message that wait on the player, so an unattended EndTurn can go on
-- purpose: if the diplomacy panel is up (an AI proposal during the AI turn), decline it through the panel script's own routes, ONE per call in order (<component>:LuaCall(<fn>): DeclineOffer, button_cancel, ClosePopup, button_close; the panel hides a frame later, so the next call sees whether it worked); if an event_message is up, close it (OnOk, then CloseDialog: event_message.lua); returns none | asked <route>=<result> (call again) | closed event_message:<fn> | open <routes tried> (all tried, the panel stays)
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/campaign_modal_close.lua" in a campaign, each poll while waiting for the next turn after campaign_end_turn.lua (the Lua pump keeps running behind the popup in a headless launch, J40)
-- when: J40 EndTurn proof (fact napoleon.campaign.modal_stops_pump); load_save.sh --end-turn; J4 unattended turns
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local root = UIComponent(Component.Root())
local function find(name, under)
	local ok, p = pcall(function() return (under or root):Find(name) end)
	if ok and p ~= nil then return UIComponent(p) end
	return nil
end
local function up(c)
	if c == nil then return false end
	local ok, v = pcall(function() return c:Visible() end)
	return ok and v == true
end
local done, tried = {}, {}
local ev = find("event_message")
if up(ev) then
	for _, fn in ipairs({ "OnOk", "CloseDialog" }) do
		local ok, err = pcall(function() ev:LuaCall(fn) end)
		tried[#tried + 1] = "event_message:" .. fn .. "=" .. (ok and "ok" or tostring(err))
		if ok then done[#done + 1] = "event_message:" .. fn; break end
	end
end
local panel = find("diplomacy_panel")
if not up(panel) then
	rawset(getfenv(1), "J40_MODAL_TRIES", 0)
	if #done > 0 then return "closed " .. table.concat(done, " ; ") end
	return #tried > 0 and ("open " .. table.concat(tried, " ")) or "none"
end
-- One route per call: every LuaCall returns before the panel hides, so trying them all at once cannot say which declined (J40 run 20261031_j40pc
-- et1/et2). The try count lives in the pumping environment and resets whenever no panel is up.
local routes = {
	{ "diplomacy_panel", panel, "DeclineOffer" },
	{ "button_cancel", find("button_cancel", panel), "OnMouseLClickUp" },
	{ "diplomacy_panel", panel, "ClosePopup" },
	{ "button_close", find("button_close", panel), "OnMouseLClickUp" },
}
local n = (rawget(getfenv(1), "J40_MODAL_TRIES") or 0) + 1
rawset(getfenv(1), "J40_MODAL_TRIES", n)
local r = routes[n]
if r == nil then return "open all " .. #routes .. " routes tried, the diplomacy panel stays" end
local label, c, fn = r[1], r[2], r[3]
if c == nil then return "asked " .. label .. ":" .. fn .. "=missing" end
local ok, err = pcall(function() c:LuaCall(fn) end)
return "asked " .. label .. ":" .. fn .. "=" .. (ok and "ok" or tostring(err))
