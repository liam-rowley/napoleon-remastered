-- s4.lua - J32 S4 probes: route A (a vanilla screen alive but undrawn) on one component, by verb.
-- Run: job.sh ctl j32 "lua <abs path>/s4.lua -- <verb> <args>". No string library call but string.match and string.len (fact napoleon.lua.string_find_stalls_pump);
-- every binding with the argument count of discovery/napoleon/lua_cfuncs.json (fact napoleon.lua.arg_stream).
-- snap <label> <id>   log every descendant as path|visible|state|text (j32snap lines); returns nodes, text count and total text length
-- pos <id>            x y w h visible interactive
-- vis <id> 0|1        SetVisible           pvis <id> 0|1   PropagateVisibility
-- move <id> <x> <y>   MoveTo               alpha <id> <0..255> PropagateOpacity
-- int <id> 0|1        SetInteractive       call <id> <fn> [arg]  LuaCall
-- top                 visible children of the root
-- clock <n>           cost of n component reads and of n wsp.log-free bridge calls, for the channel estimate
-- army                keys of the first army entry and its first unit, for a route to the unit popup
local id, ctx, wsp = ...
local arg = wsp.dev_config("lua_args") or ""
local verb, a, b, c = string.match(arg, "^(%S+)%s*(%S*)%s*(%S*)%s*(%S*)")
local root = UIComponent(Component.Root())
local function get(n)
	if n == "root" then return root end
	local f = root:Find(n)
	if f == nil then return nil end
	return UIComponent(f)
end
local function miss(n) return "absent " .. tostring(n) end

if verb == "top" then
	local out = {}
	for i = 0, root:ChildCount() - 1 do
		local k = UIComponent(root:Find(i))
		if k:Visible() then out[#out + 1] = tostring(k:Id()) end
	end
	return table.concat(out, " ")
elseif verb == "snap" then
	local cmp = get(b)
	if cmp == nil then return miss(b) end
	local chunk, part, nodes, texts, total = "", 0, 0, 0, 0
	local function emit(s)
		chunk = chunk .. s .. ";"
		if string.len(chunk) > 1400 then part = part + 1 wsp.log("j32snap " .. a .. " " .. part .. ": " .. chunk) chunk = "" end
	end
	local function walk(p, path, depth)
		for i = 0, p:ChildCount() - 1 do
			local ch = UIComponent(p:Find(i))
			local cid = tostring(ch:Id())
			local t = ch:GetStateText()
			t = t and tostring(t) or ""
			nodes = nodes + 1
			if t ~= "" then texts = texts + 1 total = total + string.len(t) end
			emit(path .. cid .. "|" .. (ch:Visible() and "1" or "0") .. "|" .. tostring(ch:CurrentState()) .. "|" .. t)
			if depth < 24 then walk(ch, path .. cid .. "/", depth + 1) end
		end
	end
	walk(cmp, "", 1)
	part = part + 1
	wsp.log("j32snap " .. a .. " " .. part .. ": " .. chunk .. "END")
	return a .. " nodes=" .. nodes .. " texts=" .. texts .. " len=" .. total
elseif verb == "pos" then
	local cmp = get(a)
	if cmp == nil then return miss(a) end
	local x, y = cmp:Position()
	local w, h = cmp:Dimensions()
	return table.concat({tostring(x), tostring(y), tostring(w), tostring(h), tostring(cmp:Visible()), tostring(cmp:IsInteractive())}, " ")
elseif verb == "vis" or verb == "pvis" or verb == "int" then
	local cmp = get(a)
	if cmp == nil then return miss(a) end
	local on = b == "1"
	if verb == "vis" then cmp:SetVisible(on) elseif verb == "pvis" then cmp:PropagateVisibility(on) else cmp:SetInteractive(on) end
	return verb .. " " .. a .. " " .. b .. " now visible=" .. tostring(cmp:Visible())
elseif verb == "move" then
	local cmp = get(a)
	if cmp == nil then return miss(a) end
	local x, y = cmp:Position()
	cmp:MoveTo(tonumber(b), tonumber(c))
	local nx, ny = cmp:Position()
	return "move " .. a .. " was " .. tostring(x) .. "," .. tostring(y) .. " now " .. tostring(nx) .. "," .. tostring(ny)
elseif verb == "alpha" then
	local cmp = get(a)
	if cmp == nil then return miss(a) end
	cmp:PropagateOpacity(tonumber(b))
	return "alpha " .. a .. " " .. b
elseif verb == "call" then
	local cmp = get(a)
	if cmp == nil then return miss(a) end
	local ok, r
	if c ~= "" then ok, r = pcall(function() return cmp:LuaCall(b, c) end) else ok, r = pcall(function() return cmp:LuaCall(b) end) end
	return "call " .. a .. " " .. b .. " " .. tostring(ok) .. " " .. tostring(r)
elseif verb == "clock" then
	local n = tonumber(a) or 1000
	local t0 = os.clock()
	for i = 1, n do local k = root:ChildCount() end
	local t1 = os.clock()
	for i = 1, n do local k = wsp.dev_config("lua_args") end
	local t2 = os.clock()
	return "n=" .. n .. " component_us=" .. tostring((t1 - t0) / n * 1000000) .. " bridge_us=" .. tostring((t2 - t1) / n * 1000000)
elseif verb == "bsel" then
	-- no-argument BattleUI calls only (fact napoleon.lua.battleui_error_stops_pump)
	local ok, r = pcall(function() return BattleUI.SelectAllInfantry() end)
	return "SelectAllInfantry " .. tostring(ok) .. " " .. tostring(r)
elseif verb == "bhalt" then
	local ok, r = pcall(function() return BattleUI.Current_Selection_Halt() end)
	return "Current_Selection_Halt " .. tostring(ok) .. " " .. tostring(r)
elseif verb == "ccost" then
	-- route B's feed cost: the panel's getters, flattened to one string as a channel would carry them
	local n = tonumber(a) or 20
	local fid = CampaignUI.PlayerFactionId()
	local t0 = os.clock()
	local forces, regions, agents
	for i = 1, n do
		forces = CampaignUI.RetrieveFactionMilitaryForceLists(fid, true) or {}
		regions = CampaignUI.RetrieveFactionRegionList(fid) or {}
		agents = CampaignUI.RetrieveFactionAgentsList(fid) or {}
	end
	local t1 = os.clock()
	local size, s = 0, ""
	for i = 1, n do
		local parts = {}
		for _, list in ipairs({forces, regions, agents}) do
			for _, e in ipairs(list) do
				for k, v in pairs(e) do
					local ty = type(v)
					if ty == "string" or ty == "number" or ty == "boolean" then parts[#parts + 1] = tostring(k) .. "=" .. tostring(v) end
				end
			end
		end
		s = table.concat(parts, "\n")
		size = string.len(s)
	end
	local t2 = os.clock()
	return "n=" .. n .. " forces=" .. #forces .. " regions=" .. #regions .. " agents=" .. #agents .. " getters_ms=" .. tostring((t1 - t0) / n * 1000) .. " flatten_ms=" .. tostring((t2 - t1) / n * 1000) .. " bytes=" .. size
elseif verb == "army" then
	local fid = CampaignUI.PlayerFactionId()
	local list = CampaignUI.RetrieveFactionMilitaryForceLists(fid, true) or {}
	local e = list[1]
	if not e then return "no army" end
	local ks = {}
	for k, v in pairs(e) do ks[#ks + 1] = tostring(k) .. "=" .. type(v) end
	table.sort(ks)
	return table.concat(ks, " ")
end
return "unknown verb " .. tostring(verb)
