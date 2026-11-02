-- fe_page.lua - J10 live pass: enter one front-end page the way its buttons do (root LuaCall TransitionTo, as autostart.lua and J9's
-- fe_pages.lua do), log its component tree, and go back to the main menu in the same call. Only the main menu pumps Lua in the front end
-- (J9 report): a probe that leaves a page open gets no next call, so the tree is taken here, not by tree.lua afterwards.
-- Run from the main menu: job.sh ctl <owner> "lua <abs path>/fe_page.lua -- <page> [stay]"; "stay" leaves the page open for a shot
-- (shot.sh needs no Lua; leaving then needs a relaunch). grand_campaign and spain_grand_campaign need the campaign key their main-menu
-- button carries (an unknown key kills the front end: autostart.lua), read with GetProperty("campaign_key"); without it the page is
-- skipped. Log lines as tree.lua: "j10tree fe_<page> <n>: path|v|x,y|w,h|state;..." Returns "<page>|<ok>|<visible>|<nodes>|<error>".
-- Read only but for the page transitions. No string library call but string.match and string.len.
local id, ctx, wsp = ...
local arg = wsp.dev_config("lua_args") or "main"
local page, mode = string.match(arg, "^(%S+)%s*(%S*)")
page = page or "main"
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
local label, nodes, chunk, part = "fe_" .. page, 0, "", 0
local function emit(s)
	chunk = chunk .. s .. ";"
	if string.len(chunk) > 1400 then part = part + 1 wsp.log("j10tree " .. label .. " " .. part .. ": " .. chunk) chunk = "" end
end
local function rec(c, path)
	local x, y = c:Position()
	local w, h = c:Dimensions()
	nodes = nodes + 1
	emit(path .. "|" .. (c:Visible() and "1" or "0") .. "|" .. tostring(x) .. "," .. tostring(y) .. "|" .. tostring(w) .. "," .. tostring(h) .. "|" .. tostring(c:CurrentState()))
end
local function walk(c, path, depth)
	for i = 0, c:ChildCount() - 1 do
		local ch = UIComponent(c:Find(i))
		local p = path .. "/" .. tostring(ch:Id())
		rec(ch, p)
		if depth < 24 then walk(ch, p, depth + 1) end
	end
end
-- the tree is logged once per page: a "stay" call (for the shot) would log the same label again in the same log
if ok and f ~= nil and page ~= "main" and mode ~= "stay" then
	local c = UIComponent(f)
	rec(c, page)
	walk(c, page, 1)
	part = part + 1
	wsp.log("j10tree " .. label .. " " .. part .. ": " .. chunk .. "END flags=0")
end
if page ~= "main" and mode ~= "stay" then pcall(function() root:LuaCall("TransitionTo", "main") end) end
return page .. "|" .. tostring(ok) .. "|" .. tostring(vis) .. "|" .. nodes .. "|" .. tostring(err)
