# Requirement and validation ledger — v0.1

The supplied architecture is retained verbatim in ARCHITECTURE_FA.md. This table distinguishes implementation from hardware validation. No synthetic test tone counts as a successful speech benchmark.

| Requirement | Release status | Evidence / boundary |
|---|---|---|
| Windows 11 / Python 3.11 / no Conda | Scripts supplied; Windows installation not executed here | Separate venvs, checked native exit codes, pinned upstream source commits |
| Phase 0 MOSS + LoRA | Real batch worker implemented | Checked against upstream API; CUDA inference and Persian listening not run |
| Four voice routes | Implemented in lab and renderer | Native / personalized anchor / English direct / post-VC; GPU validation pending |
| Approved stable anchor | Implemented | Separate listening approval, no chain of generated references, registry history |
| 8–12 licensed voice bank | User populated | No voices or licenses invented or bundled |
| Automatic embedding-based voice matching | Deferred | Manual voice assignment works |
| ASR + VAD | Faster-Whisper + built-in Silero path | Optional dependency, model download and real ASR not run here |
| Parakeet ONNX | Deferred | Whisper is the documented alternative selected for first implementation |
| Diarization | Optional pyannote Community-1 worker | Validated API and alignment logic; weights/inference not run |
| True overlapping-speech recognition | Deferred | Mixer supports overlap; ASR cannot promise both transcripts |
| Contextual translation | Implemented llama.cpp HTTP contract | Local HTTP integration test; no translation quality claim |
| Semantic boundaries | Punctuation/word-duration heuristic | Not a learned semantic segmenter |
| Persian normalization | Implemented | Numbers, letter forms, dictionary and ambiguity warnings tested |
| G2P / semantic homographs / IPA F5 | Deferred | No fabricated phonemes, manual pronunciation available |
| Emotion and prosody | Plan and capability gate implemented | Acoustic emotion/F0 model deferred, no unsupported emotion tags |
| MOSS 8B / VoxCPM / F5 / Nano / Seamless | Deferred | Not offered as working adapters |
| Duration fitting | Bounded Rubber Band + review gate | Excess duration blocks final export; no forced truncation |
| Multi-speaker stems | Implemented | Overlap, limiting, named mapping, block mixing tested |
| Background music | External bed supported | Automatic Demucs/MDX/nonverbal separation deferred |
| Project store and selective rerender | Implemented | SQLite history, reference content hashes, resume/invalidation tested |
| GUI / text edits / A–B / output | Implemented | Offscreen Qt startup and background task tests; screenshot inspected |
| Player | Qt Multimedia in this release | libmpv integration deferred; no buffered live player claim |
| GPU resource scheduling | Conservative serial workers + free-memory guard | Worker exits unload own models; external translator not controlled |
| CPU/RAM/VRAM measurements | Implemented | nvidia-smi optional, no guessed VRAM budgets in reports |
| Deadline queue / buffer policy | Isolated primitives only | Not connected to player; no claimed streaming behavior |
| Quick / Live Simulation | Explicitly unavailable | Raises clear error; Quality is the functioning mode |
| 10-second latency / RTF <1 | Not benchmarked | Must measure complete critical path on target hardware |
| 30–45 minute soak | Not run | Follow BENCHMARK.md before any production claim |
| Lip sync | Not implemented/claimed | Timeline placement only |

## Engineering choices

MOSS source and Seed source are kept outside the repository in `external/`. The host talks to workers using local JSON/WAV files and subprocess argv, never interpolated shell commands. Worker dependencies do not load into the GUI interpreter. MOSS loads once per batch, not once per utterance. Seed post-conversion currently loads once per invocation: safe memory isolation but slower than a persistent service.

The translator starts independently; CPU inference is recommended initially. A 2GB free-VRAM guard is a minimum condition, not proof that model loading fits. OOM is surfaced to the user rather than changing voice or precision silently. Model revisions default to `main` for first download; set immutable revisions in config after benchmarking. Every changed config invalidates cached speech conservatively.

## Next acceptance gates

1. Install on the target Windows machine and produce clean MOSS speech using a native Persian reference.
2. Compare all four routes on several speakers. Approve only listening-validated anchors.
3. Run a real 2–5 minute, 2–3 speaker file; fix text and speaker boundaries manually and review the exported stems.
4. Measure memory, cold/warm load time, per-utterance inference RTF, and total critical-path RTF.
5. Only after those pass, implement and validate incremental Quick/Live playback and resource-aware resident models.
