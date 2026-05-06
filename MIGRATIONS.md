# Migrations

_Online: <https://thekevinscott.github.io/coaxer/migrations/>_

This file is the source of truth for downstream-consumer upgrade instructions
when coaxer ships a breaking change or a notable behavior-only change. See
[CHANGELOG.md](CHANGELOG.md) for the full history of every release — this
file only covers the subset that requires consumer action.

Each entry is scoped to the release that introduced the change and follows a
5-section template:

```markdown
## <version> — <short slug>

### (a) Summary
One paragraph: what broke, why the change was made, who is affected.

### (b) Required changes
| Area | Before | After |
| ---- | ------ | ----- |

### (c) Deprecations removed
(list or "None.")

### (d) Behavior changes without code changes
(list or "None.")

### (e) Verification
Exact command + expected output (or the error a consumer will see if they
skipped a step).
```

---

## Unreleased — red-first PR workflow

No migration required.

---

## Unreleased — red tests for run_sync event-loop lifecycle (#73)

No migration required.

---

## Unreleased — run_sync uses a persistent per-thread event loop (#73)

No migration required.

---

## Unreleased — CI split Python test workflow

No migration required.

---

## Unreleased — npm package: add `repository` + metadata for provenance

No migration required.

---

## Unreleased — remove `bootstrap-npm.yml`; add JS package README

No migration required.

---

## Unreleased — AGENTS.md TDD order: e2e + integration together, both red

No migration required.

---

## Unreleased — TypeScript runtime previewed in docs

No migration required.

---

## Unreleased — `packages/javascript/` JavaScript/TypeScript runtime

No migration required.

---

## Unreleased — `Test (JS)` workflow with diff-cover gate

No migration required.

---

## Unreleased — JS test workflow split into Unit / Integration / Coverage checks

No migration required.

---

## Unreleased — JS package wired into putitoutthere release

No migration required.

---

## Unreleased — one-shot `bootstrap-npm.yml` for first npm publish

No migration required.

---

## Unreleased — JS CI parity: `Type Check (JS)`, `Lint (JS)`, `Build (JS)`

No migration required.

---

## Unreleased — `CoaxedPrompt.response_format`

### (a) Summary
New `@cached_property` on `CoaxedPrompt` returning a Pydantic model class derived from the compiled output schema. Additive — existing flows unchanged. Existing artifacts read fine; `output_name` falls back to `"output"` when absent from `meta.json`.

### (b) Required changes
None. Opt-in.

| Area | Before | After |
| ---- | ------ | ----- |
| Structured output | Hand-build a schema from `meta.json["fields"]["output"]`. | `p.response_format`. |

### (c) Deprecations removed
None.

### (d) Behavior changes without code changes
- `meta.json` gains a top-level `output_name` field (default `"output"`). Files without it still load.
- `pydantic` is now a declared direct dep (was transitive via DSPy).

### (e) Verification
```python
from coaxer import CoaxedPrompt

p = CoaxedPrompt("prompts/repo-classification")
print(p.response_format.model_json_schema())
```

---

## Unreleased — `diff-cover` 100% on new lines

No migration required.

---

## Unreleased — relax `requires-python` to `>=3.13`

### (a) Summary
`pyproject.toml` now declares `requires-python = ">=3.13"` (was `>=3.14`).
Pydantic 2.13.3 calls `typing._eval_type(..., prefer_fwd_module=True)` on
Python 3.14, but that kwarg only landed between 3.14.0rc2 and 3.14 final;
cloud sandbox sessions that uv resolves to 3.14.0rc2 crash at import time.
Lowering the floor unblocks 3.13 consumers and lets uv pick the system 3.13
in those sandboxes — pydantic's `>=3.13` branch doesn't pass the broken
kwarg. Affects: anyone whose lockfile or environment was previously pinned
to 3.14 *because of* this floor; you can now install on 3.13 too. No
behavior change for consumers already on 3.14.

### (b) Required changes

| Area | Before | After |
| ---- | ------ | ----- |
| `pyproject.toml` consumer constraint | `requires-python = ">=3.14"` | `requires-python = ">=3.13"` |

