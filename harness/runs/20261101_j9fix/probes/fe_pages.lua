-- fe_pages.lua - J9 fix round: can the front-end screens other than the main menu be probed?
-- Run from the main menu pump: job.sh ctl <owner> "lua <abs path>/fe_pages.lua". Lists the front-end root's pages (id, visible),
-- counts what an enumeration probe can reach (globals of _G, string keys of the registry) on the main menu, then, for each page in
-- a known-safe list (the pages autostart.lua enters every launch), transitions to it the way the front end's buttons do
-- (root LuaCall TransitionTo), counts again and lists the names that appeared, and transitions back to the main menu. Logs
-- "fepage ..." lines; returns a summary. Engine calls used: Component.Root, Find, Id, Visible, ChildCount, LuaCall, GetProperty
-- (all used by autostart.lua). No string library call. Attempt 1 (fix3.sh) checked Find(page) before the transition, so every page
-- but grand_campaign read "absent", and went back to the root child "layout" instead of the page "main": the pump stopped.
local id, ctx, wsp = ...
local root = UIComponent(Component.Root())
local function reach()
	local g, r = {}, {}
	for k in pairs(_G) do if type(k) == "string" then g[k] = true end end
	local reg = debug.getregistry()
	for k in pairs(reg) do if type(k) == "string" then r[k] = true end end
	return g, r
end
local function count(t) local c = 0 for _ in pairs(t) do c = c + 1 end return c end
local function diff(a, b) local out = {} for k in pairs(a) do if not b[k] then out[#out + 1] = k end end table.sort(out) return out end
-- the pages
local pages, main = {}, nil
for i = 0, root:ChildCount() - 1 do
	local c = UIComponent(root:Find(i))
	local pid, vis = tostring(c:Id()), c:Visible() and true or false
	pages[#pages + 1] = pid .. (vis and "*" or "")
	if vis and main == nil then main = pid end
end
wsp.log("fepage pages " .. #pages .. " visible-first=" .. tostring(main) .. ": " .. table.concat(pages, " "))
local g0, r0 = reach()
wsp.log("fepage " .. tostring(main) .. " globals=" .. count(g0) .. " registry=" .. count(r0))
-- the grand campaign page needs the campaign key its main-menu button carries (an unknown key kills the front end: autostart.lua)
local grand = root:Find("grand_campaign")
local gkey = grand and UIComponent(grand):GetProperty("campaign_key")
local SAFE = { { "sp_battle1" }, { "sp_battle2" }, { "sp_battle2_scenario" }, { "grand_campaign", gkey } }
local results = {}
for _, p in ipairs(SAFE) do
	local page, arg = p[1], p[2]
	-- pages are created by their first TransitionTo (autostart.lua finds sp_battle2 only after it), so there is no presence check
	if page == "grand_campaign" and (arg == nil or arg == "") then
		wsp.log("fepage grand_campaign skipped: no campaign_key on the main-menu button")
	else
		local ok, err
		if arg then ok, err = pcall(function() root:LuaCall("TransitionTo", page, nil, arg) end)
		else ok, err = pcall(function() root:LuaCall("TransitionTo", page) end) end
		local pc = root:Find(page)
		local vis = pc ~= nil and UIComponent(pc):Visible() and true or false
		local g1, r1 = reach()
		local ng, nr = diff(g1, g0), diff(r1, r0)
		wsp.log("fepage " .. page .. " transition=" .. tostring(ok) .. (ok and "" or (" " .. tostring(err))) .. " visible=" .. tostring(vis)
			.. " globals=" .. count(g1) .. " registry=" .. count(r1) .. " new_globals=" .. table.concat(ng, ",") .. " new_registry=" .. table.concat(nr, ","))
		results[#results + 1] = page .. ":" .. tostring(ok) .. ":" .. #ng .. "+" .. #nr
	end
end
-- back to the main menu page (autostart.lua returns the same way), whose advert pumps the bridge
local back = pcall(function() root:LuaCall("TransitionTo", "main") end)
wsp.log("fepage back to main " .. tostring(back))
return "pages " .. #pages .. "; " .. table.concat(results, " ") .. "; back " .. tostring(back)
