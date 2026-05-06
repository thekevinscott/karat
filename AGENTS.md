# coaxer

Evals-first prompt optimization. Label examples, get better prompts.

## Sandbox

- **All scratch/debug Python scripts must go to `/tmp`**. Never run `python -c` or `python3 -c` inline. Write to `/tmp/coaxer-*.py` and execute that.

## Workflow

- **Always work in a branch or git worktree** -- never commit directly to main
- Work in git worktrees under `.worktrees/` for parallel work, or feature branches for sequential work
- Tie PRs to GitHub issues
- Keep PRs minimal but complete (one self-contained feature)
- Don't add unused code for future PRs

### Issue Tracking (Beads)

Use `bd` (beads) for local issue tracking. One issue per task.

```bash
bd create "title" --description "details"   # Create issue
bd update <id> --status in_progress         # Start work
bd close <id>                               # Done
bd list                                     # Show open issues
```

### Opening PRs

- **Local sessions:** don't open a PR unless I ask.
- **Remote / cloud sessions (Claude Code on the web, sandboxed environments where I can't push from my own machine):** you *should* open a PR once the branch is ready. Push first, then open it against `main` with a summary and test plan. This is the default output of a remote session — waiting for me to ask defeats the point.

### PR Checklist

Before considering a PR complete:
1. **CI checks pass** -- monitor with `gh pr checks <pr-number>` or `gh run list`
2. **GPG commits are verified** -- all commits must be signed
3. **No merge conflicts** -- rebase on main if needed
4. **CHANGELOG.md updated** -- **every PR** adds at least one bullet under `## Unreleased`. No exceptions: bug fixes, refactors, CI, docs, internal-only. We don't follow semver strictly enough to rely on version numbers as the signal, so the audit trail lives in the changelog. Enforced by the `changelog` CI job.
   - **Bypass:** add the trailer `skip-changelog: true` to the PR's merge-commit body (or to every commit in a rebase-merge branch) to skip the check. Use sparingly — dependabot bumps, trivial typo fixes inside docs where the CHANGELOG itself is the touched file, etc. If in doubt, add a line to the changelog.
5. **MIGRATIONS.md updated** -- **every PR** adds at least one entry under `## Unreleased`, parallel to the CHANGELOG entry. For PRs that touch a public-facing surface (see *Scope* below), use the full 5-section template. For PRs with no consumer-facing impact (CI tweaks, internal refactors, doc fixes), use the no-change shorthand: a single `No migration required.` line under a slugged `## Unreleased — <slug>` header. Enforced by the `migrations` CI job — the file must be touched on every PR. Bypass with a `skip-migration: true` trailer (rare — only for CHANGELOG-only follow-ups where even the shorthand is redundant).

### Changelog format

- Sections under `## Unreleased` follow [Keep a Changelog](https://keepachangelog.com): `### Added`, `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`, `### Security`.
- Each bullet starts with a bold lead-in summarizing the change, then explains the *why* in 1-2 sentences. See the existing `## Unreleased` entries for the expected voice.
- Reference the PR/issue number at the end of the bullet when relevant (`(#27)`).
- When the change ships with a migration entry, cross-link: `See [MIGRATIONS.md](MIGRATIONS.md#<anchor>).`

### Migration guide (MIGRATIONS.md)

`MIGRATIONS.md` at the repo root is the **source of truth** for downstream-consumer upgrade instructions. It's also published on the docs site (mkdocs pulls it in directly — do not duplicate content; edit `MIGRATIONS.md` and the docs page updates on the next build).

Each migration entry is scoped to the release that introduced the change and uses this template:

```markdown
## <version-or-unreleased> — <short slug>

### (a) Summary
One paragraph: what broke, why the change was made, who is affected.

### (b) Required changes
Table of before/after snippets for every public-facing touch point: config,
CLI invocation, action inputs, imports, function signatures.

| Area        | Before                | After                  |
| ----------- | --------------------- | ---------------------- |
| Import      | `from karat import X` | `from coaxer import X` |
| CLI command | `coaxer distill ...`  | `coax ...`             |

### (c) Deprecations removed
List anything previously emitting a `DeprecationWarning` that is now fully
gone. If nothing, write "None."

### (d) Behavior changes without code changes
Same API, different runtime behavior: tag formats, exit codes, default values,
file-layout assumptions, network vs. offline behavior, etc. If nothing, write
"None."

### (e) Verification
The exact command a consumer runs to confirm the upgrade worked, plus the
expected output (or the error that proves they forgot a step). Prefer a
dry-run / non-destructive check.
```

Mark the corresponding CHANGELOG bullet in `### Changed` / `### Removed` / `### Deprecated` with **Breaking:** when the migration is required for consumers to keep working.

**No-change shorthand.** When the PR has no consumer-facing surface (CI tweaks, internal refactors, dependency bumps, doc fixes), the entry collapses to a single line — no 5-section template, no before/after table:

```markdown
## Unreleased — <short slug>

No migration required.
```

This keeps `MIGRATIONS.md` mirrored 1:1 with `CHANGELOG.md` so reviewers can scan one file and trust nothing was silently smuggled past the migration check.

**Scope -- what counts as public-facing (full template required):**
- Anything exported from `coaxer/__init__.py`.
- The `coax` CLI surface: flags, positional args, exit codes, stdout/stderr shape.
- The label-folder layout: `_schema.json`, `record.json`, sibling-file conventions.
- The compiled artifact layout: `prompt.jinja`, `meta.json`, `dspy.json`, `history.jsonl`.
- The `AgentLM` / `OpenAILM` constructor kwargs and return shape.

Changes to any of these require the full 5-section template. Anything else takes the no-change shorthand.

## Testing (Red/Green TDD, Outside-In)

1. Write test first (must fail RED)
2. Minimal implementation to pass (GREEN)
3. Refactor if needed

**TDD order: e2e + integration first (both red), then unit.** Every PR that ships a behavioral change lands its e2e tests *and* its integration tests in the same change, both starting RED, and both expected to be GREEN by the time the PR is ready. Unit tests follow once the outer rings are green and the design has settled. Integration without e2e — or e2e without integration — is incomplete: the integration ring proves the wiring; the e2e ring proves it works against a real provider.

**Red-first PR workflow (mandatory).** When fixing a bug or adding a behavioral change, the test commits land *before* the source commits, in the same branch, and the PR is opened with the tests in their RED state. Concretely:

1. Write the integration test(s) that capture the contract the fix must satisfy. They must be RED against the unmodified source.
2. Write the e2e test(s) that exercise the same contract end-to-end against a real provider. They must also be RED.
3. Commit both, push, and open the PR. The integration ring's CI job (`Test Integration`) must report failing for the new tests on the open PR — that's the visible RED state. (E2E tests are not in CI per the existing policy; their RED state is verified locally and noted in the PR description.)
4. *Only then* commit the source changes that turn the tests GREEN. Push again; the same CI checks must report passing on the head commit.

The point: a reviewer scrolling the PR's CI history must see at least one failing CI run on the test-only commits, followed by a passing CI run on the fix commits. No squashing the test+fix into a single commit before push — the audit trail is the proof. After review, the merge strategy can collapse them.

### Coverage policy

**New code ships at 100% line coverage.** New modules, new functions, and new branches added to existing functions must be fully covered by tests. Existing-code shortfalls are converted opportunistically alongside other changes — no backfill sprint.

Enforced by the `Test` CI job via `diff-cover`: on every PR, lines added in the diff (vs. the base branch) must be 100% covered or the job fails. The project-wide `fail_under` floor in `pyproject.toml` is a separate, weaker gate.

**`pragma: no cover` discipline.** Allowed for genuinely unreachable code — defensive `else` after exhausted `if/elif`, `TYPE_CHECKING` blocks, `__main__` guards, re-raises after logging. **Every pragma must carry an inline reason** on the same line: `# pragma: no cover -- TYPE_CHECKING block`. A bare `# pragma: no cover` is a code-review red flag.

Run locally before pushing:

```bash
uv run just test-ci      # produces coverage.xml
uv run just diff-cover   # fails if any new line is uncovered
```

### Test organization

- **Unit tests** (`coaxer/*_test.py`): colocated, mock everything except the function under test
- **Integration tests** (`tests/integration/`): test multiple modules together with mocked externals (SDK, filesystem). ALL integration tests go here, not colocated.
- **E2E tests** (`tests/e2e/`): hit a real LLM endpoint (Anthropic) with real credentials. **Mock nothing.** Drive the `coax` CLI as a subprocess (no internal Python imports of `distill()`) so the user-facing entry point is what's verified end-to-end. CI never points pytest at this directory; running them is the agent's call.

### Test structure

- **Wrap related tests in `pytest_describe` blocks.** `describe_<thing>` for the unit under test, `it_<does_something>` for each behavior. Nest `describe_*` for sub-cases. New tests should follow this shape; old flat `def test_*` tests are being converted opportunistically.
- **Use `pytest.mark.parametrize` where appropriate.** Whenever the same assertion shape repeats with different inputs (type mappings, enum values, before/after pairs), parametrize. Beats copy-pasted tests.

### Running Tests

```bash
uv run just test-unit        # Unit tests (colocated *_test.py)
uv run just test-integration # Integration tests
uv run just test-e2e         # E2E tests (real Anthropic; costs money)
uv run just test-cov         # Unit tests with coverage
uv run just ci               # Full local CI (lint + format + typecheck + tests)
```

### When to run E2E (agent policy)

E2E tests are **not** part of CI — they cost money and depend on live provider behavior. The agent (Claude Code) runs them locally as part of the development loop on a strict surface-area rule:

**Run e2e before declaring a PR ready when the change touches:**
- `meta.json` shape — anything affecting how the output schema is persisted
- `coaxer/cli.py` flags or stdout/stderr shape that consumers script against
- The documented Anthropic call shape in `docs/api/coaxed-prompt.md`

**Skip e2e for** PRs that don't touch the SDK contract surface (CI tweaks, internal refactors, doc-only changes, unit-test-only changes).

Failures block the PR until resolved, the same way unit/integration failures do.

**Credentials.** `claude_agent_sdk` shells out to the local `claude` CLI. The agent's own runs piggyback on its existing Claude Code session, so no credentials need to be set explicitly. CI never runs these.

## Code Style

- **One function per file** -- `extract_prompt.py` contains `extract_prompt()`
- **Multi-function -> package** -- Promote to directory with `__init__.py`
- **Colocated tests** -- `foo.py` -> `foo_test.py`
- **Test naming** -- Files end in `_test.py` (not `test_*.py`)
- **Docstrings**: Skip Args/Returns/Raises; use for *why*, not *how*
- **Type hints**: Prefer fixing issues over `# type: ignore`
- **Module organization**: `_internal/` for private utilities

## Commit Convention (Conventional Commits)

- `feat:` -- New user-facing functionality
- `fix:` -- Bug fixes
- `test:` -- Test additions
- `chore:` -- CI, tooling, maintenance
- `refactor:` -- Code restructuring
- `docs:` -- Documentation

### Trailers

- `release: <patch|minor|major|skip>` -- determines the release bump on merge. See `putitoutthere/AGENTS.md` for scoping and semantics.
- `skip-changelog: true` -- bypass the `changelog` CI job for this PR. Use rarely.
- `skip-migration: true` -- bypass the `migrations` CI job for this PR. Only valid when the `release:` trailer is `minor` or `major` and the change genuinely has no consumer surface (e.g. an internal refactor that warrants a feature bump because of a new optional API but doesn't break existing callers). Use sparingly.

## Project Structure

```
coaxer/                   # Main package
  _internal/              # Private utilities (run_sync, etc.)
  prompt.py               # CoaxedPrompt - str subclass, Jinja2 render
  compiler.py             # distill() - label folder -> prompt artifact
  records.py              # Read label folder into Record objects
  schema.py               # Parse/infer _schema.json
  signature.py            # Build DSPy Signature dynamically (internal)
  cli.py                  # CLI entry point (coax)
  lm.py                   # AgentLM - DSPy LM backed by Agent SDK
  openai_lm.py            # OpenAILM - DSPy LM for OpenAI-compatible endpoints
  for_query.py            # Async generator over SDK query blocks
  query_assistant_text.py # Extract text from assistant responses
  extract_prompt.py       # Normalize DSPy prompt formats
  dataclasses.py          # OpenAI-compatible response types
tests/
  __fixtures__/labels/demo/   # Label-folder fixture used by distill + records tests
  integration/            # Integration tests (mocked SDK)
  e2e/                    # E2E tests against real Anthropic (agent-run; not part of CI)
```

## Key Commands

```bash
uv run just lint          # Ruff lint
uv run just format        # Ruff format
uv run just typecheck     # ty type check
uv run just test-unit     # pytest (colocated tests)
uv run just ci            # Full CI pipeline
uv run just build         # Build package
```
