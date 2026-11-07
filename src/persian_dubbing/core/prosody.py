from persian_dubbing.core.types import SynthesisPlan
from persian_dubbing.persian_frontend.frontend import normalize

def plan(segment, voice, config, capabilities):
    # Manual sentence pronunciation is highest priority and is not rewritten.
    if segment.pronunciation.strip():
        text, warnings = segment.pronunciation.strip(), []
    else:
        text, warnings = normalize(segment.translation, config.dictionary)
    if not text: raise ValueError(f"Empty Persian text: {segment.id}")
    if segment.emotion != 'neutral' and segment.emotion not in capabilities.emotions:
        warnings.append('Emotion requested but unsupported by this engine; no artificial tags injected')
    result = SynthesisPlan(text,voice.selected_reference(config.route),segment.duration,segment.speaker,
                           segment.emotion if segment.emotion in capabilities.emotions else 'neutral')
    return result, warnings
