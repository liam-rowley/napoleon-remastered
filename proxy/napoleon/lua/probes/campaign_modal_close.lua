-- probes/campaign_modal_close.lua - dev (J40): STATE-CHANGING: declines an AI diplomacy proposal and closes a turn-start event message that wait on the player, so an unattended EndTurn can go on
-- purpose: if the diplomacy panel is up (an AI proposal during the AI turn), decline it through the panel script's own routes, ONE per call in order (<component>:LuaCall(<fn>): DeclineOffer, then ClosePopup on later calls, button_cancel as a last resort; the panel hides a frame later, so the next call sees whether it worked); if an event_message is up, close it (OnOk, then CloseDialog: event_message.lua); returns none | asked <route>=<result> (call again) | closed event_message:<fn> | open <routes tried> (all tried, the panel stays)
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
-- et1/et2). The try count lives in the pumping environment and resets whenever no panel is up. DeclineOffer answers the proposal but leaves
-- the panel up; ClosePopup closes it only in a LATER frame (asked in the same call as DeclineOffer, the panel stayed: run 20261031_j40pc
-- et4; asked on the next call, it closed: ls_endturn, close1), after which the AI turn goes on.
local routes = {
	{ "diplomacy_panel", panel, "DeclineOffer" },
	{ "diplomacy_panel", panel, "ClosePopup" },
	{ "diplomacy_panel", panel, "ClosePopup" },
	{ "button_cancel", find("button_cancel", panel), "OnMouseLClickUp" },
	{ "diplomacy_panel", panel, "ClosePopup" },
}
local n = (rawget(getfenv(1), "J40_MODAL_TRIES") or 0) + 1
rawset(getfenv(1), "J40_MODAL_TRIES", n)
local r = routes[n]
if r == nil then return "open all " .. #routes .. " routes tried, the diplomacy panel stays" end
local label, c = r[1], r[2]
if c == nil then return "asked " .. label .. ":" .. r[3] .. "=missing" end
local res = {}
for i = 3, #r do
	local ok, err = pcall(function() c:LuaCall(r[i]) end)
	res[#res + 1] = label .. ":" .. r[i] .. "=" .. (ok and "ok" or tostring(err))
end
return "asked " .. table.concat(res, " ")
