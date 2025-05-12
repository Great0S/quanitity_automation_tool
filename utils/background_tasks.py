"""
Background task management utility
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable, Awaitable, Union
from datetime import datetime
import json
import os
from core.logger import logger

# Singleton task manager instance
_task_manager = None

class TaskStatus:
    """Task status constants"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskManager:
    """Manager for background tasks"""
    
    def __init__(self):
        """Initialize the task manager"""
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.recent_tasks: List[str] = []
        self.max_recent_tasks = 100
    
    def create_task(self, name: str, description: str = "") -> str:
        """
        Create a new task
        
        Args:
            name: Task name
            description: Task description
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        self.tasks[task_id] = {
            "task_id": task_id,
            "name": name,
            "description": description,
            "status": TaskStatus.PENDING,
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
            "result": None,
            "error": None,
            "metadata": {}
        }
        
        # Add to recent tasks
        self.recent_tasks.insert(0, task_id)
        
        # Trim recent tasks list
        if len(self.recent_tasks) > self.max_recent_tasks:
            self.recent_tasks = self.recent_tasks[:self.max_recent_tasks]
        
        return task_id
    
    def submit_async_task(self, func: Callable[..., Awaitable[Any]], 
                         name: str = "", description: str = "", task_id: Optional[str] = None, 
                         **kwargs) -> str:
        """
        Submit an async task for execution
        
        Args:
            func: Async function to execute
            name: Task name
            description: Task description
            task_id: Optional task ID (if not provided, a new task will be created)
            **kwargs: Arguments to pass to the function
            
        Returns:
            Task ID
        """
        # Create task if not provided
        if task_id is None:
            task_id = self.create_task(name, description)
        
        # Create task coroutine
        async def task_wrapper():
            try:
                # Update task status
                self.update_task(
                    task_id=task_id,
                    status=TaskStatus.RUNNING,
                    progress=0
                )
                
                # Execute function
                result = await func(task_id=task_id, **kwargs)
                
                # Update task with result
                self.update_task(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    progress=100,
                    result=result,
                    completed_at=datetime.now().isoformat()
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Task {task_id} failed: {str(e)}")
                
                # Update task with error
                self.update_task(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    completed_at=datetime.now().isoformat()
                )
                
                # Re-raise exception
                raise
        
        # Start task
        asyncio.create_task(task_wrapper())
        
        return task_id
    
    def update_task(self, task_id: str, **kwargs) -> None:
        """
        Update task properties
        
        Args:
            task_id: Task ID
            **kwargs: Properties to update
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return
        
        # Update task properties
        for key, value in kwargs.items():
            if key in self.tasks[task_id]:
                self.tasks[task_id][key] = value
        
        # Update timestamp
        self.tasks[task_id]["updated_at"] = datetime.now().isoformat()
    
    def update_progress(self, task_id: str, progress: float, message: Optional[str] = None, 
                        step: Optional[str] = None, total_steps: Optional[int] = None,
                        current_step: Optional[int] = None, eta_seconds: Optional[int] = None,
                        details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update task progress with enhanced information
        
        Args:
            task_id: Task ID
            progress: Progress value (0-100)
            message: Optional progress message
            step: Current step description (e.g., "Fetching products", "Updating inventory")
            total_steps: Total number of steps in the process
            current_step: Current step number
            eta_seconds: Estimated time remaining in seconds
            details: Additional details about the current operation
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return
        
        # Update progress
        self.tasks[task_id]["progress"] = progress
        
        # Ensure metadata exists
        if "metadata" not in self.tasks[task_id]:
            self.tasks[task_id]["metadata"] = {}
        
        # Update metadata with enhanced information
        metadata = self.tasks[task_id]["metadata"]
        
        if message:
            metadata["progress_message"] = message
        
        if step:
            metadata["current_step"] = step
            
        if total_steps is not None:
            metadata["total_steps"] = total_steps
            
        if current_step is not None:
            metadata["step_number"] = current_step
            
        if eta_seconds is not None:
            metadata["eta_seconds"] = eta_seconds
            metadata["eta_formatted"] = self._format_time(eta_seconds)
            
        if details:
            # Merge details with existing metadata
            for key, value in details.items():
                metadata[key] = value
        
        # Update timestamp
        self.tasks[task_id]["updated_at"] = datetime.now().isoformat()
        
    def _format_time(self, seconds: int) -> str:
        """Format seconds into a human-readable time string"""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes == 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task details
        
        Args:
            task_id: Task ID
            
        Returns:
            Task details or None if not found
        """
        return self.tasks.get(task_id)
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent tasks
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of recent tasks
        """
        tasks = []
        
        for task_id in self.recent_tasks[:limit]:
            if task_id in self.tasks:
                tasks.append(self.tasks[task_id])
        
        return tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task
        
        Args:
            task_id: Task ID
            
        Returns:
            True if task was cancelled, False otherwise
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return False
        
        # Update task status
        self.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error="Task cancelled",
            completed_at=datetime.now().isoformat()
        )
        
        return True


def get_task_manager() -> TaskManager:
    """Get the singleton task manager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager