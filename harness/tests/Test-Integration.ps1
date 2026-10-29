# purpose: integration host tests for the harness on Windows: a real watcher (through watch.cmd) with fake games, driven by job files; refusals, lock, launch/kill, zombie, profiles, auto-restore, hang dump and archive, timeouts, queue rules, update with rollback, installer and uninstaller
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File Test-Integration.ps1 [-Repo <repo root>] [-Only <case-name regex>] [-Repeat <n>]   (CI: GitHub's Windows runner, Windows PowerShell 5.1; needs python for the real-kit test)
# when: on every push (CI job harness-windows); never on the PC, it starts and kills processes named Fake*.exe and sets the time zone of the machine while it runs
# not-a-verb: a PowerShell test script, not a repo operation
# -Only/-Repeat chase a flaky case (J19): the watcher starts once, each selected case runs n times in a row. Cases that build on an
# earlier case's state (the update rollbacks need 'update: a good kit') only pass when that case is selected too.
param([string]$Repo = '', [string]$Only = '', [ValidateRange(1, 1000)][int]$Repeat = 1)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Test-Lib.ps1')
$script:Only = $Only; $script:Repeat = $Repeat
if (-not $Repo) { $Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..')) }
$core = Join-Path $Repo 'harness\core'
$Inv = [Globalization.CultureInfo]::InvariantCulture
$tmp = New-Tmp 'int'
$state = Join-Path $tmp 'state'; $root = Join-Path $state 'watcher'; $kits = Join-Path $state 'kits'
$game = Join-Path $tmp 'game'; $app = Join-Path $tmp 'appdata'
New-Item -ItemType Directory -Path (Join-Path $root 'src'), $kits -Force | Out-Null
$SuiteState = @{ n = 0; tz = $null }

# ---- fake games (compiled here): FakeNapoleon.exe is 32-bit like the real game (the dump path must cope with WoW64) -----------------
$fakeSrc = @'
using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
public static class FAKECLASS {
    public static int Main(string[] a) {
        string mode = a.Length > 0 ? a[0] : "idle";
        string log = a.Length > 1 ? a[1] : null;
        DateTime end = DateTime.UtcNow.AddMinutes(15);
        while (DateTime.UtcNow < end) {
            if (mode == "spin") { Stopwatch sw = Stopwatch.StartNew(); while (sw.ElapsedMilliseconds < 150) { } Thread.Sleep(50); }
            else {
                if (mode == "log" && log != null) { try { File.AppendAllText(log, DateTime.UtcNow.ToString("o") + " tick\r\n"); } catch { } }
                Thread.Sleep(500);
            }
        }
        return 0;
    }
}
'@
function New-Fake([string]$exe, [string]$cls, [string]$platform) {
    $prov = New-Object Microsoft.CSharp.CSharpCodeProvider
    $cp = New-Object System.CodeDom.Compiler.CompilerParameters
    $cp.ReferencedAssemblies.Add("System.dll") | Out-Null; $cp.GenerateExecutable = $true; $cp.OutputAssembly = $exe; $cp.CompilerOptions = "/platform:$platform"
    $res = $prov.CompileAssemblyFromSource($cp, $fakeSrc.Replace('FAKECLASS', $cls))
    if ($res.Errors.HasErrors) { throw ("fake game compile failed: " + (($res.Errors | ForEach-Object { $_.ToString() }) -join '; ')) }
}
New-Item -ItemType Directory -Path $game -Force | Out-Null
New-Fake (Join-Path $game 'FakeNapoleon.exe') 'FakeA' 'x86'
New-Fake (Join-Path $game 'FakeEmpire.exe') 'FakeB' 'x86'
New-Fake (Join-Path $tmp 'Fake64.exe') 'FakeC' 'x64'
$logPath = Join-Path $game 'logs\proxy.log'
$adapterPath = New-TestAdapter $tmp 'FakeNapoleon.exe' 'FakeEmpire.exe' ("log `"$logPath`"")
foreach ($f in 'watcher.ps1', 'watch.cmd', 'update.ps1', 'dump.ps1', 'procfreeze.ps1', 'spawn_detached.ps1', 'vdisplay_probe.ps1') { Copy-Item -LiteralPath (Join-Path $core $f) -Destination (Join-Path $root 'src') }
Copy-Item -LiteralPath $adapterPath -Destination (Join-Path $root 'src\adapter.json')
New-Item -ItemType Directory -Path (Join-Path $root 'profiles') -Force | Out-Null
Copy-Item -Path (Join-Path $Repo 'harness\napoleon\profiles\*') -Destination (Join-Path $root 'profiles') -Recurse -Force
$ini = @"
hang_s=600
hang_startup_s=2
hung_window_s=5
zombie_wait_s=4
loop_ms=300
job_timeout_s=120
launch_confirm_s=10
dump_wait_s=90
test_hooks=1
"@
[IO.File]::WriteAllText((Join-Path $root 'watcher.ini'), $ini, $Utf8NoBom)

# ---- helpers ------------------------------------------------------------------------------------------------------------------------
function ReadText([string]$p) {
    $fs = New-Object IO.FileStream($p, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]'ReadWrite,Delete'))
    try { $sr = New-Object IO.StreamReader($fs, $Utf8NoBom); return $sr.ReadToEnd() } finally { $fs.Dispose() }
}
function Get-St { for ($i = 0; $i -lt 10; $i++) { try { $t = ReadText (Join-Path $root 'watcher.status'); if ($t) { return ($t | ConvertFrom-Json) } } catch { }; Start-Sleep -Milliseconds 120 }; return $null }
function Get-Log { try { return (ReadText (Join-Path $root 'watcher.log')) } catch { return '' } }
# Log-Mark + -Since: match only lines written after the mark, so a repeated case (-Repeat) never matches its previous run's line
function Log-Mark { return (Get-Log).Length }
function Get-LogSince([int]$mark) { $t = Get-Log; if ($t.Length -ge $mark) { return $t.Substring($mark) } else { return $t } }   # shorter: rotated at 2 MB
function Wait-LogMatch([string]$rx, [int]$secs, [string]$what, [int]$Since = 0) { Wait-Until { (Get-LogSince $Since) -match $rx } $secs $what | Out-Null }
function Alive-Age { try { return ((Get-Date) - (Get-Item -LiteralPath (Join-Path $root 'watcher.alive')).LastWriteTime).TotalSeconds } catch { return 9999 } }
function Alive-AgeOf([string]$r) { try { return ((Get-Date) - (Get-Item -LiteralPath (Join-Path $r 'watcher.alive')).LastWriteTime).TotalSeconds } catch { return 9999 } }
function Wait-Watcher([int]$secs = 40) { Wait-Until { (Alive-Age) -lt 4 -and (Get-St) } $secs 'a fresh watcher heartbeat' | Out-Null; return (Get-St) }
function Start-TestWatcher {
    $cmd = Join-Path $root 'src\watch.cmd'
    $a = "/d /s /c `"`"$cmd`" -Root `"$root`" -Adapter `"$adapterPath`"`""
    $p = Start-Process -FilePath $env:ComSpec -ArgumentList $a -WindowStyle Hidden -PassThru
    $SuiteState.launcher = $p
    return (Wait-Watcher 40)
}
function Stop-TestWatcher {
    [IO.File]::WriteAllText((Join-Path $root 'watcher.stop'), 'stop', $Utf8NoBom)
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline -and (Alive-Age) -lt 4) { Start-Sleep -Milliseconds 300 }
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($tmp) -and ($_.Name -in 'powershell.exe', 'cmd.exe') -and $_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
function New-JobId([string]$tag) { $SuiteState.n++; return ('t-{0}-{1}-{2}' -f $tag, (Get-Date).ToUniversalTime().ToString('HHmmss'), $SuiteState.n) }
function Submit([string]$body, [string]$id) {
    $j = Join-Path $root 'jobs'
    [IO.File]::WriteAllText((Join-Path $j "$id.tmp"), $body, $Utf8NoBom)
    Move-Item -LiteralPath (Join-Path $j "$id.tmp") -Destination (Join-Path $j "$id.request")
    return $id
}
function Get-Result([string]$id, [int]$secs = 60) {
    $done = Join-Path $root "jobs\$id.done"
    Wait-Until { Test-Path -LiteralPath $done } $secs "result of job $id" | Out-Null
    Start-Sleep -Milliseconds 150
    $d = (ReadText $done) | ConvertFrom-Json
    $o = ''; $op = Join-Path $root "jobs\$id.out"; if (Test-Path -LiteralPath $op) { $o = ReadText $op }
    return @{ d = $d; out = $o; id = $id }
}
function Run-Job([string]$body, [string]$tag = 'j', [int]$secs = 60) { return (Get-Result (Submit $body (New-JobId $tag)) $secs) }
function Set-Lock([string]$owner, [string]$extra = '') {
    [IO.File]::WriteAllText((Join-Path $root 'game.lock'), ("owner=$owner session=ci purpose=host test started=$(UtcNow-Str)$extra`r`n"), $Utf8NoBom)
}
function UtcNow-Str { return (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd\THH:mm:ss\Z', $Inv) }
function Clear-Lock {
    $l = Join-Path $root 'game.lock'
    if (Test-Path -LiteralPath $l) { $d = Join-Path $root '_to_delete'; New-Item -ItemType Directory -Path $d -Force | Out-Null; $SuiteState.n++; Move-Item -LiteralPath $l -Destination (Join-Path $d "game.lock.test$($SuiteState.n)") -Force }
}
function Stop-Fakes { foreach ($n in 'FakeNapoleon', 'FakeEmpire', 'Fake64') { Get-Process -Name $n -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue } }
function Fake-Procs([string]$n = 'FakeNapoleon') { return @(Get-Process -Name $n -ErrorAction SilentlyContinue) }
$prefs = Join-Path $app 'scripts\preferences.script.txt'; $keys = Join-Path $app 'custom_keys.keys.xml'
$modIni = Join-Path $game 'napoleon_remastered.ini'; $dxc = Join-Path $game 'dxvk.conf'
$bprefs = Join-Path $app 'battle_preferences\.sp_default.battle_preferences'   # HIDDEN on the PC (J3 run 20261029_4kcrash: Get-Item without -Force threw)
function Hashes { return ((@($prefs, $keys, $bprefs, $modIni, $dxc) | ForEach-Object { if (Test-Path -LiteralPath $_) { Sha256File $_ } else { 'absent' } }) -join ',') }
function Pid-Of-Watcher { return [int](Get-St).pid }

try {
    # the machine's time zone is moved far from UTC while the watcher runs: any local-time-with-a-Z-suffix bug shows as a 9 h error
    $SuiteState.tz = (& tzutil.exe /g).Trim()
    & tzutil.exe /s 'Tokyo Standard Time'
    [IO.File]::WriteAllBytes($prefs, [byte[]](0, 255, 13, 10, 10, 13, 0xC3, 0xA9, 200, 1, 2, 3))
    [IO.File]::WriteAllText($keys, '<keys/>', $Utf8NoBom)
    New-Item -ItemType Directory -Path (Split-Path $bprefs) -Force | Out-Null
    [IO.File]::WriteAllBytes($bprefs, [byte[]](1, 2, 3, 4)); (Get-Item -LiteralPath $bprefs -Force).Attributes = 'Hidden'
    $baseline = Hashes
    $st0 = Start-TestWatcher

    Test-Case 'noop and status: results are UTC (machine zone is Tokyo), no BOM, no UTF-16' {
        $r = Run-Job 'noop' 'noop'
        Assert-Eq $r.d.status 'ok' 'noop status'; Assert-Eq $r.d.exit 0 'noop exit'
        Assert-Match $r.d.start_utc '^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$' 'start_utc format'
        $t = [DateTime]::Parse($r.d.start_utc, $Inv, [Globalization.DateTimeStyles]::AdjustToUniversal)
        Assert-True ([Math]::Abs(($t - [DateTime]::UtcNow).TotalSeconds) -lt 60) "start_utc $($r.d.start_utc) is within a minute of real UTC"
        $s = Run-Job 'status' 'status'
        $j = $s.out | ConvertFrom-Json
        Assert-True ($j.processes -is [array] -or $null -eq $j.processes -or $j.processes.Count -ge 0) 'processes listed'
        Assert-Match $j.heartbeat_utc 'Z$' 'heartbeat is UTC'
        $tz = Run-Job "#ps1`r`nWrite-Output ([TimeZoneInfo]::Local.Id)" 'tz'
        Assert-Match $tz.out 'Tokyo' 'the test really ran under a non-UTC zone'
        foreach ($f in 'watcher.status', 'watcher.log', "jobs\$($r.id).done", "jobs\$($s.id).out") {
            $b = [IO.File]::ReadAllBytes((Join-Path $root $f))
            Assert-True ($b.Length -gt 2) "$f not empty"
            Assert-True (-not ($b[0] -eq 0xEF -and $b[1] -eq 0xBB)) "$f has a UTF-8 BOM"
            Assert-True (-not (($b[0] -eq 0xFF -and $b[1] -eq 0xFE) -or ($b[0] -eq 0xFE -and $b[1] -eq 0xFF))) "$f is UTF-16"
            Assert-True (-not ($b -contains 0)) "$f contains NUL bytes (UTF-16?)"
        }
        $first = (Get-Log) -split "`r?`n" | Select-Object -First 1
        Assert-Match $first '^\[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\] ' 'log timestamps are UTC with a Z'
    }
    Test-Case 'queue: a job with no output finishes normally and the next job still runs (Empire 5.0 wedged here)' {
        $a = Submit "@echo off`r`nrem prints nothing" (New-JobId 'empty'); Start-Sleep -Milliseconds 80
        $b = Submit "@echo off`r`nexit /b 3" (New-JobId 'fail'); Start-Sleep -Milliseconds 80
        $c = Submit "@echo off`r`necho line one`r`necho line two" (New-JobId 'normal'); Start-Sleep -Milliseconds 80
        $d = Submit "#ps1`r`n`$x = 1" (New-JobId 'ps1empty'); Start-Sleep -Milliseconds 80
        $e = Submit "#ps1`r`nWrite-Output (`"ps `" + `$PSVersionTable.PSVersion.Major)" (New-JobId 'ps1')
        $ra = Get-Result $a; $rb = Get-Result $b; $rc = Get-Result $c; $rd = Get-Result $d; $re = Get-Result $e
        Assert-Eq $ra.d.status 'ok' 'empty status'; Assert-Eq $ra.d.exit 0 'empty exit'; Assert-Eq $ra.out.Length 0 'empty output stays empty'
        Assert-Eq $rb.d.status 'failed' 'fail status'; Assert-Eq $rb.d.exit 3 'real exit code'
        Assert-Match $rc.out 'line two' 'normal output'
        Assert-Eq $rd.d.status 'ok' 'ps1 empty'; Assert-Match $re.out 'ps 5' 'jobs run under Windows PowerShell 5.1'
        $ts = @($ra, $rb, $rc, $rd, $re) | ForEach-Object { [DateTime]::Parse($_.d.start_utc, $Inv, [Globalization.DateTimeStyles]::AdjustToUniversal) }
        for ($i = 1; $i -lt $ts.Count; $i++) { Assert-True ($ts[$i] -ge $ts[$i - 1]) 'FIFO order' }
    }
    Test-Case 'single instance: a second watcher on the same root exits with 10' {
        $p = Start-Process -FilePath powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $root 'src\watcher.ps1')`" -Root `"$root`" -Adapter `"$adapterPath`"" -WindowStyle Hidden -Wait -PassThru
        Assert-Eq $p.ExitCode 10 'exit code of the second instance'
    }
    Test-Case 'one job error never wedges the slot: output-collection failure and a start failure both finish, the queue moves on' {
        $id = New-JobId 'collect'; New-Item -ItemType Directory -Path (Join-Path $root "jobs\$id.out.wtmp") -Force | Out-Null
        $r = Get-Result (Submit "@echo off`r`necho collect_throws" $id)
        Assert-Eq $r.d.status 'ok' 'status kept'; Assert-Match $r.out 'output could not be collected' 'the failure is noted in the output'
        $r2 = Run-Job "#job test=throw_on_start`r`n@echo off`r`necho hi" 'throw'
        Assert-Eq $r2.d.status 'failed' 'start failure closes as failed'; Assert-Match $r2.d.reason 'watcher error while starting' 'reason'
        $r3 = Run-Job 'noop' 'after'; Assert-Eq $r3.d.status 'ok' 'the queue moved on'
    }
    Test-Case 'job ids are never reused: the second request is refused; the old result stays until the new request is picked up' {
        $first = Run-Job 'noop' 'reuse'
        $long = Submit "@echo off`r`nping -n 7 127.0.0.1 >nul`r`necho long" (New-JobId 'long'); Start-Sleep -Milliseconds 200
        Submit 'noop' $first.id | Out-Null
        Start-Sleep -Milliseconds 800
        $doneNow = ReadText (Join-Path $root "jobs\$($first.id).done")
        Assert-Match $doneNow '"status":\s*"ok"' 'the old result is still there while the new request waits in the queue'
        Get-Result $long | Out-Null
        Wait-Until { (ReadText (Join-Path $root "jobs\$($first.id).done")) -match 'refused' } 30 'the reuse to be refused' | Out-Null
        $r = Get-Result $first.id 40
        Assert-Eq $r.d.status 'refused' 'reused id'; Assert-Match $r.d.reason 'already used' 'reason'
    }
    Test-Case 'job timeout kills the job tree but spares the game; a game started by the job does not block the next job' {
        Set-Lock 'ci1'
        $body = "#job owner=ci1 timeout=5`r`n@echo off`r`nstart `"`" /b `"$game\FakeNapoleon.exe`" idle`r`nping -n 60 127.0.0.1 >nul"
        $r = Run-Job $body 'timeout' 40
        Assert-Eq $r.d.status 'timeout' 'status'; Assert-Eq $r.d.exit -1 'exit'
        Assert-True ((Fake-Procs).Count -eq 1) 'the game the job started is still running'
        $n = Run-Job "@echo off`r`necho after the timeout" 'after' 20
        Assert-Match $n.out 'after the timeout' 'the next job ran (the game holds the first job output handle, but only the .part)'
        $k = Run-Job 'kill owner=ci1' 'kill' 40
        Assert-Eq $k.d.status 'ok' 'kill'; Wait-Until { (Fake-Procs).Count -eq 0 } 10 'game gone' | Out-Null
        Clear-Lock
    }
    Test-Case 'refusals: no lock, wrong owner, scripts that start/kill the game or write its config without an owner' {
        Clear-Lock
        $r = Run-Job 'launch owner=ci1' 'nolock'
        Assert-Eq $r.d.status 'refused' 'no lock'; Assert-Eq $r.d.exit -2 'refused exit'; Assert-Match $r.d.reason 'no game.lock' 'reason names the lock'
        Assert-Eq (Run-Job 'kill owner=ci1' 'nolock2').d.status 'refused' 'kill without a lock'
        Assert-Eq (Run-Job 'profile vanilla owner=ci1' 'nolock3').d.status 'refused' 'profile without a lock'
        Set-Lock 'ci1'
        $w = Run-Job 'launch owner=someone-else' 'wrong'
        Assert-Eq $w.d.status 'refused' 'wrong owner'; Assert-Match $w.d.reason 'does not hold the game' 'reason'
        Assert-Eq (Run-Job 'launch' 'noowner').d.status 'refused' 'no owner in the request'
        $s = Run-Job "@echo off`r`ntaskkill /f /im FakeNapoleon.exe" 'script'
        Assert-Eq $s.d.status 'refused' 'taskkill script without owner'; Assert-Match $s.d.reason 'needs' 'reason'
        $c = Run-Job "@echo off`r`ncopy NUL `"$dxc`"" 'cfg'
        Assert-Eq $c.d.status 'refused' 'config-writing script without owner'
        Assert-True (-not (Test-Path -LiteralPath $dxc)) 'and it did not run'
        $ro = Run-Job "@echo off`r`ntasklist /fi `"imagename eq FakeNapoleon.exe`" /fo csv /nh" 'readonly'
        Assert-Eq $ro.d.status 'ok' 'read-only tasklist is never blocked'
        Clear-Lock
    }
    Test-Case 'launch and kill: pid confirmed, second launch refused, the other title blocks, a foreign lock blocks, kill is clean' {
        Set-Lock 'ci2'
        $l = Run-Job 'launch owner=ci2' 'launch' 40
        Assert-Eq $l.d.status 'ok' "launch ($($l.out))"; Assert-Match $l.out 'running: FakeNapoleon.exe pid \d+' 'pid confirmed'
        Assert-True ((Fake-Procs).Count -eq 1) 'running'
        Wait-Until { (Get-St).game_state.state -eq 'running' } 10 'status says running' | Out-Null
        $l2 = Run-Job 'launch owner=ci2' 'launch2'
        Assert-Eq $l2.d.status 'refused' 'second launch'; Assert-Match $l2.d.reason 'already running' 'reason'
        $k = Run-Job 'kill owner=ci2' 'kill' 40
        Assert-Eq $k.d.status 'ok' 'kill'; Assert-True ((Fake-Procs).Count -eq 0) 'gone'
        $e = Start-Process -FilePath (Join-Path $game 'FakeEmpire.exe') -ArgumentList 'idle' -PassThru
        $l3 = Run-Job 'launch owner=ci2' 'other'
        Assert-Eq $l3.d.status 'refused' 'the other title is running'; Assert-Match $l3.d.reason 'FakeEmpire.exe' 'names it'
        Stop-Process -Id $e.Id -Force
        $fl = $A_foreign = (Get-Content -LiteralPath $adapterPath -Raw | ConvertFrom-Json).foreign_locks[0]
        New-Item -ItemType Directory -Path (Split-Path $fl) -Force | Out-Null
        [IO.File]::WriteAllText($fl, "owner=empire-agent session=e purpose=probe started=$(UtcNow-Str)`r`n", $Utf8NoBom)
        $l4 = Run-Job 'launch owner=ci2' 'foreign'
        Assert-Eq $l4.d.status 'refused' 'foreign lock'; Assert-Match $l4.d.reason 'another watcher' 'reason'
        Assert-Match ([IO.File]::ReadAllText($fl)) 'empire-agent' 'the foreign lock was only read'
        Remove-Item -LiteralPath $fl -Force
        Clear-Lock
    }
    Test-Case 'zombie: a process that survives the kill is flagged, persisted across a watcher restart, every launch refused until it is gone' {
        Add-Content -LiteralPath (Join-Path $root 'watcher.ini') -Value "`r`ntest_fake_zombie=1" -Encoding Ascii
        Wait-Until { (Get-Log) -match 'settings: watcher.ini reloaded' } 10 'ini reloaded' | Out-Null
        Start-Sleep -Milliseconds 600
        Set-Lock 'ci3'
        $l = Run-Job 'launch owner=ci3' 'zlaunch' 40; Assert-Eq $l.d.status 'ok' 'launch'
        $k = Run-Job 'kill owner=ci3' 'zkill' 40
        Assert-Eq $k.d.status 'failed' 'kill fails'; Assert-Match $k.d.reason 'ZOMBIE' 'reason'
        Wait-Until { $x = Get-St; $x -and [bool]$x.zombie -and [bool]$x.needs_reboot } 15 'status shows zombie and needs_reboot' | Out-Null
        $r = Run-Job 'launch owner=ci3' 'zrefuse'
        Assert-Eq $r.d.status 'failed' 'launch is refused loudly (failed, exit 1) so no agent mistakes it for a policy refusal'; Assert-Match $r.d.reason 'PC NEEDS REBOOT' 'says the PC needs a reboot'
        Assert-True (Test-Path -LiteralPath (Join-Path $root 'watcher.zombie.json')) 'persisted'
        $old = Pid-Of-Watcher
        Run-Job 'restart' 'zrestart' | Out-Null
        Wait-Until { (Alive-Age) -lt 4 -and (Pid-Of-Watcher) -ne $old } 40 'a new watcher process' | Out-Null
        Assert-True ([bool](Get-St).zombie) 'the zombie flag survived the restart'
        Stop-Fakes
        Wait-Until { -not (Get-St).zombie } 15 'flag clears once the pid is gone' | Out-Null
        Assert-Match (Get-Log) 'is gone - launches allowed again' 'logged'
        $ini2 = (ReadText (Join-Path $root 'watcher.ini')).Replace('test_fake_zombie=1', 'test_fake_zombie=0')
        [IO.File]::WriteAllText((Join-Path $root 'watcher.ini'), $ini2, $Utf8NoBom)
        Start-Sleep -Seconds 2
        Clear-Lock
    }
    Test-Case 'profiles through the watcher: apply, switch, game running refuses, restore is byte-identical (absent files too)' {
        Set-Lock 'ci4'
        $p = Run-Job 'profile proxy-dxvk owner=ci4' 'prof'
        Assert-Eq $p.d.status 'ok' "apply ($($p.out))"; Assert-Match $p.out 'snapshot: profiles' 'snapshot taken'
        Assert-Match (ReadText $modIni) '(?m)^backend=dxvk' 'overlay applied to the absent ini'
        $l = Run-Job 'launch owner=ci4' 'plaunch' 40; Assert-Eq $l.d.status 'ok' 'launch'
        $sw = Run-Job 'profile vanilla owner=ci4' 'pswitch'
        Assert-Eq $sw.d.status 'refused' 'switch while running'; Assert-Match $sw.d.reason 'already running' 'reason'
        Run-Job 'kill owner=ci4' 'pkill' 40 | Out-Null
        $sw = Run-Job 'profile vanilla owner=ci4' 'pswitch2'; Assert-Eq $sw.d.status 'ok' 'switch'
        Assert-True (-not (Test-Path -LiteralPath $modIni)) 'vanilla: no mod ini'
        $r = Run-Job 'profile restore owner=ci4' 'prest'
        Assert-Eq $r.d.status 'ok' "restore ($($r.out))"; Assert-Eq (Hashes) $baseline 'every file byte-identical to the baseline'
        Clear-Lock
    }
    Test-Case 'auto-restore: lock expiry, release, owner change, and deferral while the game runs; each says so in the log' {
        # a) expiry, with a profile active: restored UNDER ITS OWNER and logged
        Set-Lock 'ci5'; Run-Job 'profile proxy-dxvk owner=ci5' 'a1' | Out-Null
        Assert-True ((Hashes) -ne $baseline) 'profile applied'
        (Get-Item -LiteralPath (Join-Path $root 'game.lock')).LastWriteTime = (Get-Date).AddMinutes(-25)
        Wait-Until { (Hashes) -eq $baseline } 20 'restored after expiry' | Out-Null
        # the files are restored BEFORE the AUTO-RESTORE line is written: wait for the line, never read the log once (J2 review, run 40832860145)
        Wait-LogMatch 'LOCK EXPIRED: game.lock owner=ci5' 10 'expiry logged'
        Wait-LogMatch 'AUTO-RESTORE under owner=ci5' 10 'restore under the owner is logged'
        Assert-True (@(Get-ChildItem (Join-Path $root '_to_delete') -Filter 'game.lock.expired_ci5_*').Count -eq 1) 'lock moved, not deleted'
        # b) release
        Set-Lock 'ci6'; Run-Job 'profile proxy-dxvk owner=ci6' 'b1' | Out-Null; Clear-Lock
        Wait-Until { (Hashes) -eq $baseline } 20 'restored after release' | Out-Null
        Wait-LogMatch 'AUTO-RESTORE under owner=ci6 .*released or expired' 10 'release logged'
        # c) changes owner
        Set-Lock 'ci7'; Run-Job 'profile proxy-dxvk owner=ci7' 'c1' | Out-Null
        # a lock mid-rewrite (0 bytes) is not a release: no restore on it
        [IO.File]::WriteAllBytes((Join-Path $root 'game.lock'), [byte[]]@()); Start-Sleep -Seconds 5
        Assert-True ((Hashes) -ne $baseline) 'a 0-byte lock (mid-rewrite) does not trigger a restore'
        Set-Lock 'intruder'
        Wait-Until { (Hashes) -eq $baseline } 20 'restored after the owner changed' | Out-Null
        Wait-LogMatch "AUTO-RESTORE under owner=ci7 .*now belongs to 'intruder'" 10 'owner change logged'
        Clear-Lock
        # d) deferred while the game runs
        Set-Lock 'ci8'; Run-Job 'profile proxy-dxvk owner=ci8' 'd1' | Out-Null
        $idleGame = Start-Process -FilePath (Join-Path $game 'FakeNapoleon.exe') -ArgumentList 'idle' -PassThru
        Clear-Lock
        Wait-Until { (Get-Log) -match "auto-restore of 'proxy-dxvk' \(owner=ci8\) pending" } 15 'pending is logged' | Out-Null
        Assert-True ((Hashes) -ne $baseline) 'not restored while the game is open'
        Stop-Process -Id $idleGame.Id -Force
        Wait-Until { (Hashes) -eq $baseline } 20 'restored once the game exited' | Out-Null
    }
    Test-Case 'hang watchdog: a suspended game is caught (no CPU, no log write), minidumped out of process, archived, killed; busy and unarmed games are left alone' {
        Remove-Item -LiteralPath $logPath -Force -ErrorAction SilentlyContinue
        $mark = Log-Mark
        $runsBefore = @(Get-ChildItem (Join-Path $root 'runs') -Directory -Filter '*_hang' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
        # unarmed: no lock, no watcher launch -> a game Liam started himself is never touched
        Clear-Lock
        $u = Start-Process -FilePath (Join-Path $game 'FakeNapoleon.exe') -ArgumentList 'idle' -PassThru
        Start-Sleep -Seconds 11
        Assert-True (-not $u.HasExited) 'an unarmed idle game is left alone'
        Stop-Process -Id $u.Id -Force; Start-Sleep -Seconds 1
        # armed (valid lock, hang_s=6): CPU-busy game with no log is alive
        Set-Lock 'ci9' ' hang_s=6'
        $s = Start-Process -FilePath (Join-Path $game 'FakeNapoleon.exe') -ArgumentList 'spin' -PassThru
        Start-Sleep -Seconds 11
        Assert-True (-not $s.HasExited) 'a game that burns CPU is alive'
        Stop-Process -Id $s.Id -Force; Start-Sleep -Seconds 1
        # armed, log writer (no CPU to speak of): alive, then frozen
        $h = Start-Process -FilePath (Join-Path $game 'FakeNapoleon.exe') -ArgumentList "log `"$logPath`"" -PassThru
        Start-Sleep -Seconds 10
        Assert-True (-not $h.HasExited) 'a game that keeps writing its log is alive'
        $fz = Run-Job "#job type=ps1 owner=ci9`r`n& `"$(Join-Path $root 'src\procfreeze.ps1')`" -ProcessId $($h.Id) -Mode suspend" 'freeze' 30
        Assert-Eq $fz.d.status 'ok' "freeze ($($fz.out))"
        Wait-Until { $h.Refresh(); $h.HasExited } 90 'the hung game to be killed' | Out-Null
        # the process can be gone while the watcher is still in Kill-Game's polling loop: its log line is the completion signal (J19, run 40878131007)
        Wait-LogMatch 'HANG handled: killed' 30 'the watcher to finish handling the hang' -Since $mark
        $runs = @(Get-ChildItem (Join-Path $root 'runs') -Directory -Filter '*_hang' | Where-Object { $runsBefore -notcontains $_.Name })
        Assert-True ($runs.Count -eq 1) "one new runs\<utc>_hang folder (got $($runs.Count))"
        $dir = $runs[0].FullName
        $dmp = @(Get-ChildItem $dir -Filter '*.dmp')
        Assert-True ($dmp.Count -eq 1 -and $dmp[0].Length -gt 4096) 'a real minidump was written'
        Assert-Eq ([Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($dmp[0].FullName)[0..3])) 'MDMP' 'dump signature (32-bit target dumped by the SysWOW64 helper)'
        Assert-True (Test-Path -LiteralPath (Join-Path $dir 'hang.txt')) 'hang.txt'
        $hangTxt = ReadText (Join-Path $dir 'hang.txt')
        Assert-Match $hangTxt 'no CPU-time progress' 'reason in hang.txt'
        Assert-Match $hangTxt '(?m)^kill: killed\s*$' 'hang.txt holds the kill result'
        Assert-NotMatch $hangTxt 'kill: pending' 'hang.txt was rewritten after the kill'
        Assert-True (@(Get-ChildItem $dir -Filter '*proxy.log').Count -eq 1) 'the proxy log was archived'
        Assert-True (Test-Path -LiteralPath (Join-Path $dir 'game.lock')) 'the lock was archived'
        Assert-Match (Get-LogSince $mark) 'HANG: FakeNapoleon.exe' 'logged'
        Wait-Until { $x = Get-St; $x -and $x.last_hang -and [bool]$x.last_hang.killed } 15 'status.last_hang.killed' | Out-Null
        Assert-True ((Fake-Procs).Count -eq 0) 'process gone'
        Clear-Lock
    }
    Test-Case 'dump.ps1 also dumps a 64-bit process' {
        $p = Start-Process -FilePath (Join-Path $tmp 'Fake64.exe') -ArgumentList 'idle' -PassThru
        $out = Join-Path $tmp 'x64.dmp'
        $o = & (Join-Path $env:windir 'System32\WindowsPowerShell\v1.0\powershell.exe') -NoProfile -ExecutionPolicy Bypass -File (Join-Path $core 'dump.ps1') -ProcessId $p.Id -Out $out
        Stop-Process -Id $p.Id -Force
        Assert-Eq $LASTEXITCODE 0 "exit code ($o)"; Assert-True ((Get-Item -LiteralPath $out).Length -gt 4096) 'dump written'
    }
    Test-Case 'long-lived processes start detached: spawn_detached leaves no handle on the job output; the display probe only validates' {
        $mk = Join-Path $tmp 'later.cmd'
        [IO.File]::WriteAllText($mk, "@echo off`r`nping -n 6 127.0.0.1 >nul`r`necho done> `"$tmp\later.marker`"`r`n", [Text.Encoding]::ASCII)
        $r = Run-Job "#ps1`r`n& `"$(Join-Path $root 'src\spawn_detached.ps1')`" -Path `"$mk`"" 'spawn' 30
        Assert-Eq $r.d.status 'ok' "spawn ($($r.out))"; Assert-Match $r.out 'spawned pid=\d+ rc=0' 'spawned'
        Assert-True (-not (Test-Path -LiteralPath (Join-Path $root "jobs\$($r.id).part"))) 'the job output .part was released (no inherited handle)'
        Wait-Until { Test-Path -LiteralPath (Join-Path $tmp 'later.marker') } 30 'the detached process to finish on its own' | Out-Null
        $v = Run-Job "#ps1`r`n& `"$(Join-Path $root 'src\vdisplay_probe.ps1')`"" 'vd' 60
        Assert-Match $v.out 'displays \(' 'lists the displays'
        Assert-True ($v.out -match 'NO UNIQUE VIRTUAL DISPLAY' -or $v.out -match 'mode list' ) 'either no virtual display (the runner) or a mode list'
        Assert-NotMatch $v.out 'ChangeDisplaySettingsEx\(.*-> 0 .*applied' 'nothing applied'
    }
    Test-Case 'launcher restarts the watcher after a crash, and the job that was running is closed as lost' {
        $old = Pid-Of-Watcher
        $id = Submit "@echo off`r`nping -n 40 127.0.0.1 >nul`r`necho never" (New-JobId 'lost')
        Wait-Until { (Get-St).current_job.id -eq $id } 20 'job running' | Out-Null
        Stop-Process -Id $old -Force
        Wait-Until { (Alive-Age) -lt 4 -and (Pid-Of-Watcher) -ne $old } 60 'the launcher to bring a new watcher up' | Out-Null
        $r = Get-Result $id 30
        Assert-Eq $r.d.status 'lost' 'the interrupted job is closed as lost'
        Get-Process -Name ping -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Assert-Eq (Run-Job 'noop' 'afterlost').d.status 'ok' 'and the queue works'
    }

    # ---- update with a dead-man switch --------------------------------------------------------------------------------------------
    function New-TestKit([string]$id, [hashtable]$over) {
        $kd = Join-Path $kits $id; New-Item -ItemType Directory -Path $kd -Force | Out-Null
        $entries = @()
        foreach ($f in Get-ChildItem (Join-Path $root 'src') -File) {
            $bytes = if ($over.ContainsKey($f.Name)) { [byte[]]$over[$f.Name] } else { [IO.File]::ReadAllBytes($f.FullName) }
            $h = (New-Object Security.Cryptography.SHA256Managed).ComputeHash($bytes); $sha = ([BitConverter]::ToString($h)).Replace('-', '').ToLower()
            $staged = "$($sha.Substring(0, 12))__src__$($f.Name)"
            [IO.File]::WriteAllBytes((Join-Path $kd $staged), $bytes)
            $entries += [ordered]@{ path = "src/$($f.Name)"; staged = $staged; sha256 = $sha; size = $bytes.Length; role = 'test' }
        }
        $w = [Text.Encoding]::ASCII.GetString([byte[]]$(if ($over.ContainsKey('watcher.ps1')) { $over['watcher.ps1'] } else { [IO.File]::ReadAllBytes((Join-Path $root 'src\watcher.ps1')) }))
        $ver = [regex]::Match($w, "\`$Version = '([^']+)'").Groups[1].Value
        $man = [ordered]@{ kind = 'harness'; kit_id = $id; watcher_version = $ver; files = $entries; kit_files = @() }
        [IO.File]::WriteAllText((Join-Path $kd 'manifest.json'), ($man | ConvertTo-Json -Depth 5), $Utf8NoBom)
        return $ver
    }
    function Watcher-Text { return [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes((Join-Path $root 'src\watcher.ps1'))) }
    Test-Case 'update: a good kit replaces the watcher, the new one answers noop, the update is confirmed' {
        $cur = Watcher-Text
        # any current version: a literal '1.0.0' here made every watcher version bump silently break this case (J19)
        $ver = New-TestKit 'kit-good' @{ 'watcher.ps1' = [Text.Encoding]::ASCII.GetBytes(([regex]"\`$Version = '[^']+'").Replace($cur, "`$Version = '9.9.9-ci'", 1)) }
        Assert-Eq $ver '9.9.9-ci' 'kit version'
        $r = Run-Job 'update kit=kit-good noop_s=40 healthy_s=60 stable_s=5' 'upd' 30
        Assert-Eq $r.d.status 'ok' "update accepted ($($r.out))"
        Wait-Until { (Alive-Age) -lt 4 -and (Get-St).version -eq '9.9.9-ci' } 120 'the new version' | Out-Null
        Wait-Until { (Get-Log) -match '\[update\] CONFIRMED' } 90 'CONFIRMED' | Out-Null
        Assert-Match (Watcher-Text) "9\.9\.9-ci" 'file replaced'
        Assert-True (@(Get-ChildItem (Join-Path $root 'backup') -Directory).Count -ge 1) 'a backup of the old files exists'
        Assert-Eq (Run-Job 'noop' 'afterupd').d.status 'ok' 'new watcher serves jobs'
    }
    Test-Case 'update rollback 1: a watcher that does not start is put back byte for byte' {
        $before = Sha256File (Join-Path $root 'src\watcher.ps1')
        $bad = (Watcher-Text).Replace("`$Version = '9.9.9-ci'", "`$Version = '9.9.7-bad'") + "`r`n)))`r`n"
        New-TestKit 'kit-bad' @{ 'watcher.ps1' = [Text.Encoding]::ASCII.GetBytes($bad) } | Out-Null
        Run-Job 'update kit=kit-bad noop_s=20 healthy_s=20 stable_s=3' 'updbad' 30 | Out-Null
        Wait-Until { (Get-Log) -match 'REVERTED: watcher 9\.9\.9-ci' } 150 'the revert' | Out-Null
        Assert-Eq (Sha256File (Join-Path $root 'src\watcher.ps1')) $before 'src\watcher.ps1 is byte-identical to before'
        Wait-Until { (Alive-Age) -lt 4 -and (Get-St).version -eq '9.9.9-ci' } 60 'the old watcher back' | Out-Null
    }
    Test-Case 'update rollback 2: a new watcher that runs but does not answer a noop job is put back (the dead-man switch)' {
        $before = Sha256File (Join-Path $root 'src\watcher.ps1')
        $deaf = (Watcher-Text).Replace("`$Version = '9.9.9-ci'", "`$Version = '9.9.8-deaf'").Replace('function Start-NextJob {', 'function Start-NextJob { return $false')
        New-TestKit 'kit-deaf' @{ 'watcher.ps1' = [Text.Encoding]::ASCII.GetBytes($deaf) } | Out-Null
        Run-Job 'update kit=kit-deaf noop_s=10 healthy_s=60 stable_s=3' 'upddeaf' 30 | Out-Null
        Wait-Until { (Get-Log) -match 'did not answer a noop job within 10 s' } 120 'the dead-man switch' | Out-Null
        Wait-Until { (Get-Log) -match '(?s)did not answer a noop.*REVERTED: watcher 9\.9\.9-ci' } 90 'the revert' | Out-Null
        Assert-Eq (Sha256File (Join-Path $root 'src\watcher.ps1')) $before 'byte-identical after the revert'
        Wait-Until { (Alive-Age) -lt 4 -and (Get-St).version -eq '9.9.9-ci' } 60 'the old watcher back' | Out-Null
        Assert-Eq (Run-Job 'noop' 'afterdeaf').d.status 'ok' 'serving again'
    }
    Test-Case 'update refuses a stale or tampered kit before touching anything' {
        New-TestKit 'kit-stale' @{} | Out-Null
        $kd = Join-Path $kits 'kit-stale'
        $f = Get-ChildItem $kd -Filter '*__src__watcher.ps1' | Select-Object -First 1
        [IO.File]::WriteAllText($f.FullName, 'old cached copy', $Utf8NoBom)
        $before = Sha256File (Join-Path $root 'src\watcher.ps1')
        Run-Job 'update kit=kit-stale noop_s=10 healthy_s=20' 'updstale' 30 | Out-Null
        Wait-Until { (Get-Log) -match 'ABORT: staged file .* does not match the manifest sha256' } 40 'the abort' | Out-Null
        Assert-Eq (Sha256File (Join-Path $root 'src\watcher.ps1')) $before 'nothing changed'
        $none = Run-Job 'update kit=no-such-kit' 'updnone' 20
        Assert-Eq $none.d.status 'refused' 'unknown kit'
    }
    Stop-TestWatcher
    Stop-Fakes

    # ---- installer, with the real kit built by pc_deploy.py ------------------------------------------------------------------------
    $py = (Get-Command python -ErrorAction SilentlyContinue)
    Test-Case 'installer: the real harness kit installs (sha-checked), registers the logon task, starts a healthy watcher; the uninstaller removes it' {
        Assert-True ($null -ne $py) 'python is needed for the real kit'
        $out = Join-Path $tmp 'realkits'
        & python (Join-Path $Repo 'proxy\tools\pc_deploy.py') kit --what harness --out $out | Out-Null
        Assert-Eq $LASTEXITCODE 0 'pc_deploy kit'
        $kit = (Get-ChildItem $out -Directory | Select-Object -First 1).FullName
        $iroot = Join-Path $tmp 'inst\watcher'
        $tn = 'napoleon_remastered watcher citest'
        # a tampered staged file: refused, nothing installed
        $copy = Join-Path $tmp 'tamperedkit'; Copy-Item -LiteralPath $kit -Destination $copy -Recurse
        $m = (ReadText (Join-Path $copy 'manifest.json')) | ConvertFrom-Json
        [IO.File]::WriteAllText((Join-Path $copy $m.files[0].staged), 'stale', $Utf8NoBom)
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $copy 'install.ps1') -Kit $copy -Root (Join-Path $tmp 'inst_bad\watcher') -NoTask -NoStart | Out-Null
        Assert-True ($LASTEXITCODE -ne 0) 'tampered kit refused'
        Assert-True (-not (Test-Path -LiteralPath (Join-Path $tmp 'inst_bad\watcher\src\watcher.ps1'))) 'and nothing was installed'
        # the real install
        $o = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $kit 'install.ps1') -Kit $kit -Root $iroot -TaskName $tn
        Assert-Eq $LASTEXITCODE 0 "install exit ($($o -join ' | '))"
        $mm = (ReadText (Join-Path $kit 'manifest.json')) | ConvertFrom-Json
        foreach ($e in $mm.files) { Assert-Eq (Sha256File (Join-Path $iroot ($e.path -replace '/', '\'))) $e.sha256 "installed $($e.path)" }
        $t = Get-ScheduledTask -TaskName $tn
        Assert-True ($null -ne $t) 'task registered'
        Assert-Match ($t.Triggers[0].CimClass.CimClassName) 'Logon' 'logon trigger'
        Assert-Match $t.Actions[0].Arguments 'watch\.cmd' 'runs the launcher'
        Assert-True ((Alive-AgeOf $iroot) -lt 6) 'the watcher is running and reports itself'
        $res = (ReadText (Join-Path $iroot 'install_result.json')) | ConvertFrom-Json
        Assert-True ([bool]$res.ok) 'install_result.json ok'
        $again = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $kit 'install.ps1') -Kit $kit -Root $iroot -TaskName $tn
        Assert-True ($LASTEXITCODE -ne 0) 'a second install over a running watcher is refused (use update)'
        $u = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $kit 'install.ps1') -Kit $kit -Root $iroot -TaskName $tn -Uninstall
        Assert-Eq $LASTEXITCODE 0 "uninstall exit ($($u -join ' | '))"
        Assert-True ($null -eq (Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue)) 'task removed'
        Assert-True (-not (Test-Path -LiteralPath (Join-Path $iroot 'src'))) 'src moved away'
        Assert-True (@(Get-ChildItem (Join-Path $iroot '_to_delete') -Directory -Filter 'uninstall_*').Count -eq 1) 'moved to _to_delete, not deleted'
    }
}
finally {
    try { Stop-TestWatcher } catch { }
    Stop-Fakes
    Get-ScheduledTask -TaskName 'napoleon_remastered watcher citest' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue
    if ($SuiteState.tz) { & tzutil.exe /s $SuiteState.tz }
    if ($script:Fail) {
        Write-Host '---- watcher.log (last 120 lines) ----'
        try { (Get-Log) -split "`r?`n" | Select-Object -Last 120 | ForEach-Object { Write-Host $_ } } catch { }
        try { Get-ChildItem (Join-Path $tmp 'inst\watcher') -Filter '*.log' -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "---- $($_.Name) ----"; Get-Content -LiteralPath $_.FullName -Tail 60 } } catch { }
    }
}
exit (Finish-Tests 'integration')
