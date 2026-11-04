-- probes/campaign_readback.lua - dev (J40): read back what the campaign console's acting commands change, read only
-- purpose: return the player's diplomatic relationship with every faction (CampaignUI.RetrieveFactionListForDiplomacy: Key=Relationship) and the player's first agent's name, location, position and traits (RetrieveFactionAgentsList entry .Traits[].Name): rel <key>=<relationship>,... || agent <name>|<location>|<PosX>|<PosY>|traits <a>,<b>
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/campaign_readback.lua" in a campaign, before and after a console line (declare_war <faction>, add_trait <trait> 1, transport_to_region <eur_key>); compare the two results
-- when: J40 read-back of console commands (fact napoleon.console.acting_commands); J4 scenario checks of diplomacy and agent placement
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local rel = {}
local ok, l = pcall(CampaignUI.RetrieveFactionListForDiplomacy)
if ok and type(l) == "table" then
	for k, e in pairs(l) do
		if type(e) == "table" then rel[#rel + 1] = tostring(e.Key or k) .. "=" .. tostring(e.Relationship) end
	end
	table.sort(rel)
else rel[1] = "error " .. tostring(l) end
local list = CampaignUI.RetrieveFactionAgentsList(CampaignUI.PlayerFactionId()) or {}
local e, agent = list[1], "none"
if e then
	local tr = {}
	for _, t in pairs(e.Traits or {}) do tr[#tr + 1] = tostring(type(t) == "table" and t.Name or t) end
	table.sort(tr)
	agent = table.concat({ tostring(e.Name), tostring(e.Location), tostring(e.PosX), tostring(e.PosY), "traits " .. table.concat(tr, ",") }, "|")
end
return "rel " .. table.concat(rel, ",") .. " || agent " .. agent   -- no :sub or string.find (fact napoleon.lua.string_find_stalls_pump)
