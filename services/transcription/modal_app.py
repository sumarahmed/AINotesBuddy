"""Deploy the NotesBuddy anonymous transcription API on Modal.

Run from the repository root:
    modal deploy services/transcription/modal_app.py
"""

from __future__ import annotations

import modal


APP_NAME = "notesbuddy-public-transcription"
HUGGING_FACE_SECRET = "notesbuddy-huggingface"
MODEL_CACHE_VOLUME = "notesbuddy-model-cache"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install_from_requirements(
        "services/transcription/requirements-api.txt",
    )
    .pip_install(
        "torch==2.11.0",
        "torchaudio==2.11.0",
        index_url="https://download.pytorch.org/whl/cu128",
    )
    .pip_install_from_requirements(
        "services/transcription/requirements-models.txt",
    )
    .env(
        {
            "HF_HOME": "/model-cache/huggingface",
            "TORCH_HOME": "/model-cache/torch",
            "LD_LIBRARY_PATH": (
                "/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib:"
                "/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"
            ),
            "NOTESBUDDY_ACCESS_MODE": "anonymous",
            "NOTESBUDDY_ALLOWED_ORIGINS": "https://sumarahmed.github.io",
            "NOTESBUDDY_MODEL_DEVICE": "cuda",
            "NOTESBUDDY_WHISPER_COMPUTE_TYPE": "float16",
            "NOTESBUDDY_MAX_WORKERS": "1",
            "NOTESBUDDY_MAX_JOBS": "16",
            "NOTESBUDDY_MAX_SOURCE_BYTES": str(250 * 1024**2),
            "NOTESBUDDY_MAX_TOTAL_UPLOAD_BYTES": str(400 * 1024**2),
            "NOTESBUDDY_MAX_DURATION_MS": str(2 * 60 * 60 * 1000),
            "NOTESBUDDY_JOB_RETENTION_SECONDS": "3600",
            "NOTESBUDDY_SESSION_TTL_SECONDS": str(24 * 60 * 60),
            "NOTESBUDDY_MAX_SESSIONS": "2048",
            "NOTESBUDDY_MAX_SESSIONS_PER_CLIENT": "10",
            "NOTESBUDDY_MAX_JOBS_PER_SESSION": "3",
            "NOTESBUDDY_MAX_ACTIVE_JOBS_PER_SESSION": "1",
        }
    )
    .add_local_dir(
        "services/transcription/notesbuddy_transcription",
        remote_path="/root/notesbuddy_transcription",
    )
)

app = modal.App(APP_NAME)
model_cache = modal.Volume.from_name(
    MODEL_CACHE_VOLUME,
    create_if_missing=True,
)


@app.function(
    image=image,
    gpu="T4",
    secrets=[modal.Secret.from_name(HUGGING_FACE_SECRET)],
    volumes={"/model-cache": model_cache},
    timeout=60 * 60,
    scaledown_window=5 * 60,
    max_containers=1,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def public_api():
    """One autoscaled container preserves the prototype's in-memory job queue."""

    from notesbuddy_transcription.server import create_app

    return create_app(
        authentication_mode="anonymous",
        allowed_origins=["https://sumarahmed.github.io"],
    )
