"""Isolated local pyannote worker shipped in the reusable speaker pack."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from notesbuddy_transcription import cpu_threads

# OMP_NUM_THREADS/MKL_NUM_THREADS are read once when the native OpenMP/MKL
# thread pool inside torch initializes on first import -- setting them after
# `import torch` has no effect, so this must run at module import time,
# before diarize()'s own `import torch` below. This process runs a single
# diarization job per invocation with nothing else contending for CPU, so
# it is safe to default to every logical core (see cpu_threads.py).
cpu_threads.apply_env_defaults()


def diarize(audio_path: Path, model_path: Path) -> list[dict[str, object]]:
    import soundfile
    import torch
    from pyannote.audio import Pipeline

    # This same script is built into two separate executables that differ
    # only in which torch wheel is bundled -- the CPU-only build's torch
    # always reports CUDA unavailable, so this naturally stays on CPU there
    # with no separate code path needed. Confirmed live (2026-09-05): a
    # real ~24 minute meeting diarized 11.8x faster on GPU than on
    # tuned CPU, with identical speaker-turn output on both.
    use_cuda = torch.cuda.is_available()
    if not use_cuda:
        # Configured before the pipeline loads, not after -- the load
        # itself is CPU-thread-sensitive work too.
        cpu_threads.configure_torch(torch)
    pipeline = Pipeline.from_pretrained(str(model_path))
    if use_cuda:
        try:
            pipeline.to(torch.device("cuda"))
        except (RuntimeError, AssertionError):
            # Falls back to whatever device the pipeline is already on.
            cpu_threads.configure_torch(torch)
    samples, sample_rate = soundfile.read(str(audio_path), always_2d=True, dtype="float32")
    waveform = torch.from_numpy(samples.T.copy())
    result = pipeline({"waveform": waveform, "sample_rate": sample_rate})
    annotation = getattr(result, "exclusive_speaker_diarization", None)
    if annotation is None:
        annotation = getattr(result, "speaker_diarization", None)
    if annotation is None:
        annotation = result
    turns = []
    for turn, _track, label in annotation.itertracks(yield_label=True):
        turns.append({"start": float(turn.start), "end": float(turn.end), "speaker": str(label)})
    return turns


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()
    if arguments.self_test:
        import pyannote.audio
        import soundfile
        import torch
        if arguments.model:
            from pyannote.audio import Pipeline
            Pipeline.from_pretrained(str(arguments.model))
        print(json.dumps({"status": "ok", "torch": torch.__version__, "pyannote": bool(pyannote.audio), "modelLoaded": bool(arguments.model)}))
        return 0
    if not arguments.audio or not arguments.model:
        parser.error("--audio and --model are required")
    try:
        print(json.dumps({"status": "ok", "turns": diarize(arguments.audio, arguments.model)}))
        return 0
    except Exception as error:  # noqa: BLE001 - machine-readable parent-process error
        print(json.dumps({"status": "error", "error": str(error)[:1000]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
