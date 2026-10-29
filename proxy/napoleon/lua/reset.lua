-- napoleon_remastered\lua\reset.lua - dev only (J3): one step of leaving the campaign or the battle for the front end, inside the
-- same process (warm reset). The proxy (dev.cpp Reset) runs it as a `lua` command in the pumping script (the campaign root
-- layout.root or the battle root) again and again, about every 4 s, while that context still pumps (at most 8 steps).
-- purpose: one step of the warm reset (battle or campaign back to the front end) through the roots' own functions
-- usage: run by the proxy (ctl `reset <target>`); not by hand
-- when: every warm reset
-- not-a-verb: runs inside the game's own Lua, not on a host
-- Battle (run 20261029_j3pc, the vanilla quit path): ExitBattle() (quit_battle_button -> ExitBattleFromEscapeMenu) shows the
-- in-battle summary (in_battle_results_popup: its Dismiss -> DismissBattleResult()), which opens the post-battle screen
-- (mp_postbattle: its button_exit -> Root.LuaCall("ClosePopup", <popup>)), which returns to the front end.
-- Campaign: QuitToMainScreen() (menu_quit_to_main_screen_button -> QuitToMainScreenFromEscapeMenu).
local id, ctx, wsp = ...
local env = getfenv(1)
local root = UIComponent(Component.Root())
local function shown(name)
	local c = root:Find(name, false)
	if c == nil then return nil end
	local u = UIComponent(c)
	if u:Visible() then return u end
	return nil
end
local function fn(name)
	local f = rawget(env, name) or env[name]
	if type(f) ~= "function" then error("the " .. tostring(ctx) .. " root has no " .. name) end
	return f
end
if ctx == "battle" then
	local pb = shown("mp_postbattle")
	if pb then fn("ClosePopup")(pb:Address()) return "battle: post-battle screen closed (ClosePopup mp_postbattle)" end
	if shown("in_battle_results_popup") then fn("DismissBattleResult")() return "battle: summary dismissed (DismissBattleResult)" end
	fn("ExitBattle")()
	return "battle: ExitBattle"
end
if ctx == "campaign" then
	fn("QuitToMainScreen")()
	return "campaign: QuitToMainScreen"
end
error("reset from context '" .. tostring(ctx) .. "': needs the campaign or battle root")
