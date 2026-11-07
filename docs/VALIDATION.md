# Validation record

## Executed in the development environment

- Linux, Python 3.12.14; Windows installer targets Python 3.11.
- PySide6 6.8.3 desktop startup, window render/screenshot inspection, project table editing and background task completion.
- Unit and integration suite: Persian number/letter normalization, manual pronunciation priority, timestamps, SRT roundtrip, invalid data rejection, SQLite persistence, content-based cache invalidation, selective rerender, anchor approval, overlap mixing/limiting, overrun export blocking, VRAM guard, unsupported mode errors, process cancellation/timeout, partial-batch recovery, subtitle/speaker alignment, capability gating, quality gate, safe generated filenames, reference portability, deadline/buffer primitives.
- Real local HTTP request against a controlled llama-compatible test server verifies request/response parsing, context and translation storage. This is not a real LLM quality evaluation.
- Real FFmpeg-generated MP4 ingest, WAV extraction, Rubber Band stretch and MP4 export; duration checked with FFprobe.
- Explicit diagnostic-tone CLI workflow through synthesis, storage and export.
- `compileall` and `pip check`.

## Not executed here

- Windows installation scripts and driver/DLL compatibility on the user's computer.
- Download/inference of MOSS, Seed-VC, Whisper or pyannote weights; no suitable local NVIDIA GPU was available.
- Native Persian speech quality, speaker identity similarity, model licensing fitness for a particular deployment, real translation quality, a complete real-video dubbing run, target-machine latency/VRAM/RTF, or a 30–45 minute soak.
- Quick/Live preview: deliberately unavailable, not a tested feature.

GPU adapters were implemented against inspected primary-source APIs. Passing CPU tests is not evidence that model downloads, every upstream dependency combination, or GPU inference will work without a target-machine test. Windows/Linux Python 3.11 CI is configured; its status is separate from this local record.
