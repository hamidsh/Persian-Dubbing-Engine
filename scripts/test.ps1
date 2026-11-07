$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:QT_QPA_PLATFORM='offscreen'
& .\.venv\Scripts\python.exe -m pytest -q
exit $LASTEXITCODE
