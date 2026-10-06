# Start the project-local DB, then API and Vite in hidden processes.
$ErrorActionPreference = 'Stop'
$appRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonExe = Join-Path $appRoot '.venv/Scripts/python.exe'
Push-Location $appRoot
try {
    & $pythonExe scripts/database-tools.py start
    if ($LASTEXITCODE -ne 0) { throw 'The local database did not start.' }
    foreach ($entry in @(@{Port=8871;Name='API'},@{Port=5173;Name='preview'})) {
        $connection = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $entry.Port -State Listen -ErrorAction SilentlyContinue
        if ($connection) { Write-Host "Port $($entry.Port) is already listening. Reusing the running $($entry.Name); verify /api/health."; continue }
        if ($entry.Port -eq 8871) {
            Start-Process -FilePath $pythonExe -ArgumentList '-m uvicorn server.app:app --host 127.0.0.1 --port 8871' -WorkingDirectory $appRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $appRoot '.local/api.log') -RedirectStandardError (Join-Path $appRoot '.local/api-error.log') | Out-Null
        } else {
            $nodeExe = (Get-Command node.exe).Source
            Start-Process -FilePath $nodeExe -ArgumentList 'node_modules/vite/bin/vite.js --host 127.0.0.1' -WorkingDirectory $appRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $appRoot '.local/vite.log') -RedirectStandardError (Join-Path $appRoot '.local/vite-error.log') | Out-Null
        }
    }
    if (Test-Path (Join-Path $appRoot '.local/models/all-MiniLM-L6-v2/modules.json')) {
        $runningWorker = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$pythonExe*" -and $_.CommandLine -like '*-m server.worker*' }
        if (-not $runningWorker) {
            Start-Process -FilePath $pythonExe -ArgumentList '-m server.worker' -WorkingDirectory $appRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $appRoot '.local/worker.log') -RedirectStandardError (Join-Path $appRoot '.local/worker-error.log') | Out-Null
            foreach ($attempt in 1..10) {
                Start-Sleep -Milliseconds 500
                $runningWorker = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$pythonExe*" -and $_.CommandLine -like '*-m server.worker*' }
                if ($runningWorker) { break }
            }
            if (-not $runningWorker) { throw 'The knowledge worker did not stay running. Check .local/worker-error.log.' }
        }
    }
    $healthy = $false
    foreach ($attempt in 1..10) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:5173/api/health' -TimeoutSec 2
            if ($health.runtime -eq 'local' -and $health.database.engine -eq 'postgresql' -and $health.database.status -eq 'ok') { $healthy = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    if (-not $healthy) { throw 'The preview/API health check failed. Check the local log files and confirm the listening ports belong to H4T Bot.' }
    Write-Host 'Local preview ready: http://127.0.0.1:5173/ — PostgreSQL health verified.'
} finally { Pop-Location }
