# J96 read-only frame grab: copies the headless game rect (the rect headless_status.json names, as core/harness/shot.sh does) about 4 times a second, so a
# load of a few seconds is caught where shot.sh, at one shot in about 3 s through the watcher queue, misses it. Touches nothing; stops after $Seconds or when $Stop exists.
# Use: powershell -File grab.ps1 -Out <dir> -Stop <file> -Seconds <n>
param([string]$Out, [string]$Stop, [int]$Seconds = 400, [int]$Width = 640)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class J96Dpi { [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr c); }
'@
[void][J96Dpi]::SetThreadDpiAwarenessContext([IntPtr](-4))
$status = 'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\napoleon_remastered\headless_status.json'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$end = (Get-Date).AddSeconds($Seconds)
$n = 0
while ((Get-Date) -lt $end -and -not (Test-Path -LiteralPath $Stop)) {
    try {
        $s = Get-Content -Raw -LiteralPath $status | ConvertFrom-Json
        if ($s.state -eq 'on_virtual') {
            $r = $s.target.rect
            $w = [int]($r[2] - $r[0]); $h = [int]($r[3] - $r[1])
            $bmp = New-Object System.Drawing.Bitmap $w, $h
            $g = [System.Drawing.Graphics]::FromImage($bmp)
            $g.CopyFromScreen([int]$r[0], [int]$r[1], 0, 0, (New-Object System.Drawing.Size $w, $h))
            $th = [int]($h * $Width / $w)
            $small = New-Object System.Drawing.Bitmap $bmp, $Width, $th
            $n++
            $small.Save((Join-Path $Out ('f{0:D5}_{1}.jpg' -f $n, (Get-Date).ToUniversalTime().ToString('HHmmssfff'))), [System.Drawing.Imaging.ImageFormat]::Jpeg)
            $small.Dispose(); $g.Dispose(); $bmp.Dispose()
        }
    } catch { }
    Start-Sleep -Milliseconds 200
}
Write-Output "grab: $n frames"
