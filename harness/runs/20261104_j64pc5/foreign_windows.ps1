# Read-only observer for J64's acceptance run: logs visible top-level windows overlapping the virtual display's rect, and any Empire.exe, on change,
# and free memory and CPU load once a minute. win_probe lists only the game's own windows. Touches nothing. Stops when $Stop exists or after $MaxMinutes.
# Use: powershell -NoProfile -ExecutionPolicy Bypass -File foreign_windows.ps1 -Log <file> -Stop <file that does not exist yet>; recipe: jobs/J64/report.md, Open question 7.
param([string]$Log, [string]$Stop, [int]$MaxMinutes = 240, [int]$X = 2560, [int]$Y = 1440, [int]$W = 3840, [int]$H = 2160)
Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public static class FW {
  public delegate bool P(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(P cb, IntPtr l);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern int GetWindowThreadProcessId(IntPtr h, out int p);
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr c);
  [DllImport("dwmapi.dll")] static extern int DwmGetWindowAttribute(IntPtr h, int a, out int v, int s);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L, T, Rt, B; }
  public static List<string> Scan(int x, int y, int w, int h) {
    var o = new List<string>(); IntPtr fg = GetForegroundWindow();
    EnumWindows(delegate(IntPtr a, IntPtr l) {
      if (!IsWindowVisible(a) || IsIconic(a)) return true;
      int c = 0; DwmGetWindowAttribute(a, 14, out c, 4); if (c != 0) return true;
      R r; if (!GetWindowRect(a, out r)) return true;
      if (r.Rt - r.L <= 1 || r.B - r.T <= 1) return true;
      if (r.Rt <= x || r.L >= x + w || r.B <= y || r.T >= y + h) return true;
      var s = new StringBuilder(256); GetWindowText(a, s, 256); int p; GetWindowThreadProcessId(a, out p);
      string n = "?"; try { n = System.Diagnostics.Process.GetProcessById(p).ProcessName; } catch {}
      o.Add(n + " pid=" + p + " title=[" + s + "] rect=" + r.L + "," + r.T + "," + r.Rt + "," + r.B + (a == fg ? " FOREGROUND" : ""));
      return true; }, IntPtr.Zero);
    o.Sort(); return o; }
}
"@
[void][FW]::SetProcessDpiAwarenessContext([IntPtr](-4))
$end = (Get-Date).AddMinutes($MaxMinutes); $last = ''; $tick = 0
"$((Get-Date).ToUniversalTime().ToString('s'))Z start rect=$X,$Y ${W}x$H" | Add-Content -Encoding utf8 $Log
while ((Get-Date) -lt $end -and -not (Test-Path $Stop)) {
  $l = @([FW]::Scan($X, $Y, $W, $H) | Where-Object { $_ -notmatch '^Napoleon pid=' })
  $e = @(Get-Process -Name Empire -ErrorAction SilentlyContinue | ForEach-Object { "Empire.exe pid=$($_.Id) started=$($_.StartTime.ToUniversalTime().ToString('s'))Z parent=$((Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").ParentProcessId)" })
  $cur = (($l + $e) -join "`n")
  if ($cur -ne $last) { "$((Get-Date).ToUniversalTime().ToString('s'))Z ---`n$cur" | Add-Content -Encoding utf8 $Log; $last = $cur }
  if ($tick % 30 -eq 0) {
    $os = Get-CimInstance Win32_OperatingSystem
    $cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
    "$((Get-Date).ToUniversalTime().ToString('s'))Z load free_gb=$([math]::Round($os.FreePhysicalMemory / 1MB, 1)) cpu_pct=$cpu" | Add-Content -Encoding utf8 $Log
  }
  $tick++
  Start-Sleep -Seconds 2
}
"$((Get-Date).ToUniversalTime().ToString('s'))Z stop" | Add-Content -Encoding utf8 $Log
