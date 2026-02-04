"""
Base tool abstraction for ATLAS tool system.
Provides secure execution boundaries and consistent interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
import time

from pydantic import BaseModel, Field

from atlas.core.schemas import ToolCall, ToolResult


class ToolSchema(BaseModel):
    """Tool definition schema."""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Optional[str] = None
    required_permissions: list[str] = Field(default_factory=list)
    is_safe: bool = True  # Safe tools don't modify system state


class BaseTool(ABC):
    """
    Abstract base class for all tools in ATLAS.
    
    Features:
    - Type-safe parameter validation
    - Execution sandboxing
    - Permission checking
    - Automatic error handling
    - Execution metrics
    """
    
    def __init__(self, name: str, description: str, **kwargs):
        self.name = name
        self.description = description
        self.config = kwargs
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.error_count = 0
    
    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Get tool schema for LLM function calling."""
        pass
    
    @abstractmethod
    async def _execute_impl(self, **kwargs) -> Any:
        """
        Internal execution logic - implemented by subclasses.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Execution result
        """
        pass
    
    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute the tool with safety checks and metrics.
        
        Args:
            tool_call: Tool execution request
            
        Returns:
            Tool execution result
        """
        start_time = time.time()
        
        try:
            # Validate parameters
            if not await self.validate_parameters(tool_call.parameters):
                raise ValueError(f"Invalid parameters for tool {self.name}")
            
            # Check permissions
            if not await self.check_permissions(tool_call.parameters):
                raise PermissionError(f"Insufficient permissions for tool {self.name}")
            
            # Execute tool
            result = await self._execute_impl(**tool_call.parameters)
            
            execution_time = time.time() - start_time
            self.execution_count += 1
            self.total_execution_time += execution_time
            
            return ToolResult(
                tool_call_id=tool_call.id,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.error_count += 1
            
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time
            )
    
    async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate tool parameters.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if valid
        """
        schema = self.get_schema()
        required_params = schema.parameters.get("required", [])
        
        # Check required parameters
        for param in required_params:
            if param not in parameters:
                return False
        
        return True
    
    async def check_permissions(self, parameters: Dict[str, Any]) -> bool:
        """
        Check if tool execution is permitted.
        
        Args:
            parameters: Execution parameters
            
        Returns:
            True if permitted
        """
        # Base implementation allows all - override for sensitive tools
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tool execution metrics."""
        return {
            "tool_name": self.name,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": self.total_execution_time / max(self.execution_count, 1),
            "error_rate": self.error_count / max(self.execution_count, 1)
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"
