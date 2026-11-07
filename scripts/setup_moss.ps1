param([string]$TorchIndex='https://download.pytorch.org/whl/cu128')
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Checked { param([scriptblock]$Command) & $Command; if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE)" } }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git for Windows first.' }
New-Item -ItemType Directory -Force external | Out-Null
if (-not (Test-Path external/MOSS-TTS)) {
    Checked { git clone https://github.com/OpenMOSS/MOSS-TTS.git external/MOSS-TTS }
    Checked { git -C external/MOSS-TTS checkout 934d6826b084c46a0d033402174d5f8ac4ed2519 }
} else {
    $commit = & git -C external/MOSS-TTS rev-parse HEAD
    if ($commit -ne '934d6826b084c46a0d033402174d5f8ac4ed2519') { throw 'Existing MOSS checkout has another revision. Preserve your edits; configure it manually or rename the folder.' }
}
Checked { py -3.11 -m venv .venv-moss }
$python=(Resolve-Path .venv-moss/Scripts/python.exe).Path
Checked { & $python -m pip install --upgrade pip }
Checked { & $python -m pip install torch==2.9.1 torchaudio==2.9.1 --index-url $TorchIndex }
Checked { & $python -m pip install -e external/MOSS-TTS }
Checked { & $python -m pip install 'transformers==5.0.0' 'peft>=0.18,<0.19' 'accelerate>=1.10,<2' 'soundfile>=0.12,<1' }
Checked { & $python -m pip check }
Checked { & $python -c "import torch; assert torch.cuda.is_available(), 'CUDA unavailable; check NVIDIA driver'; print(torch.cuda.get_device_name())" }
Checked { .\.venv\Scripts\python.exe scripts/configure.py moss $python (Resolve-Path external/MOSS-TTS).Path }
Write-Host 'MOSS configured. First synthesis downloads base, LoRA and codec weights; allow ample disk space.'
