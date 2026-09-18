[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Push-Location $ProjectRoot
try {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
            throw "Install 64-bit Python 3.14 with the Python launcher, then rerun setup."
        }

        & py -3.14 -c "import struct; import sys; sys.exit(0 if struct.calcsize('P') == 8 else 1)"
        if ($LASTEXITCODE -ne 0) {
            throw "64-bit Python 3.14 is required by this setup script."
        }

        & py -3.14 -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Virtual environment creation failed."
        }
    }

    & $VenvPython -c "import struct; import sys; sys.exit(0 if sys.version_info[:2] == (3, 14) and struct.calcsize('P') == 8 else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "The existing .venv must use 64-bit Python 3.14. Rename it and rerun setup."
    }

    & $VenvPython -m pip install --requirement requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }

    & $VenvPython -m pip check
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency compatibility checks failed."
    }

    Write-Host ""
    Write-Host "SYMBIOTE GHOST dependencies installed."
    Write-Host "Run tests: .\.venv\Scripts\python.exe -m unittest discover -s tests -v"
    Write-Host "Run app:   .\run.ps1"
}
finally {
    Pop-Location
}
