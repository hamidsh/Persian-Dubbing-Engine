"""Optional isolated pyannote worker; manual speaker editing remains available."""
import json, os
from pathlib import Path
from persian_dubbing.core.process import run


def diarize(audio,project,config,cancel=None):
    output=project.root/'jobs'/'diarization.json'
    script=Path(__file__).with_name('diarization_worker.py')
    run([config.diarization_python,script,audio,output],cancel=cancel,timeout=config.worker_timeout,
        log_path=project.root/'logs'/'diarization.log')
    return json.loads(output.read_text(encoding='utf-8'))


def assign_segments(segments,turns):
    for segment in segments:
        overlaps={}
        for turn in turns:
            amount=max(0,min(segment.end,turn['end'])-max(segment.start,turn['start']))
            if amount: overlaps[turn['speaker']]=overlaps.get(turn['speaker'],0)+amount
        if overlaps:
            segment.speaker=max(overlaps,key=overlaps.get)
            if len(overlaps)>1: segment.warnings.append('Multiple speakers in segment: split/review manually')
    return segments
