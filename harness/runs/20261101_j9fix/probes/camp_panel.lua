-- camp_panel.lua - J9 fix round: open a campaign panel through the campaign root's own function, the one its menu-bar button calls.
-- Run in the campaign: job.sh ctl <owner> "lua <abs path>/camp_panel.lua -- <root function> | close". Root functions (from the
-- bytecode of ui\campaign ui\layout.root.luac, each a closure over its PanelManager): ToggleEntityLists (entity_lists),
-- ShowGovernmentPopup (government_screens), ToggleDiplomacyPopup (diplomacy_panel), ShowMissionsPopup (missions), ShowTechnologies
-- (technology), ShowPrestige (Prestige), ShowBuildingBrowser (building_browser). "close" calls PanelManager.CloseAllPanels.
-- Attempts 1 and 2 called the root's OnShortcut(<default_keys action>): it handles none of the show_* actions (the engine opens those
-- panels itself; no script holds the strings), so nothing opened. Returns what the call returned, or its error.
local id, ctx, wsp = ...
local arg = wsp.dev_config("lua_args")
local env = getfenv(1)
if arg == "close" then
	local ok, pm = pcall(require, "PanelManager")
	if not ok or type(pm) ~= "table" or type(pm.CloseAllPanels) ~= "function" then return "close|no PanelManager.CloseAllPanels" end
	local ok2, r = pcall(pm.CloseAllPanels)
	return "close|" .. tostring(ok2) .. "|" .. tostring(r)
end
local f = rawget(env, arg) or env[arg]
if type(f) ~= "function" then error("the " .. tostring(ctx) .. " root has no function " .. tostring(arg)) end
local ok, r = pcall(f)
return arg .. "|" .. tostring(ok) .. "|" .. tostring(r)
