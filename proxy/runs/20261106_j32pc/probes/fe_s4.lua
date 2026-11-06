-- fe_s4.lua - J32 S4 front end, route A, in ONE call: only the main menu pumps Lua (fact napoleon.lua.update_callbacks), so nothing can run on a page later.
-- Run from the main menu: job.sh ctl j32 "lua <abs path>/fe_s4.lua -- <mode>".
--   visible: enter single_player, read it, come back (control)
--   hide <how>: enter it, read it, make it undrawn (vis, pvis, move, alpha), leave it so for a shot and a click; returns the button's rect. The next Lua needs a relaunch.
--   handler <how>: enter it, undraw it, call the root's TransitionBack from the same call, report what is visible
local id, ctx, wsp = ...
local arg = wsp.dev_config("lua_args") or ""
local mode, how = string.match(arg, "^(%S+)%s*(%S*)")
local root = UIComponent(Component.Root())
local function comp(n) local f = root:Find(n) if f == nil then return nil end return UIComponent(f) end
local function rect(c) local x, y = c:Position() local w, h = c:Dimensions() return tostring(x) .. "," .. tostring(y) .. "," .. tostring(w) .. "," .. tostring(h) end
local function undraw(c)
	if how == "vis" then c:SetVisible(false)
	elseif how == "pvis" then c:PropagateVisibility(false)
	elseif how == "move" then c:MoveTo(-5000, -5000)
	elseif how == "alpha" then c:PropagateOpacity(0) end
end
local ok, err = pcall(function() root:LuaCall("TransitionTo", "single_player") end)
local page = comp("single_player")
if page == nil then return "no page " .. tostring(ok) .. " " .. tostring(err) end
local btn = comp("button_battle")
local out = "entered=" .. tostring(ok) .. " page=" .. rect(page) .. " visible=" .. tostring(page:Visible()) .. " button_battle=" .. (btn and rect(btn) or "absent")
if mode == "visible" then
	pcall(function() root:LuaCall("TransitionBack") end)
	return out .. " back main_visible=" .. tostring(comp("main") and comp("main"):Visible())
end
undraw(page)
out = out .. " undrawn=" .. how .. " visible=" .. tostring(page:Visible())
if mode == "handler" then
	local ok2, e2 = pcall(function() root:LuaCall("TransitionBack") end)
	return out .. " back=" .. tostring(ok2) .. " " .. tostring(e2) .. " main_visible=" .. tostring(comp("main") and comp("main"):Visible())
end
return out
