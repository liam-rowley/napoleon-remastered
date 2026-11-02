-- probes/army_options.lua - dev probe (J46): the custom battle's army size options and the army presets the front end offers
-- purpose: in the front end, open sp_battle2 for a battle type, read dropdown_army_size (option count and each option's ArmyFundsForSize),
--          UnitScaleFactor and MaxUnitsFromUnitScaleFactor, and FrontEnd.RetrieveArmyPresets(...) for a faction: preset names, unit counts
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/army_options.lua 30 -- <type> <faction>" in the front end (type: classic|naval|siege)
-- when: before a preset pins army.size (J46 army route); rerun after a game update
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local args = wsp.dev_config("lua_args")
local btype, fac = "classic", "france"
do
	local words = {}
	local cur = ""
	for i = 1, string.len(args) do
		local ch = string.char(string.byte(args, i))
		if ch == " " then if cur ~= "" then words[#words + 1] = cur end cur = "" else cur = cur .. ch end
	end
	if cur ~= "" then words[#words + 1] = cur end
	if words[1] then btype = words[1] end
	if words[2] then fac = words[2] end
end
local out = {}
local function add(k, v) out[#out + 1] = k .. "=" .. tostring(v) end
local function dump(t, depth)
	if type(t) ~= "table" then return tostring(t) end
	if (depth or 0) > 1 then return "{...}" end
	local f = {}
	for k, x in pairs(t) do f[#f + 1] = tostring(k) .. ":" .. dump(x, (depth or 0) + 1) end
	table.sort(f)
	return "{" .. table.concat(f, ",") .. "}"
end
local r = UIComponent(Component.Root())
r:LuaCall("TransitionTo", "sp_battle2")
local s2 = UIComponent(r:Find("sp_battle2"))
local mp = UIComponent(s2:Find("main_panel"))
mp:LuaCall("Initialise", btype, ".sp_default", false)
local dd = mp:Find("dropdown_army_size", false)
add("dropdown_army_size", dd ~= nil)
local naval = btype == "naval"
if dd ~= nil then
	local d = UIComponent(dd)
	local n = d:ChildCount()
	add("dd_children", n)
	local ok, sel = pcall(function() return d:LuaCall("SelectedOption") end)
	add("selected_option", ok and dump(sel) or "err")
	for i = 0, 6 do
		local ok2, f = pcall(FrontEnd.ArmyFundsForSize, i, naval)
		add("funds_" .. i, ok2 and tostring(f) or "err")
	end
end
add("unit_scale", FrontEnd.UnitScaleFactor())
add("max_units", FrontEnd.MaxUnitsFromUnitScaleFactor(FrontEnd.UnitScaleFactor()))
local pr = mp:LuaCall("Preferences")
add("prefs", dump(pr))
local okp, presets = pcall(FrontEnd.RetrieveArmyPresets, fac, pr.map and pr.map.Type or btype, pr.army_size, pr.era, pr.unit_scale)
add("presets_ok", okp)
if okp and type(presets) == "table" then
	for name, p in pairs(presets) do
		local nu = type(p) == "table" and type(p.Units) == "table" and #p.Units or -1
		local ns = type(p) == "table" and type(p.Ships) == "table" and #p.Ships or -1
		add("preset_" .. tostring(name), "units=" .. nu .. " ships=" .. ns .. " faction=" .. tostring(type(p) == "table" and p.Faction))
	end
else
	add("presets_err", presets)
end
-- sweep: the page's dropdowns, then every army_size option through SetPerBattlePrefs and the balanced preset it gives
local names = {}
for i = 0, mp:ChildCount() - 1 do local c = UIComponent(mp:Find(i)); names[#names + 1] = tostring(c:Id()) end
add("mp_children", table.concat(names, ","))
for _, sc in ipairs({ 0.5, 0.75, 1, 1.5, 2 }) do add("maxunits_" .. sc, FrontEnd.MaxUnitsFromUnitScaleFactor(sc)) end
for _, nm in ipairs({ "dropdown_army_size", "dropdown_unit_scale" }) do
	local c = mp:Find(nm, false)
	if c ~= nil then
		local d = UIComponent(c)
		local o = {}
		for i = 0, d:ChildCount() - 1 do o[#o + 1] = tostring(UIComponent(d:Find(i)):Id()) end
		add(nm .. "_children", table.concat(o, ","))
	end
end
for sz = 0, 2 do
	mp:LuaCall("SetPerBattlePrefs", { army_size = sz })
	local p2 = mp:LuaCall("Preferences")
	local ok3, pr3 = pcall(FrontEnd.RetrieveArmyPresets, fac, p2.map.Type, p2.army_size, p2.era, p2.unit_scale)
	local b = ok3 and pr3.balanced
	add("size" .. sz, "army_size=" .. tostring(p2.army_size) .. " funds=" .. tostring(p2.allowed_funds) .. " unit_scale=" .. tostring(p2.unit_scale) .. " balanced_units=" .. tostring(b and #b.Units) .. " ships=" .. tostring(b and #b.Ships))
end
pcall(function() r:LuaCall("TransitionTo", "main") end)
return table.concat(out, " | ")