No code or import changes are required for consumers.

### (c) Deprecations removed
None.

### (d) Behavior changes without code changes
None. Coaxer's runtime behavior is unchanged on either 3.13 or 3.14.

### (e) Verification
On Python 3.13 (or 3.14):

```bash
uv pip install coaxer
python -c "from coaxer import CoaxedPrompt; print('ok')"
```

Expected output: `ok`. If you see
`TypeError: _eval_type() got an unexpected keyword argument 'prefer_fwd_module'`,
your environment is still on 3.14.0rc2 with the older `coaxer` install —
re-run `uv sync` against the new lockfile or pin Python to `>=3.13` and
let uv pick a working interpreter.

---

## Unreleased — flat tests converted to `pytest_describe`

No migration required.

---

## Unreleased — drop `COAXER_E2E` gate and `ANTHROPIC_API_KEY` precheck from e2e tests

No migration required.

---

## Unreleased — `release.yml` trim to recommended consumer shape

No migration required.

---

## Unreleased — e2e tests (real OpenAI + Anthropic)

No migration required.

---

## Unreleased — `release.yml`: bump `download-artifact@v4` → `@v8`

No migration required.

---

## Unreleased — `release.yml` `pypi-publish` job: `environment: release`

No migration required.

---

## Unreleased — `release.yml`: caller-side PyPI publish job

No migration required.

---

## Unreleased — `putitoutthere.toml` `paths` → `globs`

No migration required.

---

## Unreleased — fix `release.yml` reusable-workflow ref

No migration required.

---

## Unreleased — release pipeline collapsed onto putitoutthere reusable workflow

No migration required.

---

## Unreleased — `MIGRATIONS.md` is now a per-PR requirement

No migration required.

---

## Unreleased — `AgentLM` defaults `env` to clear `CLAUDECODE`

### (a) Summary
Running `coax --optimizer gepa` (or any `AgentLM` call) from inside a Claude Code session previously failed every rollout with `Claude Code cannot be launched inside another Claude Code session.` because `AgentLM` inherited the parent's `CLAUDECODE` env var; the SDK and CLI refuse nested launches when that variable is set. `AgentLM.__init__` now seeds `kwargs["env"]` with `CLAUDECODE=""` via `setdefault`, so the zero-config nested-session flow works without `CLAUDECODE= coax …` wrappers. Affected: anyone constructing `AgentLM(env=...)` and inspecting the merged kwargs, or anyone explicitly setting `env` on the SDK call site downstream and relying on coaxer not to inject extra keys.

### (b) Required changes

| Area | Before | After |
| ---- | ------ | ----- |
| Nested-session workaround | `CLAUDECODE= coax --optimizer gepa <labels> --out <prompts>` | `coax --optimizer gepa <labels> --out <prompts>` (no wrapper) |
| `AgentLM().kwargs["env"]` | `{}` | `{"CLAUDECODE": ""}` |
| Caller-supplied env merge | `AgentLM(env={"FOO": "bar"}).kwargs["env"] == {"FOO": "bar"}` | `AgentLM(env={"FOO": "bar"}).kwargs["env"] == {"FOO": "bar", "CLAUDECODE": ""}` |
| Explicit override | n/a — coaxer didn't set this key | `AgentLM(env={"CLAUDECODE": "1"})` preserves your value |

### (c) Deprecations removed
None.

### (d) Behavior changes without code changes
- **`AgentLM` always seeds `env` with `CLAUDECODE=""`.** If your downstream code asserts on the exact contents of `lm.kwargs["env"]`, update the expected dict to include the new key. Pass `env={"CLAUDECODE": "1"}` (or any non-empty value) at construction to opt out.
- **Nested-session launches succeed by default.** Previously rolled-out wrappers (`CLAUDECODE= coax …`, `env={"CLAUDECODE": ""}` everywhere AgentLM is constructed) are now redundant and can be dropped — but leaving them in place is harmless.

### (e) Verification

```bash
python -c "from coaxer import AgentLM; print(AgentLM().kwargs['env'])"
```

