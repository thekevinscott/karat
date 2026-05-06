"""Run an async coroutine synchronously, even from within an async context."""

import asyncio
import concurrent.futures
import threading
from collections.abc import Coroutine
from typing import Any

from .has_running_loop import has_running_loop

_thread_local = threading.local()


def _get_thread_loop() -> asyncio.AbstractEventLoop:
    """Return the calling thread's persistent event loop.

    Created lazily on first access; never closed between ``run_sync``
    calls. Long-lived async resources owned by inner code -- e.g.
    claude-agent-sdk's ``Query`` TaskGroup, or any async generator
    whose finalization is deferred by CPython's GC -- can outlive any
    single ``run_sync`` call without landing on a closed loop or
    finalizing from a different task. The loop is reclaimed when the
    thread itself exits. See #73.
    """
    loop: asyncio.AbstractEventLoop | None = getattr(_thread_local, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        _thread_local.loop = loop
    return loop


def run_sync[T](coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine synchronously, even from within an async context.

    Detects whether we're already inside an async event loop. If so,
    dispatches to a separate thread (which uses its own persistent
    loop) to avoid "RuntimeError: This event loop is already running".
    Otherwise runs on the calling thread's persistent loop.
    """
    if has_running_loop():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run_on_thread_loop, coro)
            return future.result()  # type: ignore[return-value]
    return _get_thread_loop().run_until_complete(coro)


def _run_on_thread_loop[T](coro: Coroutine[Any, Any, T]) -> T:
    return _get_thread_loop().run_until_complete(coro)
