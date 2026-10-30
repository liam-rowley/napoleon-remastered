-- probes/weather_options.lua - dev probe (J44): the custom battle's weather and time-of-day options for one map
-- purpose: return FrontEnd.BattleWeatherAndTimeOfDayOptionsString(<map key>) (the strings sp_battle2 main_panel's SetValidWeatherAndDayTypes
--          puts into dropdown_weather and dropdown_time_of_day), so a preset can name its weather and time of day by index
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/probes/weather_options.lua 20 -- <map key>" in the front end
-- when: before pinning a battle preset's weather and time_of_day (J44 scenario library)
-- not-a-verb: runs inside the game's own Lua, not on a host
local id, ctx, wsp = ...
local key = wsp.dev_config("lua_args")
if type(FrontEnd) ~= "table" or type(FrontEnd.BattleWeatherAndTimeOfDayOptionsString) ~= "function" then
	return "weather none: no FrontEnd.BattleWeatherAndTimeOfDayOptionsString here"
end
local ok, a, b = pcall(FrontEnd.BattleWeatherAndTimeOfDayOptionsString, key)
local function dump(t)   -- {i: {field=value}} or {i: value}, one level down, plain loops (no string.find: the engine replaces it)
	if type(t) ~= "table" then return tostring(t) end
	local out = {}
	for i, v in pairs(t) do
		if type(v) == "table" then
			local f = {}
			for k, x in pairs(v) do f[#f + 1] = tostring(k) .. "=" .. tostring(x) end
			out[#out + 1] = tostring(i) .. ":{" .. table.concat(f, ",") .. "}"
		else
			out[#out + 1] = tostring(i) .. ":" .. tostring(v)
		end
	end
	return table.concat(out, " ")
end
return "weather map=" .. tostring(key) .. " ok=" .. tostring(ok) .. " weather=[" .. dump(a) .. "] tod=[" .. dump(b) .. "]"
