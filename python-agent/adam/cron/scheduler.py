"""
Scheduled task management for Adam.

Provides cron-like scheduling for automated tasks.
"""

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Callable, Dict, List, Optional, Any
from pathlib import Path
import uuid

try:
    from croniter import croniter

    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


@dataclass
class ScheduledTask:
    """A scheduled task."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    cron_expression: str = ""
    message: str = ""
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0

    def calculate_next_run(self, from_time: datetime = None) -> Optional[datetime]:
        """Calculate next run time from cron expression."""
        if not CRONITER_AVAILABLE:
            return None

        try:
            from_time = from_time or datetime.now()
            cron = croniter(self.cron_expression, from_time)
            self.next_run = cron.get_next(datetime)
            return self.next_run
        except Exception:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "cron_expression": self.cron_expression,
            "message": self.message,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        """Create from dictionary."""
        task = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", ""),
            cron_expression=data.get("cron_expression", ""),
            message=data.get("message", ""),
            enabled=data.get("enabled", True),
            run_count=data.get("run_count", 0),
        )

        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_run"):
            task.last_run = datetime.fromisoformat(data["last_run"])
        if data.get("next_run"):
            task.next_run = datetime.fromisoformat(data["next_run"])

        return task


class TaskScheduler:
    """
    Manages scheduled tasks.

    Features:
    - Add/remove tasks
    - Cron expression parsing
    - Persistent storage
    - Async execution loop
    """

    def __init__(self, storage_path: Path = None):
        """
        Initialize scheduler.

        Args:
            storage_path: Path to tasks storage file
        """
        self.storage_path = storage_path or (Path.home() / ".adam" / "data" / "tasks.json")
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._callbacks: Dict[str, Callable] = {}

    def load(self) -> None:
        """Load tasks from storage."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path) as f:
                data = json.load(f)

            for task_data in data.get("tasks", []):
                task = ScheduledTask.from_dict(task_data)
                task.calculate_next_run()
                self.tasks[task.id] = task
        except Exception as e:
            print(f"Error loading tasks: {e}")

    def save(self) -> None:
        """Save tasks to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "tasks": [task.to_dict() for task in self.tasks.values()],
            "updated_at": datetime.now().isoformat(),
        }

        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, name: str, cron_expression: str, message: str) -> ScheduledTask:
        """
        Add a new scheduled task.

        Args:
            name: Task name
            cron_expression: Cron expression (e.g., "0 9 * * *" for 9am daily)
            message: Message to send to Adam when task runs

        Returns:
            Created task
        """
        task = ScheduledTask(
            name=name,
            cron_expression=cron_expression,
            message=message,
        )
        task.calculate_next_run()

        self.tasks[task.id] = task
        self.save()

        return task

    def remove(self, task_id: str) -> bool:
        """Remove a task by ID."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.save()
            return True
        return False

    def get(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def list_all(self) -> List[ScheduledTask]:
        """List all tasks."""
        return list(self.tasks.values())

    def enable(self, task_id: str) -> bool:
        """Enable a task."""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = True
            task.calculate_next_run()
            self.save()
            return True
        return False

    def disable(self, task_id: str) -> bool:
        """Disable a task."""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = False
            task.next_run = None
            self.save()
            return True
        return False

    def on_execute(self, callback: Callable) -> None:
        """Register callback for task execution."""
        self._callbacks["execute"] = callback

    async def run_forever(self) -> None:
        """Run scheduler loop (checks every minute)."""
        if not CRONITER_AVAILABLE:
            print("Warning: croniter not installed. Scheduler disabled.")
            return

        self._running = True

        while self._running:
            await self._check_tasks()
            await asyncio.sleep(60)  # Check every minute

    async def _check_tasks(self) -> None:
        """Check if any tasks need to run."""
        now = datetime.now()

        for task in self.tasks.values():
            if not task.enabled or not task.next_run:
                continue

            if now >= task.next_run:
                await self._execute_task(task)
                task.last_run = now
                task.run_count += 1
                task.calculate_next_run()
                self.save()

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        if "execute" in self._callbacks:
            try:
                await self._callbacks["execute"](task)
            except Exception as e:
                print(f"Error executing task {task.id}: {e}")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False


# Convenience function
def parse_cron(expression: str) -> Dict[str, str]:
    """
    Parse cron expression into human-readable format.

    Args:
        expression: Cron expression (5 fields)

    Returns:
        Dictionary with parsed fields
    """
    parts = expression.split()
    if len(parts) != 5:
        return {"error": "Invalid cron expression"}

    minute, hour, day, month, weekday = parts

    return {
        "minute": minute,
        "hour": hour,
        "day_of_month": day,
        "month": month,
        "day_of_week": weekday,
    }
