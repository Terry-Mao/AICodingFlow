# AICodingFlow

AI coding workflow helpers built around Codex skills for Git, pull requests, and offline PR review.

## Install

Install the skills into the local Codex agents directory:

```bash
mkdir -p ~/.agents/skills
for skill in skills/*; do
  [ -d "$skill" ] || continue
  rsync -a "$skill/" "$HOME/.agents/skills/$(basename "$skill")/"
done
```

This makes the skills available from:

```text
~/.agents/skills/git-branch
~/.agents/skills/git-commit
~/.agents/skills/git-push
~/.agents/skills/create-pr
~/.agents/skills/review-pr
```

To preview what would change before installing, run:

```bash
for skill in skills/*; do
  [ -d "$skill" ] || continue
  rsync -ani "$skill/" "$HOME/.agents/skills/$(basename "$skill")/"
done
```

The install command updates only the skill directories present in this repository. It does not delete other skills under `~/.agents/skills/`.

## GitHub PR Review Template

The GitHub Actions workflow and helper scripts live in the repository root `.github/` directory.
To enable the PR review workflow in another repository, copy `.github/` from this repository into the target repository root.

There is no separate `assets/.github/` template; `.github/` is the single source for the workflow and scripts.
