$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$Url = "http://127.0.0.1:8000"

function Test-ServerReady {
    try {
        Invoke-WebRequest `
            -Uri "$Url/api/settings" `
            -TimeoutSec 2 `
            -UseBasicParsing | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

if (-not (Test-Path $Python)) {
    Write-Host "Linkzen virtual environment is missing: $Python"
    Write-Host ""
    Write-Host "Create it with:"
    Write-Host "  python -m venv .venv"
    Write-Host ""
    Write-Host "Then install dependencies with:"
    Write-Host "  .venv\Scripts\python.exe -m pip install -r requirements.txt"
    Read-Host "Press Enter to close"
    exit 1
}

if (Test-ServerReady) {
    Write-Host "Linkzen is already running at $Url"
    Start-Process $Url
    Read-Host "Press Enter to close"
    exit 0
}

Set-Location $ProjectDir

$ServerProcess = Start-Process `
    -FilePath $Python `
    -ArgumentList "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000" `
    -PassThru

try {
    Write-Host "Starting Linkzen..."

    for ($attempt = 1; $attempt -le 120; $attempt++) {
        if (Test-ServerReady) {
            Write-Host "Linkzen is ready at $Url"
            Start-Process $Url
            Write-Host "Keep this window open while using Linkzen. Press Ctrl+C to stop the server."
            Wait-Process -Id $ServerProcess.Id
            exit $ServerProcess.ExitCode
        }

        if ($ServerProcess.HasExited) {
            exit $ServerProcess.ExitCode
        }

        Start-Sleep -Seconds 1
    }

    Write-Host "Linkzen did not become ready within 120 seconds."
    Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
finally {
    if (-not $ServerProcess.HasExited) {
        Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
    }
}