# GitHub publishing checklist

The `main` branch is configured to publish the tested `dist/client` bundle to
GitHub Pages at <https://sumarahmed.github.io/AINotesBuddy/>. Feature branches
and pull requests run checks but do not deploy.

## Important remote configuration

This workspace uses `github` for the public repository:

```bash
git remote get-url github
# https://github.com/sumarahmed/AINotesBuddy.git
```

If cloning elsewhere:

```bash
git clone https://github.com/sumarahmed/AINotesBuddy.git
```

Verify both remotes:

```bash
git remote -v
```

Future source updates can be pushed independently:

```bash
git push github main
```

The local `sites` remote and `.openai/hosting.json` belong to an earlier
owner-restricted preview. They are not used by the GitHub Actions workflow.
Changing or deploying that target is a separate explicit operation.

## Suggested repository metadata

Description:

> Private, local-first meeting capture, playback, transcript, and notes
> prototype built with browser platform APIs.

Suggested topics:

- meeting-notes
- local-first
- media-recorder
- indexeddb
- speech-recognition
- vanilla-javascript
- privacy
- productivity

## Before making the repository public

- Select and add a license.
- Confirm the project name and branding are approved for public use.
- Confirm Git history contains no credentials, customer data, or recordings.
- Confirm the legacy Sites remote/project metadata may remain in repository
  history or remove it in a separate reviewed change.
- Enable private vulnerability reporting in **Settings > Code security**.
- Review organization policies, if publishing under a company account.

## Recommended GitHub settings

- Default branch: `main`
- Issues: enabled
- Pull requests: enabled
- Actions workflow permissions: read repository contents
- Branch protection or ruleset:
  - Require a pull request before merging
  - Require the `Repository check` status
  - Require conversations to be resolved
  - Block force pushes and branch deletion

The repository-check workflow deliberately uses read-only `contents`
permission. The Pages deployment job additionally receives only `pages: write`
and `id-token: write`, as required by GitHub Pages.

## First release

Once the license and ownership decisions are complete:

1. Run `npm test`.
2. Run the local-companion API tests.
3. Complete the manual checklist in [TESTING.md](TESTING.md).
4. Update [CHANGELOG.md](../CHANGELOG.md).
5. Create an annotated tag, for example `v0.1.0`.
6. Push the tag to the GitHub remote.
7. Create a GitHub Release using the matching changelog section.

Example:

```bash
git tag -a v0.1.0 -m "NotesBuddy v0.1.0"
git push github v0.1.0
```
