$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Checked { param([scriptblock]$Command) & $Command; if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE)" } }
New-Item -ItemType Directory -Force external | Out-Null
if (-not (Test-Path external/seed-vc)) {
    Checked { git clone https://github.com/Plachtaa/seed-vc.git external/seed-vc }
    Checked { git -C external/seed-vc checkout 51383efd921027683c89e5348211d93ff12ac2a8 }
} else {
    $commit = & git -C external/seed-vc rev-parse HEAD
    if ($commit -ne '51383efd921027683c89e5348211d93ff12ac2a8') { throw 'Seed checkout differs. Preserve existing work; configure manually or rename folder.' }
}
Checked { py -3.11 -m venv .venv-seed }
$python=(Resolve-Path .venv-seed/Scripts/python.exe).Path
Checked { & $python -m pip install --upgrade pip }
Checked { & $python -m pip install -r scripts/requirements-seed.txt }
# Reinstall the matching CUDA pair after upstream requirements; isolated from MOSS.
Checked { & $python -m pip install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu124 }
Checked { & $python -m pip check }
Checked { .\.venv\Scripts\python.exe scripts/configure.py seed $python (Resolve-Path external/seed-vc).Path }
Write-Host 'Seed configured. Its upstream Windows/GPU compatibility must be tested on your system.'
