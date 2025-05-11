"""
Background task manager for handling long-running operations
"""

import asyncio
import threading
import uuid
import time
from typing import Dict, Any, Callable, Awaitable, Optional, List, Union, TypeVar, cast
from enum import Enum
from datetime import datetime, timedelta
import concurrent.futures
import logging

from core.logger import logger

T = TypeVar('T')

class TaskStatus(Enum):
    """Task status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """Task class for background operations"""
    
    def __init__(self, task_id: str, name: str, description: str = ""):
        """
        Initialize task
        
        Args:
            task_id: Unique task ID
            name: Task name
            description: Task description
        """
        self.task_id: str = task_id
        self.name: str = name
        self.description: str = description
        self.status: TaskStatus = TaskStatus.PENDING
        self.progress: int = 0
        self.result: Any = None
        self.error: Optional[str] = None
        self.created_at: datetime = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": str(self.error) if self.error else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": (self.completed_at - self.started_at).total_seconds() if self.completed_at and self.started_at else None,
            "metadata": self.metadata
        }


class BackgroundTaskManager:
    """Manager for background tasks"""
    
    def __init__(self, max_workers: int = 5, task_timeout: int = 3600):
        """
        Initialize background task manager
        
        Args:
            max_workers: Maximum number of concurrent workers
            task_timeout: Default task timeout in seconds
        """
        self.tasks: Dict[str, Task] = {}
        self.max_workers = max_workers
        self.task_timeout = task_timeout
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.RLock()
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _execute_task(self, task_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """
        Execute a task and update its status
        
        Args:
            task_id: Task ID
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        with self.lock:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            
            with self.lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    task.progress = 100
                    task.completed_at = datetime.now()
        
        except Exception as e:
            # Use error with exc_info instead of exception
            logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
            
            with self.lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.now()
    
    def _start_cleanup_thread(self) -> None:
        """Start a thread to clean up completed tasks"""
        def cleanup_worker() -> None:
            while True:
                try:
                    # Sleep for a while
                    time.sleep(3600)  # Clean up every hour
                    
                    # Get current time
                    now = datetime.now()
                    
                    # Find tasks to clean up (completed/failed/cancelled tasks older than 24 hours)
                    tasks_to_remove = []
                    
                    with self.lock:
                        for task_id, task in self.tasks.items():
                            if (task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED) and
                                task.completed_at and
                                now - task.completed_at > timedelta(hours=24)):
                                tasks_to_remove.append(task_id)
                        
                        # Remove tasks
                        for task_id in tasks_to_remove:
                            del self.tasks[task_id]
                    
                    logger.info(f"Cleaned up {len(tasks_to_remove)} completed tasks")
                    
                except Exception as e:
                    # Use error with exc_info instead of exception
                    logger.error(f"Error in cleanup thread: {str(e)}", exc_info=True)
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def submit_task(self, func: Callable[..., T], *args: Any, name: Optional[str] = None, 
                   description: str = "", timeout: Optional[int] = None, 
                   metadata: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
        """
        Submit a task for background execution
        
        Args:
            func: Function to execute
            *args: Function arguments
            name: Task name (defaults to function name)
            description: Task description
            timeout: Task timeout in seconds (None for default)
            metadata: Additional metadata for the task
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID
        """
        with self.lock:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Create task
            task = Task(
                task_id=task_id,
                name=name if name is not None else func.__name__,
                description=description
            )
            
            # Set metadata safely
            task.metadata = metadata if metadata is not None else {}
            
            self.tasks[task_id] = task
            
            # Submit task to executor
            future = self.executor.submit(
                self._execute_task,
                task_id,
                func,
                *args,
                **kwargs
            )
            
            # Set timeout if specified
            if timeout is not None or self.task_timeout:
                def timeout_callback() -> None:
                    if not future.done():
                        future.cancel()
                        with self.lock:
                            if task_id in self.tasks:
                                task = self.tasks[task_id]
                                task.status = TaskStatus.FAILED
                                task.error = "Task timed out"
                                task.completed_at = datetime.now()
                
                timer = threading.Timer(
                    timeout if timeout is not None else self.task_timeout,
                    timeout_callback
                )
                timer.daemon = True
                timer.start()
            
            return task_id
    
    def submit_async_task(self, func: Callable[..., Awaitable[T]], *args: Any, 
                         name: Optional[str] = None, description: str = "", 
                         timeout: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None,
                         **kwargs: Any) -> str:
        """
        Submit an async task for background execution
        
        Args:
            func: Async function to execute
            *args: Function arguments
            name: Task name (defaults to function name)
            description: Task description
            timeout: Task timeout in seconds (None for default)
            metadata: Additional metadata for the task
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID
        """
        # Wrapper to run async function
        def run_async_task() -> T:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(func(*args, **kwargs))
            finally:
                loop.close()
        
        # Submit as regular task
        return self.submit_task(
            run_async_task,
            name=name if name is not None else func.__name__,
            description=description,
            timeout=timeout,
            metadata=metadata
        )
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID
        
        Args:
            task_id: Task ID
            
        Returns:
            Task as dictionary or None if not found
        """
        with self.lock:
            task = self.tasks.get(task_id)
            return task.to_dict() if task else None
    
    def get_tasks(self, status: Optional[TaskStatus] = None, 
                 limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get tasks with optional filtering
        
        Args:
            status: Filter by status
            limit: Maximum number of tasks to return
            offset: Offset for pagination
            
        Returns:
            List of tasks as dictionaries
        """
        with self.lock:
            tasks = list(self.tasks.values())
            
            # Filter by status if specified
            if status:
                tasks = [task for task in tasks if task.status == status]
            
            # Sort by created_at (newest first)
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            
            # Apply pagination
            tasks = tasks[offset:offset + limit]
            
            return [task.to_dict() for task in tasks]
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get a list of recent tasks
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of recent tasks as dictionaries
        """
        with self.lock:
            # Get all tasks sorted by creation time (newest first)
            sorted_tasks = sorted(
                list(self.tasks.values()),
                key=lambda task: task.created_at,
                reverse=True
            )
            
            # Return the most recent tasks up to the limit as dictionaries
            return [task.to_dict() for task in sorted_tasks[:limit]]
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task
        
        Args:
            task_id: Task ID
            
        Returns:
            True if task was cancelled, False otherwise
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                return True
            
            return False
    
    def update_progress(self, task_id: Optional[str], progress: int, 
                       message: Optional[str] = None) -> bool:
        """
        Update task progress
        
        Args:
            task_id: Task ID
            progress: Progress percentage (0-100)
            message: Optional progress message
            
        Returns:
            True if task was updated, False otherwise
        """
        if task_id is None:
            return False
            
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status != TaskStatus.RUNNING:
                return False
            
            task.progress = min(max(0, progress), 100)
            
            if message:
                task.metadata = task.metadata or {}
                task.metadata["progress_message"] = message
            
            return True
    
    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """
        Mark a task as completed
        
        Args:
            task_id: Task ID
            result: Task result
            
        Returns:
            True if task was completed, False otherwise
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status != TaskStatus.RUNNING:
                return False
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.progress = 100
            task.completed_at = datetime.now()
            
            return True
    
    def fail_task(self, task_id: str, error: Union[str, Exception]) -> bool:
        """
        Mark a task as failed
        
        Args:
            task_id: Task ID
            error: Error message or exception
            
        Returns:
            True if task was failed, False otherwise
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            task.status = TaskStatus.FAILED
            task.error = str(error)
            task.completed_at = datetime.now()
            
            return True
    
    def create_task(self, name: str, description: str = "") -> str:
        """
        Create a new task without submitting it
        
        Args:
            name: Task name
            description: Task description
            
        Returns:
            Task ID
        """
        with self.lock:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Create task
            task = Task(
                task_id=task_id,
                name=name,
                description=description
            )
            
            self.tasks[task_id] = task
            
            return task_id


# Singleton instance
_task_manager: Optional[BackgroundTaskManager] = None

def get_task_manager() -> BackgroundTaskManager:
    """Get the singleton task manager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = BackgroundTaskManager()
    return _task_manager