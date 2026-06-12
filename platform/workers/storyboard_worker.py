"""Storyboard worker - converts scenarios into visual storyboards.

Breaks scenario into individual frames with visual descriptions
suitable for image generation.
"""

import logging
from typing import Any

from platform.core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


async def generate_storyboard(episode_id: str, prompt: str, artifacts: dict[str, Any] = None, **kwargs) -> dict:
    """Generate a storyboard from a scenario.

    Returns frame-by-frame visual descriptions and layout.
    """
    logger.info(f"Generating storyboard for episode {episode_id}")

    scenario = (artifacts or {}).get("scenario", {})
    scenes = scenario.get("scenes", [])

    frames = []
    for i, scene in enumerate(scenes):
        frames.append({
            "frame_number": i + 1,
            "scene_number": scene.get("scene_number", 1),
            "visual_prompt": scene.get("visual_direction", ""),
            "camera_angle": "medium",
            "characters_in_frame": [],
            "duration_seconds": scene.get("duration_seconds", 3),
        })

    storyboard = {
        "episode_id": episode_id,
        "frames": frames,
        "total_frames": len(frames),
        "style": "cartoon",
    }

    await get_event_bus().emit(
        "stage_complete",
        episode_id=episode_id,
        stage="storyboard",
        result=storyboard,
    )

    return storyboard
