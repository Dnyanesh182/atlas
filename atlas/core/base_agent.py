"""
Base agent abstraction for all ATLAS agents.
Enforces consistent interface and behavior.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from atlas.core.schemas import (
    AgentState,
    AgentType,
    Message,
    Task,
    ExecutionTrace,
)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in ATLAS.
    
    Enforces:
    - Consistent execution interface
    - State management
    - Observability hooks
    - Error handling patterns
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        llm: BaseChatModel,
        name: Optional[str] = None,
        **kwargs
    ):
        self.agent_type = agent_type
        self.llm = llm
        self.name = name or agent_type.value
        self.state = AgentState(agent_type=agent_type)
        self.config = kwargs
        
        # Execution tracking
        self.execution_count = 0
        self.total_cost = 0.0
        self.total_tokens = 0
        
    @abstractmethod
    async def execute(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute the agent's primary function.
        
        Args:
            task: Task to execute
            context: Additional execution context
            
        Returns:
            Execution result (type varies by agent)
        """
        pass
    
    @abstractmethod
    async def _process(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> Any:
        """
        Internal processing logic - implemented by subclasses.
        
        Args:
            messages: Conversation messages
            **kwargs: Additional parameters
            
        Returns:
            Processing result
        """
        pass
    
    async def reflect(
        self,
        task: Task,
        result: Any,
        trace: ExecutionTrace
    ) -> str:
        """
        Self-reflection after task execution.
        
        Args:
            task: Completed task
            result: Execution result
            trace: Execution trace
            
        Returns:
            Reflection summary
        """
        reflection_prompt = f"""
        Reflect on the task execution:
        
        Task: {task.description}
        Status: {task.status}
        Result: {result}
        Duration: {trace.duration}s
        Cost: ${trace.cost:.4f}
        
        What went well?
        What could be improved?
        What did you learn?
        """
        
        messages = [
            {"role": "system", "content": "You are a self-reflective AI agent analyzing your own performance."},
            {"role": "user", "content": reflection_prompt}
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    def update_state(self, **kwargs):
        """Update agent state."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
    
    def add_message(self, message: Message):
        """Add message to agent's conversation history."""
        self.state.messages.append(message)
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Message]:
        """Get recent conversation history."""
        messages = self.state.messages
        if limit:
            messages = messages[-limit:]
        return messages
    
    def reset_state(self):
        """Reset agent state."""
        self.state = AgentState(agent_type=self.agent_type)
    
    async def validate_input(self, task: Task) -> bool:
        """
        Validate task input before execution.
        
        Args:
            task: Task to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not task.description:
            return False
        return True
    
    async def handle_error(
        self,
        task: Task,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle execution errors gracefully.
        
        Args:
            task: Failed task
            error: Exception raised
            context: Error context
            
        Returns:
            Error recovery information
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "task_id": str(task.id),
            "agent": self.name,
            "recoverable": self._is_recoverable_error(error)
        }
        
        # Log error (would integrate with logging system)
        print(f"[{self.name}] Error: {error_info}")
        
        return error_info
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """Determine if error is recoverable."""
        # Common recoverable errors
        recoverable_types = (
            TimeoutError,
            ConnectionError,
            # Add more recoverable error types
        )
        return isinstance(error, recoverable_types)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        return {
            "agent_type": self.agent_type.value,
            "name": self.name,
            "execution_count": self.execution_count,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "average_cost": self.total_cost / max(self.execution_count, 1),
            "is_busy": self.state.is_busy
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(type={self.agent_type.value}, name={self.name})>"
