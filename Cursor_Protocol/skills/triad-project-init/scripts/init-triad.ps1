# Initialize persistent Triad workflow for the current project.
# Usage: powershell -ExecutionPolicy Bypass -File .cursor/scripts/init-triad.ps1 [-Reset]

param(
    [switch]$Reset
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Get-Location
$CursorDir = Join-Path $ProjectRoot ".cursor"
$ConfigPath = Join-Path $CursorDir "triad.json"
$ScriptsDir = Join-Path $CursorDir "scripts"
$RulesDir = Join-Path $CursorDir "rules"
$SkillTemplateRule = Join-Path $env:USERPROFILE ".cursor\skills\triad-project-init\templates\triad-persistent.mdc"
$ProjectTemplateRule = Join-Path $CursorDir "templates\triad-persistent.mdc"
$ScriptTemplateRule = Join-Path $PSScriptRoot "..\templates\triad-persistent.mdc"
$TargetRule = Join-Path $RulesDir "triad-persistent.mdc"

New-Item -ItemType Directory -Force -Path $CursorDir, $ScriptsDir, $RulesDir | Out-Null

if (-not (Test-Path $TargetRule)) {
    foreach ($template in @($ProjectTemplateRule, $ScriptTemplateRule, $SkillTemplateRule)) {
        if (Test-Path $template) {
            Copy-Item $template $TargetRule
            Write-Host "Created $TargetRule"
            break
        }
    }
}

$SelfPath = Join-Path $ScriptsDir "init-triad.ps1"
if ($PSScriptRoot -ne $ScriptsDir) {
    Copy-Item (Join-Path $PSScriptRoot "init-triad.ps1") $SelfPath -Force
}

if ((Test-Path $ConfigPath) -and -not $Reset) {
    Write-Host "Triad config already exists at $ConfigPath"
    Write-Host "Use -Reset to change workflow or agent."
    Get-Content $ConfigPath
    exit 0
}

Write-Host ""
Write-Host "=== Triad Project Init ==="
Write-Host ""

Write-Host "Select workflow for this project (locked until you re-run with -Reset):"
Write-Host "  1) Full Pipeline — Thulle orchestrates Research -> Code -> Validate on every mission"
Write-Host "  2) Single Agent — work directly with one agent for the project lifetime"
Write-Host ""
$workflowChoice = Read-Host "Enter 1 or 2 [default: 1]"
if ([string]::IsNullOrWhiteSpace($workflowChoice)) { $workflowChoice = "1" }

switch ($workflowChoice) {
    "2" { $workflow = "single-agent" }
    default { $workflow = "full-pipeline" }
}

$agentMap = @{
    "1" = "thulle"
    "2" = "dominus"
    "3" = "helbrecht"
    "4" = "tyborc"
}

if ($workflow -eq "full-pipeline") {
    $activeAgent = "thulle"
    Write-Host ""
    Write-Host "Full Pipeline uses Thulle as the user-facing orchestrator."
} else {
    Write-Host ""
    Write-Host "Select agent for this project:"
    Write-Host "  1) Thulle — Orchestrator (command & clarity)"
    Write-Host "  2) Tech-Priest Dominus — Research"
    Write-Host "  3) High Marshal Helbrecht — Implementation"
    Write-Host "  4) General Tyborc — Validation"
    Write-Host ""
    $agentChoice = Read-Host "Enter 1-4 [default: 3 Helbrecht]"
    if ([string]::IsNullOrWhiteSpace($agentChoice)) { $agentChoice = "3" }
    if (-not $agentMap.ContainsKey($agentChoice)) {
        throw "Invalid agent choice: $agentChoice"
    }
    $activeAgent = $agentMap[$agentChoice]
}

$projectName = Split-Path $ProjectRoot -Leaf
$config = [ordered]@{
    version       = 1
    projectName   = $projectName
    workflow      = $workflow
    activeAgent   = $activeAgent
    locked        = $true
    initializedAt = (Get-Date).ToString("yyyy-MM-dd")
}

$config | ConvertTo-Json -Depth 3 | Set-Content -Path $ConfigPath -Encoding UTF8

Write-Host ""
Write-Host "Triad config written to $ConfigPath"
Get-Content $ConfigPath
