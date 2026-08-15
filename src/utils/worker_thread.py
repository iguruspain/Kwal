"""Helper for the QThread + worker-object lifecycle.

Most background workers in Kwal follow the same pattern: a ``QObject`` worker
is moved to a ``QThread``, the thread's ``started`` signal triggers the worker's
``process`` slot, the worker's ``finished`` signal quits the thread, and the
thread's ``finished`` signal schedules both objects for deletion.

This module centralizes that boilerplate so each call site only has to create
the worker and connect its own result/progress signals.
"""

from __future__ import annotations

from PySide6.QtCore import QThread


def start_worker_thread(worker: object) -> QThread:
    """Create a QThread, move ``worker`` into it, wire the lifecycle and start it.

    ``worker`` must be a ``QObject`` exposing a ``process`` slot and a
    ``finished`` signal. The returned thread is already running; the caller is
    responsible for keeping a reference to it (and to the worker) for cleanup.
    """
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.process)  # type: ignore[attr-defined]
    worker.finished.connect(thread.quit)  # type: ignore[attr-defined]
    thread.finished.connect(worker.deleteLater)  # type: ignore[attr-defined]
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread
