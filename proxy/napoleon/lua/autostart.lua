-- napoleon_remastered\lua\autostart.lua - dev only (J3). Run by the proxy (dev.cpp Autostart) as a `lua` command in the front end's
-- purpose: drive the front end to a target (custom battle preset, new / continued / loaded campaign) through its own Lua calls
-- usage: run by the proxy (ctl `autostart <target>`, dev.autostart, `reset <target>`); not by hand
-- when: every autostart; change it when a front-end flow changes (the calls are documented in its header)
-- not-a-verb: runs inside the game's own Lua, not on a host
-- pumping script (main.advert), so FrontEnd / UIComponent / Component are the front end's own. Drives the engine the way its own
-- buttons do (no coordinate clicks); the target comes from wsp.dev_config("target.*"), a battle preset's keys from "preset.*"
-- (napoleon_remastered\lua\battles\<preset>.txt). Returns "started ..." when the engine was told to load; errors with the failed step.
-- The proxy then waits for the scene and checks the battle map against the engine's own battle details.
--   battle:<preset>          the custom-battle screens' calls: sp_battle1 SelectBattleType (TransitionTo sp_battle2, main_panel
--                            Initialise(type, prefs, false)), the map list's NotifyItemSelected(<a list child's address>), main_panel
--                            SetupBattle (-> sp_battle3 with Preferences()), sp_battle3 StartBattle
--   campaign:continue        FrontEnd.ContinueCampaign() (main menu Continue Campaign)
--   campaign:<save>          FrontEnd.LoadCampaign(<save>)
--   campaign:new:<c>:<f>     TransitionTo("grand_campaign", nil, <c>) (= main menu), faction <f>, the page's StartCampaign()
-- Rules: no string.find / string.sub / patterns (the engine replaces them); plain loops only.
local id, ctx, wsp = ...
local kind, mode = wsp.dev_config("target.kind"), wsp.dev_config("target.mode")
local function lc(x) return string.lower(tostring(x)) end
local step = "start"
local function at(s) step = s end

local function root() return UIComponent(Component.Root()) end

