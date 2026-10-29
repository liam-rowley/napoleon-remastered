# Run 20261029_j3pc2: J3 second sitting (baselines, presets, campaign, 10 resets, cache, restore, uninstall)

officepc, 2026-10-29 09:42-10:36 UTC, Napoleon.exe sha1 `9aebcd21...` (pinned), DXVK 3.1.1, RTX 4090. Unattended through the watcher
(Liam said go; the game ran fullscreen on his primary display). Builds: `99c4503daf5e` (kit `kit_20261029T093221Z_99c4503daf5e`) with the
Lua files synced sha-checked from the repo while the campaign path was fixed (`autostart.lua` `c7d84add...`, `reset.lua` `606af215...`,
`probes/campaign_keys.lua`), then the final kit `kit_20261029T103551Z_066fbd0b7c62` (every dev key off). Dev keys for the runs:
`dev.timeline=1 dev.lua_bridge=1 dev.state_json=1 dev.ctl=1`, `dev.skip_intro` per arm. Settings under watcher profile `proxy-dxvk`
(snapshot first). Every control result: `raw/ctl.jsonl`; per launch `raw/<label>/` (timeline.json, proxy.log, DXVK log).
Phase table: `raw/timeline_table.json` (`proxy/tools/timeline_table.py intro_skip=raw/S1..S5 movies=raw/B1..B5`).

## Phase timeline, seconds from process creation (median, range; n=5 each)

| phase | intro skip (S1-S5) | movies (B1-B5) |
|---|---|---|
| DllMain | 0.06 | 0.06 |
| Direct3DCreate9 | 1.10 (1.09-1.14) | 1.09 (1.08-1.12) |
| device created / first Present | 1.80 / 1.85 | 1.78 / 1.83 |
| Lua bridge loaded | 6.73 (6.59-7.13) | 7.23 (6.68-7.57) |
| start-up movies | refused at 6.98 | sega 3.3 s, corei7 4.8 s, ntw_intro 115.7 s |
| main menu pumps (scene frontend) | **6.99 (6.85-7.39)** | **131.36 (130.70-131.70)** |
| autostart issued (1.5 s settle + ctl) | 7.53 | 135.42 |
| land battle deployed (`battle:land_small`) | **26.36 (26.13-26.81)** | 154.17 (153.79-158.87) |

Battle load (StartBattle to the battle pumping) is 18.1-18.4 s in both arms: the movies are the only difference (124.4 s).

## Autostart targets (each map or key checked; `raw/ctl.jsonl`)

| target | launches | load_s | map / result |
|---|---|---|---|
| `battle:land_small` | 10 (+11 in resets, +2 cache) | 18.1-18.4 | NAP_MP_Grassy_Flatlands every time |
| `battle:naval_small` | 3 | 19.1-19.4 | caribbean, scene `naval` |
| `battle:siege_small` | 3 | 20.5-20.9 | rti_fort_1 |
| `campaign:new:grand:<faction>` | 4 (britain, prussia, austria, russia) | 16.7-17.3 | `mp_eur_napoleon`, scene `campaign` |
| `campaign:new:napoleon:france` | 1 | - | not a campaign key: `FrontEnd.OpenMapDataFile` took an AV (KERNELBASE, first-chance) and the front end stopped pumping. Fixed: autostart now refuses keys no main-menu button carries |
| `campaign:continue`, `campaign:<save>` | 0 | - | no campaign saves on the PC (`FrontEnd.CampaignSavesExist()` false); J14 owns saves |

The grand campaign's factions are austria, britain, prussia, russia (no france); the main menu's episodic campaign button carries no key.

## Warm reset

- **Battle, 10 in a row in one process** (`reset battle:land_small`, `raw/f_resets10`): 10/10 ok, back in the deployed battle each time.
  To the front end 7.3-13.6 s (8 s of it is the settle a battle needs before quitting, run 20261029_j3pc), total 27.1-33.4 s.
  Address space 1844 -> 1859 MB over 10 cycles (about +1.5 MB per cycle), commit about 1.26 GB flat. A relaunch to the same deployed
  battle is 26.4 s, so the warm reset does not beat a relaunch on this PC; it keeps the process (and the watcher's lock) instead.
- **Campaign** (`reset frontend` from a fresh campaign): the campaign root has no `QuitToMainScreen`; the escape menu's
  `Root.LuaCall("QuitToMainScreenFromEscapeMenu")` is now sent, but the campaign stayed (its pump went silent for 123 s, then the
  opening event message showed; a second request after that also timed out). Open; relaunch is the fallback.

## Driver and DXVK cache

DXVK 3.1.1 keeps a pipeline cache in `napoleon_remastered\dxvk\cache` (`0b493d00fda21c6f.dxvk.bin`, 1.9 MB). Moved aside (to
`C:\napoleon_remastered_pc\_to_delete\dxvk_cache_cold_*`), one cold and one warm launch: front end 6.5 / 5.7 s, battle load 18.2 / 18.2 s.
No warm step is worth building. The NVIDIA driver's own cache was left warm (shared with every game on the PC): not measured.

## Settings restore, uninstall

- After all launches the lock was released: the watcher restored the five config targets (prefs `c2202172`, keys `adc99cc4`,
  battle_prefs `36642c2b`, mod ini `eb380875`, dxvk.conf absent), all byte-identical to the snapshot taken before (watcher log 10:34:12Z).
- `pc_deploy.py uninstall`: game folder identical to the pre-install snapshot (1564 files), 10:35Z. Then the final kit was reinstalled.

## Incidents

- 09:56Z, during Liam's monitor swap (the device link dropped too): one launch crawled (DllMain at +10 s, Direct3DCreate9 +103 s,
  device +191 s), the watcher killed it as hung (IsHungAppWindow 103 s; `watcher/runs/20261029T100115Z_hang`); a DXVK null read at
  the kill second. An environment event, not counted against the kill criteria.
- The watcher's lock expired while the link was down; it restored every config file by itself (0 mismatches).
- `device_commit_files` resent a cached copy when the same staged path name was reused (empire-remastered lesson 18): Lua syncs
  then used unique names plus a sha check before the copy into place.