Should print `{'CLAUDECODE': ''}`. If it prints `{}`, you're still on a pre-fix version.

```bash
CLAUDECODE=1 python -c "from coaxer import AgentLM; print(AgentLM(env={'FOO': 'bar'}).kwargs['env'])"
```

Should print `{'FOO': 'bar', 'CLAUDECODE': ''}` regardless of the parent's `CLAUDECODE`.

---

## Unreleased — caching removed from `AgentLM` / `OpenAILM`

### (a) Summary
Caching the compile-time LM is a deployment concern, not coaxer's. The `cache=` constructor kwarg on `AgentLM` was a duck-typed escape hatch (anything exposing `.wrap(fn) -> fn` worked), but its presence pulled `cachetta` into the project as an installable extra, a dev dep, integration tests, and a docstring section. The `cache=` kwarg, the `[cache]` extra (`coaxer[cache]`), and every `cachetta` reference in the package and tests are gone. Affected: anyone constructing `AgentLM(cache=...)` or installing `coaxer[cache]`. If you still want response caching, wrap the LM yourself — `cachetta` works with any callable that takes a prompt string.

### (b) Required changes

| Area | Before | After |
| ---- | ------ | ----- |
| Install extra | `uv add 'coaxer[cache]'` | `uv add coaxer cachetta` (install `cachetta` directly if you want it) |
| Construct LM with cache | `lm = AgentLM(cache=Cachetta(path=...))` | `lm = AgentLM()` then wrap externally (see snippet below) |
| `copy()` propagating cache | `lm.copy().cache is lm.cache` | No-op — wrap the copy yourself |

External-wrap snippet for consumers who still want disk-backed caching:

```python
from cachetta import Cachetta
from coaxer import AgentLM

lm = AgentLM()
cache = Cachetta(path=lambda prompt, **_: f"cache/{hash(prompt)}.pkl")
cached_forward = cache.wrap(lambda prompt, **kw: lm.forward(prompt=prompt, **kw))

# Use `cached_forward(prompt="...")` instead of `lm.forward(...)`.
# For DSPy integration, subclass AgentLM and override forward/aforward to
# delegate through the wrapped function.
```

### (c) Deprecations removed
- `AgentLM(cache=...)` constructor kwarg.
- `AgentLM.cache` and `AgentLM._cached_query` attributes.
- `coaxer[cache]` installable extra (the `cachetta>=0.6.0` optional dep).
- `cachetta` as a `dev` dependency (it was only there to back the integration tests, which are also gone).

### (d) Behavior changes without code changes
None. If you weren't passing `cache=` and weren't installing `coaxer[cache]`, nothing changes.

### (e) Verification

```bash
python -c "from coaxer import AgentLM; AgentLM(cache=None)"
```

Should raise `TypeError: AgentLM.__init__() got an unexpected keyword argument 'cache'`. If it succeeds silently, you're still on the old version (the kwarg used to be accepted as `cache: Any = None`).

```bash
pip show cachetta 2>/dev/null || echo "not installed"
```

`cachetta` is no longer pulled in transitively by `coaxer` — install it explicitly if you wrap the LM yourself.

---

## Unreleased — sibling-file resolution no longer implies file on slash

### (a) Summary
`_resolve_value` previously raised `FileNotFoundError` for any input whose value contained `/` (or ended in `.md` / `.txt` / `.json` / `.png` / `.jpg` / `.pdf`), assuming it was a sibling-file path. That broke legitimate scalar inputs — GitHub `owner/name`, dates formatted `YYYY/MM/DD`, URLs as strings, etc. Resolution is now driven by `_schema.json`: a field is treated as file-backed when it declares `"type": "file"` or `"backing": "file"`, falling back to implicit resolution only when the value is a plain filename that exists on disk. Affected: any label folder whose schema has scalar inputs that may legitimately contain `/`.

### (b) Required changes

| Area | Before | After |
| ---- | ------ | ----- |
| Scalar input with `/` | Stored in a sibling `.txt` file because `"x": "foo/bar"` raised | `"x": "foo/bar"` works as-is |
| Explicit file-backed input | `"x": "x.md"` (relied on extension heuristic) | Either keep the existing form (still works when `x.md` exists on disk) **or** add `"backing": "file"` (or `"type": "file"`) to the field's `_schema.json` entry to opt in unambiguously |

