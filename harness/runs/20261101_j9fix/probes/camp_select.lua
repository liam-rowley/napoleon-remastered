-- camp_select.lua - J9 fix round: select one of the player's armies, fleets, agents or settlements on the campaign map.
-- Run in the campaign: job.sh ctl <owner> "lua <abs path>/camp_select.lua -- army|fleet|agent|settlement"; read the surface with
-- api_surface.lua a few seconds later (the selection's panels load on the next frames). The calls are the ones the campaign UI and
-- proxy/napoleon/lua/probes/campaign_select.lua use (argument counts as the static map reads them: discovery/napoleon/lua_cfuncs.json).
local id, ctx, wsp = ...
local kind = wsp.dev_config("lua_args")
local fid = CampaignUI.PlayerFactionId()
local list, sel
if kind == "agent" then
	list = CampaignUI.RetrieveFactionAgentsList(fid) or {}
elseif kind == "army" then
	list = CampaignUI.RetrieveFactionMilitaryForceLists(fid, true) or {}
elseif kind == "fleet" then
	list = CampaignUI.RetrieveFactionMilitaryForceLists(fid, false) or {}
elseif kind == "settlement" then
	-- RetrieveFactionRegionList's entries carry no Address (attempt 1 passed nil and SelectAndZoomToRegion faulted at +0x4e reading
	-- [0+0xfc]: run 20261101_j9fix); this list is documented as "regions ... by address and localised name"
	list = {}
	for k, v in pairs(CampaignUI.RegionsOwnedByFactionOrByProtectorates(fid) or {}) do list[#list + 1] = v end
else
	error("kind must be army, fleet, agent or settlement, not " .. tostring(kind))
end
local e = list[1]
if not e then return kind .. "|none|faction=" .. tostring(fid) .. " list=" .. #list end
if type(e) ~= "table" then return kind .. "|refused|entry is a " .. type(e) .. " (" .. tostring(e) .. "), list=" .. #list end
local ks = {}
for k, v in pairs(e) do if type(v) ~= "table" and type(v) ~= "userdata" and type(v) ~= "function" then ks[#ks + 1] = tostring(k) .. "=" .. tostring(v) end end
table.sort(ks)
local ok, err
local addr = e.Address or e.RegionAddress or e.address
if addr == nil then return kind .. "|refused|no address field, not called (a nil pointer faults the engine)|list=" .. #list .. " " .. table.concat(ks, " ") end
if kind == "settlement" then
	ok, err = pcall(CampaignUI.SelectAndZoomToRegion, addr, -1)
else
	ok, err = pcall(CampaignUI.SelectAndZoomToCharacter, addr, -1)
end
return kind .. "|" .. tostring(ok) .. (ok and "" or (" " .. tostring(err))) .. "|list=" .. #list .. " " .. table.concat(ks, " ")
