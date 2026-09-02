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

## Smart meeting summary

Three independently selectable quality tiers, all sharing one destination
folder so installing a tier replaces whichever was previously installed.
Each tier's own pinned revision, size, and content hash live in
`desktop/prepare_components.py`'s `ANALYSIS_TIERS`; this section records the
per-tier upstream source and license only.

### Fast (`analysis-tiny`, default)

- Model: `Qwen/Qwen2.5-0.5B-Instruct-GGUF`, Q4_K_M quantization
- Project: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF>
- Declared license: Apache-2.0
- Verified against a real 298-segment meeting recording: raw output looked
  plausible but failed evidence-grounding validation almost entirely, so
  this tier reliably produces very little usable content on real speech.
  Kept as the smallest/fastest download, not the recommended default.

### Balanced (`analysis-standard`, recommended)

- Model: `unsloth/Qwen3-1.7B-GGUF`, Q4_K_M quantization
- Project: <https://huggingface.co/unsloth/Qwen3-1.7B-GGUF>
- Declared license: Apache-2.0 (inherited from `Qwen/Qwen3-1.7B`; this
  quantisation repo carries no LICENSE file of its own, so the license text
  bundled with this component is fetched from Qwen's own model repo)
- Verified against the same real recording: reliably produced grounded,
  validated highlights and decisions.

### High quality (`analysis-pro`)

- Model: `unsloth/Qwen3-4B-Instruct-2507-GGUF`, Q3_K_M quantization
- Project: <https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF>
- Declared license: Apache-2.0 (license text sourced the same way as
  Balanced, above)
- Q4_K_M (2.50 GB) was verified first and is the higher-fidelity option, but
  a single GitHub release asset cannot exceed 2 GiB, so it does not fit.
  Q3_K_M (1.93 GB) was re-verified against the same real meeting chunk
  afterward and produced comparable grounded content; revert to Q4_K_M in
  `desktop/prepare_components.py` if a future release host allows it.
- Verified against the same real recording: the richest, most specific
  output of the three (named owners, explicit dates, business context), at
  the cost of noticeably slower CPU generation. Needs a larger `--predict`
  output-token budget than the other tiers to reliably finish its JSON
  (handled automatically based on the installed model's file size).

### Runtime (all tiers)

- Runtime: `ggml-org/llama.cpp` Windows x64 CPU build `b10516`
- Project: <https://github.com/ggml-org/llama.cpp>
- Declared runtime license: MIT
- Each independently downloaded component includes the upstream model and
  runtime license texts plus immutable provenance and content hashes.

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
