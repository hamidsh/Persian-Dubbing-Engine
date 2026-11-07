from dataclasses import dataclass, field, asdict
from pathlib import Path
import math

@dataclass
class Segment:
    id: str
    start: float
    end: float
    source: str = ""
    speaker: str = "speaker_01"
    translation: str = ""
    pronunciation: str = ""
    emotion: str = "neutral"
    words: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def validate(self):
        if not self.id or not self.speaker:
            raise ValueError("Segment and speaker IDs must be nonempty")
        if not all(math.isfinite(t) for t in [self.start, self.end]):
            raise ValueError("Non-finite timestamp")
        if self.start < 0 or self.end <= self.start:
            raise ValueError(f"Invalid timestamps for {self.id}: {self.start}..{self.end}")
        return self

    @property
    def duration(self):
        return self.end - self.start

@dataclass
class Voice:
    id: str
    reference: str
    language: str = "fa"
    license: str = "user-provided"
    target: str = ""
    anchor: str = ""
    anchor_approved: bool = False
    style: str = "neutral"

    def selected_reference(self, route="native"):
        if route == "anchor":
            if not self.anchor_approved or not self.anchor:
                raise ValueError("Anchor needs listening approval before use; choose native explicitly")
            path = self.anchor
        elif route == "direct":
            path = self.target
        else:
            path = self.reference
            if self.language != "fa":
                raise ValueError("Native route requires a Persian reference")
        if not path or not Path(path).is_file():
            raise ValueError(f"Missing reference audio for {self.id}")
        return path

@dataclass(frozen=True)
class Capabilities:
    phonemes: bool = False
    emotions: tuple[str, ...] = ()
    duration: bool = False
    streaming: bool = False

@dataclass
class SynthesisPlan:
    text: str
    reference: str
    duration: float
    speaker: str
    emotion: str = "neutral"
    settings: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
