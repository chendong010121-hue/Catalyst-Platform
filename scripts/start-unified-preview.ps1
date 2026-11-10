param(
    [string]$Workspace = '',
    [ValidateRange(1024,65535)][int]$Port = 8800,
    [ValidateSet('json','sqlite')][string]$Backend = 'json'
)
$ErrorActionPreference = 'Stop'
$productRoot = Split-Path $PSScriptRoot -Parent
if (-not $Workspace) { $Workspace = [IO.Path]::GetFullPath((Join-Path $productRoot '../preview-workspace')) }
Write-Host 'Catalyst unified qualification preview: execution BLOCKED; no model credentials loaded.'
Write-Host 'Synthetic acceptance evidence only; this is not a Live model qualification.'
& (Join-Path $PSScriptRoot 'start-workspace.ps1') -Workspace $Workspace -Port $Port -Backend $Backend -Mode blocked
