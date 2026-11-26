# SWITCHBOARD Local Development Launcher
# Starts the FastAPI backend on :8000 and the Vite React frontend on :5173.
#
# Manual commands:
#   Backend : uvicorn backend.main:app --reload --port 8000
#   Frontend: npm run dev --prefix frontend

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

Write-Host "Starting SWITCHBOARD FastAPI backend on http://localhost:8000 ..." -ForegroundColor Cyan
$BackendProcess = Start-Process -FilePath "powershell" `
    -ArgumentList "-NoExit", "-Command", "cd '$RootDir'; uvicorn backend.main:app --reload --port 8000" `
    -PassThru

Write-Host "Starting SWITCHBOARD Vite frontend on http://localhost:5173 ..." -ForegroundColor Green
try {
    npm run dev --prefix frontend
}
finally {
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        Write-Host "Stopping backend window (PID $($BackendProcess.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $BackendProcess.Id -ErrorAction SilentlyContinue
    }
}
