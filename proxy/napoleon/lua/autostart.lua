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
--                            Initialise(type, prefs, false)), the map list's NotifyItemSelected(<map's component address>), main_panel
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
	at("map list")
	local maps = mp:GlobalExists("available_maps")
	if type(maps) ~= "table" then error("sp_battle2 main_panel has no available_maps") end
	local hit, n = nil, 0
	for _, m in pairs(maps) do
		n = n + 1
		if want ~= "" and (lc(m.Key) == want or lc(m.Name) == want or lc(m.File) == want) then hit = m end
	end
	if want == "" then error("the preset names no map (" .. n .. " maps offered)") end
	if not hit then error("map '" .. want .. "' is not among the " .. n .. " " .. btype .. " maps (probes/list_maps.lua lists them)") end
	at("NotifyItemSelected " .. tostring(hit.Key))
	mp:LuaCall("NotifyItemSelected", hit.Component:Address())
	local sel = mp:GlobalExists("selected_map")
	local selkey = type(sel) == "table" and sel.Key or nil
	wsp.report("autostart.map", tostring(selkey))
	if lc(selkey) ~= lc(hit.Key) then error("map select did not take (selected_map " .. tostring(selkey) .. ")") end
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
	return "started battle " .. tostring(hit.Key) .. " (" .. btype .. ", prefs " .. prefs .. ", button " .. tostring(state) .. ")"
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

local ok, res = pcall(function()
	if kind == "frontend" then return "frontend: nothing to do" end
	if kind == "battle" then return battle() end
	if kind == "campaign" then return campaign() end
	error("unknown target kind '" .. tostring(kind) .. "'")
end)
if not ok then error("autostart " .. tostring(kind) .. " failed at " .. step .. ": " .. tostring(res), 0) end
return res
