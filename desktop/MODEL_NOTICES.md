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

## Windows audio capture

- Library: `SoundCard`
- Project: <https://pypi.org/project/SoundCard/>
- Declared license: BSD-3-Clause
- The companion uses its Windows/WASAPI backend only while the user has an
  active NotesBuddy recording. Preserve the upstream software notice in
distributed packages.

## Optional NVIDIA acceleration runtime

- Runtime: NVIDIA cuBLAS CUDA 12 and cuDNN 9 redistributable DLLs
- Build source: the fixed GitHub release asset ID `236181970` from
  <https://github.com/Purfview/whisper-standalone-win/releases/tag/libs>
- Upstream licenses: NVIDIA CUDA Toolkit and cuDNN software license agreements
- The release workflow verifies the immutable asset ID, name, and byte size
  before packaging. Review NVIDIA's redistribution terms before each public
  companion release and preserve all required notices.

This file is an engineering control, not legal advice. Complete a license and
privacy review before publishing a public installer.
