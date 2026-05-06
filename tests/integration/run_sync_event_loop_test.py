"""Integration tests for the ``run_sync`` event-loop lifecycle policy.

Reproduces the failure mode described in #73: per-call ``asyncio.run``
creates a fresh event loop and closes it on return. The Anthropic Agent
SDK's ``Query`` object — created inside the coroutine — holds an
``anyio`` TaskGroup tied to the host task on that loop. Because the
SDK's ``process_query`` async generator can survive past
``asyncio.run`` exit (deferred async-generator finalization, cyclic GC,
intermediate generator wrappers), its eventual ``aclose()`` fires
``Query.close()`` → ``self._tg.__aexit__(None, None, None)`` from a
different task and/or against a closed loop. anyio raises
``RuntimeError("Attempted to exit cancel scope in a different task...")``,
asyncio's default exception handler logs ``Task exception was never
retrieved`` and ``Loop <...> is closed`` to stderr, and a tight loop of
``forward()`` calls floods the user's terminal with these tracebacks.

Contract under test (the fix's invariant): ``run_sync`` keeps a stable,
non-closed event loop across calls in the same thread. If both
invariants hold, no async-generator finalization scheduled by the SDK
can ever fire on a closed loop or run from a wrong task — the bug
condition is eliminated by construction.
"""

from __future__ import annotations

import asyncio

from coaxer._internal.run_sync import run_sync


def describe_run_sync_event_loop_lifecycle():
    def it_reuses_a_single_event_loop_across_calls():
        """A persistent thread-local loop is the contract; per-call
        ``asyncio.run`` violates it by minting a new loop every time."""

        async def get_loop_id() -> int:
            return id(asyncio.get_running_loop())

        loop_ids = {run_sync(get_loop_id()) for _ in range(5)}
        assert len(loop_ids) == 1, (
            f"run_sync must reuse one event loop across calls; saw {len(loop_ids)} distinct ids"
        )

    def it_does_not_close_the_loop_between_calls():
        """The loop captured during the first call must still be open
        after ``run_sync`` returns. ``asyncio.run`` violates this — it
        closes the loop on exit, so any async-generator finalizer that
        runs later (CPython's deferred GC of frames/closures) lands on
        a dead loop and asyncio logs ``Loop <...> is closed`` to stderr."""

        captured: list[asyncio.AbstractEventLoop] = []

        async def capture() -> None:
            captured.append(asyncio.get_running_loop())

        run_sync(capture())
        assert captured, "coroutine did not run"
        loop = captured[0]
        assert not loop.is_closed(), "run_sync must keep the per-thread loop alive between calls"
