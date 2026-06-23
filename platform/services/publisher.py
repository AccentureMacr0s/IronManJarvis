"""Publisher service - handles content distribution to platforms.

Supported targets (stubs):
  - YouTube Shorts
  - Instagram Reels
  - Local file export
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from platform.core.config import get_config
from platform.core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """Result of a publish operation."""
    target: str
    success: bool
    url: str | None = None
    error: str | None = None
    published_at: datetime | None = None


class Publisher:
    """Publishes completed content to various platforms."""

    def __init__(self):
        config = get_config()
        self._targets: list[str] = config.get("publish", "targets", default=["local"])
        self._output_dir: str = config.get("publish", "output_dir", default="./output")

    async def publish(self, episode_id: str, video_path: str, metadata: dict[str, Any]) -> list[PublishResult]:
        """Publish content to all configured targets."""
        results = []

        for target in self._targets:
            result = await self._publish_to_target(target, video_path, metadata)
            results.append(result)

        await get_event_bus().emit(
            "content_published",
            episode_id=episode_id,
            results=[{"target": r.target, "success": r.success} for r in results],
        )
        return results

    async def _publish_to_target(self, target: str, video_path: str, metadata: dict) -> PublishResult:
        """Publish to a specific target platform."""
        try:
            if target == "local":
                return await self._publish_local(video_path, metadata)
            elif target == "youtube":
                return await self._publish_youtube(video_path, metadata)
            elif target == "instagram":
                return await self._publish_instagram(video_path, metadata)
            else:
                return PublishResult(target=target, success=False, error=f"Unknown target: {target}")
        except Exception as e:
            logger.error(f"Publish to {target} failed: {e}")
            return PublishResult(target=target, success=False, error=str(e))

    async def _publish_local(self, video_path: str, metadata: dict) -> PublishResult:
        """Save to local output directory."""
        logger.info(f"Published locally: {video_path}")
        return PublishResult(target="local", success=True, url=video_path, published_at=datetime.utcnow())

    async def _publish_youtube(self, video_path: str, metadata: dict) -> PublishResult:
        """Publish to YouTube Shorts (stub)."""
        # TODO: implement YouTube API upload
        logger.warning("YouTube publishing not yet implemented")
        return PublishResult(target="youtube", success=False, error="Not implemented")

    async def _publish_instagram(self, video_path: str, metadata: dict) -> PublishResult:
        """Publish to Instagram Reels (stub)."""
        # TODO: implement Instagram API upload
        logger.warning("Instagram publishing not yet implemented")
        return PublishResult(target="instagram", success=False, error="Not implemented")
