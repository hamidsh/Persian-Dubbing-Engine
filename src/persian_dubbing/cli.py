import argparse, json, sys, shutil
from pathlib import Path
from dataclasses import asdict
from persian_dubbing.core.config import Config
from persian_dubbing.core.pipeline import Pipeline
from persian_dubbing.core.types import Voice
from persian_dubbing.storage.project import Project
from persian_dubbing.media.subtitles import import_srt
from persian_dubbing.core.telemetry import snapshot


def parser():
    p=argparse.ArgumentParser(description='Persian Voice-First Dubbing Engine')
    p.add_argument('--config',help='JSON config path')
    p.add_argument('--project',default='projects/default')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('gui');sub.add_parser('doctor')
    c=sub.add_parser('init');c.add_argument('media')
    c=sub.add_parser('import-srt');c.add_argument('path');c.add_argument('--persian',action='store_true')
    sub.add_parser('transcribe');sub.add_parser('diarize')
    c=sub.add_parser('translate');c.add_argument('--force',action='store_true')
    c=sub.add_parser('voice');c.add_argument('id');c.add_argument('reference');c.add_argument('--target');c.add_argument('--license',default='user-provided')
    c=sub.add_parser('assign');c.add_argument('speaker');c.add_argument('voice')
    c=sub.add_parser('anchor');c.add_argument('voice')
    c=sub.add_parser('approve-anchor');c.add_argument('voice')
    c=sub.add_parser('render');c.add_argument('--segment',action='append');c.add_argument('--force',action='store_true')
    c=sub.add_parser('export');c.add_argument('--video',action='store_true');c.add_argument('--background')
    c=sub.add_parser('lab');c.add_argument('voice');c.add_argument('text');c.add_argument('--routes',nargs='+',choices=['native','anchor','direct','post_vc'],default=['native'])
    sub.add_parser('segments');sub.add_parser('demo')
    return p


def doctor(config):
    import importlib.util
    result={'python':sys.version,'ffmpeg':shutil.which(config.ffmpeg),'ffprobe':shutil.which(config.ffprobe),
            'moss_source':(Path(config.moss_repo)/'moss_tts_realtime/inferencer.py').exists(),
            'seed_source':(Path(config.seed_repo)/'inference_v2.py').exists(),
            'asr_installed':importlib.util.find_spec('faster_whisper') is not None,
            'gui_installed':importlib.util.find_spec('PySide6') is not None,'telemetry':snapshot()}
    return result


def demo(project,config):
    """A short test-tone workflow; verifies plumbing, NOT Persian speech quality."""
    from dataclasses import replace
    import numpy as np
    from persian_dubbing.media.audio import write
    from persian_dubbing.core.types import Segment
    if project.segments(): raise ValueError('Use an empty project for demo')
    reference=project.root/'references'/'diagnostic.wav'
    t=np.arange(24000)/24000;write(reference,.05*np.sin(2*np.pi*220*t))
    project.save_voice(Voice('diagnostic',str(reference),license='synthetic test tone'))
    project.assign('speaker_01','diagnostic')
    project.save_segments([Segment('s00001',.5,2.5,source='Hello.',translation='سلام، حال شما چطوره؟')])
    cfg=replace(config,tts_engine='diagnostic',route='native',mode='quality');cfg.save(project.root/'demo-config.json')
    pipe=Pipeline(project,cfg,progress=print);pipe.render()
    return pipe.export()


def main(argv=None):
    args=parser().parse_args(argv);config=Config.load(args.config)
    try:
        if args.command=='gui':
            from persian_dubbing.ui.app import main as gui
            return gui(config=config)
        if args.command=='doctor': print(json.dumps(doctor(config),indent=2,ensure_ascii=False));return 0
        project=Project(args.project);pipe=Pipeline(project,config,progress=print)
        match args.command:
            case 'init': pipe.ingest(args.media)
            case 'import-srt': project.save_segments(import_srt(args.path,args.persian))
            case 'transcribe': pipe.transcribe()
            case 'diarize': pipe.diarize()
            case 'translate': pipe.translate(args.force)
            case 'voice':
                project.save_voice(Voice(args.id,project.import_reference(args.reference),license=args.license,
                                         target=project.import_reference(args.target) if args.target else ''))
            case 'assign': project.assign(args.speaker,args.voice)
            case 'anchor':
                from persian_dubbing.voices.seed import create_anchor
                print(create_anchor(project.voices()[args.voice],project,config))
            case 'approve-anchor':
                voice=project.voices()[args.voice]
                if not voice.anchor or not Path(voice.anchor).is_file(): raise ValueError('Create an anchor first')
                voice.anchor_approved=True;project.save_voice(voice)
            case 'render': pipe.render(args.segment,args.force)
            case 'export': print(pipe.export(args.video,args.background))
            case 'lab':
                from persian_dubbing.quality.benchmark import compare
                print(json.dumps(compare(args.text,project.voices()[args.voice],project,config,args.routes,progress=print),indent=2,ensure_ascii=False))
            case 'segments': print(json.dumps([asdict(s) for s in project.segments()],ensure_ascii=False,indent=2))
            case 'demo': print(demo(project,config))
        return 0
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 1

if __name__=='__main__': raise SystemExit(main())
