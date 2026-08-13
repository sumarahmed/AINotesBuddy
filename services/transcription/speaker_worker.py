"""Isolated local pyannote worker shipped in the reusable speaker pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def diarize(audio_path: Path, model_path: Path) -> list[dict[str, object]]:
    import soundfile
    import torch
    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(str(model_path))
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
