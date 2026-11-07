# Local benchmark protocol

Use authorized clean voice clips, one Persian native reference and one English target per speaker. Do not treat the diagnostic engine as speech. Use `examples/benchmark.fa.json` for pronunciation coverage.

## A — Persian quality

Render each text with `route=native`, then repeat using manual pronunciation when needed. Record pronunciation accuracy, ezafe, names, numbers, naturalness (1–5), repetition, truncation and first-word clipping. Keep the same reference. Record immutable model revisions and actual installed dependency versions (`pip freeze`) with each benchmark. No threshold in this repo asserts that a model has passed.

## B — voice routes

The GUI lab generates selected routes sequentially with the same text and selected speaker. The anchor route is an experimental candidate, never automatically approved for the project. Results receive randomized sample IDs. Hide `results.json` and the reveal button from the listener until ratings are saved. This is an operator-run blind listening workflow, not a double-blind study.

Rate naturalness, pronunciation and similarity separately. The GUI stores naturalness/similarity; the generated `ratings.json` template also supports notes/pronunciation for manual assessment. For now this tests methods on MOSS, not multiple installed TTS engines. Technical audio QC cannot establish speaker similarity, intelligibility or consent.

`wall_rtf_including_load = wall seconds / output audio seconds` includes cold load, initialization and conversion. MOSS sidecars separately record inference seconds, load seconds and PyTorch peak allocated memory. CUDA reserved memory and other processes are not included in PyTorch peak allocation; use the resource panel / nvidia-smi as well. Do not compare cold wall RTF with warm inference RTF as if they were identical.

## C — conversation

Choose a 2–5 minute file with 2–3 speakers and known overlapping turns. Review the transcript, translation and speaker mapping before synthesis. Save mistakes as corrected segment data. Record identity switches, late or excessively long utterances, overlap intelligibility and meaning errors. Use the stems to diagnose the mixer separately from speech generation. The first release blocks export if any segment overruns its slot beyond tolerance.

For 30–45 minute stability tests, record RAM/VRAM periodically, total processing wall time, crash/cancellation/resume behavior and exported duration. Do not infer streaming success from offline throughput: the released player does not implement live buffering.
