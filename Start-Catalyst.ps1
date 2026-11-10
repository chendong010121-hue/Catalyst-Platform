param(
    [int]$Port = 8827,
    [string]$Workspace = (Join-Path $env:LOCALAPPDATA 'Catalyst/Desktop'),
    [string]$WikiExport,
    [switch]$NoOpen
)
$ErrorActionPreference = 'Stop'
$python = (Get-Command python -ErrorAction Stop).Source
$base = "http://127.0.0.1:$Port"
$commit = (git -C $PSScriptRoot rev-parse HEAD).Trim()
if (git -C $PSScriptRoot status --porcelain --untracked-files=no) {
    throw 'The desktop launcher requires a clean committed checkout.'
}
$workspaceId = (& $python -c 'import hashlib,os,sys; from pathlib import Path; print(hashlib.sha256(os.path.normcase(str(Path(sys.argv[1]).resolve())).encode()).hexdigest())' $Workspace).Trim()
function Read-Status {
    try { Invoke-RestMethod "$base/api/status" -TimeoutSec 2 } catch { $null }
}
$status = Read-Status
if (-not $status) {
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $Port belongs to another service."
    }
    New-Item -ItemType Directory -Path $Workspace -Force | Out-Null
    $arguments = @('-m','catalyst_platform.desktop','--workspace',('"{0}"' -f $Workspace),'--port',"$Port")
    if ($WikiExport) {
        $exportPath = (Resolve-Path -LiteralPath $WikiExport).Path
        $arguments += @('--wiki-export',('"{0}"' -f $exportPath))
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
if (-not $status -or $status.build.commit -ne $commit -or $status.workspace_id -ne $workspaceId -or -not $status.connection) {
    throw "Port $Port did not return the expected Catalyst build and workspace. No existing process was stopped."
}
if ([bool]$WikiExport -ne ($status.available_tools -contains 'wiki_search')) {
    throw 'The existing service has a different Wiki configuration. Use another port or restart that service explicitly.'
}
if (-not $NoOpen) { Start-Process "$base/" }
Write-Output "CATALYST_READY $base/ $commit"
