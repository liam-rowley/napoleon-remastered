-- fe_page.lua - J10 live pass: enter one front-end page the way its buttons do (root LuaCall TransitionTo, as autostart.lua and J9's
-- fe_pages.lua do), or go back to the main menu. Run from the front end: job.sh ctl <owner> "lua <abs path>/fe_page.lua -- <page>".
-- grand_campaign and spain_grand_campaign need the campaign key their main-menu button carries (an unknown key kills the front end:
-- autostart.lua), read with GetProperty("campaign_key"); without it the page is skipped. Pages are created by their first TransitionTo,
-- so there is no presence check before it. Returns "<page>|<ok>|<visible>|<error>". No string library call but string.match.
local id, ctx, wsp = ...
local page = wsp.dev_config("lua_args") or "main"
local root = UIComponent(Component.Root())
local key = nil
if page == "grand_campaign" or page == "spain_grand_campaign" then
	local b = root:Find(page)
	key = b and UIComponent(b):GetProperty("campaign_key")
	if key == nil or key == "" then return page .. "|skipped|no campaign_key" end
end
local ok, err
if key then ok, err = pcall(function() root:LuaCall("TransitionTo", page, nil, key) end)
else ok, err = pcall(function() root:LuaCall("TransitionTo", page) end) end
local f = root:Find(page)
local vis = f ~= nil and UIComponent(f):Visible() and true or false
return page .. "|" .. tostring(ok) .. "|" .. tostring(vis) .. "|" .. tostring(err)
