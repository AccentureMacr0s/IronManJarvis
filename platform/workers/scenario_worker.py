"""Scenario worker - generates episode scenarios from prompts.

Uses LLM (local Ollama/Qwen or API) to generate structured scenarios.
"""

import logging
from typing import Any

from platform.core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


async def generate_scenario(episode_id: str, prompt: str, artifacts: dict[str, Any] = None, **kwargs) -> dict:
    """Generate a scenario from a prompt.

    Returns a structured scenario with scenes, dialogue, and directions.
    """
    logger.info(f"Generating scenario for episode {episode_id}")

    # TODO: integrate with Ollama/Qwen LLM
    # For now, return a placeholder structure
    scenario = {
        "episode_id": episode_id,
        "title": f"Generated from: {prompt[:50]}",
        "scenes": [
            {
                "scene_number": 1,
                "description": "Opening scene",
                "dialogue": [],
                "visual_direction": "Wide establishing shot",
                "duration_seconds": 5,
            }
        ],
        "total_duration": 60,
        "characters": [],
        "mood": "informative",
    }

    await get_event_bus().emit(
        "stage_complete",
        episode_id=episode_id,
        stage="scenario",
        result=scenario,
    )

    return scenario
