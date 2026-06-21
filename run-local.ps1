# Run script for local development on Windows
$ErrorActionPreference = "Stop"

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR = Join-Path $ROOT_DIR "backend"
$FRONTEND_DIR = Join-Path $ROOT_DIR "frontend"

$backendProcess = $null
$frontendProcess = $null

# Kill a process and all of its descendants (npm -> node -> vite, uvicorn reloader -> worker, ...).
# Stop-Process alone does NOT kill children, which is how stale dev servers end up
# squatting on ports 8000/5173 after Ctrl+C.
function Stop-Tree {
    param([int]$ProcessId)
    if (-not $ProcessId) { return }
    try {
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Tree -ProcessId $_.ProcessId }
    }
    catch {}
    try { Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue } catch {}
}

# Free a TCP port by killing whatever is listening on it (plus its children).
function Clear-Port {
    param([int]$Port)
    $owners = @()
    try {
        $owners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    }
    catch {
        # Fallback for systems without the NetTCPIP module. NOTE: the loop variable is
        # intentionally NOT named $pid -- $pid is a read-only automatic variable and
        # assigning to it throws a terminating error.
        $owners = netstat -ano |
            Select-String ":$Port\s+.*LISTENING" |
            ForEach-Object { ($_.ToString() -split '\s+')[-1] } |
            Sort-Object -Unique
    }
    foreach ($procId in $owners) {
        if ("$procId" -match '^\d+$') {
            Write-Host "  Freeing port $Port (PID $procId)..." -ForegroundColor DarkGray
            Stop-Tree -ProcessId ([int]$procId)
        }
    }
}

# Cleanup function
function Cleanup {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow

    if ($backendProcess) { Stop-Tree -ProcessId $backendProcess.Id }
    if ($frontendProcess) { Stop-Tree -ProcessId $frontendProcess.Id }

    # Belt and suspenders: also clear the ports in case anything was re-parented.
    Clear-Port 8000
    Clear-Port 5173
    Write-Host "Services stopped."
}

# Register cleanup on exit
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

# Handle Ctrl+C
trap {
    Cleanup
    exit 1
}

# Kill any stale processes on our ports BEFORE we start (so we always own 8000/5173).
Write-Host "Clearing ports 8000 and 5173..." -ForegroundColor Yellow
Clear-Port 8000
Clear-Port 5173

# Start backend
Write-Host "Starting backend..." -ForegroundColor Green
$venvPython = Join-Path $BACKEND_DIR ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Backend venv not found at $venvPython" -ForegroundColor Red
    Write-Host "Run .\setup-local.ps1 first." -ForegroundColor Red
    exit 1
}
$backendProcess = Start-Process -FilePath $venvPython -ArgumentList "-m app.dev_server" -WorkingDirectory $BACKEND_DIR -PassThru
Write-Host "Backend started (PID: $($backendProcess.Id))"

# Start frontend
Write-Host "Starting frontend..." -ForegroundColor Green
$npmCmd = (Get-Command npm -ErrorAction SilentlyContinue).Source
if (-not $npmCmd) { $npmCmd = "npm.cmd" }
$frontendProcess = Start-Process -FilePath $npmCmd -ArgumentList "run dev" -WorkingDirectory $FRONTEND_DIR -PassThru
Write-Host "Frontend started (PID: $($frontendProcess.Id))"

Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop both." -ForegroundColor Yellow
Write-Host ""

# Wait for processes
while ($true) {
    if ($backendProcess.HasExited -or $frontendProcess.HasExited) {
        Write-Host "One or more services stopped." -ForegroundColor Yellow
        Cleanup
        exit 1
    }
    Start-Sleep -Seconds 1
}
