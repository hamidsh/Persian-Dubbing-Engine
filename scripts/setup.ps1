$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Checked { param([scriptblock]$Command) & $Command; if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE)" } }
Checked { py -3.11 -m venv .venv }
Checked { .\.venv\Scripts\python.exe -m pip install --upgrade pip }
Checked { .\.venv\Scripts\python.exe -m pip install -e '.[gui,asr,player,dev]' }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Warning 'FFmpeg missing. Install: winget install --id Gyan.FFmpeg -e ; then restart terminal.'
}
Checked { .\.venv\Scripts\pde.exe doctor }
Write-Host 'Desktop installed. Run .\run.bat. For speech, also run scripts/setup_moss.ps1.'
