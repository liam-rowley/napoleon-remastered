#!/usr/bin/env bash
# purpose: screenshot of the headless virtual display (the rect headless_status.json names) through a read-only watcher job, saved as a JPEG; prints its path
# usage: harness/core/shot.sh <owner> <out.jpg>   (out path as a Windows path or a Git Bash /c/... path; the game must be running headless)
# when: before/after evidence in PC sittings (J15 console checks, J4 scenarios); no game lock needed, nothing is changed
# not-a-verb: a PC sitting helper over job.sh, run in Git Bash on the PC
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
owner="${1:?owner}"; out="${2:?out.jpg}"
win="$(cygpath -aw "$out" 2>/dev/null || echo "$out")"
status="$(cygpath -w "/c/Program Files (x86)/Steam/steamapps/common/Napoleon Total War/napoleon_remastered/headless_status.json")"
tmp="$(mktemp)"
cat > "$tmp" <<PS
#ps1
#job owner=$owner timeout=60 type=ps1
\$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class J15Dpi { [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr c); }
'@
[void][J15Dpi]::SetThreadDpiAwarenessContext([IntPtr](-4))
\$s = Get-Content -Raw -LiteralPath '$status' | ConvertFrom-Json
if (\$s.state -ne 'on_virtual') { Write-Output "SHOT FAILED: headless state is \$(\$s.state)"; exit 3 }
\$r = \$s.target.rect
\$w = [int](\$r[2] - \$r[0]); \$h = [int](\$r[3] - \$r[1])
\$bmp = New-Object System.Drawing.Bitmap \$w, \$h
\$g = [System.Drawing.Graphics]::FromImage(\$bmp)
\$g.CopyFromScreen([int]\$r[0], [int]\$r[1], 0, 0, (New-Object System.Drawing.Size \$w, \$h))
# evidence is committed: at most 1280 px wide, JPEG quality 70 (~150 KB, not ~1.2 MB at 2560x1440: J15 review)
\$ow = [Math]::Min(1280, \$w); \$oh = [int](\$h * \$ow / \$w)
\$out = New-Object System.Drawing.Bitmap \$ow, \$oh
\$go = [System.Drawing.Graphics]::FromImage(\$out)
\$go.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
\$go.DrawImage(\$bmp, 0, 0, \$ow, \$oh)
\$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { \$_.MimeType -eq 'image/jpeg' }
\$ep = New-Object System.Drawing.Imaging.EncoderParameters 1
\$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality), ([long]70)
\$out.Save('$win', \$enc, \$ep)
Write-Output "shot: $win \$ow x \$oh (from \$w x \$h at \$(\$r[0]),\$(\$r[1]))"
PS
"$BASH" "$HERE/job.sh" "$owner" "$tmp" 90; rc=$?
rm -f "$tmp"; exit $rc
