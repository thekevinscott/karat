---
name: try-pr
description: Check out a GitHub PR locally, sync its dependencies with `uv`, and print the command to run the `coax` CLI in one step. Use when the user wants to try, test, or run a PR's version of the coaxer CLI. Invoke as `/try-pr <PR#> [-- <cli args>...]`.
---

# try-pr

Fetch a PR branch, sync coaxer's Python environment, and print out how to run it — in one shot.

## Usage

```
/try-pr <PR#> [-- <cli args>...]
```

Examples:
- `/try-pr 42` — checkout PR 42, sync, print the command to run `coax`
- `/try-pr 42 -- path/to/labels --out /tmp/out` — same, but echo the args appended

## Workflow

Run these steps in order. Use a TodoWrite list so the user can see progress.

### 1. Parse args

From the skill `args` string, extract:
- `PR_NUMBER`: the first token, must be a positive integer
- `CLI_ARGS`: everything after the first `--` token (may be empty)

If `PR_NUMBER` is missing or non-numeric, stop and ask the user for a PR number.

### 2. Record starting branch and stash uncommitted work

Record the current branch (`git rev-parse --abbrev-ref HEAD`) so step 5 can tell the user how to return.

Then check `git status --porcelain`. If the tree is dirty, ask the user whether to:
- stash changes (`git stash push -u -m "try-pr <PR#>"`), or
- abort

Never discard uncommitted work without explicit confirmation.

### 3. Fetch and check out the PR

Use git directly (no `gh` CLI is available in remote sessions):

```bash
git fetch origin "pull/<PR#>/head:pr-<PR#>"
git checkout "pr-<PR#>"
```

If the local branch `pr-<PR#>` already exists, force-update it:

```bash
git fetch origin "pull/<PR#>/head"
git checkout -B "pr-<PR#>" FETCH_HEAD
```

If the fetch fails (network error), retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s). If it still fails, surface the error to the user and stop.

### 4. Sync the environment

```bash
uv sync
```

This installs the PR's exact dependency set into `.venv/` so `uv run coax` resolves to the PR's code. If `uv sync` fails, show the error to the user and stop — do not try to "fix" the PR's `pyproject.toml` or lockfile.

### 5. Print how to run `coax` & remind the user how to get back

Echo the invocation, appending `CLI_ARGS` if the user provided any:

```bash
echo 'uv run coax <CLI_ARGS>'
```

Also include:
- which branch they're now on (`pr-<PR#>`)
- how to return to their previous branch — use the name recorded in step 2 (or `git checkout -`)
- if a stash was created, how to restore it (`git stash pop`)

## Notes

- This skill is read-only with respect to the PR: it never pushes, comments, or modifies the PR.
- `coax` is a pure-Python entry point (`coaxer.cli:main`), so there's no compiled binary to build — `uv sync` is the only setup step.
- If the PR changes the lockfile, `uv sync` will reflect that automatically; no extra flags needed.
