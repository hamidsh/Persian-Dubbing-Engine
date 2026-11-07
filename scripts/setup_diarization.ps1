$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Checked { param([scriptblock]$Command) & $Command; if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE)" } }
Checked { py -3.11 -m venv .venv-diarization }
$python=(Resolve-Path .venv-diarization/Scripts/python.exe).Path
Checked { & $python -m pip install --upgrade pip }
Checked { & $python -m pip install 'pyannote.audio>=4,<5' soundfile }
Checked { & $python -m pip check }
Checked { .\.venv\Scripts\python.exe scripts/configure.py diarization $python }
Write-Host 'Accept community-1 model terms on Hugging Face and set HF_TOKEN in the launch terminal.'
