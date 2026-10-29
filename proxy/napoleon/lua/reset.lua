-- napoleon_remastered\lua\reset.lua - dev only (J3): leave the campaign or the battle for the front end, inside the same process.
-- purpose: leave the campaign or battle for the front end inside the same process (warm reset) with the roots' own quit functions
-- usage: run by the proxy (ctl `reset <target>`); not by hand
-- when: every warm reset
-- not-a-verb: runs inside the game's own Lua, not on a host
-- Run by the proxy (dev.cpp Reset) as a `lua` command in the pumping script: the campaign root (layout.root) or the battle root.
-- Uses the roots' own functions, as their escape menus do: campaign QuitToMainScreen() (menu_quit_to_main_screen_button ->
-- Root.LuaCall QuitToMainScreenFromEscapeMenu), battle ExitBattle() (quit_battle_button -> ExitBattleFromEscapeMenu).
local id, ctx, wsp = ...
local function call(names)
	for i = 1, #names do
		local f = rawget(getfenv(1), names[i]) or _G[names[i]]
		if type(f) == "function" then f() return names[i] end
	end
	local r = UIComponent(Component.Root())
	for i = 1, #names do
		local ok = pcall(function() r:LuaCall(names[i]) end)
		if ok then return "Root:LuaCall " .. names[i] end
	end
	error("none of " .. table.concat(names, ", ") .. " exists in the " .. tostring(ctx) .. " root")
end
if ctx == "campaign" then return "campaign: " .. call({ "QuitToMainScreen", "QuitToMainScreenFromEscapeMenu" }) end
if ctx == "battle" then return "battle: " .. call({ "ExitBattle", "ExitBattleFromEscapeMenu" }) end
error("reset from context '" .. tostring(ctx) .. "': needs the campaign or battle root")
