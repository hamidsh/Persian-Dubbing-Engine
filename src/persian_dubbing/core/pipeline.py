from pathlib import Path
from dataclasses import asdict
import json, time, uuid
from persian_dubbing.core.config import Config
from persian_dubbing.core.process import Cancellation
from persian_dubbing.core.prosody import plan
from persian_dubbing.storage.project import Project,file_hash,fingerprint
from persian_dubbing.media import audio
from persian_dubbing.media.subtitles import export_srt
from persian_dubbing.quality.audio import gate
from persian_dubbing.tts.engines import engine


class Pipeline:
    def __init__(self,project,config=None,cancel=None,progress=lambda _:None):
        self.project=project;self.config=(config or Config()).validate()
        self.cancel=cancel or Cancellation();self.progress=progress

    def ingest(self,source):
        source=Path(source).resolve();info=audio.probe(source,self.config)
        if self.project.get('source') and self.project.get('source')!=str(source):
            raise ValueError('Create a new project for a different input media file')
        audio.extract(source,self.project.root/'audio'/'source.wav',self.config,self.cancel)
        self.project.set('source',str(source));self.project.set('source_hash',file_hash(source))
        self.project.set('duration',info['duration']);self.project.set('probe',info)
        return info

    def transcribe(self):
        from persian_dubbing.speech.asr import transcribe
        source=self.project.root/'audio'/'source.wav'
        if not source.exists(): raise ValueError('Import media first')
        segments=transcribe(source,self.config,self.cancel,self.progress)
        if not segments: raise ValueError('No English speech detected')
        self.project.save_segments(segments)
        return segments

    def diarize(self):
        from persian_dubbing.speech.diarization import diarize,assign_segments
        turns=diarize(self.project.root/'audio'/'source.wav',self.project,self.config,self.cancel)
        self.project.set('speaker_turns',turns)
        self.project.save_segments(assign_segments(self.project.segments(),turns))

    def translate(self,force=False):
        from persian_dubbing.translation.llama import translate
        segments=self.project.segments()
        if not segments: raise ValueError('Transcribe or import subtitles first')
        for i,segment in enumerate(segments):
            self.cancel.check()
            if segment.translation and not force: continue
            self.progress(f'Translation {i+1}/{len(segments)}')
            following=[s.source for s in segments[i+1:i+3]] if self.config.mode!='live' else []
            translate(segment,[s.source for s in segments[max(0,i-2):i]],following,self.config,self.cancel)
            self.project.update_segment(segment)

    def _key(self,segment,voice,synthesis):
        cfg=asdict(self.config)
        # All settings included: conservative invalidation is preferable to stale audio.
        return fingerprint({'version':1,'plan':synthesis.to_dict(),'reference_hash':file_hash(synthesis.reference),
            'target_hash':file_hash(voice.target) if self.config.route=='post_vc' and voice.target else '',
            'config':cfg})

    def render(self,only=None,force=False):
        if self.config.mode!='quality':
            raise ValueError('Quick/Live playback is not yet released. Select Quality; no false realtime claim.')
        segments=self.project.segments()
        if not segments: raise ValueError('Project has no segments')
        selected=[s for s in segments if only is None or s.id in only]
        backend=engine(self.config);pending=[]
        for segment in selected:
            self.cancel.check()
            voice=self.project.voice_for(segment.speaker)
            synthesis,warnings=plan(segment,voice,self.config,backend.capabilities)
            key=self._key(segment,voice,synthesis)
            if not force and self.project.artifact(segment.id,key):
                self.progress(f'Cached: {segment.id}');continue
            output=self.project.root/'cache'/f'{key}-raw.wav'
            if force and output.exists(): output.unlink()
            pending.append((segment,voice,synthesis,warnings,key,output))
        if pending:
            self.progress(f'Synthesis: {len(pending)} segments ({backend.name})')
            jobs=[{'id':s.id,'plan':p.to_dict(),'output':str(out)} for s,v,p,w,k,out in pending if not out.is_file()]
            failure=None;tick=time.perf_counter()
            try: backend.synthesize_batch(jobs,self.project,self.cancel)
            except Exception as exc: failure=exc
            # Preserve completed jobs after an interrupted batch. Resume only needs unfinished work.
            for segment,voice,synthesis,warnings,key,raw in pending:
                if not raw.is_file(): continue
                if self.cancel.event.is_set(): break
                result=raw
                if self.config.route=='post_vc':
                    from persian_dubbing.voices.seed import convert
                    result=raw.with_name(raw.stem+'-vc.wav')
                    convert(raw,voice.target,result,self.config,self.cancel)
                metrics=gate(result)
                metric_path=raw.with_suffix('.metrics.json')
                if metric_path.exists(): metrics.update(json.loads(metric_path.read_text()))
                factor=metrics['duration']/segment.duration
                if factor>1:
                    if factor<=self.config.max_speedup:
                        fitted=raw.with_name(raw.stem+'-fit.wav')
                        audio.conform(result,fitted,self.config,self.cancel,speed=factor)
                        result=fitted;metrics['speedup']=factor
                    else:
                        warnings.append(f'Audio exceeds slot: {metrics["duration"]:.2f}s / {segment.duration:.2f}s; shorten text')
                metrics['engine']=backend.name;metrics['warnings']=warnings
                metrics['actual_duration']=gate(result)['duration']
                self.project.save_artifact(segment.id,key,result,metrics)
                self.progress(f'Ready: {segment.id}')
            self.project.set('last_render_seconds',time.perf_counter()-tick)
            if failure: raise failure
        self.cancel.check()
        return len(pending)

    def export(self,video=False,background=None):
        segments=self.project.segments();items=[];stems={};report=[]
        if not segments: raise ValueError('Nothing to export')
        backend=engine(self.config)
        for segment in segments:
            voice=self.project.voice_for(segment.speaker)
            synthesis,_=plan(segment,voice,self.config,backend.capabilities)
            artifact=self.project.artifact(segment.id,self._key(segment,voice,synthesis))
            if not artifact: raise ValueError(f'Missing/stale audio: {segment.id}. Render changed segments first.')
            path,metrics=artifact
            if metrics.get('actual_duration',0)>segment.duration+.1:
                raise ValueError(f'{segment.id} exceeds its time slot. Shorten translation or extend end time; export does not cut words.')
            items.append((segment.start,path));stems.setdefault(segment.speaker,[]).append((segment.start,path))
            report.append({'segment':segment.id,**metrics})
        duration=max(self.project.get('duration',0),max(s.end for s in segments))
        # New directory per export: cancellation cannot corrupt a previously completed export.
        folder=self.project.root/'exports'/('export-'+uuid.uuid4().hex[:10]);folder.mkdir()
        bed=None
        if background:
            bed=folder/'background.wav';audio.conform(background,bed,self.config,self.cancel)
        mixed=folder/'dubbed.wav'
        mix_metrics=audio.mix_timeline(items,duration,mixed,self.config,bed,self.cancel)
        stem_index={}
        for i,(speaker,parts) in enumerate(stems.items(),1):
            name=f'speaker_{i:02d}.wav';stem_index[speaker]=name
            audio.mix_timeline(parts,duration,folder/name,self.config,cancel=self.cancel)
        export_srt(segments,folder/'subtitles.fa.srt')
        (folder/'report.json').write_text(json.dumps({'segments':report,'mix':mix_metrics,'stems':stem_index,
            'diagnostic_only':self.config.tts_engine=='diagnostic'},ensure_ascii=False,indent=2),encoding='utf-8')
        (folder/'segments.json').write_text(json.dumps([asdict(s) for s in segments],ensure_ascii=False,indent=2),encoding='utf-8')
        if video:
            source=self.project.get('source')
            if not source: raise ValueError('No source video')
            if max(s.end for s in segments)>self.project.get('duration',0)+.1:
                raise ValueError('Segment extends past video duration')
            audio.mux(source,mixed,folder/'dubbed.mp4',self.config,self.cancel)
        self.project.set('last_export',str(folder));self.progress(f'Export: {folder}')
        return folder
