[CmdletBinding()]
param(
    [string]$ConfigPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Virtual environment not found. Run .\setup.ps1 first."
}

$ApplicationArguments = @("-m", "src.main")

if (-not [string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ResolvedConfig = (Resolve-Path -LiteralPath $ConfigPath).Path
    $ApplicationArguments += @("--config", $ResolvedConfig)
}

$ApplicationExitCode = 1
Push-Location $ProjectRoot
try {
    & $VenvPython @ApplicationArguments
    $ApplicationExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $ApplicationExitCode
