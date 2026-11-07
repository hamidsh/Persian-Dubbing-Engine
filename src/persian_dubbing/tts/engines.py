import json, time, uuid
from pathlib import Path
import numpy as np
from dataclasses import asdict
from persian_dubbing.core.types import Capabilities
from persian_dubbing.core.process import run
from persian_dubbing.media.audio import write
from persian_dubbing.core.scheduler import require_vram

class DiagnosticEngine:
    """Explicit test tone. This is NEVER a speech fallback."""
    name='diagnostic'
    capabilities=Capabilities()
    def __init__(self,config): self.config=config
    def synthesize_batch(self,jobs,project,cancel=None):
        for job in jobs:
            if cancel: cancel.check()
            duration=min(3,max(.25,job['plan']['duration']*.85))
            sr=self.config.sample_rate;t=np.arange(round(sr*duration))/sr
            write(job['output'],.06*np.sin(2*np.pi*330*t)*np.minimum(1,t/.02)*np.minimum(1,(duration-t)/.02),sr)

class MossEngine:
    name='moss'
    # This adapter uses complete utterances. Upstream streaming != implemented preview streaming.
    capabilities=Capabilities()
    def __init__(self,config): self.config=config
    def synthesize_batch(self,jobs,project,cancel=None):
        if not jobs: return
        require_vram(self.config)
        repo=Path(self.config.moss_repo).resolve()
        if not (repo/'moss_tts_realtime'/'inferencer.py').is_file():
            raise RuntimeError('MOSS source missing. Run scripts/setup_moss.ps1 and set moss_repo.')
        jobfile=project.root/'jobs'/f'moss-{uuid.uuid4().hex}.json'
        payload={'config':asdict(self.config),'jobs':jobs}
        payload['config']['moss_repo']=str(repo)
        jobfile.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        run([self.config.moss_python,Path(__file__).with_name('moss_worker.py'),jobfile],
            cancel=cancel,timeout=self.config.worker_timeout,log_path=project.root/'logs'/'moss.log')


def engine(config):
    return DiagnosticEngine(config) if config.tts_engine=='diagnostic' else MossEngine(config)
