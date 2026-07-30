"""Start the NotesBuddy local transcription companion."""

from __future__ import annotations

import argparse
import os

import uvicorn

from notesbuddy_transcription.security import ensure_pairing_token
from notesbuddy_transcription.server import create_app


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run NotesBuddy transcription on this computer.",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--show-token",
        action="store_true",
        help="Print the persistent pairing token and exit.",
    )
    parser.add_argument(
        "--empty-engine",
        action="store_true",
        help="Run an API smoke-test engine that returns no transcript text.",
    )
    arguments = parser.parse_args()
    token, token_path, created = ensure_pairing_token()

    if arguments.show_token:
        print(token)
        return
    if arguments.empty_engine:
        os.environ["NOTESBUDDY_TRANSCRIPTION_ENGINE"] = "empty"

    print("NotesBuddy local transcription companion")
    print(f"Listening only on http://127.0.0.1:{arguments.port}")
    print(f"Pairing token file: {token_path}")
    if created:
        print("A new persistent pairing token was created.")
    print("Run `python run.py --show-token` to copy it into NotesBuddy Settings.")
    uvicorn.run(
        create_app(pairing_token=token),
        host="127.0.0.1",
        port=arguments.port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
