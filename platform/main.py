"""AI Content Fabric Platform - Main Entry Point.

Starts all platform services:
  - Task scheduler (APScheduler)
  - Task queue (async worker pool)
  - Web dashboard (FastAPI/Uvicorn)
  - Event bus (pub/sub)
  - Trend watcher
  - Content factory
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import uvicorn

from platform.core.config import get_config
from platform.core.event_bus import get_event_bus
from platform.core.scheduler import get_scheduler
from platform.core.task_queue import get_task_queue, TaskPriority
from platform.services.content_factory import ContentFactory
from platform.services.trend_watcher import TrendWatcher
from platform.services.voice_agent import VoiceAgent
from platform.workers.scenario_worker import generate_scenario
from platform.workers.storyboard_worker import generate_storyboard
from platform.workers.render_worker import render_frames
from platform.workers.voice_worker import generate_voice
from platform.workers.compose_worker import compose_video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("platform")


async def setup_workers():
    """Register all worker handlers with the task queue."""
    queue = get_task_queue()
    queue.register_handler("workers.scenario", generate_scenario)
    queue.register_handler("workers.storyboard", generate_storyboard)
    queue.register_handler("workers.render", render_frames)
    queue.register_handler("workers.voice", generate_voice)
    queue.register_handler("workers.compose", compose_video)
    logger.info("Workers registered")


async def setup_scheduler():
    """Configure scheduled jobs from config."""
    config = get_config()
    scheduler = get_scheduler()

    # Schedule trend checking
    trend_interval = config.get("trends", "check_interval_minutes", default=120)
    scheduler.add_interval_job(
        job_id="trend_check",
        task_name="Check Trends",
        handler="services.trend_check",
        minutes=trend_interval,
    )

    scheduler.start()


async def start_platform():
    """Initialize and start all platform services."""
    config = get_config()
    logger.info("Starting AI Content Fabric Platform...")

    # Initialize core
    bus = get_event_bus()
    queue = get_task_queue()

    # Register workers
    await setup_workers()

    # Start task queue
    await queue.start()

    # Initialize services
    trend_watcher = TrendWatcher()
    content_factory = ContentFactory()
    voice_agent = VoiceAgent()

    # Register trend check handler
    async def trend_check_handler(**kwargs):
        await trend_watcher.check_all_sources()

    queue.register_handler("services.trend_check", trend_check_handler)

    # Setup scheduler
    await setup_scheduler()

    logger.info("Platform started successfully")
    return queue


async def shutdown_platform():
    """Gracefully shutdown all services."""
    logger.info("Shutting down platform...")
    get_scheduler().stop()
    await get_task_queue().stop()
    logger.info("Platform shutdown complete")


def main():
    """Main entry point - starts platform and web server."""
    config = get_config()
    host = config.get("web", "host", default="0.0.0.0")
    port = config.get("web", "port", default=8000)

    # Start platform services in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_platform())

    # Start web server (blocks)
    logger.info(f"Dashboard available at http://{host}:{port}")
    try:
        uvicorn.run(
            "platform.web.app:app",
            host=host,
            port=port,
            log_level="info",
        )
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(shutdown_platform())
        loop.close()


if __name__ == "__main__":
    main()
