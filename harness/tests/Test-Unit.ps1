# purpose: static and unit host tests for the harness: every learning from Empire's watcher history as a guard (BOM-less UTF-8, byte[] returns, UTC everywhere, id and lock rules, hang verdicts, overlays, profile snapshot/restore, tolerant status reads)
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File Test-Unit.ps1 [-Repo <repo root>]   (CI: Windows PowerShell 5.1; the pure parts also run under pwsh on Linux)
# when: on every push (CI job harness-windows) and before committing a change to harness/
# not-a-verb: a PowerShell test script, not a repo operation
param([string]$Repo = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Test-Lib.ps1')
if (-not $Repo) { $Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..')) }
$core = Join-Path $Repo 'harness\core'
$allScripts = @(Get-ChildItem -LiteralPath (Join-Path $Repo 'harness') -Recurse -File | Where-Object { $_.Extension -in '.ps1', '.cmd' })
$coreScripts = @($allScripts | Where-Object { $_.DirectoryName -like '*core' })

# ---- static guards over the source ---------------------------------------------------------------------------------------------
Test-Case 'static: every harness script parses (Windows PowerShell grammar)' {
    foreach ($f in $allScripts | Where-Object { $_.Extension -eq '.ps1' }) {
        $e = $null; $t = $null
        [void][Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$t, [ref]$e)
        if ($e.Count) { throw "$($f.Name): line $($e[0].Extent.StartLineNumber): $($e[0].Message)" }
    }
}
Test-Case 'static: scripts are pure ASCII with no BOM (5.1 reads a BOM-less script as ANSI)' {
    foreach ($f in $allScripts) {
        $b = [IO.File]::ReadAllBytes($f.FullName)
        if ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) { throw "$($f.Name) has a BOM" }
        for ($i = 0; $i -lt $b.Length; $i++) { if ($b[$i] -gt 127) { throw "$($f.Name): non-ASCII byte at offset $i" } }
    }
}
Test-Case 'static: batch files have CRLF line ends (an LF-only .cmd can break goto and labels)' {
    if (-not $env:CI) { Write-Host '      (skipped locally: a Linux working copy is LF until git checks it out; CI checks it)'; return }
    foreach ($f in $allScripts | Where-Object { $_.Extension -eq '.cmd' }) {
        $t = [IO.File]::ReadAllText($f.FullName)
        if ($t -match '(?<!\r)\n') { throw "$($f.Name) has a bare LF" }
    }
}
Test-Case 'static: nothing in harness/core can write UTF-16 or a BOM, or format time in local culture' {
    $ban = @(
        @{ rx = 'Tee-Object'; why = 'Tee-Object writes UTF-16 in 5.1' }, @{ rx = '\*>'; why = '*> redirection writes UTF-16 in 5.1' },
        @{ rx = 'Out-File'; why = 'Out-File defaults to UTF-16' }, @{ rx = 'Set-Content|Add-Content'; why = 'ANSI default in 5.1; use [IO.File] with $Utf8' },
        @{ rx = '\[Text\.Encoding\]::UTF8\b'; why = 'the UTF8 property writes a BOM; use New-Object Text.UTF8Encoding $false' },
        @{ rx = '-Encoding\s+(UTF8|Unicode)'; why = 'BOM or UTF-16' }, @{ rx = 'schtasks'; why = 'schtasks /create is refused without elevation; use Register-ScheduledTask' },
        @{ rx = 'return\s+\$\w+\.ToArray\(\)'; why = 'return ,$x.ToArray(): PowerShell unrolls a bare byte[]' },
        @{ rx = 'ToLocalTime|Get-Date\s+-(UFormat|Format)'; why = 'timestamps are UTC everywhere' },
        @{ rx = "ToString\('[^']*[Hh]:[^']*'\)"; why = 'a time format with a colon needs the invariant culture argument' }
    )
    foreach ($f in $coreScripts | Where-Object { $_.Extension -eq '.ps1' }) {
        $n = 0
        foreach ($line in [IO.File]::ReadAllLines($f.FullName)) {
            $n++
            if ($line.TrimStart().StartsWith('#')) { continue }
            foreach ($b in $ban) { if ($line -match $b.rx) { throw "$($f.Name):$n matches /$($b.rx)/ : $($b.why)" } }
        }
    }
}
Test-Case 'static: the display probe can only validate (CDS_TEST), never apply or change topology' {
    $t = [IO.File]::ReadAllLines((Join-Path $core 'vdisplay_probe.ps1'))
    $calls = @($t | Where-Object { $_ -match '\[VProbe\]::ChangeDisplaySettingsEx\(' })
    Assert-True ($calls.Count -ge 1) 'there is a CDS_TEST call'
    foreach ($c in $calls) { Assert-Match $c 'CDS_TEST' 'every ChangeDisplaySettingsEx call passes CDS_TEST' }
    $joined = ($t | Where-Object { -not $_.TrimStart().StartsWith('#') }) -join "`n"
    Assert-NotMatch $joined 'CDS_UPDATEREGISTRY|SetDisplayConfig|CDS_NORESET|CDS_FULLSCREEN' 'no apply flag, no topology API'
}
Test-Case 'static: update.ps1 judges liveness from the heartbeat file mtime and retries status reads' {
    $t = [IO.File]::ReadAllText((Join-Path $core 'update.ps1'))
    Assert-Match $t 'watcher\.alive' 'uses watcher.alive'
    Assert-Match $t 'LastWriteTime' 'uses its mtime'
    Assert-Match $t 'for \(\$i = 0; \$i -lt 8; \$i\+\+\)' 'retries the status read'
}

# ---- unit tests on the watcher's functions (dot-sourced, no main loop) ----------------------------------------------------------
$tmp = New-Tmp 'unit'
$root = Join-Path $tmp 'watcher'; New-Item -ItemType Directory -Path $root -Force | Out-Null
$adapterPath = New-TestAdapter $tmp
. (Join-Path $core 'watcher.ps1') -Root $root -Adapter $adapterPath -NoRun
Ensure-Dirs

Test-Case 'Read-Shared always returns a byte[] (0, 1 and N bytes): an empty file must not become $null' {
    foreach ($n in 0, 1, 7, 5000) {
        $p = Join-Path $tmp "rs$n.bin"; [IO.File]::WriteAllBytes($p, [byte[]](1..255 * 40)[0..($n - 1)] + $(if ($n -eq 0) { [byte[]]@() } else { [byte[]]@() }))
        if ($n -eq 0) { [IO.File]::WriteAllBytes($p, [byte[]]@()) }
        $b = Read-Shared $p
        Assert-True ($null -ne $b) "n=$n not null"
        Assert-Eq $b.GetType().FullName 'System.Byte[]' "n=$n type"
        Assert-Eq $b.Length ([IO.FileInfo]$p).Length "n=$n length"
    }
}
Test-Case 'UtcStr is UTC, labelled Z and culture-proof' {
    $d = New-Object DateTime 2026, 10, 28, 12, 34, 56, ([DateTimeKind]::Utc)
    Assert-Eq (UtcStr $d) '2026-10-28T12:34:56Z' 'utc in'
    Assert-Eq (UtcStr $d.ToLocalTime()) '2026-10-28T12:34:56Z' 'local in, utc out'
    Assert-Eq (UtcStamp $d) '20261028T123456Z' 'stamp'
    $old = [Threading.Thread]::CurrentThread.CurrentCulture
    try {
        foreach ($c in 'fi-FI', 'ar-SA', 'th-TH') {
            try { [Threading.Thread]::CurrentThread.CurrentCulture = New-Object Globalization.CultureInfo $c } catch { continue }
            Assert-Eq (UtcStr $d) '2026-10-28T12:34:56Z' "culture $c"
        }
    } finally { [Threading.Thread]::CurrentThread.CurrentCulture = $old }
}
Test-Case 'Parse-KV reads owner, session, a purpose with spaces, started and hang_s' {
    $kv = Parse-KV 'owner=agent-1 session=s9 purpose=load a big battle started=2026-10-28T10:00:00Z hang_s=30'
    Assert-Eq $kv['owner'] 'agent-1' 'owner'; Assert-Eq $kv['purpose'] 'load a big battle' 'purpose'; Assert-Eq $kv['hang_s'] '30' 'hang_s'
    Assert-Eq $kv['started'] '2026-10-28T10:00:00Z' 'started'
}
Test-Case 'job ids: pattern enforced' {
    foreach ($ok in 'a', 'agent-20261028T100000Z-123', 'x.y_z-1') { Assert-True (Is-ValidId $ok) $ok }
    foreach ($bad in '', '-x', '.x', 'a b', 'a/b', 'a..\b', ('x' * 121)) { Assert-True (-not (Is-ValidId $bad)) "bad id [$bad]" }
}
Test-Case 'game lock: absent, empty, owner rules, refresh by mtime, staleness after 20 minutes' {
    $lock = Join-Path $root 'game.lock'
    Assert-True ($null -eq (Get-Lock)) 'no lock'
    Assert-Match (Check-Owner 'a') 'no game.lock' 'refused without a lock'
    [IO.File]::WriteAllBytes($lock, [byte[]]@())
    Assert-True ($null -eq (Get-Lock)) '0 bytes counts as absent (being written)'
    [IO.File]::WriteAllText($lock, "owner=alice session=s1 purpose=a test started=2026-10-28T10:00:00Z hang_s=45`r`n", $Utf8)
    $l = Get-Lock
    Assert-Eq $l.owner 'alice' 'owner'; Assert-Eq $l.hang_s '45' 'hang_s'; Assert-True (-not $l.stale) 'fresh'
    Assert-True ($null -eq (Check-Owner 'alice')) 'owner accepted'
    Assert-Match (Check-Owner 'bob') "owner=bob does not hold the game" 'wrong owner'
    Assert-Match (Check-Owner '') 'carries no owner' 'missing owner'
    (Get-Item -LiteralPath $lock).LastWriteTime = (Get-Date).AddMinutes(-19)
    Assert-True (-not (Get-Lock).stale) '19 min is not stale'
    (Get-Item -LiteralPath $lock).LastWriteTime = (Get-Date).AddMinutes(-21)
    Assert-True ((Get-Lock).stale) '21 min is stale'
    Assert-Match (Check-Owner 'alice') 'stale' 'a stale lock is no lock'
    Expire-StaleLock
    Assert-True (-not (Test-Path -LiteralPath $lock)) 'expired lock moved away'
    Assert-Eq @(Get-ChildItem (Join-Path $root '_to_delete') -Filter 'game.lock.expired_alice_*').Count 1 'moved to _to_delete'
    $log = [IO.File]::ReadAllText($LogPath)
    Assert-Match $log 'LOCK EXPIRED: game.lock owner=alice' 'logged'
    Assert-Match $log '^\[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\] ' 'log lines start with a UTC timestamp'
}
Test-Case 'foreign lock (another watcher on this PC) is read, never written' {
    $fl = $A.foreign_locks[0]; New-Item -ItemType Directory -Path (Split-Path $fl) -Force | Out-Null
    Assert-True ($null -eq (Foreign-LockReason)) 'none'
    [IO.File]::WriteAllText($fl, "owner=empire-agent session=e purpose=probe started=2026-10-28T10:00:00Z`r`n", $Utf8)
    Assert-Match (Foreign-LockReason) 'another watcher.*empire-agent' 'fresh foreign lock blocks'
    $before = Sha256File $fl
    (Get-Item -LiteralPath $fl).LastWriteTime = (Get-Date).AddMinutes(-30)
    Assert-True ($null -eq (Foreign-LockReason)) 'a stale foreign lock does not block'
    Remove-Item -LiteralPath $fl -Force
}
Test-Case 'hang verdict: CPU idle AND log quiet for hang_s; start-up grace; minimised is not a hang; IsHungAppWindow counts only when sustained' {
    $base = @{ armed = $true; off = $false; since_start_s = 500; window = 'visible'; window_hung_s = 0; cpu_idle_s = 0; log_idle_s = 0; hang_s = 120; startup_s = 180; hung_window_s = 60; holds_game = $false }
    function V($over) { $f = $base.Clone(); foreach ($k in $over.Keys) { $f[$k] = $over[$k] }; return (Get-HangVerdict $f).hung }
    Assert-True (-not (V @{})) 'alive'
    Assert-True (V @{ cpu_idle_s = 130; log_idle_s = 130 }) 'idle cpu and quiet log = hung'
    Assert-True (-not (V @{ cpu_idle_s = 130; log_idle_s = 5 })) 'log still written = alive'
    Assert-True (-not (V @{ cpu_idle_s = 5; log_idle_s = 130 })) 'cpu still moving = alive'
    Assert-True (V @{ cpu_idle_s = 130; log_idle_s = $null }) 'no heartbeat file configured: CPU alone decides'
    Assert-True (-not (V @{ cpu_idle_s = 130; log_idle_s = 130; since_start_s = 100 })) 'start-up grace'
    Assert-True (-not (V @{ cpu_idle_s = 130; log_idle_s = 130; window = 'minimized' })) 'minimised window is not a hang'
    Assert-True (-not (V @{ cpu_idle_s = 130; log_idle_s = 130; window = 'hidden' })) 'hidden window is not a hang'
    Assert-True (-not (V @{ cpu_idle_s = 130; log_idle_s = 130; armed = $false })) 'not armed: a game Liam started himself is never touched'
    Assert-True (-not (V @{ cpu_idle_s = 130; log_idle_s = 130; off = $true })) 'watchdog off'
    Assert-True (-not (V @{ cpu_idle_s = 130; log_idle_s = 130; holds_game = $true })) 'a launch/kill job is handling the game'
    Assert-True (V @{ window = 'not_responding'; window_hung_s = 61 }) 'IsHungAppWindow sustained = hung'
    Assert-True (-not (V @{ window = 'not_responding'; window_hung_s = 10 })) 'a short freeze while loading is not a hang'
}
Test-Case 'Write-Atomic + Read-JsonRetry: a status file replaced every few ms is never read as broken' {
    $p = Join-Path $tmp 'busy.status'
    Write-Atomic $p '{"n":0}'
    $rs = [runspacefactory]::CreateRunspace(); $rs.Open()
    $ps = [powershell]::Create(); $ps.Runspace = $rs
    [void]$ps.AddScript({
        param($path, $count)
        $enc = New-Object Text.UTF8Encoding $false
        for ($i = 1; $i -le $count; $i++) {
            $tmpf = "$path.wtmp"; [IO.File]::WriteAllText($tmpf, ('{"n":' + $i + ',"pad":"' + ('x' * 3000) + '"}'), $enc)
            for ($k = 0; $k -lt 20; $k++) { try { [IO.File]::Replace($tmpf, $path, [NullString]::Value); break } catch { Start-Sleep -Milliseconds 5 } }
        }
    }).AddArgument($p).AddArgument(3000)
    $h = $ps.BeginInvoke()
    $bad = 0; $reads = 0
    while (-not $h.IsCompleted) { $j = Read-JsonRetry $p; $reads++; if ($null -eq $j) { $bad++ } }
    $ps.EndInvoke($h); $ps.Dispose(); $rs.Dispose()
    Assert-True ($reads -gt 3) "read $reads times"
    Assert-Eq $bad 0 'unreadable results'
}
Test-Case 'Get-AliveAgeS: liveness is the heartbeat file mtime' {
    $d = Join-Path $tmp 'alive'; New-Item -ItemType Directory -Path $d -Force | Out-Null
    Assert-True ($null -eq (Get-AliveAgeS $d)) 'no file: unknown'
    [IO.File]::WriteAllText((Join-Path $d 'watcher.alive'), 'x')
    Assert-True ((Get-AliveAgeS $d) -lt 5) 'fresh'
    (Get-Item -LiteralPath (Join-Path $d 'watcher.alive')).LastWriteTime = (Get-Date).AddSeconds(-60)
    Assert-True ((Get-AliveAgeS $d) -gt 55) 'old'
}

function Enc([string]$s) { return $Latin1.GetBytes($s) }
function Dec([byte[]]$b) { return $Latin1.GetString($b) }
Test-Case 'overlay (ini): replaces a key, keeps CRLF and every other byte, adds a key at the end of its section, creates a section' {
    $base = "; head`r`n[proxy]`r`nbackend=system`r`nlog_level=info`r`n`r`n[other]`r`nx=1`r`n"
    Assert-Eq (Dec (Apply-Overlay (Enc $base) "proxy.backend=dxvk`n" 'ini' 't')) ($base.Replace('backend=system', 'backend=dxvk')) 'replace'
    Assert-Eq (Dec (Apply-Overlay (Enc $base) "proxy.backend=system`n" 'ini' 't')) $base 'same value = identical bytes'
    $r = Dec (Apply-Overlay (Enc $base) "proxy.minidump=2`n" 'ini' 't')
    Assert-Eq $r "; head`r`n[proxy]`r`nbackend=system`r`nlog_level=info`r`nminidump=2`r`n`r`n[other]`r`nx=1`r`n" 'added at the end of [proxy], before the blank line and [other]'
    $r = Dec (Apply-Overlay (Enc $base) "extra.k=v`n" 'ini' 't')
    Assert-Eq $r ($base + "`r`n[extra]`r`nk=v`r`n") 'new section at the end'
    $r = Dec (Apply-Overlay (Enc $base) "!proxy.log_level`n" 'ini' 'p1')
    Assert-Match $r '; \(profile p1\) log_level=info' 'removed key commented out'
}
Test-Case 'overlay (ini): LF files stay LF, duplicates are commented, an empty or absent base works' {
    $r = Dec (Apply-Overlay (Enc "[proxy]`nbackend=a`nbackend=b`n") "proxy.backend=dxvk`n" 'ini' 'p')
    Assert-Eq $r "[proxy]`nbackend=dxvk`n; (profile p) backend=b`n" 'dups'
    Assert-Eq (Dec (Apply-Overlay ([byte[]]@()) "proxy.backend=dxvk`n" 'ini' 'p')) "[proxy]`r`nbackend=dxvk`r`n" 'absent base'
}
Test-Case 'overlay: UTF-16LE with BOM survives (the encoding and BOM are kept)' {
    $u16 = New-Object Text.UnicodeEncoding($false, $false)
    $base = [byte[]]@(0xFF, 0xFE) + $u16.GetBytes("[proxy]`r`nbackend=system`r`n")
    $out = Apply-Overlay $base "proxy.backend=dxvk`n" 'ini' 'p'
    Assert-True ($out[0] -eq 0xFF -and $out[1] -eq 0xFE) 'BOM kept'
    Assert-Eq $u16.GetString($out, 2, $out.Length - 2) "[proxy]`r`nbackend=dxvk`r`n" 'content'
}
Test-Case 'overlay (conf): whole-name keys, written as "key = value", appended when missing; style none refuses' {
    $r = Dec (Apply-Overlay (Enc "# dxvk`nd3d9.maxFrameRate = 0`n") "d3d9.maxFrameRate = 60`ndxvk.logLevel = info`n" 'conf' 'p')
    Assert-Eq $r "# dxvk`nd3d9.maxFrameRate = 60`ndxvk.logLevel = info`n" 'conf'
    $threw = $false; try { Apply-Overlay (Enc 'x') "a=b`n" 'none' 'p' } catch { $threw = $true }
    Assert-True $threw 'style none throws (only a full copy is allowed)'
}

# ---- profiles: snapshot, apply, switch (never stack), restore byte for byte, absent as a recorded state ---------------------------
$profSrc = Join-Path $Repo 'harness\napoleon\profiles'
Copy-Item -Path (Join-Path $profSrc '*') -Destination $ProfilesDir -Recurse -Force
$prefs = Join-Path $A.appdata_dir 'scripts\preferences.script.txt'
$keys = Join-Path $A.appdata_dir 'custom_keys.keys.xml'
$ini = Join-Path $A.game_dir 'napoleon_remastered.ini'
$dxc = Join-Path $A.game_dir 'dxvk.conf'
$odd = [byte[]](0, 255, 13, 10, 10, 13, 0xC3, 0xA9, 200, 1, 2, 3)           # NULs, lone CR/LF, high bytes: nothing may normalise these
[IO.File]::WriteAllBytes($prefs, $odd)
[IO.File]::WriteAllBytes($keys, (Enc "<keys/>"))
function Hashes { return ((@($prefs, $keys, $ini, $dxc) | ForEach-Object { if (Test-Path -LiteralPath $_) { Sha256File $_ } else { 'absent' } }) -join ',') }
$baseline = Hashes
Test-Case 'profile: apply proxy-dxvk with the mod files absent, restore returns every file to its baseline (absent stays absent)' {
    $o = New-Object Collections.Generic.List[string]
    $err = Profile-Apply 'proxy-dxvk' 'agent1' $o
    Assert-True ($null -eq $err) "apply: $err"
    Assert-True (Test-Path -LiteralPath $ini) 'ini installed from absent'
    Assert-Match (Dec ([IO.File]::ReadAllBytes($ini))) '(?m)^backend=dxvk' 'overlay applied to an empty base'
    Assert-Match (Dec ([IO.File]::ReadAllBytes($dxc))) 'dxvk\.logLevel = info' 'dxvk.conf installed'
    Assert-True (($o -join "`n") -match 'WARNING: game:d3d9.dll is not on the PC') 'warns that the DLL is not installed'
    $act = Get-Active; Assert-Eq $act.owner 'agent1' 'active owner'
    $o2 = New-Object Collections.Generic.List[string]
    $err = Profile-Restore 'test' $o2
    Assert-True ($null -eq $err) "restore: $err"
    Assert-Eq (Hashes) $baseline 'byte for byte'
    Assert-True (-not (Test-Path -LiteralPath $ini)) 'absent again'
    Assert-True ($null -eq (Get-Active)) 'no active profile'
    Assert-True (@(Get-ChildItem (Join-Path $root '_to_delete') -Recurse -Filter 'mod_ini__*').Count -ge 1) 'the file moved to _to_delete, not deleted'
}
Test-Case 'profile: files that exist are overlaid, switching A to B never stacks, restore returns to the first snapshot' {
    [IO.File]::WriteAllBytes($ini, (Enc "[proxy]`r`nbackend=system`r`nlog_level=debug`r`n"))
    [IO.File]::WriteAllBytes($dxc, (Enc "d3d9.maxFrameRate = 0`r`n"))
    $b2 = Hashes
    $o = New-Object Collections.Generic.List[string]
    Assert-True ($null -eq (Profile-Apply 'proxy-dxvk' 'agent1' $o)) 'apply A'
    Assert-Eq (Dec ([IO.File]::ReadAllBytes($ini))) "[proxy]`r`nbackend=dxvk`r`nlog_level=debug`r`n" 'ini overlay keeps the other key and CRLF'
    $snap = (Get-Active).snapshot
    Assert-True ($null -eq (Profile-Apply 'vanilla' 'agent1' $o)) 'switch to B'
    Assert-True (-not (Test-Path -LiteralPath $ini)) 'B made the ini absent, nothing of A is left'
    Assert-Eq (Get-Active).snapshot $snap 'the first snapshot is kept'
    Assert-True ($null -eq (Profile-Apply 'proxy-dxvk' 'agent1' $o)) 'back to A'
    Assert-Eq (Dec ([IO.File]::ReadAllBytes($ini))) "[proxy]`r`nbackend=dxvk`r`nlog_level=debug`r`n" 'A applied on the snapshot base, not on top of B'
    Assert-True ($null -eq (Profile-Restore 'test' $o)) 'restore'
    Assert-Eq (Hashes) $b2 'byte for byte'
}
Test-Case 'profile: another owner is refused while one is active; unknown profile and bad names are refused with the reason' {
    $o = New-Object Collections.Generic.List[string]
    Assert-True ($null -eq (Profile-Apply 'vanilla' 'agent1' $o)) 'apply'
    Assert-Match (Profile-Apply 'proxy-dxvk' 'agent2' $o) "still active" 'other owner'
    Assert-Match (Profile-Apply 'nope' 'agent1' $o) "no profile 'nope' \(have: " 'unknown'
    Assert-Match (Profile-Apply '..\x' 'agent1' $o) 'bad profile name' 'bad name'
    Assert-True ($null -eq (Profile-Restore 'test' $o)) 'restore'
}
Test-Case 'profile: a full-file overlay on a style-none target is refused before anything is written' {
    $d = Join-Path $ProfilesDir 'badprefs'; New-Item -ItemType Directory -Path $d -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $d 'prefs.set'), "x=1`n")
    $h = Hashes; $o = New-Object Collections.Generic.List[string]
    Assert-Match (Profile-Apply 'badprefs' 'agent1' $o) "only a full copy" 'refused'
    Assert-Eq (Hashes) $h 'nothing touched'
    Assert-True ($null -eq (Get-Active)) 'nothing active'
    Remove-Item -LiteralPath $d -Recurse -Force
}
Test-Case 'profile: a mismatching restore is reported, not hidden' {
    $baseline = Hashes
    $o = New-Object Collections.Generic.List[string]
    Assert-True ($null -eq (Profile-Apply 'vanilla' 'agent1' $o)) 'apply'
    $snapDir = Join-Path $SavedDir (Get-Active).snapshot
    $saved = Join-Path $snapDir 'files\prefs'
    [IO.File]::WriteAllBytes($saved, (Enc 'tampered'))                 # the saved copy no longer matches its sha256
    [IO.File]::WriteAllBytes($prefs, (Enc 'changed by the game'))
    $err = Profile-Restore 'test' $o
    Assert-Match $err 'did not verify' 'restore fails loudly'
    Assert-True ($null -ne (Get-Active)) 'stays active so it is retried'
    [IO.File]::WriteAllBytes($saved, $odd)                              # repair the saved copy and retry
    Assert-True ($null -eq (Profile-Restore 'test' $o)) 'second restore'
    Assert-Eq (Hashes) $baseline 'back to the baseline'
}
Test-Case 'guards: scripts that start/kill the game or write its config need an owner; read-only ones never do' {
    Assert-True ($null -ne (Script-TouchesGame 'taskkill /f /im Napoleon.exe')) 'taskkill'
    Assert-True ($null -ne (Script-TouchesGame 'start "" "C:\x\Napoleon.exe"')) 'start'
    Assert-True ($null -ne (Script-TouchesGame 'Stop-Process -Name Napoleon -Force')) 'Stop-Process'
    Assert-True ($null -ne (Script-TouchesGame 'start steam://rungameid/34030')) 'steam'
    Assert-True ($null -ne (Script-TouchesGame '& "C:\x\Empire.exe"')) 'direct call (either title)'
    Assert-True ($null -eq (Script-TouchesGame 'tasklist /fi "imagename eq Napoleon.exe" /fo csv /nh')) 'tasklist is read-only'
    Assert-True ($null -eq (Script-TouchesGame 'rem taskkill /f /im Napoleon.exe')) 'comments are ignored'
    Assert-True ($null -ne (Script-TouchesConfig 'copy x.txt "C:\g\dxvk.conf"')) 'copy over a config'
    Assert-True ($null -ne (Script-TouchesConfig 'echo a>> napoleon_remastered.ini')) 'redirect into a config'
    Assert-True ($null -eq (Script-TouchesConfig 'type dxvk.conf')) 'reading a config is fine'
}
Test-Case 'zombie: cleared when the pid is free or reused by another image (the flag outlives the reboot it asks for)' {
    $z = [pscustomobject]@{ pid = 4242; image = 'Napoleon.exe' }
    Assert-True (Zombie-Gone $z $null) 'pid free'
    Assert-True (Zombie-Gone $z ([pscustomobject]@{ ProcessName = 'svchost' })) 'pid reused by another image'
    Assert-True (-not (Zombie-Gone $z ([pscustomobject]@{ ProcessName = 'Napoleon' }))) 'same image still there'
    Assert-True (-not (Zombie-Gone $z ([pscustomobject]@{ ProcessName = 'NAPOLEON' }))) 'image compared case-insensitively'
}
Test-Case 'test runner: -Only selects by regex, -Repeat runs n times and stops at the first failure (J19)' {
    $box = @{ n = 0 }
    $count = { $box.n++ }
    $sel = Invoke-Selected 'hang watchdog: a suspended game' $count 'other case' 5
    Assert-True (-not $sel.ran) 'a case the filter does not match is not run'; Assert-Eq $box.n 0 'body not called'
    $sel = Invoke-Selected 'hang watchdog: a suspended game' $count '^hang watchdog' 5
    Assert-True $sel.ran 'a matching case runs'; Assert-Eq $sel.passed 5 'all 5 runs pass'; Assert-Eq $box.n 5 'body called 5 times'; Assert-True ($null -eq $sel.error) 'no error'
    $box.n = 0
    $sel = Invoke-Selected 'any' $count '' 1
    Assert-True $sel.ran 'no filter: every case runs'; Assert-Eq $box.n 1 'default: once'
    $box.n = 0
    $flaky = { $box.n++; if ($box.n -eq 3) { throw 'third run fails' } }
    $sel = Invoke-Selected 'flaky' $flaky '' 10
    Assert-Eq $sel.passed 2 'two runs passed'; Assert-Eq $box.n 3 'stopped at the first failure'; Assert-Match $sel.error 'third run fails' 'the failure message is kept'
    $box.n = 0
    $sel = Invoke-Selected 'zero' $count '' 0
    Assert-Eq $box.n 1 'a repeat below 1 still runs once'
    foreach ($s in 'Run-HostTests.ps1', 'Test-Integration.ps1') {
        $e = $null; $t = $null
        $ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $s), [ref]$t, [ref]$e)
        $ps = @{}; foreach ($p in $ast.ParamBlock.Parameters) { $ps[$p.Name.VariablePath.UserPath] = $p }
        Assert-True ($ps.ContainsKey('Only') -and $ps.ContainsKey('Repeat')) "$s declares -Only and -Repeat"
        Assert-Eq $ps['Only'].DefaultValue.Value '' "$s -Only defaults to no filter"
        Assert-Eq $ps['Repeat'].DefaultValue.Value 1 "$s -Repeat defaults to 1"
        Assert-True (@($ps['Repeat'].Attributes | Where-Object { $_.TypeName.Name -eq 'ValidateRange' }).Count -eq 1) "$s -Repeat is range-checked"
    }
}
Test-Case 'test runner: Test-Lib never assigns a script variable named like a suite parameter (it would reset -Only; J19 run 40898907246)' {
    # params live in the suite's script scope and names are case-insensitive: Test-Lib's `$script:Only = ''` silently reset -Only
    $e = $null; $t = $null
    $lib = [Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Test-Lib.ps1'), [ref]$t, [ref]$e)
    $assigned = @($lib.FindAll({ param($n) $n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left -is [Management.Automation.Language.VariableExpressionAst] }, $true) |
        ForEach-Object { $_.Left.VariablePath.UserPath -replace '^script:', '' })
    foreach ($s in 'Run-HostTests.ps1', 'Test-Integration.ps1', 'Test-Unit.ps1') {
        $ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $s), [ref]$t, [ref]$e)
        foreach ($p in $ast.ParamBlock.Parameters) {
            $pn = $p.Name.VariablePath.UserPath
            Assert-True (-not ($assigned | Where-Object { $_ -ieq $pn })) "Test-Lib.ps1 assigns `$script:$pn, which is the -$pn parameter of $s"
        }
    }
    # and end to end: a suite script with -Only/-Repeat that dot-sources Test-Lib still sees the values
    $probe = Join-Path $tmp 'probe_suite.ps1'
    [IO.File]::WriteAllText($probe, "param([string]`$Only = '', [int]`$Repeat = 1)`r`n. '$(Join-Path $PSScriptRoot 'Test-Lib.ps1')'`r`n`$script:TcOnly = `$Only; `$script:TcRepeat = `$Repeat`r`nWrite-Output `"[`$(`$script:TcOnly)] [`$(`$script:TcRepeat)]`"`r`n", $Utf8NoBom)
    $o = & (Get-Process -Id $PID).Path -NoProfile -ExecutionPolicy Bypass -File $probe -Only 'hang watchdog' -Repeat 3
    Assert-Eq "$o".Trim() '[hang watchdog] [3]' 'the values reach Test-Case through a dot-sourced Test-Lib'
}
Test-Case 'static: Handle-Hang writes hang.txt before Kill-Game and again after it (a watcher stopped mid-kill still leaves evidence; J19)' {
    $e = $null; $t = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile((Join-Path $core 'watcher.ps1'), [ref]$t, [ref]$e)
    $fn = $ast.Find({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Handle-Hang' }, $true)
    Assert-True ($null -ne $fn) 'Handle-Hang exists'
    $body = $fn.Body.Extent.Text
    $kill = $body.IndexOf('Kill-Game')
    $writes = @([regex]::Matches($body, 'Write-Atomic \$hangTxt') | ForEach-Object { $_.Index })
    Assert-True ($kill -gt 0) 'Handle-Hang calls Kill-Game'
    Assert-True ($writes.Count -eq 2 -and $writes[0] -lt $kill -and $writes[1] -gt $kill) 'hang.txt written atomically once before and once after Kill-Game'
    Assert-Match $body "kill: pending" 'the first write says the kill is pending'
    Assert-True ($body.IndexOf('HANG handled') -gt $writes[1]) 'HANG handled (the completion signal tests wait for) is logged after the final write'
}
Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
exit (Finish-Tests 'unit')
