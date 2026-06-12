"""APScheduler-based task scheduler for the platform.

Supports cron-like scheduling for:
  - Trend checking (every N hours)
  - Content publishing (at specific times)
  - Health checks and maintenance
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Coroutine

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from platform.core.event_bus import get_event_bus
from platform.core.task_queue import Task, TaskPriority, get_task_queue

logger = logging.getLogger(__name__)


class PlatformScheduler:
    """Wraps APScheduler for platform task scheduling."""

    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._jobs: dict[str, dict[str, Any]] = {}

    def add_cron_job(
        self,
        job_id: str,
        task_name: str,
        handler: str,
        cron_expression: str,
        params: dict[str, Any] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ):
        """Add a cron-scheduled job that submits tasks to the queue.

        Args:
            job_id: Unique identifier for the job
            task_name: Human-readable task name
            handler: Dotted path to handler function
            cron_expression: Cron expression (e.g., '0 */2 * * *' for every 2 hours)
            params: Parameters passed to the task handler
            priority: Task priority level
        """
        parts = cron_expression.split()
        trigger = CronTrigger(
            minute=parts[0] if len(parts) > 0 else "*",
            hour=parts[1] if len(parts) > 1 else "*",
            day=parts[2] if len(parts) > 2 else "*",
            month=parts[3] if len(parts) > 3 else "*",
            day_of_week=parts[4] if len(parts) > 4 else "*",
        )

        self._scheduler.add_job(
            self._submit_task,
            trigger=trigger,
            id=job_id,
            kwargs={
                "task_name": task_name,
                "handler": handler,
                "params": params or {},
                "priority": priority,
            },
        )
        self._jobs[job_id] = {
            "task_name": task_name,
            "handler": handler,
            "cron": cron_expression,
            "priority": priority.name,
        }
        logger.info(f"Scheduled cron job '{job_id}': {cron_expression}")

    def add_interval_job(
        self,
        job_id: str,
        task_name: str,
        handler: str,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        params: dict[str, Any] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ):
        """Add an interval-scheduled job."""
        trigger = IntervalTrigger(seconds=seconds, minutes=minutes, hours=hours)

        self._scheduler.add_job(
            self._submit_task,
            trigger=trigger,
            id=job_id,
            kwargs={
                "task_name": task_name,
                "handler": handler,
                "params": params or {},
                "priority": priority,
            },
        )
        self._jobs[job_id] = {
            "task_name": task_name,
            "handler": handler,
            "interval": f"{hours}h {minutes}m {seconds}s",
            "priority": priority.name,
        }
        logger.info(f"Scheduled interval job '{job_id}': every {hours}h {minutes}m {seconds}s")

    async def _submit_task(
        self, task_name: str, handler: str, params: dict, priority: TaskPriority
    ):
        """Submit a scheduled task to the queue."""
        queue = get_task_queue()
        task = Task(
            name=task_name,
            handler=handler,
            params=params,
            priority=priority,
            source="scheduler",
        )
        await queue.submit(task)
        await get_event_bus().emit("task_scheduled", task_id=task.task_id, task_name=task_name)

    def remove_job(self, job_id: str):
        """Remove a scheduled job."""
        if job_id in self._jobs:
            self._scheduler.remove_job(job_id)
            del self._jobs[job_id]
            logger.info(f"Removed job '{job_id}'")

    def start(self):
        """Start the scheduler."""
        self._scheduler.start()
        logger.info("Platform scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self._scheduler.shutdown(wait=False)
        logger.info("Platform scheduler stopped")

    def list_jobs(self) -> dict[str, dict[str, Any]]:
        """List all scheduled jobs."""
        return dict(self._jobs)


# Global scheduler singleton
_scheduler: PlatformScheduler | None = None


def get_scheduler() -> PlatformScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PlatformScheduler()
    return _scheduler
