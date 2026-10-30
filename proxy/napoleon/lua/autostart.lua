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
--                            SetupBattle (-> sp_battle3 with Preferences()), sp_battle3 StartBattle; a preset of type=historic uses
--                            the historical screens the same way (sp_battle1 HistoricBattle: sp_battle2_scenario, main_panel
--                            Initialise("historic", ...), SetupBattle -> sp_battle3_scenario, its StartBattle; J44), map = the battle key
--   campaign:continue        FrontEnd.ContinueCampaign() (main menu Continue Campaign)
--   campaign:<save>          FrontEnd.LoadCampaign(<save>)
--   campaign:new:<c>:<f>     TransitionTo("grand_campaign", nil, <c>) (= main menu), faction <f>, the page's StartCampaign();
--                            <c> must be a main-menu button's campaign_key (grand = the grand campaign: mp_eur_napoleon)
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
	local page2, page3 = "sp_battle2", "sp_battle3"
	if btype == "historic" then page2, page3 = "sp_battle2_scenario", "sp_battle3_scenario" end
	at("TransitionTo " .. page2); r:LuaCall("TransitionTo", page2)
	local s2 = UIComponent(r:Find(page2))
	local mp = UIComponent(s2:Find("main_panel"))
	-- preset all_maps=1: Initialise's third argument true (FrontEnd.EnumerateBattleMaps(type, true)): for type historic the only list with
	-- maps on this PC (the historical NHMPB_ battles; with false it is empty, run 20261030_j44pc, fact napoleon.autostart.historical)
	local allMaps = wsp.dev_config("preset.all_maps") == "1"
	at("Initialise " .. btype .. " " .. prefs .. " " .. tostring(allMaps)); mp:LuaCall("Initialise", btype, prefs, allMaps)
	-- the map list: available_maps is a local of main_panel, so walk the list box's children (one per map, made by InitialiseMaps)
	-- and select each through the page's own NotifyItemSelected until selected_map (a global of the page) is the wanted one
	at("map list")
	if want == "" then error("the preset names no map") end
	local lbc = mp:Find("list_box")
	if lbc == nil then error(page2 .. " main_panel has no list_box") end
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
	local cur, dot = "", false   -- a historical map's File ends in a file name ("...hb_dresden/dresden_battle.xml"): then the folder before it
	for i = 1, string.len(f) do
		local ch = string.char(string.byte(f, i))
		if ch == "/" or ch == "\\" then if cur ~= "" then folder = cur end cur = ""; dot = false
		else cur = cur .. ch; if ch == "." then dot = true end end
	end
	if cur ~= "" and not dot then folder = cur end
	-- a historical setup's folder (dresden_3v3) is not its terrain's (hb_dresden): the preset names the terrain the engine must load
	if wsp.dev_config("preset.terrain") ~= "" then folder = wsp.dev_config("preset.terrain") end
	wsp.report("autostart.map_folder", string.lower(folder))
	-- weather and time of day (J44): NotifyItemSelected refilled dropdown_weather / dropdown_time_of_day for this map
	-- (SetValidWeatherAndDayTypes), so pin them after it, through the page's own SetPerBattlePrefs (SelectOption per dropdown)
	local wantW, wantT = wsp.dev_config("preset.weather"), wsp.dev_config("preset.time_of_day")
	if wantW ~= "" or wantT ~= "" then
		local t = {}
		if wantW ~= "" then t.weather = tonumber(wantW) end
		if wantT ~= "" then t.time_of_day = tonumber(wantT) end
		at("SetPerBattlePrefs weather=" .. wantW .. " time_of_day=" .. wantT); mp:LuaCall("SetPerBattlePrefs", t)
	end
	at("Preferences readback")
	local pr = mp:LuaCall("Preferences")
	local said = ""
	if type(pr) == "table" then
		said = " weather=" .. tostring(pr.weather) .. "/" .. tostring(pr.weather_string) .. " time_of_day=" .. tostring(pr.time_of_day)
		wsp.report("autostart.weather", tostring(pr.weather) .. "/" .. tostring(pr.weather_string))
		wsp.report("autostart.time_of_day", tostring(pr.time_of_day))
	end
	at("SetupBattle"); mp:LuaCall("SetupBattle")
	local s3c = r:Find(page3, false)
	if s3c == nil then error(page3 .. " did not open") end
	local s3 = UIComponent(s3c)
	at("StartBattle")
	local okb = s3:Find("button_start", false) or s3:Find("button_ok", false)
	local state = okb and UIComponent(okb):CurrentState() or "?"
	local start = s3:GlobalExists("StartBattle")
	if type(start) ~= "function" then error(page3 .. " has no StartBattle") end
	if state == "inactive" then error("the start button is inactive (no armies? state " .. tostring(state) .. ")") end
	start()
	return "started battle " .. tostring(selkey) .. " (" .. btype .. ", prefs " .. prefs .. ", button " .. tostring(state) .. ")" .. said
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
	-- The key must be one a main-menu campaign button carries (main.main reads grand_campaign's campaign_key the same way):
	-- grand_campaign.OnEnter calls FrontEnd.OpenMapDataFile(key), and an unknown key is an access violation in the engine
	-- (J3 run 20261029_j3pc2: "napoleon" killed the front end). "grand" = whatever the grand campaign button carries.
	at("campaign key " .. camp)
	local known = {}
	for _, b in ipairs({ "grand_campaign", "episodic_campaign", "spain_campaign" }) do
		local a = r:Find(b)
		local k = a and UIComponent(a):GetProperty("campaign_key")
		if k ~= nil and k ~= "" then known[#known + 1] = tostring(k); if lc(camp) == "grand" and b == "grand_campaign" then camp = tostring(k) end end
	end
	local okKey = false
	for i = 1, #known do if lc(known[i]) == lc(camp) then okKey = true; camp = known[i] end end
	if not okKey then error("campaign '" .. camp .. "' is not a main-menu campaign key (known: " .. table.concat(known, " ") .. "; probes/campaign_keys.lua)") end
	wsp.report("autostart.campaign", camp)
	at("TransitionTo grand_campaign " .. camp); r:LuaCall("TransitionTo", "grand_campaign", nil, camp)
	local page = UIComponent(r:Find("grand_campaign"))
	local mp = UIComponent(page:Find("main_panel"))
	at("faction " .. fac)
	local cur = mp:LuaCall("FactionAndVCType")
	if lc(cur) ~= lc(fac) then
		-- main_panel.Initialise has two faction widgets: faction_selection (flags, one child per faction named by its Key; its
		-- FactionSelected(key) sets the flag states and calls the panel's NotifyFactionSelected) or, for button campaigns,
		-- faction_ButtonGroup (buttons with a global `faction`; SelectButton + WellingtonFactionButtonSelected, its g_notify_func)
		local fsA = mp:Find("faction_selection")
		local g = mp:Find("faction_ButtonGroup")
		if fsA ~= nil then
			local fs = UIComponent(fsA)
			local seen, key = {}, nil
			-- faction_selection.Initialise: CreateFromComponent(template, <Key>, placeholder_faction_<i>): the flags are grandchildren
			for i = 0, fs:ChildCount() - 1 do
				local ph = fs:Find(i)
				local pc = ph and UIComponent(ph)
				for j = 0, (pc and pc:ChildCount() or 0) - 1 do
					local c = pc:Find(j); local id = c and UIComponent(c):Id()
					if id ~= nil then seen[#seen + 1] = tostring(id); if lc(id) == lc(fac) then key = id end end
				end
			end
			if key == nil then error("faction '" .. fac .. "' is not offered (faction_selection children: " .. table.concat(seen, " ") .. ")") end
			fs:LuaCall("FactionSelected", key)
		elseif g ~= nil then
			local grp = UIComponent(g)
			local notify = mp:GlobalExists("WellingtonFactionButtonSelected")
			if type(notify) ~= "function" then error("main_panel has no WellingtonFactionButtonSelected") end
			local seen, hit = {}, nil
			for i = 0, grp:ChildCount() - 1 do
				local c = grp:Find(i)
				local f = c and UIComponent(c):GlobalExists("faction")
				if f ~= nil then seen[#seen + 1] = tostring(f); if lc(f) == lc(fac) then hit = c end end
			end
			if hit == nil then error("faction '" .. fac .. "' is not offered (factions: " .. table.concat(seen, " ") .. ")") end
			grp:LuaCall("SelectButton", hit)
			notify(hit)
		else
			error("main_panel has neither faction_selection nor faction_ButtonGroup (faction is " .. tostring(cur) .. ")")
		end
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
