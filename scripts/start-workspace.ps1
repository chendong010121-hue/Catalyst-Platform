param(
    [string]$Workspace = '',
    [ValidateRange(1024,65535)][int]$Port = 8792,
    [ValidateSet('json','sqlite')][string]$Backend = 'json',
    [ValidateSet('mock','blocked')][string]$Mode = 'mock'
)
$ErrorActionPreference = 'Stop'
$productRoot = Split-Path $PSScriptRoot -Parent
if (-not $Workspace) { $Workspace = [IO.Path]::GetFullPath((Join-Path $productRoot '../data')) }
$env:PYTHONUTF8 = '1'
Push-Location $productRoot
try {
    python -m catalyst_platform.workspace_ui --workspace $Workspace --port $Port --wiki-backend $Backend --mode $Mode
} finally {
    Pop-Location
}
