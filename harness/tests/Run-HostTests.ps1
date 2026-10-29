# purpose: run the harness host test suites (unit, integration or all) under the PowerShell that launches it and exit non-zero on any failure
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File Run-HostTests.ps1 [-Suite unit|integration|all] [-Repo <repo root>]
# when: CI job harness-windows runs it with -Suite all under Windows PowerShell 5.1; locally -Suite unit works under pwsh on Linux
# not-a-verb: a PowerShell test runner, not a repo operation
param([ValidateSet('unit', 'integration', 'all')][string]$Suite = 'all', [string]$Repo = '')
if (-not $Repo) { $Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..')) }
$rc = 0
if ($Suite -in 'unit', 'all') { & (Join-Path $PSScriptRoot 'Test-Unit.ps1') -Repo $Repo; if ($LASTEXITCODE -ne 0) { $rc = 1 } }
if ($Suite -in 'integration', 'all') { & (Join-Path $PSScriptRoot 'Test-Integration.ps1') -Repo $Repo; if ($LASTEXITCODE -ne 0) { $rc = 1 } }
exit $rc
