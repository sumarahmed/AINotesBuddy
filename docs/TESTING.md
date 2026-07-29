# Testing guide

NotesBuddy combines static UI, browser storage, permissions, and media APIs.
Repository checks cover syntax and build integrity; recording changes also need
browser-level regression testing.

## Automated repository check

```bash
npm test
```

The command:

1. Syntax-checks source and build scripts.
2. Builds a fresh `dist/` directory.
3. Syntax-checks the generated client.
4. Confirms the generated bundle matches the committed `dist/` files.

GitHub Actions runs this check on pushes to `main` and on pull requests.

## Core manual regression

Use synthetic or non-confidential speech.

### Launch paths

- Open `index.html` directly and confirm the home screen loads and is styled.
- Run `npm run dev` and open <http://127.0.0.1:4173>.
- Run `npm run build`, then `npm run preview`, and open the preview.

### Recording

- Start a capture and allow microphone permission.
- Confirm the timer advances without moving or replacing the pause/finish
  controls.
- Pause and confirm the timer stops.
- Resume and confirm the timer continues.
- Open capture settings while recording and confirm capture continues.
- Finish and confirm a meeting opens with an original-recording player.
- Deny microphone permission and confirm the app stays in the ready state with
  a useful error.
- Turn the microphone source off and confirm recording cannot start.

### Playback

- Play through the native audio controls and confirm time advances.
- Open Transcript and use the green waveform play button.
- Confirm the icon changes to pause and elapsed time advances.
- Pause, resume, and seek using the waveform.
- Change tabs while playing and confirm playback resumes from the same
  position.
- Filter the transcript while playing and confirm the audio element is not
  replaced.
- Download the recording and verify the filename and extension.

### Transcript integrity

- With browser recognition disabled or unavailable, confirm no sample
  transcript is inserted.
- With recognition available, confirm only returned recognition text is saved.
- Search for a speaker or phrase and confirm the segment list filters.
- Click a transcript timestamp for a meeting with audio and confirm the player
  seeks.
- Confirm timestamps are plain text when no recording exists.

### Persistence and meeting tools

- Rename a meeting, add notes, toggle an action, and reload.
- Confirm all three changes persist.
- Copy a meeting and inspect the clipboard result.
- Export Markdown and inspect the downloaded file.
- Import WAV or MP3 audio and play it.
- Confirm imported files retain the correct download extension.
- Delete a meeting and confirm it and its audio disappear.
- Simulate a missing IndexedDB recording and confirm controls become disabled
  with a clear unavailable message.

### Library, settings, and keyboard

- Search meetings and clear the search.
- Toggle View all and Show recent.
- Open and close Settings using Done and Escape.
- Change a setting and reload to confirm persistence.
- Press `N` outside a text field to open capture.
- Press `Ctrl+K` or `Cmd+K` to focus meeting search.

### Responsive checks

At 390 x 844 and 320 px wide:

- Confirm there is no horizontal overflow.
- Open and close mobile navigation with both the close button and scrim.
- Record, pause, resume, finish, and play audio.
- Confirm settings remain usable during recording.

## Browser console

Repeat the main workflow with the browser developer console open. Treat
uncaught exceptions, failed asset requests, unhandled promise rejections, and
media decoding failures as test failures.

## Pull request evidence

Include:

- Operating system and browser versions
- Launch method (`file://`, development server, or preview)
- Automated command output
- Manual scenarios exercised
- Screenshots for visual changes
- Confirmation that only synthetic test audio was used
