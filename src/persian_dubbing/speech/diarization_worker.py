import json, os, sys
from pathlib import Path

def main():
    import torch, soundfile as sf
    from pyannote.audio import Pipeline
    audio,sr=sf.read(sys.argv[1],always_2d=True,dtype='float32')
    pipeline=Pipeline.from_pretrained('pyannote/speaker-diarization-community-1',token=os.environ.get('HF_TOKEN'))
    result=pipeline({'waveform':torch.from_numpy(audio.T),'sample_rate':sr})
    turns=[{'start':turn.start,'end':turn.end,'speaker':speaker} for turn,speaker in result.speaker_diarization]
    Path(sys.argv[2]).write_text(json.dumps(turns),encoding='utf-8')

if __name__=='__main__': main()
