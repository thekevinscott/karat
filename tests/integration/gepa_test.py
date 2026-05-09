"""Integration test: ``distill(..., optimizer='gepa', lm=...)`` writes
``dspy.json`` with non-empty program state.

DSPy's GEPA runs many internal LM calls against a real optimizer loop --
well outside the integration scope. We stub ``dspy.GEPA`` so its ``.compile()``
returns a program stub whose ``dump_state()`` emits a small dict, then verify
that the stubbed program state lands on disk via the real
``_dump_program``/``distill`` path. The AgentLM is pointed at a mocked
``run_sync`` so nothing ever reaches the Claude Agent SDK.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import pytest

from coaxer.compiler import distill
from coaxer.lm import AgentLM

FIXTURE = Path(__file__).resolve().parents[1] / "__fixtures__" / "labels" / "demo"


class _StubProgram:
    """Minimal object that mimics a compiled DSPy program for serialization."""

    def dump_state(self) -> dict:
        return {
            "signature": "stub",
            "demos": [],
            "predictors": {"output": {"prompt": "stub-prompt"}},
        }


class _StubOptimizer:
    def __init__(self, *_: object, **__: object) -> None:
        self.compile_calls: list[tuple[object, object]] = []

    def compile(self, program, *, trainset):
        self.compile_calls.append((program, trainset))
        return _StubProgram()


class _MetricCapturingOptimizer:
    """Mirrors DSPy 3's ``dspy.GEPA.__init__`` metric-signature check.

    DSPy 3 calls ``inspect.signature(metric).bind(None, None, None, None, None)``
    to enforce a 5-arg contract ``(gold, pred, trace, pred_name, pred_trace)``.
    Using a stub that replicates this check keeps the test fast (no real GEPA
    loop) while still failing if ``_run_gepa``'s metric drifts from the
    contract.
    """

    captured_metric: object = None

    def __init__(self, *, metric: object, **_: object) -> None:
        inspect.signature(metric).bind(None, None, None, None, None)
        _MetricCapturingOptimizer.captured_metric = metric

    def compile(self, program, *, trainset):  # noqa: ARG002
        return _StubProgram()


class _KwargsCapturingOptimizer:
    """Captures every kwarg passed to ``dspy.GEPA.__init__``.

    Also enforces DSPy 3's reflection-LM assertion so a regression where
    ``_run_gepa`` stops passing ``reflection_lm`` surfaces here too.
    """

    captured_kwargs: ClassVar[dict] = {}

    def __init__(self, **kwargs: object) -> None:
        # Mirror DSPy 3's assertion so we fail loudly if reflection_lm goes missing.
        assert (
            kwargs.get("reflection_lm") is not None
            or kwargs.get("instruction_proposer") is not None
        ), "GEPA requires reflection_lm or instruction_proposer"
        _KwargsCapturingOptimizer.captured_kwargs = dict(kwargs)

    def compile(self, program, *, trainset):  # noqa: ARG002
        return _StubProgram()


def describe_distill_with_gepa():
    def it_writes_dspy_json_with_program_state(tmp_path: Path) -> None:
        out = tmp_path / "out"

        with (
            patch("coaxer.lm.run_sync", return_value="true"),
            patch("dspy.GEPA", _StubOptimizer),
        ):
            lm = AgentLM()
            distill(FIXTURE, out, lm=lm, optimizer="gepa")

        assert (out / "dspy.json").is_file()
        state = json.loads((out / "dspy.json").read_text())
        # State must be non-empty and reflect our stub's shape.
        assert state
        assert state["signature"] == "stub"
        assert "predictors" in state

    def it_requires_an_lm(tmp_path: Path) -> None:
        """Missing ``lm`` must surface as a clear error, not a silent no-op."""
        out = tmp_path / "out"
        with (
            patch("dspy.GEPA", _StubOptimizer),
            pytest.raises(ValueError, match="GEPA requires an `lm`"),
        ):
            distill(FIXTURE, out, lm=None, optimizer="gepa")

    def it_records_optimizer_in_meta(tmp_path: Path) -> None:
        out = tmp_path / "out"
        with patch("coaxer.lm.run_sync", return_value="true"), patch("dspy.GEPA", _StubOptimizer):
            distill(FIXTURE, out, lm=AgentLM(), optimizer="gepa")

        meta = json.loads((out / "meta.json").read_text())
        assert meta["optimizer"] == "gepa"
        assert meta["example_count"] == 3

    def describe_metric_contract():
        def it_accepts_dspy3_five_arg_signature(tmp_path: Path) -> None:
            """``_run_gepa``'s metric must satisfy DSPy 3's 5-arg contract.

            Regression test for https://github.com/thekevinscott/coaxer/issues/26:
            DSPy 3 validates ``inspect.signature(metric).bind(None, None, None, None, None)``
            inside ``dspy.GEPA.__init__``. A 3-arg metric raises TypeError there.
            """
            out = tmp_path / "out"
            _MetricCapturingOptimizer.captured_metric = None

            with (
                patch("coaxer.lm.run_sync", return_value="true"),
                patch("dspy.GEPA", _MetricCapturingOptimizer),
            ):
                distill(FIXTURE, out, lm=AgentLM(), optimizer="gepa")

            metric = _MetricCapturingOptimizer.captured_metric
            assert metric is not None, "metric was never passed to dspy.GEPA"
            # The 5-arg bind must succeed; this is the exact check DSPy 3 runs.
            inspect.signature(metric).bind(None, None, None, None, None)

            # Sanity: scoring still works -- matching gold/pred yields 1.0, mismatch 0.0.
            class _Obj:
                def __init__(self, **kwargs: object) -> None:
                    self.__dict__.update(kwargs)

            assert metric(_Obj(output="true"), _Obj(output="true")) == 1.0
            assert metric(_Obj(output="true"), _Obj(output="false")) == 0.0

    def describe_reflection_lm():
        def it_defaults_to_main_lm(tmp_path: Path) -> None:
            """Regression for #43: ``_run_gepa`` must pass ``reflection_lm`` to ``dspy.GEPA``.

            DSPy 3's ``dspy.GEPA.__init__`` asserts ``reflection_lm is not None`` when
            no custom ``instruction_proposer`` is set. Without a default, every
            ``coax --optimizer gepa`` invocation crashes before optimization starts.
            The compiler now defaults ``reflection_lm`` to the program's main ``lm`` so
            the zero-config flow works.
            """
            out = tmp_path / "out"
            _KwargsCapturingOptimizer.captured_kwargs = {}

            with (
                patch("coaxer.lm.run_sync", return_value="true"),
                patch("dspy.GEPA", _KwargsCapturingOptimizer),
            ):
                lm = AgentLM()
                distill(FIXTURE, out, lm=lm, optimizer="gepa")

            captured = _KwargsCapturingOptimizer.captured_kwargs
            assert captured.get("reflection_lm") is lm, (
                "reflection_lm should default to the main lm when not explicitly provided"
            )

        def it_accepts_explicit_override(tmp_path: Path) -> None:
            """An explicit ``reflection_lm`` overrides the main-lm default."""
            out = tmp_path / "out"
            _KwargsCapturingOptimizer.captured_kwargs = {}

            with (
                patch("coaxer.lm.run_sync", return_value="true"),
                patch("dspy.GEPA", _KwargsCapturingOptimizer),
            ):
                main_lm = AgentLM()
                reflection_lm = AgentLM()
                distill(FIXTURE, out, lm=main_lm, reflection_lm=reflection_lm, optimizer="gepa")

            captured = _KwargsCapturingOptimizer.captured_kwargs
            assert captured.get("reflection_lm") is reflection_lm
            assert captured.get("reflection_lm") is not main_lm

    def describe_default_metric_handles_structured_output():
        """Regression for #75: the bundled metric is byte-exact, so JSON
        outputs that differ only in formatting score ``0.0`` and GEPA gets
        no signal. The fix: when both gold and pred parse as JSON objects,
        score per-field agreement; fall back to exact match otherwise.
        """

        def _capture_metric(tmp_path: Path):
            out = tmp_path / "out"
            _MetricCapturingOptimizer.captured_metric = None
            with (
                patch("coaxer.lm.run_sync", return_value="true"),
                patch("dspy.GEPA", _MetricCapturingOptimizer),
            ):
                distill(FIXTURE, out, lm=AgentLM(), optimizer="gepa")
            metric = _MetricCapturingOptimizer.captured_metric
            assert metric is not None
            return metric

        class _Obj:
            def __init__(self, **kwargs: object) -> None:
                self.__dict__.update(kwargs)

        def it_scores_semantically_equivalent_json_as_one(tmp_path: Path) -> None:
            """Same JSON object, different whitespace and key order = 1.0."""
            metric = _capture_metric(tmp_path)
            gold_pretty = (
                "{\n"
                '  "includes_what_it_does": false,\n'
                '  "includes_when_to_use": false,\n'
                '  "mentions_file_types": false\n'
                "}"
            )
            pred_compact = (
                '{"mentions_file_types":false,'
                '"includes_when_to_use":false,'
                '"includes_what_it_does":false}'
            )
            score = metric(_Obj(output=gold_pretty), _Obj(output=pred_compact))
            assert score == 1.0, f"semantically-equivalent JSON should score 1.0, got {score}"

        def it_gives_partial_credit_on_json_field_disagreement(tmp_path: Path) -> None:
            """One of two fields wrong = score in (0, 1) so GEPA sees a gradient."""
            metric = _capture_metric(tmp_path)
            gold = '{"a": false, "b": false}'
            pred = '{"a": false, "b": true}'
            score = metric(_Obj(output=gold), _Obj(output=pred))
            assert 0.0 < score < 1.0, f"partial match should score in (0, 1), got {score}"

        def it_falls_back_to_exact_match_on_non_json(tmp_path: Path) -> None:
            """Non-JSON outputs (e.g. enum strings) keep exact-match behavior."""
            metric = _capture_metric(tmp_path)
            assert metric(_Obj(output="true"), _Obj(output="true")) == 1.0
            assert metric(_Obj(output="true"), _Obj(output="false")) == 0.0
