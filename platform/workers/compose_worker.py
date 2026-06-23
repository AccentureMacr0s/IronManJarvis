"""Compose worker - assembles final video from rendered frames and audio.

Uses FFmpeg to:
  - Combine image frames into video
  - Add voice narration and sound effects
  - Apply transitions and effects
  - Export in target format (YouTube Shorts, Instagram Reels)
"""

import logging
from typing import Any

from platform.core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


async def compose_video(episode_id: str, prompt: str, artifacts: dict[str, Any] = None, **kwargs) -> dict:
    """Compose final video from rendered frames and audio.

    Returns path to the final video file.
    """
    logger.info(f"Composing video for episode {episode_id}")

    render_result = (artifacts or {}).get("render", {})
    voice_result = (artifacts or {}).get("voice", {})

    # TODO: implement FFmpeg composition
    output_path = f"output/{episode_id}/final.mp4"

    result = {
        "episode_id": episode_id,
        "video_path": output_path,
        "format": "mp4",
        "resolution": "1080x1920",  # vertical for shorts/reels
        "duration_seconds": 60,
        "status": "placeholder",
    }

    await get_event_bus().emit(
        "stage_complete",
        episode_id=episode_id,
        stage="compose",
        result=result,
    )

    return result
