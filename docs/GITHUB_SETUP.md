# GitHub publishing checklist

The repository is ready to publish, but the GitHub owner and repository URL
must be chosen by the maintainer.

## Important remote configuration

The existing `origin` remote is used by the connected Sites deployment. Do not
replace or remove it.

After creating an empty GitHub repository, add GitHub as a second remote:

```bash
git remote add github https://github.com/OWNER/notesbuddy.git
git push -u github main
```

For SSH:

```bash
git remote add github git@github.com:OWNER/notesbuddy.git
git push -u github main
```

Verify both remotes:

```bash
git remote -v
```

Future source updates can be pushed independently:

```bash
git push github main
```

The managed Sites remote uses short-lived deployment credentials. Continue to
publish the deployed site through the connected Sites workflow instead of
assuming a normal unauthenticated `git push origin` will work.

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
- Confirm seed meeting text contains no confidential information.
- Confirm Git history contains no credentials, customer data, or recordings.
- Confirm the managed Sites remote URL and project metadata may be disclosed.
- Confirm `.openai/hosting.json` is appropriate to publish.
- Decide whether the owner-restricted live preview should remain in README.
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

The workflow deliberately uses read-only `contents` permission.

## First release

Once the license and ownership decisions are complete:

1. Run `npm test`.
2. Complete the manual checklist in [TESTING.md](TESTING.md).
3. Update [CHANGELOG.md](../CHANGELOG.md).
4. Create an annotated tag, for example `v0.1.0`.
5. Push the tag to the GitHub remote.
6. Create a GitHub Release using the matching changelog section.

Example:

```bash
git tag -a v0.1.0 -m "NotesBuddy v0.1.0"
git push github v0.1.0
```