local function battle()
	local btype = wsp.dev_config("preset.type"); if btype == "" then btype = "classic" end
	local prefs = wsp.dev_config("preset.prefs"); if prefs == "" then prefs = ".sp_default" end
	local want = lc(wsp.dev_config("preset.map"))
	local r = root()
	at("TransitionTo sp_battle2"); r:LuaCall("TransitionTo", "sp_battle2")
	local s2 = UIComponent(r:Find("sp_battle2"))
	local mp = UIComponent(s2:Find("main_panel"))
	at("Initialise " .. btype .. " " .. prefs); mp:LuaCall("Initialise", btype, prefs, false)
	-- the map list: available_maps is a local of main_panel, so walk the list box's children (one per map, made by InitialiseMaps)
	-- and select each through the page's own NotifyItemSelected until selected_map (a global of the page) is the wanted one
	at("map list")
	if want == "" then error("the preset names no map") end
	local lbc = mp:Find("list_box")
	if lbc == nil then error("sp_battle2 main_panel has no list_box") end
	local lb = UIComponent(lbc)
	local n = lb:ChildCount()
	local selkey, seen = nil, {}
	for i = 0, n - 1 do
		local c = UIComponent(lb:Find(i))
		at("NotifyItemSelected child " .. i)
		mp:LuaCall("NotifyItemSelected", c:Address())
		local sel = mp:GlobalExists("selected_map")
		selkey = type(sel) == "table" and sel.Key or nil
		seen[#seen + 1] = tostring(selkey)
		if lc(selkey) == want or (type(sel) == "table" and (lc(sel.Name) == want or lc(sel.File) == want)) then break end
		selkey = nil
	end
	if not selkey then error("map '" .. want .. "' is not among the " .. n .. " " .. btype .. " maps: " .. table.concat(seen, " ")) end
	wsp.report("autostart.map", tostring(selkey))
	local sel = mp:GlobalExists("selected_map")
	local folder = ""   -- the last part of the map's File ("BattleTerrain/Presets/NAP_MP_Grassy_Flatlands/"), plain scan, no patterns
	local f = tostring(type(sel) == "table" and sel.File or "")
	local cur = ""
	for i = 1, string.len(f) do
		local ch = string.char(string.byte(f, i))
		if ch == "/" or ch == "\\" then if cur ~= "" then folder = cur end cur = "" else cur = cur .. ch end
	end
	if cur ~= "" then folder = cur end
	wsp.report("autostart.map_folder", string.lower(folder))
	at("SetupBattle"); mp:LuaCall("SetupBattle")
	local s3c = r:Find("sp_battle3", false)
	if s3c == nil then error("sp_battle3 did not open") end
	local s3 = UIComponent(s3c)
	at("StartBattle")
	local okb = s3:Find("button_start", false) or s3:Find("button_ok", false)
	local state = okb and UIComponent(okb):CurrentState() or "?"
	local start = s3:GlobalExists("StartBattle")
	if type(start) ~= "function" then error("sp_battle3 has no StartBattle") end
	if state == "inactive" then error("the start button is inactive (no armies? state " .. tostring(state) .. ")") end
	start()
	return "started battle " .. tostring(selkey) .. " (" .. btype .. ", prefs " .. prefs .. ", button " .. tostring(state) .. ")"
end

local function campaign()
	if mode == "continue" then at("ContinueCampaign"); FrontEnd.ContinueCampaign(); return "started campaign (continue)" end
	if mode == "save" then
		local save = wsp.dev_config("target.save")
		at("LoadCampaign " .. save)
		if type(FrontEnd.LoadCampaign) ~= "function" then error("FrontEnd.LoadCampaign does not exist") end
		FrontEnd.LoadCampaign(save)
		return "started campaign " .. save
	end
	local camp, fac = wsp.dev_config("target.campaign"), wsp.dev_config("target.faction")
	local r = root()
	at("TransitionTo grand_campaign " .. camp); r:LuaCall("TransitionTo", "grand_campaign", nil, camp)
	local page = UIComponent(r:Find("grand_campaign"))
	local mp = UIComponent(page:Find("main_panel"))
	at("faction " .. fac)
	local cur = mp:LuaCall("FactionAndVCType")
	if lc(cur) ~= lc(fac) then
		local fl = mp:GlobalExists("faction_list")
		if fl == nil then error("main_panel has no faction_list (faction is " .. tostring(cur) .. ")") end
		local flc = type(fl) == "table" and fl or UIComponent(fl)
		pcall(function() flc:LuaCall("SetSelected", fac) end)
		cur = mp:LuaCall("FactionAndVCType")
		if lc(cur) ~= lc(fac) then error("faction select did not take (page says " .. tostring(cur) .. ")") end
	end
	wsp.report("autostart.faction", tostring(cur))
	at("StartCampaign")
	local start = page:GlobalExists("StartCampaign")
	if type(start) ~= "function" then error("grand_campaign has no StartCampaign") end
	start()
	return "started new campaign " .. camp .. " as " .. tostring(cur)
end

-- Everything happens synchronously inside this one chunk: only the main menu's advert script pumps (the custom-battle and campaign
-- screens have no update callback), so a half-done flow could not be continued by a later command (run 20261029_j3pc).
local ok, res = pcall(function()
	if kind == "frontend" then return "frontend: nothing to do" end
	if kind == "battle" then return battle() end
	if kind == "campaign" then return campaign() end
	error("unknown target kind '" .. tostring(kind) .. "'")
end)
if not ok then
	pcall(function() root():LuaCall("TransitionTo", "main") end)   -- back to the main menu, so the next autostart can run
	error("autostart " .. tostring(kind) .. " failed at " .. step .. ": " .. tostring(res), 0)
end
return res
