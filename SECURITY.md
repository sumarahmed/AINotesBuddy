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
- Whether microphone/display capture, local storage, imports, exports,
  downloaded files, pairing/CORS, or the local model companion are involved
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

The optional transcription companion must remain bound to `127.0.0.1`. It
authenticates all API routes with a persistent random token and restricts
browser origins. Do not expose port 8765 to a LAN/public interface, commit model
or pairing tokens, or weaken temporary-job cleanup. Reports involving a leaked
token, cross-origin access, retained job audio, unsafe media decoding, or model
supply-chain behavior should be treated as security reports.
