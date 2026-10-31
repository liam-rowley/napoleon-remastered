# install_packs.ps1: put upscaled-art packs into the game's data folder, sha-checked, and take them out again (J36 flow, J50).
#
# purpose: copy .pack files into <game>\data\ with sha256 checked on the source, against its <pack>.json manifest (when there is one) and on the copy, refusing to overwrite any file and copying nothing until every source checks (a failed copy moves this call's copies to -Trash); uninstall moves them to a _to_delete folder (nothing is deleted)
# usage: called from a watcher ps1 job (the lock owner's): & <this> -Mode install -Game <dir> -Packs <src.pack>,... -Trash <dir> | -Mode uninstall -Game <dir> -Names <x.pack>,... -Trash <dir>; prints one JSON object, exit 0 ok, 1 failed, 2 refused
# when: before a load test of ui_art_2x5_*.pack or a scratch probe pack (J50); never by hand into the game folder
# not-a-verb: a PC-side script run by the watcher (the agent shell may not write into the game folder), not a registry operation
#
# Refuses while Napoleon.exe or Empire.exe runs, and refuses a pack name that is not <letters, digits, _ -.>.pack. The uninstall check
# that matters is the caller's: pc_deploy.py snapshot + diff against the snapshot taken before the install.
param(
    [ValidateSet('install', 'uninstall')][string]$Mode,
    [Parameter(Mandatory = $true)][string]$Game,
    [string[]]$Packs = @(),
    [string[]]$Names = @(),
    [string]$Trash = ''
)
$ErrorActionPreference = 'Stop'
$result = [ordered]@{ mode = $Mode; game = $Game; status = 'ok'; reason = ''; packs = @() }

function Done($status, $reason, $code) {
    $result.status = $status; $result.reason = $reason
    $result | ConvertTo-Json -Depth 5
    exit $code
}
function Sha($p) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() }

$running = Get-Process -Name Napoleon, Empire -ErrorAction SilentlyContinue
if ($running) { Done 'refused' ("a game is running: " + (($running | ForEach-Object { "$($_.Name) $($_.Id)" }) -join ', ')) 2 }
$data = Join-Path $Game 'data'
if (-not (Test-Path -LiteralPath (Join-Path $data 'data.pack'))) { Done 'refused' "$data has no data.pack: not a game data folder" 2 }

if ($Mode -eq 'install') {
    if (-not $Packs) { Done 'refused' 'install needs -Packs' 2 }
    if (-not $Trash) { Done 'refused' 'install needs -Trash (a failed copy is moved there, never left in data\)' 2 }
    # Every check before the first copy, so a bad source (J50 review) never leaves the packs before it in data\.
    $rows = @()
    foreach ($src in $Packs) {
        $name = Split-Path -Leaf $src
        if ($name -notmatch '^[A-Za-z0-9_.-]+\.pack$') { Done 'refused' "pack name '$name' is not [A-Za-z0-9_.-]+.pack" 2 }
        if (-not (Test-Path -LiteralPath $src)) { Done 'refused' "source $src missing" 2 }
        if (Test-Path -LiteralPath (Join-Path $data $name)) { Done 'refused' "$name is already in $data (never overwritten)" 2 }
        $row = [ordered]@{ name = $name; source = $src; bytes = (Get-Item -LiteralPath $src).Length }
        $row.sha256 = Sha $src
        $man = "$src.json"
        if (Test-Path -LiteralPath $man) {
            $want = (Get-Content -LiteralPath $man -Raw | ConvertFrom-Json).sha256
            $row.manifest = $want
            if ($want -ne $row.sha256) { $result.packs += $row; Done 'failed' "$name source sha256 $($row.sha256) is not the manifest's $want (nothing copied)" 1 }
        }
        $rows += $row
    }
    foreach ($row in $rows) {
        $dst = Join-Path $data $row.name
        Copy-Item -LiteralPath $row.source -Destination $dst
        $row.copy_sha256 = Sha $dst
        $result.packs += $row
        if ($row.copy_sha256 -ne $row.sha256) {
            New-Item -ItemType Directory -Force $Trash | Out-Null
            foreach ($done in $result.packs) {
                $to = Join-Path $Trash $done.name
                if (Test-Path -LiteralPath $to) { $to = "$to." + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') }
                Move-Item -LiteralPath (Join-Path $data $done.name) -Destination $to
                $done.moved_to = $to
            }
            Done 'failed' "$($row.name) copy sha256 differs from the source: this call's copies moved to $Trash" 1
        }
    }
    Done 'ok' ("installed " + $result.packs.Count + " pack(s), sha256 checked") 0
}

if (-not $Names) { Done 'refused' 'uninstall needs -Names' 2 }
if (-not $Trash) { Done 'refused' 'uninstall needs -Trash (packs are moved, never deleted)' 2 }
New-Item -ItemType Directory -Force $Trash | Out-Null
foreach ($name in $Names) {
    if ($name -notmatch '^[A-Za-z0-9_.-]+\.pack$') { Done 'refused' "pack name '$name' is not [A-Za-z0-9_.-]+.pack" 2 }
    $p = Join-Path $data $name
    if (Test-Path -LiteralPath $p) {
        $to = Join-Path $Trash $name
        if (Test-Path -LiteralPath $to) { $to = "$to." + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') }
        Move-Item -LiteralPath $p -Destination $to
        $result.packs += [ordered]@{ name = $name; moved_to = $to }
    } else {
        $result.packs += [ordered]@{ name = $name; moved_to = $null; note = 'not installed' }
    }
}
Done 'ok' ("moved " + $Names.Count + " name(s) to $Trash") 0