Example schema with the new opt-in:

```json
{
  "inputs": {
    "readme": {"type": "str", "backing": "file"},
    "repo_name": {"type": "str"}
  },
  "output": {"type": "enum", "values": ["true", "false"]}
}
```

### (c) Deprecations removed
None — this is a behavior fix, not a deprecation removal.

### (d) Behavior changes without code changes
- **`/` in a scalar input value is no longer treated as a path indicator.** Previously raised `FileNotFoundError`; now passes through as a string. If you were relying on the error to catch typos in file paths, mark the field with `"backing": "file"` (or `"type": "file"`) in `_schema.json` to keep that strictness.
- **Extension-based file detection is gone.** Values ending in `.md` / `.txt` / `.json` / `.png` / `.jpg` / `.pdf` are no longer auto-treated as file paths unless the named file actually exists on disk in the record directory or the schema marks the field as file-backed.

### (e) Verification
For a label folder where an input genuinely holds slashes:

```bash
coax labels/my-task --out prompts/my-task --optimizer none
```

Should compile cleanly. Before the fix this would print:

```
FileNotFoundError: Sibling file not found: labels/my-task/0001/expo/skills
```

For a schema-declared file field where the file is missing, you should still see a `FileNotFoundError` mentioning the expected path — the strict mode is now opt-in via schema rather than guessed from the value.

---

## Unreleased — compiled prompt cleanup and enum auto-format

