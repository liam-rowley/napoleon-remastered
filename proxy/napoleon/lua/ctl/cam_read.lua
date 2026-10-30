-- ctl/cam_read.lua - dev (J43): the battle camera's pose from BattleUI.BackProjectPosition, the readback ctl cam checks against
-- purpose: read the battle camera back: trilaterate its position from the camera distances BackProjectPosition returns for four fixed
--          points, then project points around it so the host fits yaw, pitch and the field of view (harness/core/campose.py)
-- usage: job.sh ctl <owner> "lua napoleon_remastered/lua/ctl/cam_read.lua" in a battle; ctl.py cam runs it
-- when: every ctl cam (the readback and its check) and any probe that needs the battle camera's pose
-- not-a-verb: runs inside the game's own Lua, not on a host
-- Returns "cam C=<x>,<y>,<z> S=<w>,<h> P=<x>,<y>,<z>,<sx>,<sy>,<depth>,<dist>;..." (no string.find/sub/gmatch: they stop the pump, fact
-- napoleon.lua.string_find_stalls_pump). BackProjectPosition(x, y, z, 0) returns screen x, screen y, depth, distance from the camera.
local id, ctx, wsp = ...
local B = getfenv(1).BattleUI
if type(B) ~= "table" or type(B.BackProjectPosition) ~= "function" then return "cam none: no BattleUI.BackProjectPosition (not a battle?)" end
local function bp(x, y, z)
	local ok, sx, sy, dp, d = pcall(B.BackProjectPosition, x, y, z, 0)
	if not ok or type(d) ~= "number" then return nil end
	return sx, sy, dp, d
end
-- trilateration from four non-coplanar points: |P_i - C|^2 = d_i^2, subtract the first -> a 3x3 linear system
local R = { { 0, 0, 0 }, { 400, 0, 0 }, { 0, 400, 0 }, { 0, 0, 400 } }
local d = {}
for i = 1, 4 do
	local _, _, _, di = bp(R[i][1], R[i][2], R[i][3])
	if not di then return "cam none: BackProjectPosition failed" end
	d[i] = di
end
-- with these reference points the system is diagonal: 2*400*c_k = d1^2 - d_{k+1}^2 + 400^2
local C = {}
for k = 1, 3 do C[k] = (d[1] * d[1] - d[k + 1] * d[k + 1] + 160000) / 800 end
local okw, w, h = pcall(B.ScreenSize)
local out = { string.format("cam C=%.4f,%.4f,%.4f S=%s,%s P=", C[1], C[2], C[3], tostring(w), tostring(h)) }
-- forward: of 26 directions at 100 m, the one nearest the screen centre; then a 3x3x3 cluster of points 100 m along it, 20 m apart,
-- all in front of the camera and on screen, for the host's fit
local best, bd = nil, nil
for dx = -1, 1 do for dy = -1, 1 do for dz = -1, 1 do
	if dx ~= 0 or dy ~= 0 or dz ~= 0 then
		local n = math.sqrt(dx * dx + dy * dy + dz * dz)
		local u = { dx / n, dy / n, dz / n }
		local sx, sy, dp = bp(C[1] + 100 * u[1], C[2] + 100 * u[2], C[3] + 100 * u[3])
		if sx and dp > 0 and dp < 1 and sx >= 0 and sy >= 0 and sx <= (w or 0) and sy <= (h or 0) then
			local e = (sx - w / 2) * (sx - w / 2) + (sy - h / 2) * (sy - h / 2)
			if not bd or e < bd then best, bd = u, e end
		end
	end
end end end
if not best then return "cam none: no direction projects on screen" end
local pts = {}
for ox = -1, 1 do for oy = -1, 1 do for oz = -1, 1 do
	local x, y, z = C[1] + 100 * best[1] + 20 * ox, C[2] + 100 * best[2] + 20 * oy, C[3] + 100 * best[3] + 20 * oz
	local sx, sy, dp, dd = bp(x, y, z)
	if sx then pts[#pts + 1] = string.format("%.3f,%.3f,%.3f,%.4f,%.4f,%.6f,%.4f", x, y, z, sx, sy, dp, dd) end
end end end
return out[1] .. table.concat(pts, ";")
