#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: install.sh [--target <path>] [--dry-run]

Install AICodingFlow files into a target repository.

Options:
  --target <path>  Target repository path. Defaults to the current directory.
  --dry-run        Print planned copies and skips without writing files.
  -h, --help       Show this help message.

Examples:
  ./install.sh --target /path/to/repo
  ./install.sh --target /path/to/repo --dry-run
  curl -fsSL https://raw.githubusercontent.com/Terry-Mao/AICodingFlow/main/install.sh | bash -s -- --target /path/to/repo
USAGE
}

fail() {
  printf 'install.sh: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '%s\n' "$*"
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target_dir="$(pwd)"
dry_run=false
install_repository="${AICODINGFLOW_INSTALL_REPOSITORY:-https://github.com/Terry-Mao/AICodingFlow.git}"

is_source_tree() {
    [ -f "$script_dir/install.sh" ] &&
    [ -f "$script_dir/AGENTS.md" ] &&
    [ -d "$script_dir/.agents/skills" ] &&
    [ -d "$script_dir/.agents/contracts" ] &&
    [ -d "$script_dir/.github/skills" ] &&
    [ -d "$script_dir/.github/workflows" ]
}

if ! is_source_tree; then
  command -v git >/dev/null 2>&1 || fail "git is required for remote installation"
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT
  git clone --depth 1 "$install_repository" "$tmpdir/AICodingFlow" >/dev/null
  bash "$tmpdir/AICodingFlow/install.sh" "$@"
  exit $?
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || fail "--target requires a path"
      target_dir="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      fail "unknown option: $1"
      ;;
    *)
      target_dir="$1"
      shift
      ;;
  esac
done

command -v rsync >/dev/null 2>&1 || fail "rsync is required but was not found"

[ -d "$target_dir" ] || fail "target path is not a directory: $target_dir"
[ -d "$script_dir/.agents/skills" ] || fail "source .agents/skills directory is missing"
[ -d "$script_dir/.agents/contracts" ] || fail "source .agents/contracts directory is missing"
[ -d "$script_dir/.github/skills" ] || fail "source .github/skills directory is missing"

target_dir="$(cd "$target_dir" && pwd)"

copy_dir() {
  local src="$1"
  local dest="$2"
  shift 2

  if [ "$dry_run" = true ]; then
    info "Would sync $src -> $dest"
  else
    mkdir -p "$dest"
    rsync -a "$@" "$src/" "$dest/"
  fi
}

cleanup_legacy_agent_skills() {
  local skills_dest="$target_dir/.agents/skills"
  local github_skills_dest="$target_dir/.github/skills"
  local name legacy dest
  local legacy_workflow_skills=(
    check-impl-against-spec
    create-product-spec
    create-tech-spec
    dedupe-issue
    implement-issue
    implement-specs
    product-change-report
    product-docs-sync
    product-wiki
    review-pr
    review-spec
    security-review-pr
    security-review-spec
    triage-issue
    update-dedupe
    update-pr-review
    update-triage
  )
  local legacy_companion_skills=(
    dedupe-issue-repo
    review-pr-repo
    review-spec-repo
    triage-issue-repo
  )

  [ -d "$skills_dest" ] || return 0

  for name in "${legacy_workflow_skills[@]}"; do
    legacy="$skills_dest/$name"
    [ -e "$legacy" ] || continue
    if [ "$dry_run" = true ]; then
      info "Would remove legacy workflow skill: .agents/skills/$name"
    else
      rm -rf "$legacy"
    fi
  done

  for name in "${legacy_companion_skills[@]}"; do
    legacy="$skills_dest/$name"
    dest="$github_skills_dest/$name"
    [ -e "$legacy" ] || continue

    if [ -e "$dest" ]; then
      info "Preserving existing .github/skills/$name; leaving legacy companion at .agents/skills/$name"
      continue
    fi

    if [ "$dry_run" = true ]; then
      info "Would migrate legacy repo-local companion skill: .agents/skills/$name -> .github/skills/$name"
    else
      mkdir -p "$github_skills_dest"
      mv "$legacy" "$dest"
    fi
  done
}

sync_skills() {
  local skills_src="$script_dir/.agents/skills"
  local skills_dest="$target_dir/.agents/skills"
  copy_dir "$skills_src" "$skills_dest" --exclude '*-repo'
}

sync_github_skills() {
  local skills_src="$script_dir/.github/skills"
  local skills_dest="$target_dir/.github/skills"
  local skill name dest

  if [ "$dry_run" = false ]; then
    mkdir -p "$skills_dest"
  fi

  for skill in "$skills_src"/*; do
    [ -d "$skill" ] || continue
    name="$(basename "$skill")"
    dest="$skills_dest/$name"

    if [[ "$name" == *-repo ]]; then
      info "Skipping repo-local companion skill: .github/skills/$name/SKILL.md"
      continue
    fi

    copy_dir "$skill" "$dest"
  done
}

sync_github_dirs() {
  local dirname src dest

  for dirname in agents scripts workflows; do
    src="$script_dir/.github/$dirname"
    [ -d "$src" ] || continue
    dest="$target_dir/.github/$dirname"
    if [ "$dirname" = "workflows" ]; then
      copy_dir "$src" "$dest" --exclude ci.yml
    else
      copy_dir "$src" "$dest"
    fi
  done
}

cleanup_legacy_agent_skills
sync_skills
copy_dir "$script_dir/.agents/contracts" "$target_dir/.agents/contracts"
sync_github_skills
sync_github_dirs

if [ "$dry_run" = true ]; then
  info "Dry run complete. No files were written."
else
  info "AICodingFlow installation complete."
fi

cat <<'NEXT'

Optional next step for first-time issue triage setup:
$bootstrap-issue-config

This optional bootstrap uses the GitHub CLI and may create labels or update .github/CODEOWNERS.
It is intended for first-time triage setup, not regular scheduled runs.
NEXT