### (a) Summary
The compiled `prompt.jinja` previously contained two cosmetic-but-distracting artifacts: a `..` double-period when `output.desc` ended in `.`, and two `Inputs:` headers (one inline in the instructions block, one as the template's slot block) that read like duplicate sections. Both are fixed: `_build_instructions` now joins parts with `\n\n` and the inline section is titled `Field descriptions:`. Additionally, when `output.type == "enum"`, the compiler auto-appends `Respond with exactly one of: <values>.` so callers no longer have to stuff format hints into `output.desc` themselves. Affected: anyone consuming the compiled `prompt.jinja` artifact downstream — the rendered output text changes shape (no API or parameter changes).

### (b) Required changes

| Area | Before | After |
| ---- | ------ | ----- |
| Compiled instructions inline section | `Inputs: \`x\`: …; \`y\`: …` | `Field descriptions: \`x\`: …; \`y\`: …` |
| Joiner between instruction parts | `". "` (collides with trailing `.`) | `"\n\n"` |
| Enum format hint | Caller stuffed it into `output.desc` manually | Compiler emits `Respond with exactly one of: <values>.` automatically |
| Snapshot / golden-file tests on `prompt.jinja` | Match the old text | Re-record after `coax …` |

If you maintain golden-file tests asserting the exact contents of compiled `prompt.jinja`, regenerate them via `coax <labels> --out <prompts>` — the only changes are in the static instruction text, the variable slots (`{{ field }}`) are unchanged.

If your `output.desc` already ends in a sentence like `Respond with one of: ...` for an enum output, you can drop that line — the compiler now emits it. Leaving it in is harmless but produces a slight duplication.

### (c) Deprecations removed
None.

### (d) Behavior changes without code changes
- **Compiled `prompt.jinja` text is reformatted.** No changes to inputs, no changes to the output schema, no changes to the runtime behavior of `CoaxedPrompt(...)`. Snapshot/golden-file tests that pin the exact instruction text need to be re-recorded.
- **Enum outputs surface their allowed values automatically.** Models receive `Respond with exactly one of: <comma-separated-values>.` as part of the instructions even when `output.desc` doesn't mention them. Compliance with the enum constraint should improve in practice.

### (e) Verification

```bash
coax labels/your-task --out prompts/your-task --optimizer none
grep -c "Inputs:" prompts/your-task/prompt.jinja
# Expected: 1 (the template's slot block)
grep -c "Field descriptions:" prompts/your-task/prompt.jinja
# Expected: 1 (the schema-derived inline block)
grep -c "\.\." prompts/your-task/prompt.jinja
# Expected: 0 (no double-periods)
```

For an enum output, additionally:

```bash
grep "Respond with exactly one of:" prompts/your-task/prompt.jinja
# Expected: a single line listing the enum values, e.g.
# Respond with exactly one of: true, false.
```

---

## 0.3.x — public API replaced

### (a) Summary
Coaxer's public API was rebuilt around a label-folder / compiled-prompt split.
DSPy is no longer part of the exported surface, the CLI binary was renamed
from `coaxer` to `coax`, and the `CoaxPrompt` class was renamed to
`CoaxedPrompt`. The interactive labeling TUI and the `/optimize` skill
installer were removed. Anyone using the 0.2.x public API must update imports,
CLI invocations, and workflow scripts.

### (b) Required changes
| Area            | Before                                   | After                                                |
| --------------- | ---------------------------------------- | ---------------------------------------------------- |
| CLI binary      | `coaxer distill <labels> --out <prompts>` | `coax <labels> --out <prompts>`                      |
| Prompt class    | `from coaxer import CoaxPrompt`           | `from coaxer import CoaxedPrompt`                    |
| Loading a prompt | `coaxer.load_predict("prompts/<name>")`   | `CoaxedPrompt("prompts/<name>")`                     |
| Labeling TUI    | `coaxer label`                            | Removed — edit the label folder directly, or have an agent populate `record.json` + sibling files. |
| Skill installer | `coaxer install`                          | Removed — the `/optimize` skill's workflow is now just `coax`. |

### (c) Deprecations removed
- `coaxer.load_predict` (undocumented path re-export of DSPy's `Predict`).
- `coaxer label` CLI and the `coaxer/tui/` package.
- `coaxer install` CLI and the `coaxer/skills/` package.
- The `coaxer` console script (replaced by `coax`).

### (d) Behavior changes without code changes
- Prompt templating switched from Python-style `{field}` to Jinja2 `{{ field }}`
  to avoid collisions with JSON and code blocks inside labels. Existing prompt
  artifacts compiled with 0.2.x must be rebuilt with `coax`.
- The default optimizer is now `--optimizer none` (schema-derived template, no
  network access). Pass `--optimizer gepa` to opt into DSPy 3 + GEPA
  optimization.

### (e) Verification
```bash
coax --help
```
Should print the new CLI's usage (`coax <labels> --out <prompts> [--optimizer ...]`).

```bash
python -c "from coaxer import CoaxedPrompt; print(CoaxedPrompt.__module__)"
```
Should print `coaxer.prompt` and exit 0. If you see
`ImportError: cannot import name 'CoaxPrompt'` or
`command not found: coaxer`, you're still on 0.2.x.

---

## 0.2.x — package renamed `karat` → `coaxer` and karat shim removed

### (a) Summary
The library was renamed from `karat` to `coaxer` and moved to
`https://github.com/thekevinscott/coaxer`. The `karat` distribution was kept
as a thin re-export shim that emitted a `DeprecationWarning`, then removed
in a later 0.2.x release. Anyone still depending on `karat` must switch the
distribution name and every import.

### (b) Required changes
| Area    | Before                  | After                    |
| ------- | ----------------------- | ------------------------ |
| Install | `uv add karat`          | `uv add coaxer`          |
| Import  | `from karat import X`   | `from coaxer import X`   |
| Repo    | `github.com/.../karat`  | `github.com/thekevinscott/coaxer` |

### (c) Deprecations removed
- The `karat` shim package (`from karat import X` used to re-export from
  `coaxer` with a `DeprecationWarning`). The shim is gone; `karat` on PyPI is
  no longer published.

### (d) Behavior changes without code changes
None.

### (e) Verification
```bash
python -c "from karat import CoaxedPrompt"
```
Should raise `ModuleNotFoundError: No module named 'karat'`. If the import
succeeds, you still have the old shim pinned — check your lockfile for a
`karat` entry and replace it with `coaxer`.

```bash
python -c "from coaxer import CoaxedPrompt; print('ok')"
```
Should print `ok`.
