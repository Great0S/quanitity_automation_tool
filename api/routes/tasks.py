"""
Tasks API routes
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from core.logger import logger
from core.auth import get_current_user
from utils.background_tasks import TaskManager

router = APIRouter()
task_manager = TaskManager()

@router.get("/{task_id}")
async def get_task(
    task_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get task status
    
    Args:
        task_id: Task ID
        
    Returns:
        Task status
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task

@router.get("/")
async def get_tasks(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get all tasks
    
    Returns:
        List of tasks
    """
    tasks = task_manager.get_tasks()
    return {"tasks": tasks}