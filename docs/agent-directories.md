# Agent Directories

This repository keeps shared agent configuration in `.agents/`.

Tool-specific directories are symlinks to the same shared directory:

- `.claude -> .agents`
- `.codex -> .agents`
- `.cursor -> .agents`

This gives each tool its expected local entrypoint while keeping skills and
repository guidance in one place.

Important shared files:

- `.agents/AGENTS.md` is the canonical repository guidance.
- `.agents/CLAUDE.md` points to `AGENTS.md` for Claude-compatible lookup.
- `.agents/skills/` contains reusable workflow skills.
- `.agents/rules/` contains Cursor rules, exposed through `.cursor/rules/`.

## Windows Symlinks

Windows supports this layout directly when Git is allowed to check out real
symlinks. This is the preferred path because the repository records `.claude`,
`.codex`, and `.cursor` as symlinks, so no local ignore rules or generated
directories are needed.

Before cloning on Windows, enable symlink checkout:

```powershell
git config --global core.symlinks true
```

Then clone normally, or set it explicitly for one clone:

```powershell
git clone -c core.symlinks=true <repo-url>
```

Windows also needs permission to create symlinks. Use one of:

- Enable Developer Mode in Windows settings.
- Run the Git shell as Administrator.

If the repository was already cloned with `core.symlinks=false`, Git may have
checked symlinks out as plain text files. Re-enable symlink support, remove
those placeholder files, and restore them from Git.

PowerShell commands:

```powershell
git config core.symlinks true
Remove-Item .claude, .codex, .cursor
git checkout -- .claude .codex .cursor
```

Directory junctions are only a local fallback for environments that cannot use
real symlinks:

```cmd
mklink /J .claude .agents
mklink /J .codex .agents
mklink /J .cursor .agents
```

Do not use junctions as the default setup for tracked symlink paths. They can
make the working tree look different from the Git index and may require local
cleanup. Prefer real Git symlinks for normal Windows development.
