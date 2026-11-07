# Integration provenance

Source code and primary model cards consulted while building this release:

- [MOSS-TTS](https://github.com/OpenMOSS/MOSS-TTS), inspected commit `934d6826b084c46a0d033402174d5f8ac4ed2519`. `moss_tts_realtime/inferencer.py`, model card and `pyproject.toml` establish the real inference class and dependency API.
- [Persian MOSS LoRA](https://huggingface.co/hamidfzm/MOSS-TTS-Realtime-Persian-lora), model card and demo: PEFT merge, reference-conditioned generation, comma prefix and codec decode. The app uses its own frontend, not a downloaded normalization script.
- [Seed-VC](https://github.com/Plachtaa/seed-vc), inspected commit `51383efd921027683c89e5348211d93ff12ac2a8`. `inference_v2.py` establishes `--source`, `--target`, `--output` and `--convert-style false`. The checked upstream requirements contain multiple torch declarations; this repository provides isolated non-torch requirements and one explicit compatible torch/torchvision/torchaudio trio.
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper), official transcribe API with VAD and word timestamps.
- [pyannote Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1), official token-gated setup and output iteration contract.
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server), local chat-completions protocol.

Each upstream model/library retains its own license. No third-party weights or proprietary voice recordings are included. Re-check the model license and reference permissions for your use. API inspection is not equivalent to running the models on the target GPU.
