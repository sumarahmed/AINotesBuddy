"""Shared CPU-thread tuning for torch-based local inference (diarization).

Diarization was observed running visibly CPU-bound with no explicit thread
configuration anywhere in the pipeline -- PyTorch's own default thread count
is not guaranteed to reflect the host's real core count on every Windows
build, and the isolated speaker worker subprocess has nothing else
contending for CPU during its one diarization call, so defaulting to every
logical core is safe there. ``OMP_NUM_THREADS``/``MKL_NUM_THREADS`` are read
once by torch's native thread pool at import time, so ``apply_env_defaults``
must run before that process's first ``import torch``.
"""

from __future__ import annotations

import os


def resolve_thread_count() -> int:
    configured = os.getenv("NOTESBUDDY_DIARIZATION_CPU_THREADS", "").strip()
    if configured:
        try:
            return max(1, int(configured))
        except ValueError:
            pass
    return os.cpu_count() or 4


def apply_env_defaults() -> int:
    """Set OMP/MKL thread env vars before this process's first torch import."""
    threads = resolve_thread_count()
    os.environ.setdefault("OMP_NUM_THREADS", str(threads))
    os.environ.setdefault("MKL_NUM_THREADS", str(threads))
    return threads


def configure_torch(torch_module, *, log: bool = True) -> int:
    """Apply the resolved thread count directly to an already-imported torch."""
    threads = resolve_thread_count()
    torch_module.set_num_threads(threads)
    try:
        # A single diarization call has no independent ops to run
        # concurrently -- interop parallelism only helps when multiple
        # unrelated ops run at once, and leaving it at torch's default here
        # just adds thread-pool bookkeeping overhead for no benefit.
        torch_module.set_num_interop_threads(1)
    except RuntimeError:
        # Can only be set once per process; a second call in the same
        # process (e.g. under test, or a second diarize() invocation) hits
        # this harmlessly.
        pass
    if log:
        from .diagnostics import log_diagnostic

        log_diagnostic(f"torch cpu threads={threads}, interop threads=1")
    return threads
