"""In-process task queue for the platform.

Accepts tasks from:
  - User (via web dashboard or voice command)
  - AI trend watcher (auto-generated when hotwords detected)
  - Scheduled triggers (via scheduler)

Tasks are executed asynchronously with status tracking.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Task:
    """A unit of work in the platform."""
    name: str
    handler: str  # dotted path to handler function
    params: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    source: str = "user"  # user | scheduler | ai
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any = None
    error: str | None = None


class TaskQueue:
    """Priority-based async task queue."""

    def __init__(self, max_concurrent: int = 3):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._tasks: dict[str, Task] = {}
        self._handlers: dict[str, Callable[..., Coroutine]] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False
        self._worker_task: asyncio.Task | None = None

    def register_handler(self, name: str, handler: Callable[..., Coroutine]):
        """Register a named task handler."""
        self._handlers[name] = handler
        logger.debug(f"Registered task handler: {name}")

    async def submit(self, task: Task) -> str:
        """Submit a task to the queue. Returns task_id."""
        self._tasks[task.task_id] = task
        # Priority queue: lower number = higher priority, negate for correct order
        await self._queue.put((-task.priority.value, task.task_id))
        logger.info(f"Task submitted: {task.name} [{task.task_id}] priority={task.priority.name}")
        return task.task_id

    async def start(self):
        """Start the queue worker loop."""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Task queue started")

    async def stop(self):
        """Stop the queue worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Task queue stopped")

    async def _worker_loop(self):
        """Main worker loop processing tasks from the queue."""
        while self._running:
            try:
                _, task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            task = self._tasks.get(task_id)
            if not task or task.status == TaskStatus.CANCELLED:
                continue

            asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: Task):
        """Execute a single task with concurrency control."""
        async with self._semaphore:
            handler = self._handlers.get(task.handler)
            if not handler:
                task.status = TaskStatus.FAILED
                task.error = f"No handler registered for '{task.handler}'"
                logger.error(task.error)
                return

            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            logger.info(f"Executing task: {task.name} [{task.task_id}]")

            try:
                task.result = await handler(**task.params)
                task.status = TaskStatus.COMPLETED
                logger.info(f"Task completed: {task.name} [{task.task_id}]")
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                logger.error(f"Task failed: {task.name} [{task.task_id}]: {e}")
            finally:
                task.completed_at = datetime.utcnow()

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self, status: TaskStatus | None = None, limit: int = 50) -> list[Task]:
        """List tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        return False


# Global task queue singleton
_queue: TaskQueue | None = None


def get_task_queue() -> TaskQueue:
    """Get or create the global task queue instance."""
    global _queue
    if _queue is None:
        _queue = TaskQueue()
    return _queue
