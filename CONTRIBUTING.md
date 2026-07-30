# Contributing to NotesBuddy

Thank you for helping improve NotesBuddy. The static client is intentionally
small, dependency-free, and local-first. The optional Python model companion is
isolated under `services/transcription`. Changes should preserve that boundary
unless a proposal explains a different privacy and deployment model.

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Before you start

- Search existing issues before creating a new one.
- Use a bug report for reproducible defects.
- Use a feature request for product or architecture proposals.
- Never attach real meeting recordings, transcripts, credentials, or personal
  information to an issue.

## Development setup

Node.js 20 or later is required for the static client and build scripts. There
are no client packages to install.

```bash
npm run dev
```

Open <http://127.0.0.1:4173>. You can also open `index.html` directly to verify
the `file://` launch path.

## Repository checks

Run the same validation used by GitHub Actions:

```bash
npm test
```

This syntax-checks the JavaScript, rebuilds `dist/`, and verifies the generated
client entry point. Commit generated `dist/` changes whenever source assets
change.

For companion changes, create a Python environment and install
`services/transcription/requirements-test.txt`. For recording, playback, or
speaker changes, run the synthetic browser suite and complete the applicable
real-device regression in [docs/TESTING.md](docs/TESTING.md).

## Coding guidelines

- Keep the client dependency-free unless a change has been discussed first.
- Keep model and API dependencies out of the static bundle.
- Prefer platform APIs and progressive capability detection.
- Preserve honest data behavior: never fabricate transcript text or imply that
  unsupported processing occurred.
- Keep recordings local unless a feature explicitly obtains informed user
  consent for another destination.
- Use semantic HTML, accessible labels, keyboard-operable controls, and clear
  unavailable states.
- Avoid full application re-renders during active recording or playback.
- Bind the companion to loopback, authenticate every route, and remove job
  audio in terminal paths.
- Escape user-controlled content before inserting it into HTML.
- Keep mobile layouts usable at a 320 px minimum viewport width.

## Pull requests

A pull request should:

1. Describe the user-visible outcome.
2. Link the issue or explain why no issue is needed.
3. List the checks and browser scenarios run.
4. Include screenshots for visual changes.
5. Call out privacy, storage, permission, or compatibility implications.
6. Include source and matching generated `dist/` changes.

Keep pull requests focused. Refactors and behavior changes are easier to review
when submitted separately.

## Commit messages

Use a short imperative summary, for example:

```text
Fix recording playback after tab changes
```

## License notice

The repository does not currently include an open-source license. External
contributions should not be accepted until the repository owner selects a
license and confirms the contribution terms.
