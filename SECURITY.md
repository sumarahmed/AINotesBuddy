# Security policy

## Supported version

NotesBuddy is currently a prototype. Security fixes are applied to the latest
commit on the `main` branch; older commits and deployments are not supported.

## Reporting a vulnerability

Do not report a vulnerability through a public GitHub issue.

Use GitHub's **Security** tab and choose **Report a vulnerability** if private
vulnerability reporting is enabled. If it is unavailable, contact the
repository owner privately before sharing technical details.

Include:

- A concise description and potential impact
- Reproduction steps or a minimal proof of concept
- Affected browser, operating system, and launch method
- Whether microphone, local storage, imports, exports, or downloaded files are
  involved
- Suggested mitigations, if known

Do not include genuine meeting audio, transcripts, access tokens, employee
information, or customer information. Use synthetic test data.

## Response expectations

The maintainer should acknowledge a report, assess severity, and coordinate a
fix before public disclosure. Timelines depend on impact and reproducibility.

## Security boundaries

NotesBuddy stores meeting metadata in `localStorage` and audio Blobs in
IndexedDB. This storage is local to the browser profile but is not encrypted by
the application. Anyone with access to the browser profile or an unlocked
device may be able to access it.

Browser speech recognition may process audio through the browser provider's
service. See [docs/PRIVACY.md](docs/PRIVACY.md) for the full data model and
privacy boundary.
