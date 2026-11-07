"""Four-way voice-route lab with explicit metrics and blind listening records."""
from pathlib import Path
from dataclasses import replace, asdict
import json, time, uuid, random
from persian_dubbing.core.types import Segment
from persian_dubbing.core.prosody import plan
from persian_dubbing.tts.engines import engine
from persian_dubbing.voices.seed import convert
from persian_dubbing.quality.audio import gate


def compare(text,voice,project,config,routes=('native',),cancel=None,progress=lambda _:None):
    folder=project.root/'exports'/('lab-'+uuid.uuid4().hex[:8]);folder.mkdir()
    rows=[]
    for route in routes:
        if cancel: cancel.check()
        progress('Lab: '+route)
        cfg=replace(config,route=route);v=replace(voice)
        if route=='anchor':
            anchor=folder/'experimental-anchor.wav'
            convert(v.reference,v.target,anchor,cfg,cancel)
            # Only the lab uses this unapproved experimental anchor. Registry is unchanged.
            v.anchor=str(anchor);v.anchor_approved=True
        backend=engine(cfg)
        synthesis,warnings=plan(Segment('lab',0,12,translation=text),v,cfg,backend.capabilities)
        raw=folder/(route+'-raw.wav');tick=time.perf_counter()
        backend.synthesize_batch([{'id':route,'plan':synthesis.to_dict(),'output':str(raw)}],project,cancel)
        final=raw
        if route=='post_vc':
            final=folder/'post_vc.wav';convert(raw,v.target,final,cfg,cancel)
        metrics=gate(final);elapsed=time.perf_counter()-tick
        rows.append({'route':route,'path':str(final),'wall_seconds':elapsed,
                     'wall_rtf_including_load':elapsed/metrics['duration'],**metrics,'warnings':warnings})
    random.SystemRandom().shuffle(rows)
    for i,row in enumerate(rows,1): row['blind_id']=f'Sample {i}'
    (folder/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    ratings=[{'sample':r['blind_id'],'naturalness_1_5':None,'pronunciation_1_5':None,'similarity_1_5':None,'notes':''} for r in rows]
    (folder/'ratings.json').write_text(json.dumps(ratings,ensure_ascii=False,indent=2),encoding='utf-8')
    return rows
