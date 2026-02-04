"""
Tool Agent - Secure tool execution and management.

Responsibilities:
- Execute tools safely
- Validate tool inputs
- Handle tool errors
- Track tool usage
- Manage tool permissions
"""

from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel

from atlas.core.base_agent import BaseAgent
from atlas.core.schemas import AgentType, Task, ToolCall, ToolResult
from atlas.core.base_tool import BaseTool


class ToolAgent(BaseAgent):
    """
    Tool Agent - Safe tool execution and orchestration.
    
    Provides secure access to tools with validation and monitoring.
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        **kwargs
    ):
        super().__init__(
            agent_type=AgentType.TOOL,
            llm=llm,
            name="ToolAgent",
            **kwargs
        )
        self.tools = tools or []
        self.tool_map = {tool.name: tool for tool in self.tools}
    
    async def execute(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute a tool call.
        
        Args:
            task: Tool execution task
            context: Additional context
            
        Returns:
            Tool execution result
        """
        self.update_state(is_busy=True, current_task=task.id)
        
        try:
            # Extract tool call information
            tool_name = task.context.get("tool_name")
            parameters = task.context.get("parameters", {})
            
            if not tool_name:
                raise ValueError("No tool name specified")
            
            # Create tool call
            tool_call = ToolCall(
                tool_name=tool_name,
                parameters=parameters
            )
            
            # Execute tool
            result = await self._execute_tool(tool_call)
            
            self.execution_count += 1
            return result
            
        finally:
            self.update_state(is_busy=False, current_task=None)
    
    async def _process(
        self,
        messages: List[Any],
        **kwargs
    ) -> Any:
        """Process messages for tool operations."""
        response = await self.llm.ainvoke(messages)
        return response
    
    async def _execute_tool(
        self,
        tool_call: ToolCall
    ) -> ToolResult:
        """
        Execute a tool with safety checks.
        
        Args:
            tool_call: Tool call to execute
            
        Returns:
            Tool execution result
        """
        tool_name = tool_call.tool_name
        
        if tool_name not in self.tool_map:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                result=None,
                error=f"Tool '{tool_name}' not found",
                execution_time=0.0
            )
        
        tool = self.tool_map[tool_name]
        
        try:
            # Execute tool
            result = await tool.execute(tool_call)
            
            # Track usage
            self.state.tool_calls.append(tool_call)
            self.state.tool_results.append(result)
            
            return result
            
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                result=None,
                error=str(e),
                execution_time=0.0
            )
    
    def add_tool(self, tool: BaseTool):
        """Add a tool to the agent."""
        self.tools.append(tool)
        self.tool_map[tool.name] = tool
    
    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from the agent."""
        if tool_name in self.tool_map:
            tool = self.tool_map[tool_name]
            self.tools.remove(tool)
            del self.tool_map[tool_name]
            return True
        return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tool_map.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all available tools."""
        return self.tools
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.get_schema().dict()
            }
            for tool in self.tools
        ]
    
    def get_tool_metrics(self) -> Dict[str, Any]:
        """Get metrics for all tools."""
        return {
            tool.name: tool.get_metrics()
            for tool in self.tools
        }
    
    async def validate_tool_call(
        self,
        tool_call: ToolCall
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a tool call before execution.
        
        Args:
            tool_call: Tool call to validate
            
        Returns:
            (is_valid, error_message)
        """
        tool_name = tool_call.tool_name
        
        if tool_name not in self.tool_map:
            return False, f"Tool '{tool_name}' not found"
        
        tool = self.tool_map[tool_name]
        
        try:
            is_valid = await tool.validate_parameters(tool_call.parameters)
            if not is_valid:
                return False, "Invalid parameters"
            
            has_permission = await tool.check_permissions(tool_call.parameters)
            if not has_permission:
                return False, "Insufficient permissions"
            
            return True, None
            
        except Exception as e:
            return False, str(e)
