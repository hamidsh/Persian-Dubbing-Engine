from pathlib import Path
import json, math, os
import numpy as np
import soundfile as sf
from persian_dubbing.core.process import run


def probe(path, config):
    raw = run([config.ffprobe,'-v','error','-show_format','-show_streams','-of','json',Path(path).resolve()])
    result = json.loads(raw)
    if not any(s['codec_type']=='audio' for s in result['streams']): raise ValueError('No audio stream')
    result['duration'] = float(result['format']['duration'])
    if not math.isfinite(result['duration']) or result['duration'] <= 0: raise ValueError('Invalid media duration')
    return result


def extract(source, dest, config, cancel=None):
    dest = Path(dest)
    temp = dest.with_name(dest.stem+'.part.wav')
    run([config.ffmpeg,'-v','error','-y','-i',Path(source).resolve(),'-map','0:a:0','-vn',
         '-af','aresample=async=1:first_pts=0','-ac','1','-ar',config.sample_rate,'-c:a','pcm_s16le',temp],cancel=cancel)
    os.replace(temp,dest)


def read(path, expected_sr=None):
    data, sr = sf.read(path,dtype='float32',always_2d=True)
    data = data.mean(axis=1)
    if expected_sr and sr != expected_sr: raise ValueError(f'Expected {expected_sr} Hz, got {sr}')
    if not len(data) or not np.isfinite(data).all(): raise ValueError('Empty or nonfinite audio')
    return data,sr


def write(path, data, sr=24000):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.stem+'.part.wav')
    sf.write(tmp,np.asarray(data),sr,subtype='PCM_16')
    os.replace(tmp,path)


def conform(source,dest,config,cancel=None,speed=1.0):
    args=[config.ffmpeg,'-v','error','-y','-i',source,'-ac','1','-ar',config.sample_rate]
    if abs(speed-1)>0.001:
        # Rubber Band preserves pitch. Never silently replace with destructive resampling.
        args += ['-af',f'rubberband=tempo={speed:.8f}']
    tmp=Path(dest).with_name(Path(dest).stem+'.part.wav')
    run(args+['-c:a','pcm_s16le',tmp],cancel=cancel)
    os.replace(tmp,dest)


def mix_timeline(items, duration, dest, config, background=None, cancel=None):
    """Block-based mixing: memory bounded even for 45-minute multi-speaker projects."""
    sr=config.sample_rate
    descriptors=[]
    try:
        for start,path in items:
            f=sf.SoundFile(path)
            if f.samplerate!=sr or f.channels!=1:
                f.close(); raise ValueError('Timeline expects mono 24 kHz PCM')
            descriptors.append((round(start*sr),f))
        bg=sf.SoundFile(background) if background else None
        if bg and (bg.samplerate!=sr or bg.channels!=1):
            bg.close(); raise ValueError('Background must be mono 24 kHz')
        total=round(duration*sr)
        for start,f in descriptors: total=max(total,start+len(f))
        tmp=Path(dest).with_name(Path(dest).stem+'.part.wav')
        peak=0.0
        try:
            with sf.SoundFile(tmp,'w',samplerate=sr,channels=1,subtype='PCM_16') as out:
                for pos in range(0,total,65536):
                    if cancel: cancel.check()
                    size=min(65536,total-pos); block=np.zeros(size,dtype=np.float32)
                    if bg and pos<len(bg):
                        bg.seek(pos); bed=bg.read(size,dtype='float32');block[:len(bed)] += bed*config.background_gain
                    for start,f in descriptors:
                        left=max(pos,start);right=min(pos+size,start+len(f))
                        if right>left:
                            f.seek(left-start);block[left-pos:right-pos] += f.read(right-left,dtype='float32')
                    peak=max(peak,float(np.max(np.abs(block),initial=0)))
                    # Soft limiting only above 0.95; each stem remains available for remixing.
                    mask=np.abs(block)>.95
                    block[mask]=np.sign(block[mask])*(.95+.05*np.tanh((np.abs(block[mask])-.95)/.05))
                    out.write(block)
            os.replace(tmp,dest)
        finally:
            if bg: bg.close()
        return {'pre_limiter_peak':peak,'duration':total/sr,'limiter_engaged':peak>.95}
    finally:
        for _,f in descriptors: f.close()


def mux(video, audio, dest, config, cancel=None):
    # Audio is padded to the original video's duration, never truncates the video.
    duration=probe(video,config)['duration']
    temp=Path(dest).with_name(Path(dest).stem+'.part.mp4')
    run([config.ffmpeg,'-v','error','-y','-i',video,'-i',audio,'-map','0:v:0','-map','1:a:0',
         '-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-b:a','192k',
         '-af','apad','-t',str(duration),'-movflags','+faststart',temp],cancel=cancel,timeout=7200)
    os.replace(temp,dest)
