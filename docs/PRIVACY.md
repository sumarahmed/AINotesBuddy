# Privacy and data handling

NotesBuddy is designed to keep meeting records and original recordings in the
browser profile used to create them. This document describes the current
prototype, not a guarantee provided by the operating system or browser vendor.

## Data inventory

| Data | Storage or processor | Retention |
| --- | --- | --- |
| Local profile name, initials, and ID | Browser `localStorage` | Until site data is cleared |
| Meeting titles and timestamps | Browser `localStorage` | Until the meeting/site data is deleted |
| Summaries, highlights, decisions, and actions | Browser `localStorage` | Until the meeting/site data is deleted |
| Transcript segments | Browser `localStorage` | Until the meeting/site data is deleted |
| Personal notes | Browser `localStorage` | Until the meeting/site data is deleted |
| Capture settings | Browser `localStorage` | Until site data is cleared |
| Original audio Blobs | Browser IndexedDB | Until the meeting/site data is deleted |
| Live speech audio | Browser speech provider, when enabled | Controlled by the browser/provider |
| Downloaded audio or Markdown | User-selected filesystem location | Controlled by the user/device |

## What stays local

MediaRecorder audio chunks are combined and stored in IndexedDB. Meeting
metadata and notes are stored in `localStorage`. NotesBuddy has no application
server, account system, telemetry endpoint, analytics integration, or cloud
sync.

The first-run profile personalises the greeting and transcript attribution. It
does not authenticate a person, create a server account, or isolate multiple
people sharing the same browser profile.

The app creates temporary `blob:` URLs to play and download locally stored
recordings. These URLs exist only within the browser session and origin.

## Browser speech recognition

The browser Speech Recognition API is separate from local MediaRecorder
storage. Depending on the browser and its configuration, recognition audio may
be sent to a service operated by the browser provider.

Users can turn off **Browser live transcription** in Settings. Recording can
continue without it.

NotesBuddy:

- Stores only recognition results returned by the browser
- Does not upload stored recording Blobs for transcription
- Does not fabricate a transcript when recognition returns no text
- Shows an unavailable state when recognition is unsupported

## Origin separation

Browser storage is scoped by origin. These launch methods may have separate
meeting libraries:

- Opening `index.html` through `file://`
- Using `http://127.0.0.1:4173`
- Using a deployed HTTPS URL

Moving between them does not automatically migrate data.

## Deleting data

Deleting a meeting in NotesBuddy removes:

- Its meeting record from `localStorage`
- Its associated audio Blob from IndexedDB

To remove the entire workspace, clear site data for the relevant origin in the
browser settings. Downloaded exports and audio files must be deleted separately
from the filesystem.

## Security considerations

- Browser storage is not encrypted by NotesBuddy.
- Device users with access to the same unlocked browser profile may access the
  data.
- Browser extensions or compromised scripts with sufficient access may inspect
  page data.
- Private/incognito sessions may remove storage when the session ends.
- Browser storage quotas and cleanup policies can remove recordings.
- Imported audio should be treated as untrusted input even though the browser
  media element performs decoding.

## Responsible testing

Use synthetic speech and generated audio when reporting bugs or contributing
tests. Never upload confidential meetings, employee conversations, customer
data, or credentials to a public repository or issue.
