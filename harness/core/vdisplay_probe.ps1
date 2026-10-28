# purpose: PROBE ONLY: list the displays and the virtual display driver's modes, and test whether it accepts given resolutions with CDS_TEST; changes nothing and prints the vdd_settings.xml edit when a mode is missing
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File vdisplay_probe.ps1 [-Test 1920x1080,2560x1440] [-Hz 60] [-Name "Virtual Display Driver"]   (as a watcher ps1 job; exit 0 = all tested modes accepted, 3 = no unique virtual display, 6 = a mode is not offered)
# when: before headless work needs a resolution other than the driver's current one (Empire's driver offered only 3840x2160 and refused 1080p and 1440p with DISP_CHANGE_BADMODE)
# not-a-verb: runs on the PC under Windows PowerShell 5.1, outside the repo checkout
# Safety: the only ChangeDisplaySettingsEx call passes CDS_TEST (validate, never apply). It acts on the display found BY NAME, never the primary, never a by-size guess, never SetDisplayConfig (no topology change).
# Ported from empire-remastered rml_mod/tools/remote/vdisplay_mode.ps1 (-Modes / -Res -TestOnly paths); the apply paths are deliberately left out. Putting the game window on the virtual display is proxy work (J3).
param([string]$Test = '1920x1080,2560x1440', [int]$Hz = 60, [string]$Name = 'Virtual Display Driver')
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class VProbe {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct DISPLAY_DEVICE {
        public int cb;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string DeviceName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceString;
        public int StateFlags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceID;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceKey;
    }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct DEVMODE {
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmDeviceName;
        public short dmSpecVersion, dmDriverVersion, dmSize, dmDriverExtra;
        public int dmFields;
        public int dmPositionX, dmPositionY;
        public int dmDisplayOrientation, dmDisplayFixedOutput;
        public short dmColor, dmDuplex, dmYResolution, dmTTOption, dmCollate;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmFormName;
        public short dmLogPixels;
        public int dmBitsPerPel, dmPelsWidth, dmPelsHeight, dmDisplayFlags, dmDisplayFrequency;
        public int dmICMMethod, dmICMIntent, dmMediaType, dmDitherType, dmReserved1, dmReserved2, dmPanningWidth, dmPanningHeight;
    }
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern bool EnumDisplayDevices(string lpDevice, int iDevNum, ref DISPLAY_DEVICE lpDisplayDevice, int dwFlags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern bool EnumDisplaySettings(string deviceName, int modeNum, ref DEVMODE devMode);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern bool EnumDisplaySettingsEx(string deviceName, int modeNum, ref DEVMODE devMode, int dwFlags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int ChangeDisplaySettingsEx(string lpszDeviceName, ref DEVMODE lpDevMode, IntPtr hwnd, int dwflags, IntPtr lParam);
    public const int EDS_RAWMODE = 0x2, ATTACHED = 0x1, PRIMARY = 0x4, ENUM_CURRENT_SETTINGS = -1;
    public const int DM_PELSWIDTH = 0x80000, DM_PELSHEIGHT = 0x100000, DM_BITSPERPEL = 0x40000, DM_DISPLAYFREQUENCY = 0x400000, DM_DISPLAYFIXEDOUTPUT = 0x20000000;
    public const int CDS_TEST = 0x2;
}
'@
function New-DevMode { $m = New-Object VProbe+DEVMODE; $m.dmSize = [int16][Runtime.InteropServices.Marshal]::SizeOf([type][VProbe+DEVMODE]); $m }
function Dcs([int]$rc) { switch ($rc) { 0 { 'DISP_CHANGE_SUCCESSFUL' } 1 { 'DISP_CHANGE_RESTART' } -1 { 'DISP_CHANGE_FAILED' } -2 { 'DISP_CHANGE_BADMODE' } -3 { 'DISP_CHANGE_NOTUPDATED' } -4 { 'DISP_CHANGE_BADFLAGS' } -5 { 'DISP_CHANGE_BADPARAM' } default { "code $rc" } } }
$displays = @()
for ($i = 0; $i -lt 64; $i++) {
    $dd = New-Object VProbe+DISPLAY_DEVICE; $dd.cb = [Runtime.InteropServices.Marshal]::SizeOf([type][VProbe+DISPLAY_DEVICE])
    if (-not [VProbe]::EnumDisplayDevices([NullString]::Value, $i, [ref]$dd, 0)) { break }
    if (-not ($dd.StateFlags -band [VProbe]::ATTACHED)) { continue }
    $md = New-Object VProbe+DISPLAY_DEVICE; $md.cb = $dd.cb
    $mon = ''; if ([VProbe]::EnumDisplayDevices($dd.DeviceName, 0, [ref]$md, 0)) { $mon = $md.DeviceString }
    $cur = New-DevMode; [void][VProbe]::EnumDisplaySettings($dd.DeviceName, [VProbe]::ENUM_CURRENT_SETTINGS, [ref]$cur)
    $displays += [pscustomobject]@{ Device = $dd.DeviceName; Adapter = $dd.DeviceString; Monitor = $mon; Primary = [bool]($dd.StateFlags -band [VProbe]::PRIMARY); W = $cur.dmPelsWidth; H = $cur.dmPelsHeight; Hz = $cur.dmDisplayFrequency; X = $cur.dmPositionX; Y = $cur.dmPositionY }
}
Write-Output "displays ($($displays.Count) attached):"
foreach ($d in $displays) { Write-Output ("  {0,-14} {1}x{2}@{3}Hz at {4},{5}{6}  adapter='{7}' monitor='{8}'" -f $d.Device, $d.W, $d.H, $d.Hz, $d.X, $d.Y, $(if ($d.Primary) { ' PRIMARY' } else { '' }), $d.Adapter, $d.Monitor) }
$byName = @($displays | Where-Object { -not $_.Primary -and ($_.Adapter -like "*$Name*" -or $_.Monitor -like "*$Name*") })
if ($byName.Count -ne 1) {
    Write-Output "NO UNIQUE VIRTUAL DISPLAY: $($byName.Count) non-primary display(s) match '$Name' (driver not installed, disabled, or primary). Nothing was changed."
    exit 3
}
$target = $byName[0]
Write-Output "target: $($target.Device) (non-primary, matched by name '$Name'); current mode $($target.W)x$($target.H)@$($target.Hz)Hz"
$have = @{}
foreach ($flag in 0, [VProbe]::EDS_RAWMODE) {
    $seen = @{}
    for ($n = 0; $n -lt 8192; $n++) {
        $m = New-DevMode
        if (-not [VProbe]::EnumDisplaySettingsEx($target.Device, $n, [ref]$m, $flag)) { break }
        $seen["{0}x{1}@{2}/{3}bpp" -f $m.dmPelsWidth, $m.dmPelsHeight, $m.dmDisplayFrequency, $m.dmBitsPerPel] = 1
        $have["{0}x{1}" -f $m.dmPelsWidth, $m.dmPelsHeight] = 1
    }
    Write-Output ("mode list ({0}, {1} modes): {2}" -f $(if ($flag) { 'EDS_RAWMODE' } else { 'normal' }), $seen.Count, (($seen.Keys | Sort-Object) -join ' '))
}
$missing = @()
foreach ($res in ($Test -split ',')) {
    $res = $res.Trim(); if (-not $res) { continue }
    if ($res -notmatch '^(\d+)x(\d+)$') { Write-Output "skipped '$res': want WxH"; continue }
    $w = [int]$Matches[1]; $h = [int]$Matches[2]
    foreach ($fx in 0, 1, 2) {   # 0 = driver mode as is, 1 = GPU stretch, 2 = GPU centre
        $dm = New-DevMode
        [void][VProbe]::EnumDisplaySettings($target.Device, [VProbe]::ENUM_CURRENT_SETTINGS, [ref]$dm)
        $dm.dmPelsWidth = $w; $dm.dmPelsHeight = $h; $dm.dmDisplayFrequency = $Hz; $dm.dmBitsPerPel = 32
        $dm.dmFields = [VProbe]::DM_PELSWIDTH -bor [VProbe]::DM_PELSHEIGHT -bor [VProbe]::DM_DISPLAYFREQUENCY -bor [VProbe]::DM_BITSPERPEL
        if ($fx -ne 0) { $dm.dmDisplayFixedOutput = $fx; $dm.dmFields = $dm.dmFields -bor [VProbe]::DM_DISPLAYFIXEDOUTPUT }
        $rc = [VProbe]::ChangeDisplaySettingsEx($target.Device, [ref]$dm, [IntPtr]::Zero, [VProbe]::CDS_TEST, [IntPtr]::Zero)   # CDS_TEST: validate only, nothing is applied
        Write-Output ("CDS_TEST({0}, {1}x{2}@{3}, fixed_output {4}) -> {5} ({6})" -f $target.Device, $w, $h, $Hz, $fx, $rc, (Dcs $rc))
        if ($fx -eq 0 -and $rc -ne 0) { $missing += "${w}x${h}" }
    }
}
$post = New-DevMode; [void][VProbe]::EnumDisplaySettings($target.Device, [VProbe]::ENUM_CURRENT_SETTINGS, [ref]$post)
if ($post.dmPelsWidth -ne $target.W -or $post.dmPelsHeight -ne $target.H -or $post.dmDisplayFrequency -ne $target.Hz) { Write-Output "WARNING: the target's mode changed during the probe (should be impossible with CDS_TEST)" }
else { Write-Output "unchanged: $($target.Device) is still $($post.dmPelsWidth)x$($post.dmPelsHeight)@$($post.dmDisplayFrequency)Hz" }
if ($missing.Count) {
    Write-Output ''
    Write-Output "NOT OFFERED by the driver: $($missing -join ', '). The change for Liam (administrator; agents never do this):"
    Write-Output '  1. Open Notepad as administrator, open C:\VirtualDisplayDriver\vdd_settings.xml.'
    Write-Output '  2. Inside <resolutions>...</resolutions> add one block per missing size, keeping the existing 3840x2160 blocks:'
    foreach ($m in ($missing | Select-Object -Unique)) {
        $p = $m -split 'x'
        Write-Output "       <resolution><width>$($p[0])</width><height>$($p[1])</height><refresh_rate>$Hz</refresh_rate></resolution>"
    }
    Write-Output '  3. The file must still start with <?xml as its very first characters (no blank line before it). Save.'
    Write-Output '  4. VDD Control -> Reload driver (or Device Manager: disable, enable the Virtual Display Driver). Reboot if nothing changes.'
    Write-Output '  5. Run this probe again.'
    exit 6
}
Write-Output 'all tested modes are offered by the driver'
exit 0
