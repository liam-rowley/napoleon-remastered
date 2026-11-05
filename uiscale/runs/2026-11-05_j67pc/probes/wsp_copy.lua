-- wsp_copy.lua - J67 route probe: which copy of ui\battle ui\root.luac does wsp.vanilla return while a scale pack patches it?
-- Run in a battle: job.sh ctl <owner> "lua <abs path>/wsp_copy.lua". Patch main#80 K7 is 38 in vanilla and 76 at 2x; the float32 constant
-- record 03 00 00 98 42 (76.0) is only in the patched script and 03 00 00 18 42 (38.0) only in the vanilla one (checked on the host, run
-- 2026-11-05_j67pc). Other factors: 47.5 -> 48 at 1.25 (03 00 00 40 42), 57 at 1.5 (03 00 00 64 42).
-- Returns "<len>|38:<bool>|76:<bool>|48:<bool>|57:<bool>". Read only. No string library call but string.match and string.len.
local id, ctx, wsp = ...
local bytes, err = wsp.vanilla("ui\\battle ui\\root.luac")
if not bytes then return "no copy|" .. tostring(err) end
local function has(p) return string.match(bytes, p) ~= nil end
return string.len(bytes) .. "|38:" .. tostring(has("\3%z%z\24B")) .. "|76:" .. tostring(has("\3%z%z\152B"))
	.. "|48:" .. tostring(has("\3%z%z@B")) .. "|57:" .. tostring(has("\3%z%zdB"))
