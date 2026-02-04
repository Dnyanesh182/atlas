"""
Core data schemas for ATLAS using Pydantic v2.
Strong typing for all system components.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class MessageRole(str, Enum):
    """Message role types."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    AGENT = "agent"
    TOOL = "tool"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    CRITIQUING = "critiquing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """Agent role types."""
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    MEMORY = "memory"
    TOOL = "tool"


class Priority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Message(BaseModel):
    """Structured message for agent communication."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: UUID = Field(default_factory=uuid4)
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_type: Optional[AgentType] = None
    parent_id: Optional[UUID] = None


class ToolCall(BaseModel):
    """Tool execution request."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: UUID = Field(default_factory=uuid4)
    tool_name: str
    parameters: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolResult(BaseModel):
    """Tool execution result."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: UUID = Field(default_factory=uuid4)
    tool_call_id: UUID
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Task(BaseModel):
    """Task definition and state."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: UUID = Field(default_factory=uuid4)
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Task hierarchy
    parent_id: Optional[UUID] = None
    subtasks: List[UUID] = Field(default_factory=list)
    
    # Execution tracking
    assigned_agent: Optional[AgentType] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Results
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Metrics
    estimated_complexity: Optional[float] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[UUID] = Field(default_factory=list)


class Plan(BaseModel):
    """Multi-step execution plan."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: UUID = Field(default_factory=uuid4)
    goal: str
    steps: List[Task]
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict)
    estimated_total_cost: float = 0.0
    estimated_total_time: float = 0.0
    risk_assessment: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CritiqueResult(BaseModel):
    """Quality assessment from critic agent."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    score: float = Field(ge=0.0, le=10.0)
    passed: bool
    feedback: str
    areas_for_improvement: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MemoryEntry(BaseModel):
    """Memory storage entry."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: UUID = Field(default_factory=uuid4)
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    memory_type: str  # episodic, semantic, short_term, long_term
    importance: float = Field(ge=0.0, le=1.0, default=0.5)
    access_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """Current state of an agent."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    agent_type: AgentType
    current_task: Optional[UUID] = None
    messages: List[Message] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    is_busy: bool = False


class SystemMetrics(BaseModel):
    """System-wide metrics and observability."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    active_agents: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    average_task_time: float = 0.0
    uptime: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionTrace(BaseModel):
    """Execution trace for observability."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    agent_type: AgentType
    action: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    duration: float
    cost: float = 0.0
    tokens: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None
