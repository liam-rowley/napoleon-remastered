-- tree.lua - J10 live pass: log a component subtree (every descendant: path, visible, position, size, current state) so the static
-- atlas can be compared with what the game built. Run: job.sh ctl <owner> "lua <abs path>/tree.lua -- <label> [<component id> | *]".
-- "*" (default) dumps every visible child of Component.Root with its whole subtree; unit flags (ids starting 3D_) are counted, not walked.
-- Read only. Engine calls: Component.Root, Find, ChildCount, Id, Visible, Position, Dimensions, CurrentState (all used by the vanilla
-- scripts). string.match only (string.find, sub and gmatch stall the pump: napoleon.lua.string_find_stalls_pump).
-- Log lines: "j10tree <label> <n>: path|v|x,y|w,h|state;path|..." in chunks under 1500 characters; returns "<label> <nodes> nodes".
local id, ctx, wsp = ...
local arg = wsp.dev_config("lua_args") or ""
local label, which = string.match(arg, "^(%S+)%s*(%S*)")
label = label or "tree"
if which == nil or which == "" then which = "*" end
local root = UIComponent(Component.Root())
local nodes, flags, chunk, part = 0, 0, "", 0
local function emit(s)
	chunk = chunk .. s .. ";"
	if string.len(chunk) > 1400 then part = part + 1 wsp.log("j10tree " .. label .. " " .. part .. ": " .. chunk) chunk = "" end
end
local function walk(c, path, depth)
	local n = c:ChildCount()
	for i = 0, n - 1 do
		local ch = UIComponent(c:Find(i))
		local cid = tostring(ch:Id())
		if string.match(cid, "^3D_") then flags = flags + 1
		else
			local x, y = ch:Position()
			local w, h = ch:Dimensions()
			local st = ch:CurrentState()
			nodes = nodes + 1
			emit(path .. cid .. "|" .. (ch:Visible() and "1" or "0") .. "|" .. tostring(x) .. "," .. tostring(y) .. "|" .. tostring(w) .. "," .. tostring(h) .. "|" .. tostring(st))
			if depth < 24 then walk(ch, path .. cid .. "/", depth + 1) end
		end
	end
end
if which == "*" then
	for i = 0, root:ChildCount() - 1 do
		local c = UIComponent(root:Find(i))
		local cid = tostring(c:Id())
		if c:Visible() and not string.match(cid, "^3D_") then
			local x, y = c:Position()
			local w, h = c:Dimensions()
			nodes = nodes + 1
			emit(cid .. "|1|" .. tostring(x) .. "," .. tostring(y) .. "|" .. tostring(w) .. "," .. tostring(h) .. "|" .. tostring(c:CurrentState()))
			walk(c, cid .. "/", 1)
		elseif string.match(cid, "^3D_") then flags = flags + 1 end
	end
else
	local f = root:Find(which)
	if f == nil then return label .. " absent " .. which end
	local c = UIComponent(f)
	local x, y = c:Position()
	local w, h = c:Dimensions()
	nodes = nodes + 1
	emit(which .. "|" .. (c:Visible() and "1" or "0") .. "|" .. tostring(x) .. "," .. tostring(y) .. "|" .. tostring(w) .. "," .. tostring(h) .. "|" .. tostring(c:CurrentState()))
	walk(c, which .. "/", 1)
end
part = part + 1
wsp.log("j10tree " .. label .. " " .. part .. ": " .. chunk .. "END flags=" .. flags)
return label .. " " .. nodes .. " nodes, " .. flags .. " unit flags"
