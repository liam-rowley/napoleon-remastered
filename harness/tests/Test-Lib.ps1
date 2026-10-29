# purpose: tiny shared test kit for the harness host tests (Test-Case, assertions, Wait-Until, temp folders, a test adapter); dot-sourced by Test-Unit.ps1 and Test-Integration.ps1
# usage: . "$PSScriptRoot\Test-Lib.ps1"   (not run on its own)
# when: only from the harness host tests; ASCII only, no Pester (Windows PowerShell 5.1 ships Pester 3 and the runner another)
# not-a-verb: a dot-sourced PowerShell library for the host tests
$script:Pass = 0
$script:Fail = 0
$script:Failures = @()
function Test-Case([string]$name, [scriptblock]$body) {
    Write-Host "START $((Get-Date).ToUniversalTime().ToString('HH:mm:ss'))Z $name"   # a hang shows which test it was in (J2 CI round 8 was cancelled with no log)
    try { & $body | Out-Null; Write-Host "PASS  $name"; $script:Pass++ }
    catch { Write-Host "FAIL  $name : $($_.Exception.Message)"; $script:Fail++; $script:Failures += $name }
}
function Assert-True($cond, [string]$msg) { if (-not $cond) { throw "assertion failed: $msg" } }
function Assert-Eq($actual, $expected, [string]$msg) { if ("$actual" -ne "$expected") { throw "$msg : expected [$expected] but got [$actual]" } }
function Short([string]$t) { if ($t.Length -gt 300) { return $t.Substring(0, 300) + '...' } else { return $t } }
function Assert-Match([string]$text, [string]$rx, [string]$msg) { if ($text -notmatch $rx) { throw "$msg : [$(Short $text)] does not match /$rx/" } }
function Assert-NotMatch([string]$text, [string]$rx, [string]$msg) { if ($text -match $rx) { throw "$msg : matched [$($Matches[0])] /$rx/" } }
function Wait-Until([scriptblock]$cond, [int]$secs, [string]$what) {
    $deadline = (Get-Date).AddSeconds($secs)
    while ((Get-Date) -lt $deadline) { $r = & $cond; if ($r) { return $r }; Start-Sleep -Milliseconds 300 }
    throw "timed out after $secs s waiting for: $what"
}
function New-Tmp([string]$tag) {
    $base = $env:RUNNER_TEMP; if (-not $base) { $base = [IO.Path]::GetTempPath() }
    $d = Join-Path $base ("wt_{0}_{1}" -f $tag, ([Guid]::NewGuid().ToString('N').Substring(0, 8)))
    New-Item -ItemType Directory -Path $d -Force | Out-Null
    return $d
}
$Utf8NoBom = New-Object Text.UTF8Encoding $false
function Sha256File([string]$p) { return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() }
# A test adapter: fake game and AppData folders under $dir, the real config-file table (same ids as harness/napoleon/adapter.json).
function New-TestAdapter([string]$dir, [string]$gameImage = 'Napoleon.exe', [string]$otherImage = 'Empire.exe', [string]$launchArgs = '') {
    $game = Join-Path $dir 'game'; $app = Join-Path $dir 'appdata'
    foreach ($d in @($game, (Join-Path $app 'scripts'), (Join-Path $game 'logs'))) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    $adapter = [ordered]@{
        game = 'testgame'; title = 'Test Game'; state_dir = $dir; watcher_subdir = 'watcher'; device_mount = 'x'; task_name = 'napoleon_remastered watcher citest'
        game_dir = $game; appdata_dir = $app; game_image = $gameImage; other_images = @($otherImage)
        launch = [ordered]@{ route = 'exe'; exe = $gameImage; args = $launchArgs; steam_uri = ''; steam_wait_s = 5 }
        heartbeat_files = @('logs\proxy.log')
        archive = [ordered]@{ dirs_log = @('logs'); dirs_dump = @('dumps'); files = @('napoleon_remastered.ini', 'dxvk.conf') }
        foreign_locks = @((Join-Path $dir 'foreign\game.lock'))
        config_files = @(
            [ordered]@{ id = 'prefs'; anchor = 'appdata'; path = 'scripts\preferences.script.txt'; style = 'none' },
            [ordered]@{ id = 'keys'; anchor = 'appdata'; path = 'custom_keys.keys.xml'; style = 'none' },
            [ordered]@{ id = 'battle_prefs'; anchor = 'appdata'; path = 'battle_preferences\.sp_default.battle_preferences'; style = 'none' },
            [ordered]@{ id = 'mod_ini'; anchor = 'game'; path = 'napoleon_remastered.ini'; style = 'ini' },
            [ordered]@{ id = 'dxvk_conf'; anchor = 'game'; path = 'dxvk.conf'; style = 'conf' }
        )
    }
    $path = Join-Path $dir 'adapter.json'
    [IO.File]::WriteAllText($path, ($adapter | ConvertTo-Json -Depth 6), $Utf8NoBom)
    return $path
}
function Finish-Tests([string]$suite) {
    Write-Host ''
    Write-Host "$suite : $($script:Pass) passed, $($script:Fail) failed"
    if ($script:Fail) { Write-Host ('FAILED: ' + ($script:Failures -join '; ')) }
    return $script:Fail
}
