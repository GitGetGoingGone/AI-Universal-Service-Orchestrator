"""Multi-Vendor Task Queue API (Module 11)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from db import create_tasks_for_order, get_tasks_for_partner, get_task_by_id, start_task, complete_task

router = APIRouter(prefix="/api/v1", tags=["Task Queue"])


@router.post("/orders/{order_id}/tasks")
def create_order_tasks(order_id: str) -> Dict[str, Any]:
    """
    Create vendor tasks from order_legs for an order.
    Idempotent: does not duplicate tasks if order already has tasks.
    """
    created = create_tasks_for_order(order_id)
    return {"order_id": order_id, "tasks_created": len(created), "tasks": created}


@router.get("/tasks")
def list_tasks(
    partner_id: str = Query(..., description="Partner ID"),
    status: Optional[str] = Query(None, description="Filter: pending, in_progress, completed"),
) -> Dict[str, Any]:
    """List tasks for a partner. Pending tasks only include next-available (previous in order completed)."""
    tasks = get_tasks_for_partner(partner_id, status_filter=status)
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    partner_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Get a single task. If partner_id provided, only that partner's task."""
    task = get_task_by_id(task_id, partner_id=partner_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/start")
def start_task_endpoint(
    task_id: str,
    partner_id: str = Query(..., description="Partner ID (must own task)"),
) -> Dict[str, Any]:
    """Mark task as in progress. Updates order_leg status."""
    task = start_task(task_id, partner_id)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or not pending")
    return task


@router.post("/tasks/{task_id}/complete")
def complete_task_endpoint(
    task_id: str,
    partner_id: str = Query(..., description="Partner ID (must own task)"),
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Mark task as completed. Updates order_leg status."""
    task = complete_task(task_id, partner_id, metadata=metadata)
    if not task:
        raise HTTPException(status_code=400, detail="Task not found or not in progress/pending")
    return task
