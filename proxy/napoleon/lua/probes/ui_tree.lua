-- probes/ui_tree.lua - dev discovery (J3): log the UI tree under Root (two levels: id, visible, child count; unit flags skipped) so the screens and
-- popups on show are found by name, not assumed.
-- purpose: log the visible UI component tree under Root (two levels) in the pumping context
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/ui_tree.lua" in any context
-- when: discovery of which popup or screen is showing (warm reset, autostart flows)
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local root = UIComponent(Component.Root())
local out = {}
local function walk(c, depth, prefix)
	local n = c:ChildCount()
	for i = 0, n - 1 do
		local ch = UIComponent(c:Find(i))
		local vis = ch:Visible()
		local cid = tostring(ch:Id())
		if string.match(cid, "^3D_") then -- unit flags: skip (string.match is safe in engine Lua; find and sub are not)
		else out[#out + 1] = prefix .. tostring(ch:Id()) .. (vis and "" or "(hidden)") .. "[" .. ch:ChildCount() .. "]"
		if depth < 2 and vis then walk(ch, depth + 1, prefix .. cid .. "/") end end
	end
end
walk(root, 1, "")
local line = ""
for i = 1, #out do
	line = line .. " " .. out[i]
	if string.len(line) > 1500 then wsp.log("ui tree (" .. tostring(ctx) .. "):" .. line) line = "" end
end
wsp.log("ui tree (" .. tostring(ctx) .. "):" .. line)
return #out .. " components"
