"""E2E: ``coax distill`` (CLI subprocess) → real ``claude_agent_sdk``.

Drives the user-facing ``coax`` CLI as a subprocess, then renders the
resulting artifact and feeds it to ``AgentLM`` — the same provider
integration coaxer ships. Asserts on schema/format conformance, never on
response content.

Each describe block is one CLI surface: the demo classifier, the GEPA
optimizer flag, non-string output types, the ``--output-name`` flag, and
file-backed inputs.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from coaxer.prompt import CoaxedPrompt

from ..conftest import DEMO_FIXTURE, run_coax

if TYPE_CHECKING:
    from coaxer.lm import AgentLM


def _agent_response(lm: AgentLM, prompt: str) -> str:
    return lm.forward(prompt=prompt).choices[0].message.content.strip()


def describe_distill():
    def describe_demo_classifier():
        def it_returns_one_of_the_enum_values(
            agent_lm: AgentLM,
            demo_artifact: Path,
            demo_meta: dict,
            demo_inputs: dict,
        ) -> None:
            rendered = CoaxedPrompt(demo_artifact)(**demo_inputs)
            enum_values = demo_meta["fields"]["output"]["values"]

            text = _agent_response(agent_lm, rendered).lower()

            assert any(v.lower() in text for v in enum_values), (
                f"expected response to contain one of {enum_values}, got: {text!r}"
            )

    def describe_with_gepa_optimizer():
        def it_writes_dspy_json_and_round_trips_in_schema(
            agent_lm: AgentLM,
            demo_inputs: dict,
            tmp_path: Path,
        ) -> None:
            """``--optimizer gepa`` runs nested AgentLM rollouts against the network.

            Light mode keeps cost to a handful of LM calls. The optimized
            artifact must still produce in-schema responses.
            """
            out = tmp_path / "gepa_artifact"
            run_coax(str(DEMO_FIXTURE), "--out", str(out), "--optimizer", "gepa")
            assert (out / "dspy.json").is_file()
            meta = json.loads((out / "meta.json").read_text())
            assert meta["optimizer"] == "gepa"

            rendered = CoaxedPrompt(out)(**demo_inputs)
            text = _agent_response(agent_lm, rendered).lower()
            enum_values = meta["fields"]["output"]["values"]
            assert any(v.lower() in text for v in enum_values), (
                f"expected response to contain one of {enum_values}, got: {text!r}"
            )

    def describe_with_gepa_on_json_output():
        def it_emits_nonzero_score_signal(
            make_label_folder: Callable[..., Path],
            tmp_path: Path,
        ) -> None:
            """Regression for #75. With JSON-shaped gold outputs, the
            byte-exact default metric returns 0.0 for every prediction —
            the LM never produces output with the exact whitespace and key
            order the gold uses, so GEPA gets no signal.

            Contract: at least one of the per-candidate scores GEPA prints
            during compile must be ``> 0``. Pre-fix, every score in stdout
            is ``0.0``; post-fix, the JSON-aware default scores per-field
            agreement so semantically-correct predictions register.
            """
            labels = make_label_folder(
                schema={
                    "inputs": {"text": {"desc": "Short text snippet"}},
                    "output": {
                        "desc": (
                            "JSON object with two boolean keys: "
                            "'positive' (text expresses positive sentiment) and "
                            "'negative' (text expresses negative sentiment). "
                            "Output the raw JSON object only — no prose."
                        ),
                        "type": "str",
                    },
                },
                records=[
                    (
                        "0001",
                        {"text": "I love this so much, best day ever!"},
                        '{\n    "positive": true,\n    "negative": false\n}\n',
                        None,
                    ),
                    (
                        "0002",
                        {"text": "Worst experience of my life, total disaster."},
                        '{\n    "positive": false,\n    "negative": true\n}\n',
                        None,
                    ),
                    (
                        "0003",
                        {"text": "Absolutely fantastic, highly recommend!"},
                        '{\n    "positive": true,\n    "negative": false\n}\n',
                        None,
                    ),
                ],
            )
            out = tmp_path / "json_gepa_artifact"
            result = run_coax(str(labels), "--out", str(out), "--optimizer", "gepa")

            haystack = result.stdout + "\n" + result.stderr
            scores = [
                float(m)
                for m in re.findall(r"score[^0-9]*([0-9]+(?:\.[0-9]+)?)", haystack, re.IGNORECASE)
            ]
            assert scores, (
                f"expected GEPA to emit at least one score line; stdout/stderr:\n{haystack!r}"
            )
            assert any(s > 0 for s in scores), (
                "GEPA reported only zero scores — the silent-failure case from #75. "
                f"All scores: {scores}\nstdout/stderr:\n{haystack!r}"
            )

    def describe_with_bool_output():
        def it_returns_a_parseable_boolean(
            agent_lm: AgentLM,
            make_label_folder: Callable[..., Path],
            tmp_path: Path,
        ) -> None:
            labels = make_label_folder(
                schema={
                    "inputs": {"text": {"desc": "Short text snippet"}},
                    "output": {"desc": "Whether the text is positive sentiment", "type": "bool"},
                },
                records=[
                    ("0001", {"text": "I love this so much, best day ever!"}, True, None),
                    ("0002", {"text": "Worst experience of my life, total disaster."}, False, None),
                    ("0003", {"text": "Absolutely fantastic, highly recommend!"}, True, None),
                ],
            )
            out = tmp_path / "bool_artifact"
            run_coax(str(labels), "--out", str(out))

            rendered = CoaxedPrompt(out)(text="The food was incredible and the service was great.")
            text = _agent_response(agent_lm, rendered).lower().rstrip(".")

            assert text in {"true", "false"}, f"expected bare 'true'/'false', got: {text!r}"

    def describe_with_int_output():
        def it_returns_a_parseable_integer(
            agent_lm: AgentLM,
            make_label_folder: Callable[..., Path],
            tmp_path: Path,
        ) -> None:
            labels = make_label_folder(
                schema={
                    "inputs": {"text": {"desc": "Phrase mentioning a count of items"}},
                    "output": {"desc": "The number of items mentioned", "type": "int"},
                },
                records=[
                    ("0001", {"text": "I bought three apples at the store."}, 3, None),
                    ("0002", {"text": "She has seven cats."}, 7, None),
                    ("0003", {"text": "Two dogs ran past the window."}, 2, None),
                ],
            )
            out = tmp_path / "int_artifact"
            run_coax(str(labels), "--out", str(out))

            rendered = CoaxedPrompt(out)(text="Five birds flew over the rooftop.")
            text = _agent_response(agent_lm, rendered).rstrip(".")

            assert text.isdigit(), f"expected a bare integer, got: {text!r}"

    def describe_with_custom_output_name():
        def it_does_not_break_round_trip(
            agent_lm: AgentLM,
            demo_inputs: dict,
            demo_meta: dict,
            tmp_path: Path,
        ) -> None:
            """``--output-name`` reaches the signature builder. End-to-end
            today this is a smoke test that the flag doesn't break the
            round-trip; the parsed-attribute check in #58 lands once
            ``response_format()`` is on main.
            """
            out = tmp_path / "named_artifact"
            run_coax(str(DEMO_FIXTURE), "--out", str(out), "--output-name", "is_curated")

            rendered = CoaxedPrompt(out)(**demo_inputs)
            text = _agent_response(agent_lm, rendered).lower()
            enum_values = demo_meta["fields"]["output"]["values"]
            assert any(v.lower() in text for v in enum_values), (
                f"expected response to contain one of {enum_values}, got: {text!r}"
            )

    def describe_with_file_backed_inputs():
        def it_inlines_sibling_file_contents_into_the_prompt(
            agent_lm: AgentLM,
            make_label_folder: Callable[..., Path],
            tmp_path: Path,
        ) -> None:
            """``{"backing": "file"}`` resolves a record value as a sibling
            filename. The CLI must load + render that path end-to-end.
            """
            labels = make_label_folder(
                schema={
                    "inputs": {
                        "doc": {"desc": "Document body", "backing": "file"},
                    },
                    "output": {
                        "desc": "Whether the document mentions Python",
                        "type": "enum",
                        "values": ["yes", "no"],
                    },
                },
                records=[
                    (
                        "0001",
                        {"doc": "body.txt"},
                        "yes",
                        {"body.txt": "Python is a high-level programming language."},
                    ),
                    (
                        "0002",
                        {"doc": "body.txt"},
                        "no",
                        {"body.txt": "JavaScript runs in every browser on Earth."},
                    ),
                    (
                        "0003",
                        {"doc": "body.txt"},
                        "yes",
                        {"body.txt": "Many data scientists prefer Python over R."},
                    ),
                ],
            )
            out = tmp_path / "file_backed_artifact"
            run_coax(str(labels), "--out", str(out))

            rendered = CoaxedPrompt(out)(doc="The Python ecosystem is enormous.")
            text = _agent_response(agent_lm, rendered).lower().rstrip(".")

            assert text in {"yes", "no"}, f"expected 'yes'/'no', got: {text!r}"
