-- vis.lua - J9 fix round: the visible top-level UI components (children of Component.Root and of its first-level children), so a
-- probe step can show which panel or popup is on screen. Run: job.sh ctl <owner> "lua <abs path>/vis.lua". Engine calls: Root, Find,
-- ChildCount, Id, Visible (as campaign_modal_close.lua and autostart.lua use them). No string library call.
local id, ctx, wsp = ...
local root = UIComponent(Component.Root())
local out = {}
for i = 0, root:ChildCount() - 1 do
	local c = UIComponent(root:Find(i))
	if c:Visible() then
		local kids = {}
		for j = 0, c:ChildCount() - 1 do
			local k = UIComponent(c:Find(j))
			if k:Visible() then kids[#kids + 1] = tostring(k:Id()) end
		end
		out[#out + 1] = tostring(c:Id()) .. "[" .. table.concat(kids, ",") .. "]"
	end
end
return table.concat(out, " ")
