"""Unit tests for ``run_sync``."""

from __future__ import annotations

import asyncio

import pytest

from coaxer._internal.run_sync.run_sync import _get_thread_loop, run_sync


def describe_run_sync():
    def it_runs_a_coroutine_and_returns_its_value():
        async def coro() -> int:
            return 42

        assert run_sync(coro()) == 42

    @pytest.mark.asyncio
    async def it_dispatches_to_a_worker_thread_when_called_inside_a_running_loop():
        """The has_running_loop branch: callers already inside a loop
        can't run another via run_until_complete, so run_sync routes
        the coroutine to a worker thread (which uses its own
        persistent loop)."""
        outer_loop = asyncio.get_running_loop()
        seen: list[asyncio.AbstractEventLoop] = []

        async def coro() -> str:
            seen.append(asyncio.get_running_loop())
            return "from-worker"

        result = run_sync(coro())

        assert result == "from-worker"
        assert seen, "coroutine did not run"
        assert seen[0] is not outer_loop, (
            "worker-thread coro must run on the worker's own loop, not the caller's"
        )


def describe_get_thread_loop():
    def it_recreates_the_loop_if_an_external_caller_closes_it():
        """Defensive: if some other code in the process calls
        ``_thread_local.loop.close()``, the next ``run_sync`` call must
        mint a fresh loop instead of trying to reuse the closed one."""
        first = _get_thread_loop()
        first.close()

        second = _get_thread_loop()
        assert second is not first
        assert not second.is_closed()
