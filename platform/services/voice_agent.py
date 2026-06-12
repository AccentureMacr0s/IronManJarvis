"""Voice agent service - wraps existing Jarvis voice logic.

Bridges the existing dima_6_stark_mode and dima_assistant modules
into the platform's event-driven architecture.
"""

import logging
from platform.core.event_bus import get_event_bus
from platform.core.task_queue import Task, TaskPriority, get_task_queue

logger = logging.getLogger(__name__)


class VoiceAgent:
    """Platform-integrated voice agent."""

    def __init__(self):
        self._active = False
        self._wake_word = "jarvis"

    async def start(self):
        """Start listening for voice commands."""
        self._active = True
        bus = get_event_bus()
        bus.subscribe("speak_request", self._on_speak_request)
        logger.info("Voice agent started")

    async def stop(self):
        """Stop the voice agent."""
        self._active = False
        logger.info("Voice agent stopped")

    async def process_command(self, text: str):
        """Process a voice command and submit it as a task."""
        bus = get_event_bus()
        await bus.emit("voice_command", text=text)

        queue = get_task_queue()
        task = Task(
            name=f"voice_cmd:{text[:30]}",
            handler="services.voice_command",
            params={"text": text},
            priority=TaskPriority.HIGH,
            source="user",
        )
        await queue.submit(task)

    async def _on_speak_request(self, text: str, **kwargs):
        """Handle speak requests from other services."""
        logger.info(f"Speaking: {text}")
        # TODO: integrate with actual TTS from dima_6_stark_mode/modules/voice.py

    @property
    def is_active(self) -> bool:
        return self._active
