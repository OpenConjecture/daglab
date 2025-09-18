"""Scheduling and orchestration components."""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from croniter import croniter
import asyncio
from enum import Enum
import pendulum


class ScheduleType(str, Enum):
    """Types of schedules."""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"
    EVENT = "event"


class Schedule:
    """Base schedule definition."""
    
    def __init__(self, schedule_type: ScheduleType, expression: str):
        self.schedule_type = schedule_type
        self.expression = expression
        self._next_run: Optional[datetime] = None
    
    def get_next_run(self, after: Optional[datetime] = None) -> datetime:
        """Get next scheduled run time."""
        if not after:
            after = datetime.now()
        
        if self.schedule_type == ScheduleType.CRON:
            cron = croniter(self.expression, after)
            return cron.get_next(datetime)
        elif self.schedule_type == ScheduleType.INTERVAL:
            # Parse interval expression (e.g., "5m", "1h", "1d")
            interval = self._parse_interval(self.expression)
            return after + interval
        elif self.schedule_type == ScheduleType.ONCE:
            # Parse ISO datetime
            return pendulum.parse(self.expression)
        else:
            raise ValueError(f"Unsupported schedule type: {self.schedule_type}")
    
    def _parse_interval(self, expression: str) -> timedelta:
        """Parse interval expression to timedelta."""
        unit_map = {
            's': 'seconds',
            'm': 'minutes',
            'h': 'hours',
            'd': 'days',
            'w': 'weeks'
        }
        
        # Extract number and unit
        import re
        match = re.match(r'(\d+)([smhdw])', expression)
        if not match:
            raise ValueError(f"Invalid interval expression: {expression}")
        
        value = int(match.group(1))
        unit = unit_map[match.group(2)]
        
        return timedelta(**{unit: value})


class ScheduledTask:
    """A task with schedule information."""
    
    def __init__(self, task_id: str, schedule: Schedule, 
                 callback: Callable, **kwargs):
        self.task_id = task_id
        self.schedule = schedule
        self.callback = callback
        self.kwargs = kwargs
        self.enabled = True
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
    
    async def execute(self) -> Any:
        """Execute the scheduled task."""
        self.last_run = datetime.now()
        self.run_count += 1
        result = await self.callback(**self.kwargs)
        self.next_run = self.schedule.get_next_run(after=self.last_run)
        return result


class Orchestrator:
    """Orchestrates scheduled tasks."""
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
    
    def add_task(self, task: ScheduledTask) -> None:
        """Add a scheduled task."""
        self._tasks[task.task_id] = task
        task.next_run = task.schedule.get_next_run()
    
    def remove_task(self, task_id: str) -> None:
        """Remove a scheduled task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
    
    def pause_task(self, task_id: str) -> None:
        """Pause a scheduled task."""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
    
    def resume_task(self, task_id: str) -> None:
        """Resume a scheduled task."""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            self._tasks[task_id].next_run = self._tasks[task_id].schedule.get_next_run()
    
    async def start(self) -> None:
        """Start the orchestrator."""
        if self._running:
            return
        
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())
    
    async def stop(self) -> None:
        """Stop the orchestrator."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
    
    async def _run_loop(self) -> None:
        """Main orchestrator loop."""
        while self._running:
            now = datetime.now()
            
            # Check for tasks to run
            for task in self._tasks.values():
                if not task.enabled or not task.next_run:
                    continue
                
                if now >= task.next_run:
                    # Execute task in background
                    asyncio.create_task(self._execute_task(task))
            
            # Sleep for a short interval
            await asyncio.sleep(1)
    
    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a single task."""
        try:
            await task.execute()
        except Exception as e:
            # Log error but don't crash orchestrator
            print(f"Error executing task {task.task_id}: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a scheduled task."""
        if task_id not in self._tasks:
            return None
        
        task = self._tasks[task_id]
        return {
            "task_id": task.task_id,
            "enabled": task.enabled,
            "last_run": task.last_run,
            "next_run": task.next_run,
            "run_count": task.run_count,
            "schedule_type": task.schedule.schedule_type,
            "expression": task.schedule.expression
        }
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all scheduled tasks."""
        return [self.get_task_status(task_id) for task_id in self._tasks]


__all__ = [
    "ScheduleType",
    "Schedule",
    "ScheduledTask",
    "Orchestrator",
]