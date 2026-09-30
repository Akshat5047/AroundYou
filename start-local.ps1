$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot 'venv\Scripts\python.exe'
$logDirectory = Join-Path $projectRoot '.ui-preview'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'The project Python environment is missing.' }

$healthy = $false
try { $healthy = (Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 3).service -eq 'Around You API' } catch {}
if (-not $healthy) {
    if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
        throw 'Port 8000 is occupied by another service. Free that port before starting Around You.'
    }
    Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'backend.stdout.log') -RedirectStandardError (Join-Path $logDirectory 'backend.stderr.log') | Out-Null
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        Start-Sleep -Seconds 2
        try { $healthy = (Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2).service -eq 'Around You API' } catch {}
        if ($healthy) { break }
    }
    if (-not $healthy) { throw 'Backend did not start. Check .ui-preview/backend.stderr.log.' }
}
if (-not (Get-NetTCPConnection -LocalPort 5500 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $pythonPath -ArgumentList @('-m','http.server','5500','--bind','127.0.0.1') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'frontend.stdout.log') -RedirectStandardError (Join-Path $logDirectory 'frontend.stderr.log') | Out-Null
}
Write-Output 'Around You backend is ready. Open http://127.0.0.1:5500/planner.html'
