"""
Main ATLAS system - integrates all components.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from atlas.config import AtlasConfig, get_config
from atlas.core.schemas import Task, TaskStatus, SystemMetrics
from atlas.memory.manager import MemoryManager
from atlas.agents.planner import PlannerAgent
from atlas.agents.executor import ExecutorAgent
from atlas.agents.critic import CriticAgent
from atlas.agents.memory_agent import MemoryAgent
from atlas.agents.tool_agent import ToolAgent
from atlas.agents.orchestrator import OrchestratorAgent
from atlas.tools.web_tools import WebSearchTool, WebScrapeTool
from atlas.tools.file_tools import FileReadTool, FileWriteTool, FileListTool
from atlas.tools.code_tools import PythonExecuteTool, ShellExecuteTool
from atlas.tools.api_tools import HTTPRequestTool, DatabaseQueryTool
from atlas.observability import ObservabilityManager


class AtlasSystem:
    """
    Main ATLAS system orchestrator.
    
    Integrates all components:
    - Configuration
    - Memory systems
    - Agents
    - Tools
    - Observability
    """
    
    def __init__(self, config: Optional[AtlasConfig] = None):
        self.config = config or get_config()
        
        # Component references
        self.llm = None
        self.memory_manager = None
        self.agents = {}
        self.orchestrator = None
        self.observability = None
        
        # Task tracking
        self.tasks: Dict[UUID, Task] = {}
        self.start_time = datetime.utcnow()
    
    async def initialize(self):
        """Initialize all ATLAS components."""
        # Initialize LLM
        self.llm = self._create_llm()
        
        # Initialize observability
        self.observability = ObservabilityManager(
            log_level=self.config.observability.log_level,
            log_file=self.config.observability.log_file if self.config.observability.enable_logging else None,
            trace_dir=Path("data/traces") if self.config.observability.enable_tracing else None
        )
        
        self.observability.log("info", "Initializing ATLAS system")
        
        # Initialize memory
        self.memory_manager = MemoryManager(
            persist_dir=self.config.memory.persist_dir
        )
        
        # Initialize tools
        tools = self._create_tools()
        
        # Initialize agents
        self.agents["planner"] = PlannerAgent(llm=self.llm)
        self.agents["executor"] = ExecutorAgent(llm=self.llm, tools=tools)
        self.agents["critic"] = CriticAgent(
            llm=self.llm,
            quality_threshold=self.config.agent.quality_threshold
        )
        self.agents["memory"] = MemoryAgent(
            llm=self.llm,
            memory_manager=self.memory_manager
        )
        self.agents["tool"] = ToolAgent(llm=self.llm, tools=tools)
        
        # Initialize orchestrator
        self.orchestrator = OrchestratorAgent(
            llm=self.llm,
            planner=self.agents["planner"],
            executor=self.agents["executor"],
            critic=self.agents["critic"],
            memory=self.agents["memory"],
            tool_agent=self.agents["tool"]
        )
        
        self.observability.log("info", "ATLAS system initialized successfully")
    
    def _create_llm(self):
        """Create LLM instance based on configuration."""
        if self.config.llm.provider == "openai":
            api_key = self.config.llm.api_key or self.config.openai_api_key
            return ChatOpenAI(
                model=self.config.llm.model,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
                api_key=api_key
            )
        elif self.config.llm.provider == "anthropic":
            api_key = self.config.llm.api_key or self.config.anthropic_api_key
            return ChatAnthropic(
                model=self.config.llm.model,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
                api_key=api_key
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm.provider}")
    
    def _create_tools(self):
        """Create tool instances based on configuration."""
        tools = []
        
        if self.config.tool.enable_web_search:
            tools.append(WebSearchTool())
            tools.append(WebScrapeTool())
        
        if self.config.tool.enable_file_ops:
            tools.append(FileReadTool(
                allowed_paths=self.config.tool.allowed_file_paths
            ))
            tools.append(FileWriteTool(
                allowed_paths=self.config.tool.allowed_file_paths
            ))
            tools.append(FileListTool())
        
        if self.config.tool.enable_code_execution:
            tools.append(PythonExecuteTool(
                timeout=self.config.tool.code_execution_timeout
            ))
        
        if self.config.tool.enable_shell_execution:
            tools.append(ShellExecuteTool())
        
        tools.append(HTTPRequestTool())
        tools.append(DatabaseQueryTool())
        
        return tools
    
    async def execute_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a task using the orchestrator.
        
        Args:
            task: Task to execute
            context: Additional context
            
        Returns:
            Task result
        """
        # Store task
        self.tasks[task.id] = task
        
        try:
            # Log task start
            self.observability.log(
                "info",
                f"Executing task: {task.description[:100]}",
                task_id=task.id,
                priority=task.priority.value
            )
            
            # Execute via orchestrator
            result = await self.orchestrator.execute(task, context)
            
            # Update metrics
            await self._update_metrics()
            
            return result
            
        except Exception as e:
            self.observability.log(
                "error",
                f"Task execution failed: {str(e)}",
                task_id=task.id
            )
            raise
    
    def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID."""
        # Check active tasks
        if task_id in self.tasks:
            return self.tasks[task_id]
        
        # Check orchestrator
        if task_id in self.orchestrator.active_tasks:
            return self.orchestrator.active_tasks[task_id]
        
        # Check completed
        for task in self.orchestrator.completed_tasks:
            if task.id == task_id:
                return task
        
        # Check failed
        for task in self.orchestrator.failed_tasks:
            if task.id == task_id:
                return task
        
        return None
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[Task]:
        """List tasks with optional filtering."""
        all_tasks = (
            list(self.orchestrator.active_tasks.values()) +
            self.orchestrator.completed_tasks +
            self.orchestrator.failed_tasks
        )
        
        if status:
            all_tasks = [t for t in all_tasks if t.status == status]
        
        # Sort by created_at descending
        all_tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return all_tasks[:limit]
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a task."""
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.CANCELLED
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "status": "operational",
            "active_tasks": len(self.orchestrator.active_tasks),
            "completed_tasks": len(self.orchestrator.completed_tasks),
            "failed_tasks": len(self.orchestrator.failed_tasks),
            "uptime_seconds": uptime,
            "memory_stats": self.memory_manager.get_stats(),
            "agent_metrics": {
                name: agent.get_metrics()
                for name, agent in self.agents.items()
            }
        }
    
    async def _update_metrics(self):
        """Update system metrics."""
        metrics = SystemMetrics(
            total_tasks=len(self.tasks),
            completed_tasks=len(self.orchestrator.completed_tasks),
            failed_tasks=len(self.orchestrator.failed_tasks),
            active_agents=sum(1 for a in self.agents.values() if a.state.is_busy),
            total_cost=sum(a.total_cost for a in self.agents.values()),
            total_tokens=sum(a.total_tokens for a in self.agents.values()),
            uptime=(datetime.utcnow() - self.start_time).total_seconds()
        )
        
        self.observability.metrics(metrics)
    
    async def shutdown(self):
        """Shutdown ATLAS system gracefully."""
        self.observability.log("info", "Shutting down ATLAS system")
        
        # Save memory systems
        self.memory_manager.save_all()
        
        self.observability.log("info", "ATLAS system shut down successfully")
