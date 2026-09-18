$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Assert-Exit($Stage) { if ($LASTEXITCODE -ne 0) { throw "$Stage failed. Review the error above." } }
py -3.12 --version
Assert-Exit "Python version check"
node -e "const [a,b]=process.versions.node.split('.').map(Number); if(a<22 || (a===22 && b<12)){console.error('Node 22.12 or newer required');process.exit(1)}"
Assert-Exit "Node version check"
py -3.12 -m venv backend/.venv
Assert-Exit "Virtual environment creation"
& .\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Assert-Exit "Python package installation"
& .\backend\.venv\Scripts\python.exe scripts/configure.py
Assert-Exit "Environment configuration"
Push-Location frontend
try { npm.cmd ci; Assert-Exit "Frontend dependency installation" } finally { Pop-Location }
Write-Host "Setup complete. Run .\start-backend.ps1 and .\start-frontend.ps1 in separate terminals."
