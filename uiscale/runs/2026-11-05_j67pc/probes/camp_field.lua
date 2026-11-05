-- camp_field.lua - J67: select a field army, so the campaign unit-card row shows. camp_select.lua takes the list's first entry, a garrison
-- (Location = a town, Lemberg), which selects the settlement. A field army's Location is a province. Run in campaign_start (Austria):
-- job.sh ctl <owner> "lua <abs path>/camp_field.lua". Calls as camp_select.lua (argument counts: discovery/napoleon/lua_cfuncs.json).
local id, ctx, wsp = ...
local fid = CampaignUI.PlayerFactionId()
local list = CampaignUI.RetrieveFactionMilitaryForceLists(fid, true) or {}
local want = { Bavaria = true, Bohemia = true, Austria = true, Venetia = true }
for _, e in ipairs(list) do
	if type(e) == "table" and want[e.Location] and e.Address ~= nil then
		local ok, err = pcall(CampaignUI.SelectAndZoomToCharacter, e.Address, -1)
		return "field|" .. tostring(ok) .. "|" .. tostring(e.Name) .. "|" .. tostring(e.Location) .. "|units=" .. tostring(e.Units) .. (ok and "" or ("|" .. tostring(err)))
	end
end
return "field|none|list=" .. #list
