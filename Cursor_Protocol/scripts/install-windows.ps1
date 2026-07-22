# Install Triad protocol from this repo into ~/.cursor (Windows).
param()

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProtoRoot = Resolve-Path (Join-Path $ScriptDir "..")
$CursorHome = Join-Path $env:USERPROFILE ".cursor"

Write-Host "Installing Triad protocol from:"
Write-Host "  $ProtoRoot"
Write-Host "To:"
Write-Host "  $CursorHome"
Write-Host ""

New-Item -ItemType Directory -Force -Path `
    (Join-Path $CursorHome "skills"), `
    (Join-Path $CursorHome "rules"), `
    (Join-Path $CursorHome "scripts") | Out-Null

Copy-Item (Join-Path $ProtoRoot "triad-default.json") (Join-Path $CursorHome "triad-default.json") -Force
Copy-Item (Join-Path $ProtoRoot "rules\triad-global-default.mdc") (Join-Path $CursorHome "rules\triad-global-default.mdc") -Force

$pipelineSrc = Join-Path $ProtoRoot "skills\research-code-validate-pipeline"
$pipelineDst = Join-Path $CursorHome "skills\research-code-validate-pipeline"
if (Test-Path $pipelineDst) { Remove-Item $pipelineDst -Recurse -Force }
Copy-Item $pipelineSrc $pipelineDst -Recurse -Force

$initSrc = Join-Path $ProtoRoot "skills\triad-project-init"
$initDst = Join-Path $CursorHome "skills\triad-project-init"
if (Test-Path $initDst) { Remove-Item $initDst -Recurse -Force }
Copy-Item $initSrc $initDst -Recurse -Force

Copy-Item (Join-Path $ProtoRoot "scripts\apply-triad-user-rules.py") (Join-Path $CursorHome "scripts\apply-triad-user-rules.py") -Force

Write-Host "Installed Triad protocol. Reload Cursor, then optionally run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File Cursor_Protocol\skills\triad-project-init\scripts\init-triad.ps1"
