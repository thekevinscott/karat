"""CLI entry point for coax."""

import argparse
from pathlib import Path

from coaxer.compiler import distill


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="coax",
        description="Compile a label folder into a reusable prompt.",
    )
    parser.add_argument("labels", type=Path, help="Path to the label folder.")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output folder for prompt.jinja + meta.json + history.jsonl.",
    )
    parser.add_argument(
        "--optimizer",
        choices=["gepa", "none"],
        default="none",
        help="Optimizer to run. `gepa` requires an API key; `none` emits a raw template.",
    )
    parser.add_argument(
        "--output-name",
        default="output",
        help="Name of the predicted field in the rendered template (default: output).",
    )

    args = parser.parse_args()

    optimizer = None if args.optimizer == "none" else args.optimizer
    lm = _build_default_lm() if optimizer else None
    out = distill(
        args.labels,
        args.out,
        lm=lm,
        optimizer=optimizer,
        output_name=args.output_name,
    )
    print(f"Wrote prompt to {out}/prompt.jinja")


def _build_default_lm():
    from coaxer.lm import AgentLM

    # GEPA rollouts ask the LM for one structured response per call. Default
    # AgentLM enables every Claude Code tool and leaves max_turns unbounded,
    # which turns each rollout into a full agentic session and makes
    # `coax --optimizer gepa` orders of magnitude slower than it should be.
    return AgentLM(tools=[], max_turns=1)


if __name__ == "__main__":
    main()
