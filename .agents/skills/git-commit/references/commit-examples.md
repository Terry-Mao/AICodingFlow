# Commit message examples

## Good examples

### Bug fix

```text
fix(router): avoid nil worker panic during reconnect
```

```text
fix(auth): preserve session after token refresh race
```

### Feature

```text
feat(editor): add slash command search for recent notes
```

### Refactor

```text
refactor(runtime): split worker lifecycle management
```

### Performance

```text
perf(cache): reduce kv allocator fragmentation
```

With body:

```text
perf(cache): reduce kv allocator fragmentation

Reuse fixed-size cache pages during mixed prefill/decode
workloads to reduce allocator churn and tail latency.
```

### Docs

```text
docs(api): clarify webhook retry semantics
```

### Tests

```text
test(queue): cover retry ordering under backpressure
```

---

## Weak examples

Avoid messages like:

```text
update
misc fixes
wip
changes
stuff
final
more work
```

These are too vague and do not help review, rollback, or future debugging.

---

## Boundary examples

### Keep together

Bug fix + directly related test:

```text
fix(parser): reject invalid nested frontmatter blocks
```

Includes:
- parser fix
- one or more tests proving the fix

### Split apart

Refactor + bug fix:

Commit 1:

```text
refactor(parser): extract token boundary helpers
```

Commit 2:

```text
fix(parser): preserve offsets for escaped delimiters
```

### Split docs cleanup from feature work

Commit 1:

```text
feat(cli): add --json output for session status
```

Commit 2:

```text
docs(cli): remove outdated examples from status section
```

---

## Scope examples

Prefer specific scopes when obvious:

- `fix(router): ...`
- `perf(cache): ...`
- `refactor(runtime): ...`
- `docs(config): ...`
- `test(scheduler): ...`

If scope is unclear, omit it:

```text
fix: prevent duplicate retry scheduling on restart
```

## Issue linking examples

### Auto-closing footer

```text
fix(router): avoid nil worker panic during reconnect

Fixes #123
```

Use this only when the commit should close the issue.

### Related issue footer

```text
docs(skill): clarify branch naming safeguards

Refs #123
```

Use this for related, partial, preparatory, docs-only, tests-only, cleanup-only,
or ambiguous work. Prefer it when the issue ID comes only from the branch name.

### Inline style

```text
fix(router): avoid nil worker panic during reconnect (#123)
```

Use inline style only when the repository convention requires it.
