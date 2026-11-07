import numpy as np
from persian_dubbing.media.audio import read

def inspect(path):
    audio,sr=read(path)
    rms=float(np.sqrt(np.mean(audio.astype(np.float64)**2)))
    peak=float(np.max(np.abs(audio)))
    return {'duration':len(audio)/sr,'sample_rate':sr,'rms':rms,'peak':peak,
            'clipped_fraction':float(np.mean(np.abs(audio)>=.999)),
            'silent':rms<0.0001}


def gate(path):
    metrics=inspect(path)
    if metrics['silent']: raise ValueError('Generated audio is silent; artifact rejected')
    if metrics['duration']<.1: raise ValueError('Generated audio too short')
    if metrics['clipped_fraction']>.02: raise ValueError('Severely clipped audio; artifact rejected')
    return metrics
