"""Distill pipeline: label folder → compiled prompt artifact.

```
coax labels/foo --out prompts/foo
```

Reads records + schema, builds a DSPy signature, optionally runs an
optimizer (GEPA), renders a Jinja2 template, and writes
`prompt.jinja`, `meta.json`, `dspy.json` (if optimized), and appends
to `history.jsonl`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from coaxer.records import load_records
from coaxer.schema import Schema, infer_schema, load_schema
from coaxer.signature import build_signature

if TYPE_CHECKING:
    import dspy

_VALID_OPTIMIZERS = {None, "gepa"}


def distill(
    labels_dir: str | Path,
    out_dir: str | Path,
    *,
    lm: Any = None,
    reflection_lm: Any = None,
    optimizer: str | None = None,
    output_name: str = "output",
) -> Path:
    if optimizer not in _VALID_OPTIMIZERS:
        raise ValueError(f"Unknown optimizer: {optimizer!r}. Expected one of {_VALID_OPTIMIZERS}")

    labels = Path(labels_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    records = load_records(labels)
    schema = load_schema(labels) or infer_schema(records)
    signature = build_signature(schema, output_name=output_name)

    program = _optimize(
        signature,
        records,
        output_name=output_name,
        lm=lm,
        reflection_lm=reflection_lm,
        optimizer=optimizer,
    )

    template = _render_template(signature, schema)
    (out / "prompt.jinja").write_text(template)

    if program is not None:
        (out / "dspy.json").write_text(_dump_program(program))

    meta = {
        "compiled_at": datetime.now(UTC).isoformat(),
        "optimizer": optimizer,
        "example_count": len(records),
        "label_hash": _hash_labels(labels),
        "output_name": output_name,
        "fields": {
            "inputs": {n: asdict(f) for n, f in schema.inputs.items()},
            "output": asdict(schema.output),
        },
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))

    with (out / "history.jsonl").open("a") as f:
        f.write(json.dumps(meta) + "\n")

    return out


def _optimize(
    signature: type[dspy.Signature],
    records: list,
    *,
    output_name: str,
    lm: Any,
    reflection_lm: Any,
    optimizer: str | None,
) -> Any:
    if optimizer is None:
        return None
    if optimizer == "gepa":
        return _run_gepa(
            signature,
            records,
            output_name=output_name,
            lm=lm,
            reflection_lm=reflection_lm,
        )
    raise ValueError(f"Unknown optimizer: {optimizer!r}")


def _parse_json_object(value: Any) -> dict | None:
    """Return value parsed as a JSON object, or None if not a JSON object string."""
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _run_gepa(
    signature: type[dspy.Signature],
    records: list,
    *,
    output_name: str,
    lm: Any,
    reflection_lm: Any,
) -> Any:
    import dspy

    if lm is None:
        raise ValueError("GEPA requires an `lm` argument (AgentLM, OpenAILM, or any dspy.LM)")

    # DSPy 3's dspy.GEPA asserts reflection_lm is not None at construction time.
    # Default to the program's main lm so `coax --optimizer gepa` works zero-config.
    if reflection_lm is None:
        reflection_lm = lm

    program = dspy.Predict(signature)
    trainset = [
        dspy.Example(**r.inputs, **{output_name: r.output}).with_inputs(*r.inputs) for r in records
    ]

    def metric(
        gold: Any,
        pred: Any,
        trace: Any = None,  # noqa: ARG001
        pred_name: Any = None,  # noqa: ARG001
        pred_trace: Any = None,  # noqa: ARG001
    ) -> float:
        gold_val = getattr(gold, output_name, None)
        pred_val = getattr(pred, output_name, None)
        gold_obj = _parse_json_object(gold_val)
        pred_obj = _parse_json_object(pred_val)
        if gold_obj is not None and pred_obj is not None:
            # Both sides decode to JSON objects -- score per-key agreement so
            # whitespace and key order don't matter and GEPA sees a gradient
            # when only some fields are wrong. Pure byte-match here returns
            # 0.0 for every realistic LM output and GEPA stalls (#75).
            keys = set(gold_obj) | set(pred_obj)
            if not keys:
                return 1.0
            matches = sum(1 for k in keys if gold_obj.get(k) == pred_obj.get(k))
            return matches / len(keys)
        return 1.0 if pred_val == gold_val else 0.0

    with dspy.context(lm=lm):
        optimizer = dspy.GEPA(
            metric=metric,
            auto="light",
            reflection_lm=reflection_lm,
        )
        return optimizer.compile(program, trainset=trainset)


def _render_template(signature: type[dspy.Signature], schema: Schema) -> str:
    instructions = signature.instructions or ""
    lines = [instructions.strip(), "", "Inputs:"]
    for name in schema.inputs:
        lines.append(f"- {name}: {{{{ {name} }}}}")
    lines.append("")
    lines.append("Respond with the predicted output.")
    return "\n".join(lines) + "\n"


def _dump_program(program: Any) -> str:
    if hasattr(program, "dump_state"):
        state = program.dump_state()
        return json.dumps(state, indent=2, default=str)
    return json.dumps({"repr": repr(program)}, indent=2)


def _hash_labels(labels_dir: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(labels_dir.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(labels_dir).as_posix().encode())
            h.update(b"\0")
            h.update(p.read_bytes())
    return h.hexdigest()[:16]
