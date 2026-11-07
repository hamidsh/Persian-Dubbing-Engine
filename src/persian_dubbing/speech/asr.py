from persian_dubbing.core.types import Segment


def transcribe(audio,config,cancel=None,progress=lambda _:None):
    try: from faster_whisper import WhisperModel
    except ImportError as exc: raise RuntimeError('Install ASR: pip install -e ".[asr]"') from exc
    model=WhisperModel(config.asr_model,device=config.asr_device,compute_type=config.asr_compute)
    try:
        stream,info=model.transcribe(str(audio),language='en',vad_filter=True,word_timestamps=True,beam_size=5)
        result=[]
        for i,s in enumerate(stream):
            if cancel: cancel.check()
            # Split long ASR segments at word punctuation or 12 seconds, preserve word times.
            words=[{'start':w.start,'end':w.end,'word':w.word} for w in (s.words or [])]
            groups=[]; current=[]
            for word in words:
                current.append(word)
                if word['end']-current[0]['start']>=12 or word['word'].strip().endswith(('.', '?', '!')):
                    groups.append(current);current=[]
            if current: groups.append(current)
            if not groups:
                if s.end>s.start and s.text.strip(): result.append(Segment(f's{len(result)+1:05d}',s.start,s.end,s.text.strip()))
            for group in groups:
                if group[-1]['end']>group[0]['start']:
                    result.append(Segment(f's{len(result)+1:05d}',group[0]['start'],group[-1]['end'],''.join(w['word'] for w in group).strip(),words=group))
            progress(f'ASR {s.end:.1f}s / {info.duration:.1f}s')
        return result
    finally:
        del model
