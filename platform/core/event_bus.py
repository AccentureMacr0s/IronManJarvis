"""Simple pub/sub event bus for decoupling platform services.

Events flow between modules without direct dependencies:
  - trend_watcher emits 'trend_detected'
  - content_factory listens and creates episode tasks
  - workers emit 'stage_complete' events
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """Async event bus with named channels."""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[dict[str, Any]] = []
        self._max_history = 1000

    def subscribe(self, event_name: str, handler: EventHandler):
        """Subscribe a handler to an event channel."""
        self._handlers[event_name].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to '{event_name}'")

    def unsubscribe(self, event_name: str, handler: EventHandler):
        """Remove a handler from an event channel."""
        if handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)

    async def emit(self, event_name: str, **data):
        """Emit an event to all subscribers."""
        event = {
            "name": event_name,
            "data": data,
        }
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = self._handlers.get(event_name, [])
        logger.info(f"Event '{event_name}' → {len(handlers)} handler(s)")

        for handler in handlers:
            try:
                await handler(**data)
            except Exception as e:
                logger.error(f"Handler {handler.__name__} failed on '{event_name}': {e}")

    def get_history(self, event_name: str | None = None, limit: int = 50) -> list[dict]:
        """Get recent event history, optionally filtered by name."""
        if event_name:
            filtered = [e for e in self._history if e["name"] == event_name]
        else:
            filtered = self._history
        return filtered[-limit:]

    @property
    def channels(self) -> list[str]:
        """List all registered event channels."""
        return list(self._handlers.keys())


# Global event bus singleton
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
