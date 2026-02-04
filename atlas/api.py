"""
FastAPI REST API for ATLAS.
Production-grade API endpoints.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from uuid import UUID
import asyncio
import json

from atlas.core.schemas import Task, TaskStatus, Priority
from atlas.config import get_config
from atlas.system import AtlasSystem


# API Models
class TaskCreate(BaseModel):
    """Request model for task creation."""
    description: str
    priority: Priority = Priority.MEDIUM
    max_retries: int = 3
    context: Dict[str, Any] = {}


class TaskResponse(BaseModel):
    """Response model for task."""
    id: UUID
    description: str
    status: TaskStatus
    priority: Priority
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int
    created_at: str
    completed_at: Optional[str] = None


class SystemStatus(BaseModel):
    """System status response."""
    status: str
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    uptime_seconds: float
    memory_stats: Dict[str, Any]


# Initialize FastAPI app
app = FastAPI(
    title="ATLAS API",
    description="Autonomous Task Learning & Agent System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key if configured."""
    if config.api.api_key and api_key != config.api.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# Global ATLAS system instance
atlas_system: Optional[AtlasSystem] = None


@app.on_event("startup")
async def startup_event():
    """Initialize ATLAS on startup."""
    global atlas_system
    atlas_system = AtlasSystem(config=config)
    await atlas_system.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if atlas_system:
        await atlas_system.shutdown()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ATLAS",
        "version": "1.0.0",
        "description": "Autonomous Task Learning & Agent System",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_create: TaskCreate,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Create and execute a new task.
    
    The task will be executed asynchronously.
    """
    if not atlas_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    # Create task
    task = Task(
        description=task_create.description,
        priority=task_create.priority,
        max_retries=task_create.max_retries,
        context=task_create.context
    )
    
    # Execute in background
    background_tasks.add_task(atlas_system.execute_task, task)
    
    return TaskResponse(
        id=task.id,
        description=task.description,
        status=task.status,
        priority=task.priority,
        result=task.result,
        error=task.error,
        retry_count=task.retry_count,
        created_at=task.created_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None
    )


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    api_key: str = Depends(verify_api_key)
):
    """Get task status and result."""
    if not atlas_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    task = atlas_system.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        id=task.id,
        description=task.description,
        status=task.status,
        priority=task.priority,
        result=task.result,
        error=task.error,
        retry_count=task.retry_count,
        created_at=task.created_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None
    )


@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """List tasks with optional filtering."""
    if not atlas_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    tasks = atlas_system.list_tasks(status=status, limit=limit)
    
    return [
        TaskResponse(
            id=task.id,
            description=task.description,
            status=task.status,
            priority=task.priority,
            result=task.result,
            error=task.error,
            retry_count=task.retry_count,
            created_at=task.created_at.isoformat(),
            completed_at=task.completed_at.isoformat() if task.completed_at else None
        )
        for task in tasks
    ]


@app.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    api_key: str = Depends(verify_api_key)
):
    """Cancel a running task."""
    if not atlas_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    success = await atlas_system.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
    
    return {"message": "Task cancelled", "task_id": str(task_id)}


@app.get("/status", response_model=SystemStatus)
async def system_status(api_key: str = Depends(verify_api_key)):
    """Get system status and metrics."""
    if not atlas_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    status = atlas_system.get_status()
    
    return SystemStatus(**status)


@app.get("/tasks/{task_id}/stream")
async def stream_task(
    task_id: UUID,
    api_key: str = Depends(verify_api_key)
):
    """Stream task execution updates."""
    if not atlas_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    async def event_generator():
        """Generate SSE events for task updates."""
        task = atlas_system.get_task(task_id)
        if not task:
            yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
            return
        
        # Stream updates
        while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task = atlas_system.get_task(task_id)
            yield f"data: {json.dumps({'status': task.status.value, 'retry_count': task.retry_count})}\n\n"
            await asyncio.sleep(1)
        
        # Final update
        task = atlas_system.get_task(task_id)
        yield f"data: {json.dumps({'status': task.status.value, 'result': str(task.result)[:500], 'completed': True})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/memory/store")
async def store_memory(
    content: str,
    memory_type: str = "short_term",
    importance: float = 0.5,
    api_key: str = Depends(verify_api_key)
):
    """Store a memory."""
    if not atlas_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    memory_id = await atlas_system.memory_manager.remember(
        content=content,
        memory_type=memory_type,
        importance=importance
    )
    
    return {"memory_id": str(memory_id), "message": "Memory stored"}


@app.post("/memory/recall")
async def recall_memory(
    query: str,
    memory_types: Optional[List[str]] = None,
    top_k: int = 5,
    api_key: str = Depends(verify_api_key)
):
    """Recall relevant memories."""
    if not atlas_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    memories = await atlas_system.memory_manager.recall(
        query=query,
        memory_types=memory_types,
        top_k=top_k
    )
    
    # Convert to serializable format
    result = {}
    for mem_type, entries in memories.items():
        result[mem_type] = [
            {
                "id": str(entry.id),
                "content": entry.content[:200],
                "importance": entry.importance,
                "created_at": entry.created_at.isoformat()
            }
            for entry in entries
        ]
    
    return result


@app.get("/metrics")
async def get_metrics(api_key: str = Depends(verify_api_key)):
    """Get system metrics and observability data."""
    if not atlas_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return atlas_system.observability.get_summary()


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    
    uvicorn.run(
        "atlas.api:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        workers=config.api.workers
    )
