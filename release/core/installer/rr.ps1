# purpose: the player-side installer of a release folder (no Python, Git or repo needed): install (owned set = union of every installed release, foreign files backed up on every run), uninstall (byte-exact against the pre-install snapshot; after a game update the files the update changed are listed apart), repair, check, clean (frees _to_delete after confirmation) and a redacted support bundle, all refusing while the game runs and install on a non-vanilla exe
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File rr.ps1 install|uninstall|repair|check|clean|support [-GamePath <game folder>] [-StateDir <folder>] [-AssumeClosed] [-IncludeDumps] [-Yes]   (the .cmd files in the release folder call it)
# when: it is the release folder's own engine (release/core/build_release.py copies it to installer\rr.ps1 and writes the Install, Uninstall, Repair, Check, Clean and Support .cmd entry points); behaviour parity with core/proxy/tools/pc_deploy.py is the contract (tests/test_release_installer.py compares them)
# not-a-verb: runs on the player's PC from the release folder, outside the repo and the wsc CLI
# Windows PowerShell 5.1, ASCII only. Everything the installer keeps (snapshot, backups, install.json, moved-aside files) lives OUTSIDE the game
# folder (D25) in %LOCALAPPDATA%\<state_dir_name>. A removal is a move to <state>\_to_delete after a verified copy; only the clean verb deletes, only inside
# <state>\_to_delete and only after the player confirms (J81: the player's tool on the player's PC; the agents' never-delete rule is for their PC folders).
param(
    [Parameter(Position = 0)][ValidateSet('install', 'uninstall', 'repair', 'check', 'clean', 'support', 'redact', 'version')][string]$Verb = 'check',
    [string]$GamePath = '', [string]$StateDir = '', [string]$AppDataDir = '',
    [switch]$AssumeClosed, [switch]$IncludeDumps, [switch]$OfferDumps, [switch]$NoPause, [switch]$Yes,
    [string]$OutDir = '', [string]$RedactUser = '', [string]$RedactMachine = '', [string]$RedactProfile = '',
    [string]$In = '', [string]$Out = ''
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Web.Extensions
Add-Type -AssemblyName System.IO.Compression.FileSystem
$script:Ser = New-Object System.Web.Script.Serialization.JavaScriptSerializer
$script:Ser.MaxJsonLength = [int]::MaxValue
$script:Ser.RecursionLimit = 64
$script:Utf8 = New-Object System.Text.UTF8Encoding($false)
$script:Big = 100MB
$script:RelRoot = Split-Path -Parent $PSScriptRoot
$script:Man = $null

function Say([string]$m) { Write-Host $m }
function Stamp { return [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') }
function Fail([string]$m, [int]$code = 2) { Write-Host ("rr: " + $m); exit $code }
function Read-Json([string]$p) { return $script:Ser.DeserializeObject([IO.File]::ReadAllText($p, $script:Utf8)) }
function To-Plain($o) {   # unwrap PSObjects (function output wraps) so the serializer sees only dictionaries, lists and scalars
    if ($null -eq $o) { return $null }
    $o = $o.PSObject.BaseObject
    if ($o -is [string] -or $o -is [ValueType]) { return $o }
    if ($o -is [System.Collections.IDictionary]) {
        $d = New-Object 'System.Collections.Generic.Dictionary[string,object]'
        foreach ($k in @($o.Keys)) {
            $v = To-Plain $o[$k]
            if ($null -ne $v) { $v = $v.PSObject.BaseObject }
            $d[[string]$k] = $v
        }
        return $d
    }
    if ($o -is [System.Collections.IEnumerable]) {
        $l = New-Object 'System.Collections.Generic.List[object]'
        foreach ($x in $o) {
            $v = To-Plain $x
            if ($null -ne $v) { $v = $v.PSObject.BaseObject }
            $l.Add($v)
        }
        return , $l
    }
    return [string]$o
}
function Write-Json([string]$p, $o) {
    $plain = To-Plain $o
    if ($null -ne $plain) { $plain = $plain.PSObject.BaseObject }
    [IO.File]::WriteAllText($p, ($script:Ser.Serialize($plain)), $script:Utf8)
}
function Has($d, [string]$k) { if ($d -is [System.Collections.IDictionary]) { return ([System.Collections.IDictionary]$d).Contains($k) }; return $false }

function Hash-File([string]$p, [string]$alg = 'SHA256') {
    $h = [System.Security.Cryptography.HashAlgorithm]::Create($alg)
    $s = [IO.File]::Open($p, 'Open', 'Read', 'ReadWrite')
    try { $b = $h.ComputeHash($s) } finally { $s.Dispose(); $h.Dispose() }
    return ([BitConverter]::ToString($b) -replace '-', '').ToLower()
}

# ---- one path form (J74): a TEMP or game path may be an 8.3 short name (C:\Users\RUNNER~1\...) while the files under it enumerate in the long form,
# so every relative path is computed from the long, full form of the game and state folders, resolved once at start.
Add-Type -ErrorAction Stop -Name RrPath -Namespace Rr -MemberDefinition '[DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] public static extern uint GetLongPathNameW(string s, System.Text.StringBuilder b, uint n);'
function Long-Path([string]$p) {
    $p = [IO.Path]::GetFullPath($p).TrimEnd('\')
    if ($p.Length -le 3) { return $p }
    if (-not (Test-Path -LiteralPath $p)) { return (Join-Path (Long-Path (Split-Path -Parent $p)) (Split-Path -Leaf $p)) }
    $sb = New-Object System.Text.StringBuilder 32768
    $n = [Rr.RrPath]::GetLongPathNameW($p, $sb, 32768)
    if ($n -eq 0 -or $n -gt 32768) { return $p }
    return $sb.ToString().TrimEnd('\')
}

# ---- snapshots (same format and rules as pc_deploy.snapshot / diff_snapshots) ---------------------------------------------------
$script:EpochTicks = 621355968000000000
function Walk-Snap($dir, $root, $out) {
    $infos = (New-Object IO.DirectoryInfo($dir)).GetFileSystemInfos() | Sort-Object Name
    $anyFile = $false
    foreach ($i in $infos) { $anyFile = $true; break }
    if (-not $anyFile -and $dir -ne $root) {
        $rel = $dir.Substring($root.Length).TrimStart('\').Replace('\', '/') + '/'
        $out[$rel] = @{ dir = $true }
        return
    }
    foreach ($i in $infos) {
        if ($i -is [IO.DirectoryInfo]) { Walk-Snap $i.FullName $root $out; continue }
        $rel = $i.FullName.Substring($root.Length).TrimStart('\').Replace('\', '/')
        $sha = $null
        if ($i.Length -le $script:Big) { $sha = Hash-File $i.FullName }
        $out[$rel] = @{ size = [long]$i.Length; mtime_ns = [long](($i.LastWriteTimeUtc.Ticks - $script:EpochTicks) * 100); sha256 = $sha }
    }
}
function Take-Snapshot([string]$game) {
    $root = Long-Path $game
    $out = @{}
    Walk-Snap $root $root $out
    return $out
}
function Diff-Snapshots($a, $b) {
    $res = New-Object System.Collections.ArrayList
    $keys = New-Object 'System.Collections.Generic.SortedSet[string]' ([StringComparer]::Ordinal)
    foreach ($k in $a.Keys) { [void]$keys.Add([string]$k) }
    foreach ($k in $b.Keys) { [void]$keys.Add([string]$k) }
    foreach ($k in $keys) {
        $x = $null; $y = $null
        if ($a.ContainsKey($k)) { $x = $a[$k] }
        if ($b.ContainsKey($k)) { $y = $b[$k] }
        if ($null -eq $x) { [void]$res.Add("added   $k") }
        elseif ($null -eq $y) { [void]$res.Add("removed $k") }
        elseif ((Has $x 'dir') -or (Has $y 'dir')) { continue }
        elseif ([long]$x['size'] -ne [long]$y['size'] -or ((($null -ne $x['sha256']) -or ($null -ne $y['sha256'])) -and ($x['sha256'] -ne $y['sha256']))) { [void]$res.Add("changed $k") }
        elseif (($null -eq $x['sha256']) -and ([long]$x['mtime_ns'] -ne [long]$y['mtime_ns'])) { [void]$res.Add("touched $k (large file: same size, other mtime)") }
    }
    return , $res
}

# ---- moving, never deleting -----------------------------------------------------------------------------------------------------
function Copy-Verify([string]$src, [string]$dest) {
    if (Test-Path -LiteralPath $src -PathType Container) {
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        foreach ($c in (Get-ChildItem -LiteralPath $src -Force)) { Copy-Verify $c.FullName (Join-Path $dest $c.Name) }
    } else {
        Copy-Item -LiteralPath $src -Destination $dest -Force
        if ((Hash-File $src) -ne (Hash-File $dest)) { Fail "copy of $src does not verify; nothing removed" 1 }
    }
}
function Move-Out([string]$src, [string]$dest) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
    $isDir = Test-Path -LiteralPath $src -PathType Container
    try {
        if ($isDir) { [IO.Directory]::Move($src, $dest) } else { [IO.File]::Move($src, $dest) }
        return
    } catch [System.IO.IOException] { }
    Copy-Verify $src $dest
    Remove-Item -LiteralPath $src -Recurse -Force
}

# ---- the release and the game -------------------------------------------------------------------------------------------------------
function Load-Manifest {
    $p = Join-Path $script:RelRoot 'manifest.json'
    if (-not (Test-Path -LiteralPath $p)) { Fail "no manifest.json in $($script:RelRoot): run this from the release folder" }
    $script:Man = Read-Json $p
    $script:Ident = Read-Json (Join-Path $PSScriptRoot 'exe_identity.json')
    $want = $script:Man['exe_identity']['sha256']
    if ((Hash-File (Join-Path $PSScriptRoot 'exe_identity.json')) -ne $want) { Fail 'installer\exe_identity.json does not match the manifest (damaged or edited release folder)' }
}
function Find-Game {
    if ($GamePath) { return $GamePath.TrimEnd('\') }
    $exe = $script:Man['game']['exe_name']
    $d = $script:RelRoot
    while ($d) {   # first upward from the release folder: unzipped inside the game folder it still finds the game (J81: the one discovery story; README.txt says
                   # unzip anywhere, and that verify-and-reinstall in Steam deletes a copy inside the game folder), then Steam's registry key and libraryfolders.vdf
        if (Test-Path -LiteralPath (Join-Path $d $exe)) { return $d }
        $parent = Split-Path -Parent $d
        if ($parent -eq $d) { break }
        $d = $parent
    }
    $libs = New-Object System.Collections.ArrayList
    foreach ($k in 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam', 'HKLM:\SOFTWARE\Valve\Steam', 'HKCU:\Software\Valve\Steam') {
        try {
            $v = Get-ItemProperty -LiteralPath $k -ErrorAction Stop
            foreach ($n in 'InstallPath', 'SteamPath') { if ($v.$n) { [void]$libs.Add(([string]$v.$n).Replace('/', '\')) } }
        } catch { }
    }
    foreach ($s in @($libs)) {
        $vdf = Join-Path $s 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            foreach ($m in [regex]::Matches([IO.File]::ReadAllText($vdf), '"path"\s+"([^"]+)"')) { [void]$libs.Add($m.Groups[1].Value.Replace('\\', '\')) }
        }
    }
    foreach ($l in $libs) {
        $g = Join-Path $l ('steamapps\common\' + $script:Man['game']['steam_folder'])
        if (Test-Path -LiteralPath (Join-Path $g $exe)) { return $g }
    }
    Fail ("cannot find " + $script:Man['game']['name'] + ": run again with -GamePath ""<folder that holds $exe>""")
}
function State-Dir {
    if ($StateDir) { return $StateDir.TrimEnd('\') }
    $la = $env:LOCALAPPDATA
    if (-not $la) { Fail 'no LOCALAPPDATA: pass -StateDir' }
    return (Join-Path $la $script:Man['state_dir_name'])
}
function Exe-Verdict([string]$game) {
    $name = $script:Ident['exe_name']
    $exe = Join-Path $game $name
    if (-not (Test-Path -LiteralPath $exe)) { return @{ ok = $null; sha1 = $null; line = "exe: CANNOT CHECK: $exe not found" } }
    $h = Hash-File $exe 'SHA1'
    if ($h -eq ([string]$script:Ident['sha1']).ToLower()) { return @{ ok = $true; sha1 = $h; line = "exe: ok $name sha1 $h is the vanilla build this release knows" } }
    return @{ ok = $false; sha1 = $h; line = "exe: MISMATCH $name sha1 $h is not the vanilla build this release knows ($($script:Ident['sha1'])): the game was updated or the exe was modified" }
}
function Require-Closed {
    if ($AssumeClosed) { return }
    $names = @($script:Man['game']['exe_name']) + @($script:Man['game']['other_exes'])
    foreach ($n in $names) {
        $base = [IO.Path]::GetFileNameWithoutExtension([string]$n)
        $p = Get-Process -Name $base -ErrorAction SilentlyContinue
        if ($p) { Fail "refusing: $n is running (pid $($p[0].Id)). Close the game first." }
    }
}
function Owned-Entry([string]$o, [string]$rel) { return ($rel -eq $o.TrimEnd('/')) -or ($o.EndsWith('/') -and $rel.StartsWith($o)) }
function Verify-Payload {
    $bad = @()
    foreach ($e in $script:Man['files']) {
        $p = Join-Path $script:RelRoot ([string]$e['payload']).Replace('/', '\')
        if (-not (Test-Path -LiteralPath $p)) { $bad += "$($e['payload']): missing"; continue }
        if ((Get-Item -LiteralPath $p).Length -ne [long]$e['size'] -or (Hash-File $p) -ne $e['sha256']) { $bad += "$($e['payload']): sha256 or size differs from the manifest (damaged download or edited file)" }
        $parts = ([string]$e['path']).Split('/')
        if ($parts -contains '..' -or ([string]$e['path']).StartsWith('/') -or ([string]$e['path']).Contains(':')) { $bad += "$($e['path']): not a relative path inside the game folder" }
        $in = $false
        foreach ($o in $script:Man['owned']) { if (Owned-Entry $o ([string]$e['path'])) { $in = $true } }
        if (-not $in) { $bad += "$($e['path']): outside the paths the release owns" }
    }
    return , $bad
}
function Clear-UiCache([string]$state, [string]$stamp) {
    if (-not $script:Man['clear_ui_cache']) { return }
    $ad = $AppDataDir
    if (-not $ad) { $ad = Join-Path $env:APPDATA ($script:Man['game']['appdata_subpath']) }
    $uc = Join-Path $ad 'ui_cache'
    if (Test-Path -LiteralPath $uc) {
        foreach ($f in (Get-ChildItem -LiteralPath $uc -File -Force)) {
            Move-Out $f.FullName (Join-Path $state ("_to_delete\" + $stamp + "\ui_cache\" + $f.Name))
            Say "rr: moved the UI cache file $($f.Name) aside (the game rebuilds it)"
        }
    }
}
function Record-Exe($rec, [string]$game, [string]$action, [string]$stamp) {
    $v = Exe-Verdict $game
    Say ("rr $action`: " + $v.line)
    if ($null -ne $rec) {
        $verdict = 'unchecked'
        if ($v.ok -eq $true) { $verdict = 'vanilla' } elseif ($v.ok -eq $false) { $verdict = 'MISMATCH' }
        [void]$rec['history'].Add(@{ utc = $stamp; action = "$action exe check"; exe_sha1 = $v.sha1; exe_verdict = $verdict })
    }
    if ($v.ok -eq $false -and $action -eq 'uninstall') { Say 'rr uninstall: the exe is not the build this release knows: a game update changed it (the installer never writes the exe)' }
    elseif ($v.ok -eq $false -and $action -ne 'check') { Say "rr $action`: !!! THE EXE ON DISK IS NOT VANILLA AFTER $($action.ToUpper()) !!! (the installer never writes the exe: tell the support contact)" }
    return $v.ok
}

# ---- the owned set across releases (J81) ------------------------------------------------------------------------------------------
function Union-Owned($a, $b) {   # sorted (ordinal) union of two owned lists: what every release installed so far may have put in the game folder
    $s = New-Object 'System.Collections.Generic.SortedSet[string]' ([StringComparer]::Ordinal)
    foreach ($x in @($a) + @($b)) { if ($null -ne $x -and [string]$x) { [void]$s.Add([string]$x) } }
    return , ([string[]]@($s))
}
function Install-Touched($rec) {   # this installer has copied files into the game folder already (a completed install, or a run past its backups)
    if ($rec['installed_utc']) { return $true }
    foreach ($h in @($rec['history'])) { if ($h -is [System.Collections.IDictionary] -and [string]$h['action'] -eq 'install started') { return $true } }
    return $false
}
function Ours-File([string]$game, [string]$rel, $rec) {   # a file this installer put there: listed (installed record or this release) with the sha256 it still has
    $h = $null
    foreach ($f in @($rec['files']) + @($script:Man['files'])) {
        if ($null -eq $f -or [string]$f['path'] -ne $rel) { continue }
        if ($f['config']) { return $true }   # a settings file the installer wrote, edited by the player since: still ours
        if ($null -eq $h) { $h = Hash-File (Join-Path $game $rel.Replace('/', '\')) }
        if ($h -eq [string]$f['sha256']) { return $true }
    }
    return $false
}
function Diff-Path([string]$d) {   # the path of a Diff-Snapshots line ('changed <path>', 'touched <path> (large file: ...)')
    $r = $d.Substring(8)
    $i = $r.IndexOf(' (large file:')
    if ($i -ge 0) { $r = $r.Substring(0, $i) }
    return $r
}
function Ours-Path([string]$rel, $rec) {   # inside the recorded owned set (the union) or at a backed-up path: a difference there is this tool's, never the game update's
    foreach ($o in @($rec['owned'])) { if (Owned-Entry ([string]$o) $rel) { return $true } }
    foreach ($b in @($rec['backups'])) { $bp = [string]$b['path']; if ($rel -eq $bp -or $rel.TrimEnd('/') -eq $bp -or $rel.StartsWith($bp + '/')) { return $true } }
    return $false
}
function Is-Ours([string]$game, [string]$rel, $rec) {   # ours: listed with its sha, a runtime_globs file, or (in our own mod folder) a file nobody listed (a leftover .tmp); never the whole folder foreign for that
    $p = Join-Path $game $rel.Replace('/', '\')
    $globs = @($script:Man['runtime_globs'])
    $mod = ([string]$rec['mod_dir']).Trim('/')
    if (-not (Test-Path -LiteralPath $p -PathType Container)) { return ((Glob-Match $rel $globs) -or (Ours-File $game $rel $rec)) }
    foreach ($f in (Get-ChildItem -LiteralPath $p -Recurse -File -Force)) {
        $r = $f.FullName.Substring($game.TrimEnd('\').Length).TrimStart('\').Replace('\', '/')
        if ((Glob-Match $r $globs) -or (Ours-File $game $r $rec)) { continue }
        if ($mod -and ($r -eq $mod -or $r.StartsWith($mod + '/')) -and -not (Listed-File $r $rec)) { continue }
        return $false
    }
    return $true
}
function Listed-File([string]$rel, $rec) {
    foreach ($f in @($rec['files']) + @($script:Man['files'])) { if ($null -ne $f -and [string]$f['path'] -eq $rel) { return $true } }
    return $false
}

# ---- install ---------------------------------------------------------------------------------------------------------------
function Do-Install([string]$game, [string]$state) {
    $bad = Verify-Payload
    if ($bad.Count) { Fail ("the release folder does not verify, nothing installed:`n  " + ($bad -join "`n  ")) }
    $exeName = $script:Man['game']['exe_name']
    if (-not (Test-Path -LiteralPath (Join-Path $game $exeName))) { Fail "$(Join-Path $game $exeName) not found: wrong game folder" }
    $v = Exe-Verdict $game
    if ($v.ok -ne $true) { Fail ($v.line + "`nrr install: nothing was installed. This release only supports the unmodified Steam build of the game; verify the game files in Steam, then try again.") }
    Say ("rr install: " + $v.line)
    Require-Closed
    New-Item -ItemType Directory -Force -Path $state | Out-Null
    $stamp = Stamp
    $recPath = Join-Path $state 'install.json'
    $rec = $null
    if (Test-Path -LiteralPath $recPath) { $rec = Read-Json $recPath; $rec['history'] = New-Object System.Collections.ArrayList(, @($rec['history'])); $rec['backups'] = New-Object System.Collections.ArrayList(, @($rec['backups'])) }
    if ($null -eq $rec) {
        $pre = Take-Snapshot $game
        New-Item -ItemType Directory -Force -Path (Join-Path $state 'snapshots') | Out-Null
        $prePath = Join-Path $state ("snapshots\pre_install_" + $stamp + ".json")
        Write-Json $prePath $pre
        $rec = @{ pre_snapshot = ("snapshots\pre_install_" + $stamp + ".json"); backups = (New-Object System.Collections.ArrayList); history = (New-Object System.Collections.ArrayList)
                  release_version = $null; build_id = $null; installed_utc = $null; files = @(); game = $game
                  owned = @($script:Man['owned']); mod_dir = $script:Man['game']['mod_dir']; exe_name = $exeName; config_file = $script:Man['game']['config_file']; other_exes = @($script:Man['game']['other_exes']); game_config_files = @() }
        Write-Json $recPath $rec
    }
    # J81 G5b: back up on every install, not only on the first: a re-run after a failed install (record on disk, backups half done) and an upgrade
    # check every path of the union owned set. Anything there that is not ours is foreign; a path already backed up is not backed up again.
    $touched = Install-Touched $rec
    $union = Union-Owned $rec['owned'] $script:Man['owned']
    $done = @{}
    foreach ($b in $rec['backups']) { $done[[string]$b['path']] = $true }
    foreach ($o in $union) {
        $rel = ([string]$o).TrimEnd('/')
        $p = Join-Path $game $rel.Replace('/', '\')
        if (-not (Test-Path -LiteralPath $p)) { continue }
        if ($done.ContainsKey($rel)) {
            $bk = $null
            foreach ($x in $rec['backups']) { if ([string]$x['path'] -eq $rel) { $bk = Join-Path $state ([string]$x['backup']) } }
            if ($bk -and (Test-Path -LiteralPath $bk)) { continue }
            # recorded but never moved (the run stopped between the record and the move): the original is still here; finish the move now
            # but never "finish" it with our own file: after a completed install whose backup the player deleted, that would make ours the original
            if ($bk -and $touched -and (Is-Ours $game $rel $rec)) { Say "rr install: WARNING: the backup of $o recorded at $bk is missing and the $o here is ours; it is not backed up again, so the uninstall cannot restore the original"; continue }
            if ($bk) { Move-Out $p $bk; Say "rr install: backed up the existing $o to $bk (finishing an earlier run)"; continue }
        }
        if ($touched -and (Is-Ours $game $rel $rec)) { continue }
        $b = Join-Path $state ("backup\" + $stamp + "\" + $rel.Replace('/', '\'))
        [void]$rec['backups'].Add(@{ path = $rel; backup = ("backup\" + $stamp + "\" + $rel.Replace('/', '\')) })
        $done[$rel] = $true
        Write-Json $recPath $rec
        Move-Out $p $b
        Say "rr install: backed up the existing $o to $b"
    }
    $rec['exe_identity'] = @{ sha1 = $script:Ident['sha1']; exe_name = $exeName }
    [void]$rec['history'].Add(@{ utc = $stamp; action = 'install started'; release_version = $script:Man['version'] })
    Write-Json $recPath $rec
    $new = @{}
    foreach ($e in $script:Man['files']) { $new[[string]$e['path']] = $true }
    foreach ($f in @($rec['files'])) {   # J81: a file the installed release shipped and this one does not (renamed or dropped): out of the way, still owned
        if ($null -eq $f) { continue }
        $fp = Join-Path $game ([string]$f['path']).Replace('/', '\')
        if ($new.ContainsKey([string]$f['path']) -or -not (Test-Path -LiteralPath $fp -PathType Leaf)) { continue }
        if ((Hash-File $fp) -ne $f['sha256']) { continue }   # edited since (a settings file): left in place, the uninstall takes it with the owned set
        Move-Out $fp (Join-Path $state ("_to_delete\" + $stamp + "\" + ([string]$f['path']).Replace('/', '\')))
        Say "rr install: moved $($f['path']) of release $($rec['release_version']) aside (this release does not ship it)"
    }
    foreach ($e in $script:Man['files']) {
        $dest = Join-Path $game ([string]$e['path']).Replace('/', '\')
        if (Test-Path -LiteralPath $dest) { Move-Out $dest (Join-Path $state ("_to_delete\" + $stamp + "\" + ([string]$e['path']).Replace('/', '\'))) }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        $tmp = $dest + '.' + $stamp + '.tmp'
        Copy-Item -LiteralPath (Join-Path $script:RelRoot ([string]$e['payload']).Replace('/', '\')) -Destination $tmp -Force
        if ((Hash-File $tmp) -ne $e['sha256']) { Fail "$tmp does not verify after the copy" 1 }
        Move-Item -LiteralPath $tmp -Destination $dest -Force
        if ((Hash-File $dest) -ne $e['sha256']) { Fail "$dest does not verify after the copy" 1 }
        Say "rr install: $($e['path']) sha256 $(([string]$e['sha256']).Substring(0, 12)) ok"
    }
    Clear-UiCache $state $stamp
    $files = @()
    foreach ($e in $script:Man['files']) { $files += @{ path = $e['path']; sha256 = $e['sha256']; size = $e['size']; component = $e['component']; config = [bool]$e['config'] } }
    $rec['release_version'] = $script:Man['version']; $rec['build_id'] = $script:Man['dll_build_id']; $rec['installed_utc'] = $stamp
    $rec['files'] = $files; $rec['owned'] = $union; $rec['game'] = $game   # J81 G5a: the union, so a file an older release owned is still taken at uninstall
    $rec['components'] = @($script:Man['components'] | ForEach-Object { $_['id'] })
    [void]$rec['history'].Add(@{ utc = $stamp; action = 'install'; release_version = $script:Man['version'] })
    $after = Record-Exe $rec $game 'install' $stamp
    Write-Json $recPath $rec
    Say "rr install: release $($script:Man['version']) installed (DLL build $($script:Man['dll_build_id']))"
    if ($after -ne $true) { Fail 'the exe is not vanilla after the install (see above)' 1 }
    return 0
}

# ---- uninstall -------------------------------------------------------------------------------------------------------------
function Do-Uninstall([string]$game, [string]$state) {
    $recPath = Join-Path $state 'install.json'
    if (-not (Test-Path -LiteralPath $recPath)) { Fail "no install.json in $state`: nothing installed by this tool" 2 }
    $rec = Read-Json $recPath
    $rec['history'] = New-Object System.Collections.ArrayList(, @($rec['history']))
    Require-Closed
    $stamp = Stamp
    foreach ($o in $rec['owned']) {   # the whole owned set, including what the DLL wrote at runtime (logs, dumps, DXVK files, the notice)
        $rel = ([string]$o).TrimEnd('/')
        $p = Join-Path $game $rel.Replace('/', '\')
        if (Test-Path -LiteralPath $p) {
            Move-Out $p (Join-Path $state ("_to_delete\uninstall_" + $stamp + "\" + $rel.Replace('/', '\')))
            Say "rr uninstall: moved $o to _to_delete"
        }
    }
    foreach ($b in $rec['backups']) {
        $bp = Join-Path $state ([string]$b['backup'])
        if (-not (Test-Path -LiteralPath $bp)) { continue }   # recorded just before a backup move that never happened (a failed install)
        Move-Out $bp (Join-Path $game ([string]$b['path']).Replace('/', '\'))
        Say "rr uninstall: restored the original $($b['path'])"
    }
    Clear-UiCache $state ("uninstall_" + $stamp)
    $pre = Read-Json (Join-Path $state ([string]$rec['pre_snapshot']))
    $post = Take-Snapshot $game
    $all = Diff-Snapshots $pre $post
    New-Item -ItemType Directory -Force -Path (Join-Path $state 'snapshots') | Out-Null
    Write-Json (Join-Path $state ("snapshots\post_uninstall_" + $stamp + ".json")) $post
    $exeOk = Record-Exe $rec $game 'uninstall' $stamp
    # J81 G7: after a game update (exe verdict MISMATCH) every file the update changed differs from the pre-install snapshot. A diff outside the owned
    # set and outside the backups is then the update's, listed apart, and does not fail the uninstall; a diff at an owned or backed-up path is ours and always does.
    $diffs = New-Object System.Collections.ArrayList
    $steam = New-Object System.Collections.ArrayList
    foreach ($d in $all) {
        if ($exeOk -eq $false -and -not (Ours-Path (Diff-Path $d) $rec)) { [void]$steam.Add($d) } else { [void]$diffs.Add($d) }
    }
    $h = @{ utc = $stamp; action = 'uninstall'; identical = ($all.Count -eq 0); diffs = @($diffs | Select-Object -First 50) }
    if ($steam.Count) { $h['steam_update_diffs'] = $steam.Count; $h['steam_update'] = @($steam | Select-Object -First 50) }
    [void]$rec['history'].Add($h)
    New-Item -ItemType Directory -Force -Path (Join-Path $state 'history') | Out-Null
    Write-Json (Join-Path $state ("history\install_" + $stamp + ".json")) $rec
    Move-Out $recPath (Join-Path $state ("_to_delete\uninstall_" + $stamp + "\install.json"))
    if ($steam.Count) {
        Say ("rr uninstall: changed by the game update, not by this tool ($($steam.Count)):`n  " + (($steam | Select-Object -First 50) -join "`n  "))
    }
    if ($diffs.Count) {
        Say ("rr uninstall: game folder DIFFERS from the pre-install snapshot:`n  " + (($diffs | Select-Object -First 50) -join "`n  "))
        return 1
    }
    if ($exeOk -eq $false) {
        Say "rr uninstall: the mod's files are removed and your own files restored; the rest of the game folder is as the game update left it ($($post.Count) files)"
        return 0
    }
    Say "rr uninstall: game folder identical to the pre-install snapshot ($($post.Count) files)"
    return 0
}

# ---- check and repair -----------------------------------------------------------------------------------------------------------
function Glob-Match([string]$rel, $globs) {
    foreach ($g in $globs) { if ($rel -like [string]$g) { return $true } }
    return $false
}
function Do-Check([string]$game, [string]$state) {
    $lines = New-Object System.Collections.ArrayList
    $bad = 0
    $v = Exe-Verdict $game
    [void]$lines.Add($v.line)
    if ($v.ok -ne $true) { $bad++ }
    $recPath = Join-Path $state 'install.json'
    $owned = @($script:Man['owned'])
    if (-not (Test-Path -LiteralPath $recPath)) {
        [void]$lines.Add('install: not installed by this tool (no install record)')
        foreach ($o in $owned) {
            $rel = ([string]$o).TrimEnd('/')
            if (Test-Path -LiteralPath (Join-Path $game $rel.Replace('/', '\'))) { [void]$lines.Add("note: $rel is present but not from this installer (an install backs it up and the uninstall puts it back)") }
        }
        return @{ Code = [int]($bad -gt 0); Lines = $lines }
    }
    $rec = Read-Json $recPath
    [void]$lines.Add("install: release $($rec['release_version']) (DLL build $($rec['build_id'])) installed $($rec['installed_utc'])")
    if ($rec['release_version'] -ne $script:Man['version']) { [void]$lines.Add("note: this release folder is $($script:Man['version']); run its Install.cmd to update") }
    $known = @{}
    foreach ($f in $rec['files']) {
        $known[[string]$f['path']] = $true
        $p = Join-Path $game ([string]$f['path']).Replace('/', '\')
        if (-not (Test-Path -LiteralPath $p)) { [void]$lines.Add("MISSING $($f['path'])"); $bad++; continue }
        if ((Hash-File $p) -ne $f['sha256']) {
            if ($f['config']) { [void]$lines.Add("edited  $($f['path']) (settings file: your changes are kept)") }
            else { [void]$lines.Add("CHANGED $($f['path'])"); $bad++ }
            continue
        }
        [void]$lines.Add("ok      $($f['path'])")
    }
    $globs = @($script:Man['runtime_globs'])
    foreach ($o in $owned) {
        if (-not ([string]$o).EndsWith('/')) { continue }
        $dir = Join-Path $game ([string]$o).TrimEnd('/').Replace('/', '\')
        if (-not (Test-Path -LiteralPath $dir)) { continue }
        foreach ($f in (Get-ChildItem -LiteralPath $dir -Recurse -File -Force)) {
            $rel = $f.FullName.Substring($game.TrimEnd('\').Length).TrimStart('\').Replace('\', '/')
            if ($known.ContainsKey($rel) -or (Glob-Match $rel $globs)) { continue }
            [void]$lines.Add("FOREIGN $rel (a file at an owned path that no component owns)"); $bad++
        }
    }
    $md = Join-Path $game ([string]$script:Man['game']['mod_dir'])
    $dumps = @()
    if (Test-Path -LiteralPath (Join-Path $md 'dumps')) { $dumps = @(Get-ChildItem -LiteralPath (Join-Path $md 'dumps') -Filter *.dmp -File) }
    [void]$lines.Add("dumps: $($dumps.Count)")
    if (Test-Path -LiteralPath (Join-Path $md 'EXE_MISMATCH.txt')) {
        [void]$lines.Add('notice: EXE_MISMATCH.txt present: the game was updated, the remaster is inactive until a build for this exe exists. Uninstall.cmd returns the game to vanilla.')
    }
    return @{ Code = [int]($bad -gt 0); Lines = $lines }
}
function Do-Repair([string]$game, [string]$state) {
    $recPath = Join-Path $state 'install.json'
    if (-not (Test-Path -LiteralPath $recPath)) { Fail 'nothing is installed by this tool: run Install.cmd' 2 }
    $rec = Read-Json $recPath
    $rec['history'] = New-Object System.Collections.ArrayList(, @($rec['history']))
    if ($rec['release_version'] -ne $script:Man['version']) { Fail "the install is release $($rec['release_version']) but this folder is $($script:Man['version']): run this folder's Install.cmd to update" 2 }
    $v = Exe-Verdict $game
    Say ("rr repair: " + $v.line)
    if ($v.ok -eq $false) {
        Say 'rr repair: game updated, remaster is inactive until a build for this exe exists. Nothing was changed. Run Uninstall.cmd to return the game to vanilla, or wait for a release that supports this game build.'
        return 3
    }
    if ($v.ok -ne $true) { Fail 'cannot check the exe; nothing changed' 2 }
    Require-Closed
    $bad = Verify-Payload
    if ($bad.Count) { Fail ("the release folder does not verify, nothing repaired:`n  " + ($bad -join "`n  ")) }
    $stamp = Stamp
    $fixed = 0
    foreach ($e in $script:Man['files']) {
        $dest = Join-Path $game ([string]$e['path']).Replace('/', '\')
        $exists = Test-Path -LiteralPath $dest
        if ($exists -and (Hash-File $dest) -eq $e['sha256']) { continue }
        if ($exists -and $e['config']) { Say "rr repair: kept your edited settings file $($e['path'])"; continue }
        if ($exists) { Move-Out $dest (Join-Path $state ("_to_delete\repair_" + $stamp + "\" + ([string]$e['path']).Replace('/', '\'))) }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        $tmp = $dest + '.' + $stamp + '.tmp'
        Copy-Item -LiteralPath (Join-Path $script:RelRoot ([string]$e['payload']).Replace('/', '\')) -Destination $tmp -Force
        if ((Hash-File $tmp) -ne $e['sha256']) { Fail "$tmp does not verify after the copy" 1 }
        Move-Item -LiteralPath $tmp -Destination $dest -Force
        Say "rr repair: restored $($e['path'])"
        $fixed++
    }
    Clear-UiCache $state ("repair_" + $stamp)
    [void]$rec['history'].Add(@{ utc = $stamp; action = 'repair'; restored = $fixed })
    [void](Record-Exe $rec $game 'repair' $stamp)
    Write-Json $recPath $rec
    Say "rr repair: $fixed file(s) restored"
    $c = Do-Check $game $state
    foreach ($l in $c.Lines) { Say $l }
    return $c.Code
}

# ---- _to_delete: its size and the clean verb (J81 G6) --------------------------------------------------------------------------------
function Human-Size([double]$n) {
    foreach ($u in 'bytes', 'KB', 'MB', 'GB') {
        if ($n -lt 1024 -or $u -eq 'GB') { if ($u -eq 'bytes') { return ('{0:0} bytes' -f $n) }; return ([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0:0.0} {1}', $n, $u)) }
        $n = $n / 1024
    }
}
function Folder-Size([string]$p) {
    if (Test-Path -LiteralPath $p -PathType Leaf) { return [long](Get-Item -LiteralPath $p -Force).Length }
    $s = [long]0
    foreach ($f in (Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue)) { $s += [long]$f.Length }
    return $s
}
function ToDelete-Items([string]$state) {   # the stamp folders (and any loose file) directly under <state>\_to_delete, oldest name first
    $td = Join-Path $state '_to_delete'
    if (-not (Test-Path -LiteralPath $td -PathType Container)) { return , @() }
    return , @(Get-ChildItem -LiteralPath $td -Force | Sort-Object Name)
}
function Say-ToDelete([string]$state) {   # the closing line of install, repair and uninstall
    $items = ToDelete-Items $state
    if (-not $items.Count) { return }
    $sum = [long]0
    foreach ($i in $items) { $sum += Folder-Size $i.FullName }
    Say "rr: _to_delete holds $(Human-Size $sum) in $($items.Count) folders: run Clean.cmd to free it"
}
function Ask([string]$q) {   # a prompt that also reads a redirected stdin (the tests answer it); end of input is 'no'
    if ([Console]::IsInputRedirected) { Write-Host -NoNewline ($q + ' '); $a = [Console]::In.ReadLine(); Write-Host $a; return [string]$a }
    return [string](Read-Host $q)
}
function Remove-Links([string]$dir) {   # PowerShell 5.1 Remove-Item -Recurse follows junctions and symlinks: take every link out as a link first, never descending
    foreach ($c in @(Get-ChildItem -LiteralPath $dir -Force)) {
        if ($c.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            if ($c.PSIsContainer) { [IO.Directory]::Delete($c.FullName) } else { [IO.File]::Delete($c.FullName) }
        } elseif ($c.PSIsContainer) { Remove-Links $c.FullName }
    }
}
function Do-Clean([string]$state) {
    Require-Closed
    $td = Long-Path (Join-Path $state '_to_delete')
    $items = ToDelete-Items $state
    if (-not $items.Count) { Say "rr clean: nothing to free ($td is empty or absent)"; return 0 }
    $sum = [long]0
    foreach ($i in $items) { $n = Folder-Size $i.FullName; $sum += $n; Say ("rr clean: {0,10}  {1}" -f (Human-Size $n), $i.Name) }
    Say "rr clean: $(Human-Size $sum) in $($items.Count) folders under $td (files earlier installs, repairs and uninstalls moved aside; your backups, snapshots, history and install record are elsewhere and are kept)"
    if (-not $Yes) {
        if ($NoPause) { Say 'rr clean: nothing deleted (-NoPause without -Yes: run Clean.cmd to be asked)'; return 0 }
        $a = Ask 'Delete these? [y/N]'
        if ($a -notmatch '^\s*[yY]') { Say 'rr clean: nothing deleted'; return 0 }
    }
    foreach ($i in $items) {
        $full = Long-Path $i.FullName
        if (-not $full.StartsWith($td + '\', [StringComparison]::OrdinalIgnoreCase)) { Fail "refusing to delete $full`: not inside $td" 2 }
        if ((Get-Item -LiteralPath $full -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { [IO.Directory]::Delete($full) }
        else { Remove-Links $full; Remove-Item -LiteralPath $full -Recurse -Force }
        Say "rr clean: deleted $($i.Name)"
    }
    Say "rr clean: freed $(Human-Size $sum)"
    return 0
}

# ---- support bundle and redaction ------------------------------------------------------------------------------------------------
function Redact-Text([string]$t, [string]$user, [string]$machine, [string]$prof) {
    foreach ($p in @($prof, $env:USERPROFILE)) {
        if ($p) {
            $t = [regex]::Replace($t, [regex]::Escape($p), '%USERPROFILE%', 'IgnoreCase')
            $t = [regex]::Replace($t, [regex]::Escape($p.Replace('\', '/')), '%USERPROFILE%', 'IgnoreCase')
            $t = [regex]::Replace($t, [regex]::Escape($p.Replace('\', '\\')), '%USERPROFILE%', 'IgnoreCase')   # inside a JSON string (install.json)
        }
    }
    if ($user) { $t = [regex]::Replace($t, '(?<![A-Za-z0-9_])' + [regex]::Escape($user) + '(?![A-Za-z0-9_])', '<user>', 'IgnoreCase') }
    if ($machine) { $t = [regex]::Replace($t, '(?<![A-Za-z0-9_])' + [regex]::Escape($machine) + '(?![A-Za-z0-9_])', '<machine>', 'IgnoreCase') }
    $t = [regex]::Replace($t, '7656119\d{10}', '<steamid>')
    $t = [regex]::Replace($t, '(?i)(userdata[\\/])\d{3,}', '$1<steamid>')
    $t = [regex]::Replace($t, 'S-1-5-21(-\d+){3,4}', '<sid>')
    return $t
}
function Redact-File([string]$src, [string]$dest, [string]$u, [string]$m, [string]$p) {
    $t = [IO.File]::ReadAllText($src, $script:Utf8)
    [IO.File]::WriteAllText($dest, (Redact-Text $t $u $m $p), $script:Utf8)
}
function Do-Support([string]$game, [string]$state) {
    $u = $RedactUser; if (-not $u) { $u = [Environment]::UserName }
    $m = $RedactMachine; if (-not $m) { $m = [Environment]::MachineName }
    $p = $RedactProfile
    $stamp = Stamp
    $od = $OutDir; if (-not $od) { $od = Join-Path $state 'support' }
    New-Item -ItemType Directory -Force -Path $od | Out-Null
    $work = Join-Path $state ("support\work_" + $stamp)
    New-Item -ItemType Directory -Force -Path $work | Out-Null
    $md = Join-Path $game ([string]$script:Man['game']['mod_dir'])
    $items = @(
        @{ src = (Join-Path $md 'logs\proxy.log'); name = 'proxy.log' },
        @{ src = (Join-Path $md 'logs\proxy.prev.log'); name = 'proxy.prev.log' },
        @{ src = (Join-Path $game $script:Man['game']['config_file']); name = $script:Man['game']['config_file'] },
        @{ src = (Join-Path $md 'EXE_MISMATCH.txt'); name = 'EXE_MISMATCH.txt' },
        @{ src = (Join-Path $state 'install.json'); name = 'install.json' })
    $listed = New-Object System.Collections.ArrayList
    foreach ($i in $items) {
        if (Test-Path -LiteralPath $i.src) { Redact-File $i.src (Join-Path $work $i.name) $u $m $p; [void]$listed.Add($i.name) }
    }
    $c = Do-Check $game $state
    $chk = "Check output (exit $($c.Code)):`r`n" + ($c.Lines -join "`r`n") + "`r`n"
    [IO.File]::WriteAllText((Join-Path $work 'check.txt'), (Redact-Text $chk $u $m $p), $script:Utf8)
    $gpu = ''
    try { $gpu = (@(Get-CimInstance Win32_VideoController -ErrorAction Stop | ForEach-Object { $_.Name + ' (driver ' + $_.DriverVersion + ')' }) -join "`r`n  ") } catch { $gpu = 'unavailable' }
    $exeVer = ''
    $exeP = Join-Path $game $script:Man['game']['exe_name']
    if (Test-Path -LiteralPath $exeP) { $exeVer = (Get-Item -LiteralPath $exeP).VersionInfo.FileVersion }
    $ver = "release: $($script:Man['product']) $($script:Man['version'])`r`nDLL build id: $($script:Man['dll_build_id'])`r`ncore tag: $($script:Man['core_tag'])`r`ngame exe: $($script:Man['game']['exe_name']) file version $exeVer`r`nWindows: $([Environment]::OSVersion.VersionString)`r`nGPU:`r`n  $gpu`r`n"
    [IO.File]::WriteAllText((Join-Path $work 'versions.txt'), (Redact-Text $ver $u $m $p), $script:Utf8)
    $dumps = @()
    if (Test-Path -LiteralPath (Join-Path $md 'dumps')) { $dumps = @(Get-ChildItem -LiteralPath (Join-Path $md 'dumps') -Filter *.dmp -File) }
    $wer = Join-Path $env:LOCALAPPDATA ('CrashDumps\' + $script:Man['game']['mod_dir'])
    if (Test-Path -LiteralPath $wer) { $dumps += @(Get-ChildItem -LiteralPath $wer -File) }
    $dl = "Crash dumps found: $($dumps.Count). A dump holds the game's memory (it can contain personal data), so it is only in this bundle when you ran Support with -IncludeDumps.`r`n"
    foreach ($d in $dumps) { $dl += "  $($d.Name)  $($d.Length) bytes  $($d.LastWriteTimeUtc.ToString('o'))`r`n" }
    if ($IncludeDumps) {
        foreach ($d in $dumps) { Copy-Item -LiteralPath $d.FullName -Destination (Join-Path $work ('dump_' + $d.Name)); $dl += "included: dump_$($d.Name)`r`n" }
    }
    [IO.File]::WriteAllText((Join-Path $work 'dumps.txt'), (Redact-Text $dl $u $m $p), $script:Utf8)
    [IO.File]::WriteAllText((Join-Path $work 'README.txt'), "Support bundle of $($script:Man['product']) $($script:Man['version']), $stamp.`r`nThe Windows user name, the machine name, the profile path and Steam ids were replaced by <user>, <machine>, %USERPROFILE% and <steamid>. Saves and the game folder listing are never included.`r`n", $script:Utf8)
    $zip = Join-Path $od ("napoleon_remastered_support_" + $stamp + ".zip")
    [IO.Compression.ZipFile]::CreateFromDirectory($work, $zip)
    Move-Out $work (Join-Path $state ("_to_delete\support_work_" + $stamp))
    Say "rr support: wrote $zip"
    Say 'rr support: look inside before you send it. Crash dumps are only included with -IncludeDumps.'
    return 0
}

# ---- main -----------------------------------------------------------------------------------------------------------------------
Load-Manifest
$code = 0
switch ($Verb) {
    'version' { Say "$($script:Man['product']) $($script:Man['version'])"; $code = 0 }
    'redact' {
        $u = $RedactUser; if (-not $u) { $u = [Environment]::UserName }
        $m = $RedactMachine; if (-not $m) { $m = [Environment]::MachineName }
        Redact-File $In $Out $u $m $RedactProfile
        $code = 0
    }
    'clean' {   # needs no game folder: only the state folder
        $state = Long-Path (State-Dir)
        Say "rr: $($script:Man['product']) $($script:Man['version']); state folder $state"
        $code = Do-Clean $state
    }
    default {
        $game = Long-Path (Find-Game)
        $state = Long-Path (State-Dir)
        Say "rr: $($script:Man['product']) $($script:Man['version']); game folder $game; state folder $state"
        switch ($Verb) {
            'install' {
                $code = Do-Install $game $state
                if ($code -eq 0 -and $OfferDumps -and -not $NoPause) {
                    $a = Read-Host 'Turn on crash dumps for the game (asks for administrator rights; helps support find a crash)? [y/N]'
                    if ($a -match '^[yY]') { & (Join-Path $script:RelRoot 'tools\Enable crash dumps.cmd') }
                }
            }
            'uninstall' { $code = Do-Uninstall $game $state }
            'repair' { $code = Do-Repair $game $state }
            'check' {
                $c = Do-Check $game $state
                foreach ($l in $c.Lines) { Say $l }
                $code = $c.Code
                if ($code -eq 0) { Say 'rr check: clean' } else { Say 'rr check: PROBLEMS (see above); Repair.cmd fixes missing or changed files' }
            }
            'support' { $code = Do-Support $game $state }
        }
        if ($Verb -in 'install', 'uninstall', 'repair') { Say-ToDelete $state }
    }
}
exit $code
