from dataclasses import dataclass, field, asdict
from pathlib import Path
import json, sys

@dataclass
class Config:
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    asr_model: str = "large-v3-turbo"
    asr_device: str = "cpu"
    asr_compute: str = "int8"
    translator_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    translator_model: str = "local"
    translator_timeout: int = 180
    tts_engine: str = "moss"
    moss_python: str = sys.executable
    moss_repo: str = "external/MOSS-TTS"
    moss_base: str = "OpenMOSS-Team/MOSS-TTS-Realtime"
    moss_lora: str = "hamidfzm/MOSS-TTS-Realtime-Persian-lora"
    moss_codec: str = "OpenMOSS-Team/MOSS-Audio-Tokenizer"
    base_revision: str = "main"
    lora_revision: str = "main"
    codec_revision: str = "main"
    seed_python: str = sys.executable
    seed_repo: str = "external/seed-vc"
    diarization_python: str = sys.executable
    route: str = "native"
    mode: str = "quality"
    buffer_seconds: float = 10
    max_speedup: float = 1.15
    sample_rate: int = 24000
    background_gain: float = 0.15
    vram_reserve_mb: int = 2048
    worker_timeout: int = 1200
    dictionary: dict[str, str] = field(default_factory=dict)

    def validate(self):
        if self.mode not in ("quality", "quick", "live"):
            raise ValueError("Unknown mode")
        if self.tts_engine not in ("moss", "diagnostic"):
            raise ValueError("Unknown TTS engine")
        if self.route not in ("native", "anchor", "direct", "post_vc"):
            raise ValueError("Unknown voice route")
        if not 1 <= self.max_speedup <= 1.25:
            raise ValueError("max_speedup must be 1..1.25")
        if not 0 <= self.background_gain <= 1 or self.buffer_seconds < 0:
            raise ValueError("Invalid gain/buffer")
        if self.sample_rate != 24000:
            raise ValueError("This release uses a 24 kHz timeline")
        return self

    @classmethod
    def load(cls, path=None):
        return cls(**json.loads(Path(path).read_text(encoding="utf-8"))).validate() if path else cls()

    def save(self, path):
        Path(path).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
