# Desktop model notices

The release builder must review these notices before distributing a companion
installer containing model weights.

## Speech-to-text

- Model: `Systran/faster-whisper-small`
- Project: <https://huggingface.co/Systran/faster-whisper-small>
- Declared license: MIT
- The release artifact must retain the upstream model and software notices.

## Speaker diarization

- Model: `pyannote/speaker-diarization-community-1`
- Project: <https://huggingface.co/pyannote/speaker-diarization-community-1>
- Declared license: CC-BY-4.0
- Access is gated. The publisher must accept the repository conditions, provide
  a build-only `HF_TOKEN`, preserve attribution, and confirm that the intended
  redistribution complies with the accepted terms.

The `HF_TOKEN` is a release-build secret only. It must never be compiled into
the executable, copied into the installer, committed to Git, or requested from
an end user. `desktop/prepare_models.py` records the immutable repository
revisions in `MODEL_MANIFEST.json` for every build.

This file is an engineering control, not legal advice. Complete a license and
privacy review before publishing a public installer.
