"""Simple thread-safe event bus used by services.

This is intentionally small and dependency-free so you can swap to pyventus later.
"""
from collections import defaultdict
import threading
from typing import Callable, Type


class EventBus:
    def __init__(self):
        self._subs = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event_type: Type, handler: Callable):
        """Subscribe a handler to an event type. Handler must accept a single argument (the event)."""
        with self._lock:
            self._subs[event_type].append(handler)

    def publish(self, event) -> None:
        """Publish an event to all subscribers of its type.

        Handlers are invoked in background threads to avoid blocking the publisher.
        """
        handlers = []
        with self._lock:
            handlers = list(self._subs[type(event)])

        for h in handlers:
            t = threading.Thread(target=self._safe_call, args=(h, event), daemon=True)
            t.start()

    def _safe_call(self, handler, event):
        try:
            handler(event)
        except Exception:
            # keep the bus resilient; services can publish error events if desired
            pass
