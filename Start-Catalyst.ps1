param(
    [int]$Port = 8817,
    [string]$Workspace = (Join-Path $env:LOCALAPPDATA 'Catalyst/Desktop'),
    [string]$ProjectConfig,
    [switch]$NoOpen
)
$ErrorActionPreference = 'Stop'
$python = (Get-Command python -ErrorAction Stop).Source
$base = "http://127.0.0.1:$Port"
$commit = (git -C $PSScriptRoot rev-parse HEAD).Trim()
if (git -C $PSScriptRoot status --porcelain --untracked-files=no) {
    throw 'The desktop launcher requires a clean committed checkout.'
}
function Get-PathIdentity([string]$Path) {
    (& $python -c 'import hashlib,os,sys; from pathlib import Path; print(hashlib.sha256(os.path.normcase(str(Path(sys.argv[1]).resolve())).encode()).hexdigest())' $Path).Trim()
}
$workspaceId = Get-PathIdentity $Workspace
$sourceRootId = Get-PathIdentity $PSScriptRoot
function Read-Status {
    try { Invoke-RestMethod "$base/api/workspace" -TimeoutSec 2 } catch { $null }
}
$status = Read-Status
if (-not $status) {
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $Port belongs to another service."
    }
    New-Item -ItemType Directory -Path $Workspace -Force | Out-Null
    $arguments = @('-m','catalyst_platform.workspace_ui','--workspace',('"{0}"' -f $Workspace),'--port',"$Port")
    if ($ProjectConfig) {
        $configPath = (Resolve-Path -LiteralPath $ProjectConfig).Path
        $arguments += @('--project-config',('"{0}"' -f $configPath))
    }
    $env:PYTHONUTF8 = '1'
    $process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru
    for ($i = 0; $i -lt 40; $i++) {
        if ($process.HasExited) { throw 'Catalyst service exited during startup.' }
        $status = Read-Status
        if ($status) { break }
        Start-Sleep -Milliseconds 250
    }
}
if (-not $status -or $status.source_identity.commit -ne $commit -or $status.source_root_id -ne $sourceRootId -or $status.workspace_id -ne $workspaceId) {
    throw "Port $Port did not return the expected Catalyst build and workspace. No existing process was stopped."
}
if (-not $NoOpen) { Start-Process "$base/" }
Write-Output "CATALYST_READY $base/ $commit"
