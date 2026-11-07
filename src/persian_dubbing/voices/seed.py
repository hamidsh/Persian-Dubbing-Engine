from pathlib import Path
import tempfile
from persian_dubbing.core.process import run
from persian_dubbing.media.audio import conform
from persian_dubbing.quality.audio import gate
from persian_dubbing.core.scheduler import require_vram


def convert(source,target,dest,config,cancel=None):
    repo=Path(config.seed_repo).resolve()
    if not (repo/'inference_v2.py').is_file(): raise RuntimeError('Seed-VC not installed. See scripts/setup_seed.ps1.')
    if not target or not Path(target).is_file(): raise ValueError('A clean target voice sample is required')
    require_vram(config)
    with tempfile.TemporaryDirectory(prefix='pde-vc-') as directory:
        run([config.seed_python,repo/'inference_v2.py','--source',Path(source).resolve(),
             '--target',Path(target).resolve(),'--output',directory,'--convert-style','false'],
            cwd=repo,cancel=cancel,timeout=config.worker_timeout)
        files=list(Path(directory).glob('*.wav'))
        if len(files)!=1: raise RuntimeError('Seed-VC did not create exactly one WAV')
        gate(files[0]);conform(files[0],dest,config,cancel)
    return gate(dest)


def create_anchor(voice,project,config,cancel=None):
    import uuid
    dest=project.root/'references'/f'anchor-{uuid.uuid4().hex}.wav'
    # Technical QC is not a listening approval; approval is deliberately separate.
    convert(voice.reference,voice.target,dest,config,cancel)
    voice.anchor=str(dest);voice.anchor_approved=False
    project.save_voice(voice)
    return dest
