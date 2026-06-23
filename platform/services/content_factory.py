"""Content factory service - orchestrates the content generation pipeline.

Pipeline stages:
  Trend/Prompt → Scenario → Storyboard → Render → Voice → Compose → Publish

Each stage is handled by a dedicated worker.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from platform.core.event_bus import get_event_bus
from platform.core.task_queue import Task, TaskPriority, get_task_queue

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    SCENARIO = "scenario"
    STORYBOARD = "storyboard"
    RENDER = "render"
    VOICE = "voice"
    COMPOSE = "compose"
    PUBLISH = "publish"


@dataclass
class Episode:
    """A content episode moving through the pipeline."""
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    prompt: str = ""
    source: str = "user"  # user | trend | ai
    current_stage: PipelineStage = PipelineStage.SCENARIO
    created_at: datetime = field(default_factory=datetime.utcnow)
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ContentFactory:
    """Orchestrates content creation through the pipeline."""

    STAGE_HANDLERS = {
        PipelineStage.SCENARIO: "workers.scenario",
        PipelineStage.STORYBOARD: "workers.storyboard",
        PipelineStage.RENDER: "workers.render",
        PipelineStage.VOICE: "workers.voice",
        PipelineStage.COMPOSE: "workers.compose",
        PipelineStage.PUBLISH: "workers.publish",
    }

    STAGE_ORDER = list(PipelineStage)

    def __init__(self):
        self._episodes: dict[str, Episode] = {}
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """Subscribe to relevant events."""
        bus = get_event_bus()
        bus.subscribe("trend_detected", self._on_trend_detected)
        bus.subscribe("stage_complete", self._on_stage_complete)

    async def create_episode(self, prompt: str, title: str = "", source: str = "user") -> Episode:
        """Create a new episode and start the pipeline."""
        episode = Episode(
            title=title or f"Episode from {source}",
            prompt=prompt,
            source=source,
        )
        self._episodes[episode.episode_id] = episode
        logger.info(f"Created episode '{episode.title}' [{episode.episode_id}]")

        await self._advance_pipeline(episode)
        return episode

    async def _on_trend_detected(self, keyword: str, title: str, url: str, **kwargs):
        """Auto-create episode when a trend is detected."""
        prompt = f"Create content about trending topic: {keyword}. Context: {title}"
        await self.create_episode(prompt=prompt, title=f"Trend: {keyword}", source="trend")

    async def _on_stage_complete(self, episode_id: str, stage: str, result: Any = None, **kwargs):
        """Advance episode to next pipeline stage."""
        episode = self._episodes.get(episode_id)
        if not episode:
            return

        episode.artifacts[stage] = result
        current_idx = self.STAGE_ORDER.index(episode.current_stage)
        if current_idx < len(self.STAGE_ORDER) - 1:
            episode.current_stage = self.STAGE_ORDER[current_idx + 1]
            await self._advance_pipeline(episode)
        else:
            logger.info(f"Episode '{episode.title}' pipeline complete!")
            await get_event_bus().emit("episode_complete", episode_id=episode.episode_id)

    async def _advance_pipeline(self, episode: Episode):
        """Submit the next stage as a task."""
        handler = self.STAGE_HANDLERS.get(episode.current_stage)
        if not handler:
            return

        queue = get_task_queue()
        task = Task(
            name=f"{episode.current_stage.value}:{episode.title}",
            handler=handler,
            params={
                "episode_id": episode.episode_id,
                "prompt": episode.prompt,
                "artifacts": episode.artifacts,
            },
            priority=TaskPriority.NORMAL,
            source="pipeline",
        )
        await queue.submit(task)

    def get_episode(self, episode_id: str) -> Episode | None:
        return self._episodes.get(episode_id)

    def list_episodes(self, limit: int = 50) -> list[Episode]:
        return sorted(self._episodes.values(), key=lambda e: e.created_at, reverse=True)[:limit]
