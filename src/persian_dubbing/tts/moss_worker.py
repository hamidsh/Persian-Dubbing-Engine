"""Standalone GPU worker. JSON files isolate torch/transformers from the desktop venv."""
import json, sys, time, re, os
from pathlib import Path


def split_text(text,limit=180):
    result=[];part=''
    for word in text.split():
        if part and len(part)+len(word)+1>limit: result.append(part);part=''
        part=(part+' '+word).strip()
        if len(part)>45 and part[-1:] in '.!?؟؛': result.append(part);part=''
    if part: result.append(part)
    return result


def main(jobfile):
    import numpy as np
    import torch
    import soundfile as sf
    data=json.loads(Path(jobfile).read_text(encoding='utf-8'));cfg=data['config']
    if not torch.cuda.is_available(): raise RuntimeError('MOSS profile requires CUDA; GPU unavailable in worker environment')
    sys.path.insert(0,str(Path(cfg['moss_repo'])/'moss_tts_realtime'))
    from peft import PeftModel
    from transformers import AutoModel, AutoTokenizer
    from inferencer import MossTTSRealtimeInference
    from mossttsrealtime.modeling_mossttsrealtime import MossTTSRealtime
    dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    started=time.perf_counter()
    model=MossTTSRealtime.from_pretrained(cfg['moss_base'],revision=cfg['base_revision'],torch_dtype=dtype,attn_implementation='sdpa')
    model=PeftModel.from_pretrained(model,cfg['moss_lora'],revision=cfg['lora_revision']).merge_and_unload().to('cuda').eval()
    tokenizer=AutoTokenizer.from_pretrained(cfg['moss_base'],revision=cfg['base_revision'])
    codec=AutoModel.from_pretrained(cfg['moss_codec'],revision=cfg['codec_revision'],trust_remote_code=True).eval().to('cuda')
    # SoundFile avoids torchaudio.load's TorchCodec DLL dependency on Windows.
    class WindowsFriendlyInference(MossTTSRealtimeInference):
        def _load_audio(self,audio_path,target_sample_rate):
            import torchaudio
            data,sr=sf.read(audio_path,always_2d=True,dtype='float32')
            waveform=torch.from_numpy(data.mean(axis=1).copy()).unsqueeze(0)
            if sr!=target_sample_rate:
                waveform=torchaudio.functional.resample(waveform,sr,target_sample_rate)
            return waveform
    infer=WindowsFriendlyInference(model,tokenizer,max_length=1200,codec=codec,codec_sample_rate=24000,codec_encode_kwargs={'chunk_duration':8})
    load_seconds=time.perf_counter()-started
    for job in data['jobs']:
        tick=time.perf_counter();waves=[]
        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            for text in split_text(job['plan']['text']):
                tokens=infer.generate(text=['، '+text],reference_audio_path=[job['plan']['reference']],
                                      temperature=.8,top_p=.6,top_k=30,repetition_penalty=1.1,repetition_window=50,device='cuda')[0]
                if len(tokens)>=1200: raise RuntimeError('Generation hit token cap; shorten or review text')
                if len(tokens)==0: raise RuntimeError('MOSS returned no speech tokens')
                codes=torch.as_tensor(tokens,device='cuda').permute(1,0)
                wav=codec.decode(codes,chunk_duration=8)['audio'][0].detach().float().cpu().numpy().squeeze()
                if wav.ndim==2: wav=wav.mean(axis=0)
                if wav.ndim!=1 or not len(wav) or not np.isfinite(wav).all(): raise RuntimeError('Invalid codec output')
                waves.append(wav)
        if not waves: raise ValueError('Empty synthesis input')
        audio=np.concatenate(waves)
        dest=Path(job['output']);temp=dest.with_suffix('.part.wav')
        sf.write(temp,audio,24000,subtype='PCM_16');os.replace(temp,dest)
        seconds=time.perf_counter()-tick
        metrics={'inference_seconds':seconds,'load_seconds':load_seconds,'rtf':seconds/(len(audio)/24000),
                 'peak_allocated_vram_mb':torch.cuda.max_memory_allocated()/1024**2,
                 'torch':torch.__version__,'base_revision':cfg['base_revision'],'lora_revision':cfg['lora_revision']}
        dest.with_suffix('.metrics.json').write_text(json.dumps(metrics),encoding='utf-8')
        print(f"Completed {job['id']}: {seconds:.2f}s",flush=True)

if __name__=='__main__': main(sys.argv[1])
