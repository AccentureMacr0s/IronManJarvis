"""Analytics API routes."""

from fastapi import APIRouter

from platform.core.event_bus import get_event_bus
from platform.core.task_queue import get_task_queue, TaskStatus
from platform.core.scheduler import get_scheduler

router = APIRouter()


@router.get("/overview")
async def get_overview():
    """Get platform overview analytics."""
    queue = get_task_queue()
    all_tasks = queue.list_tasks(limit=1000)

    return {
        "tasks": {
            "total": len(all_tasks),
            "pending": len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            "running": len([t for t in all_tasks if t.status == TaskStatus.RUNNING]),
            "completed": len([t for t in all_tasks if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in all_tasks if t.status == TaskStatus.FAILED]),
        },
        "scheduled_jobs": get_scheduler().list_jobs(),
        "event_channels": get_event_bus().channels,
    }


@router.get("/tasks")
async def get_tasks(status: str | None = None, limit: int = 50):
    """Get task list with optional status filter."""
    queue = get_task_queue()
    status_filter = TaskStatus(status) if status else None
    tasks = queue.list_tasks(status=status_filter, limit=limit)
    return [
        {
            "task_id": t.task_id,
            "name": t.name,
            "status": t.status.value,
            "source": t.source,
            "priority": t.priority.name,
            "created_at": t.created_at.isoformat(),
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "error": t.error,
        }
        for t in tasks
    ]


@router.get("/events")
async def get_events(event_name: str | None = None, limit: int = 50):
    """Get recent event history."""
    bus = get_event_bus()
    return bus.get_history(event_name=event_name, limit=limit)
