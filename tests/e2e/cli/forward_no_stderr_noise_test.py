"""E2E regression for #73 — tight ``forward()`` loop produces no stderr noise.

The original failure mode: each ``AgentLM.forward()`` call ran the
coroutine via ``asyncio.run``, which closed the event loop on return.
The Anthropic Agent SDK's ``Query`` object, created inside the
coroutine, holds an ``anyio`` TaskGroup tied to the loop's host task.
When the SDK's ``process_query`` async generator survived past
``asyncio.run`` exit (deferred async-generator finalization), its
eventual ``aclose()`` fired ``Query.close()`` against a closed loop or
from a different task and anyio raised
``RuntimeError("Attempted to exit cancel scope in a different task...")``.
asyncio's default exception handler logged ``Task exception was never
retrieved`` and ``Loop <...> is closed`` on every call, drowning logs
and tqdm at scale.

Contract: a tight loop of ``forward()`` calls returns correct content
*and* leaves stderr clean of cancel-scope / closed-loop tracebacks.

Not part of CI (e2e is agent-run; see AGENTS.md). Hits the real
Anthropic backend via the local ``claude_agent_sdk`` session.
"""

from __future__ import annotations

import gc

import pytest

from coaxer.lm import AgentLM


def describe_forward_in_a_tight_loop():
    def it_does_not_emit_cancel_scope_or_closed_loop_errors(
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        lm = AgentLM(tools=[], max_turns=1)

        for _ in range(8):
            response = lm.forward(prompt="reply with the single word ok")
            assert response.choices[0].message.content, "empty response"

        # Force any deferred async-generator finalization to run *now*,
        # while we can still capture the resulting stderr. Without this
        # the noise shows up at interpreter shutdown after pytest has
        # released the capture handle and the assertion can't see it.
        gc.collect()

        _, err = capfd.readouterr()

        forbidden = (
            "Attempted to exit cancel scope",
            "Task exception was never retrieved",
            "Loop <",  # "Loop <_UnixSelectorEventLoop ...> is closed"
        )
        offenders = [s for s in forbidden if s in err]
        assert not offenders, (
            f"forward() emitted forbidden stderr noise: {offenders}\n--- captured stderr ---\n{err}"
        )
