# Setup script for local development on Windows
$ErrorActionPreference = "Stop"

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR = Join-Path $ROOT_DIR "backend"
$FRONTEND_DIR = Join-Path $ROOT_DIR "frontend"

Write-Host "Setting up backend..." -ForegroundColor Green

# Create Python virtual environment
Push-Location $BACKEND_DIR

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment"
    }
}

# Set up paths for the venv Python
$pythonPath = Join-Path (Get-Location) ".venv\Scripts\python.exe"
$pipPath = Join-Path (Get-Location) ".venv\Scripts\pip.exe"

if (-not (Test-Path $pythonPath)) {
    throw "Virtual environment creation failed or incomplete"
}

Write-Host "Upgrading pip..."
& $pythonPath -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip"
}

Write-Host "Installing Python dependencies..."
& $pipPath install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Python requirements"
}

Pop-Location

Write-Host "Setting up frontend..." -ForegroundColor Green

Push-Location $FRONTEND_DIR

Write-Host "Installing npm dependencies..."
npm install
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install npm dependencies"
}

# Setup .env file
if ((Test-Path ".env.example") -and -not (Test-Path ".env")) {
    Write-Host "Copying .env.example to .env..."
    Copy-Item ".env.example" ".env"
}

# Update or add VITE_API_BASE
$envFile = ".env"
$apiBase = "VITE_API_BASE=http://localhost:8000/api"

if (Test-Path $envFile) {
    $content = Get-Content $envFile -Raw
    if ($content -match '^VITE_API_BASE=') {
        $content = $content -replace '^VITE_API_BASE=.*$', $apiBase
    }
    else {
        $content += "`n$apiBase"
    }
    Set-Content $envFile $content
}

Pop-Location

Write-Host "Local setup complete." -ForegroundColor Green
