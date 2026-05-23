# Agent Directories

This repository keeps shared agent configuration in `.agents/`.

Tool-specific directories are real directories that expose the shared files each
tool expects:

- `.codex/skills -> ../.agents/skills`
- `.codex/AGENTS.md -> ../.agents/AGENTS.md`
- `.claude/skills -> ../.agents/skills`
- `.claude/CLAUDE.md -> ../.agents/AGENTS.md`
- `.cursor/rules/agents.mdc` is a regular Cursor rule file.

This gives each tool its expected local entrypoint while keeping skills and
repository guidance centralized in `.agents`.

Important shared files:

- `.agents/AGENTS.md` is the canonical repository guidance.
- `.agents/skills/` contains reusable workflow skills.
- `.cursor/rules/agents.mdc` contains Cursor-specific rule guidance.

## Windows Symlinks

Windows supports this layout directly when Git is allowed to check out the
symlinks inside `.claude/` and `.codex/`. The top-level `.claude`, `.codex`,
and `.cursor` paths are ordinary directories.

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
checked the inner symlinks out as plain text files. Re-enable symlink support,
remove those placeholder files, and restore them from Git.

PowerShell commands:

```powershell
git config core.symlinks true
Remove-Item .claude\skills, .claude\CLAUDE.md, .codex\skills, .codex\AGENTS.md
git checkout -- .claude .codex
```

Directory junctions are only a local fallback for environments that cannot use
real symlinks:

```cmd
mklink /J .claude\skills .agents\skills
mklink /J .codex\skills .agents\skills
```

Do not use junctions as the default setup for tracked symlink paths. They can
make the working tree look different from the Git index and may require local
cleanup. Prefer real Git symlinks for normal Windows development.
