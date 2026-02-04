"""
Executor Agent - Executes tasks using tools and code.

Responsibilities:
- Execute action plans
- Use tools and APIs
- Write and run code
- Handle retries and errors
- Produce results
"""

from typing import Any, Dict, List, Optional
import asyncio

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from atlas.core.base_agent import BaseAgent
from atlas.core.schemas import AgentType, Task, TaskStatus, ToolCall, ToolResult
from atlas.core.base_tool import BaseTool


class ExecutorAgent(BaseAgent):
    """
    Executor Agent - Action execution and tool orchestration.
    
    Executes tasks using available tools and generates results.
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List[BaseTool]] = None,
        **kwargs
    ):
        super().__init__(
            agent_type=AgentType.EXECUTOR,
            llm=llm,
            name="ExecutorAgent",
            **kwargs
        )
        self.tools = tools or []
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.agent_executor = None
        
        if self.tools:
            self._initialize_agent_executor()
    
    def _initialize_agent_executor(self):
        """Initialize LangChain agent executor with tools."""
        # Convert ATLAS tools to LangChain tools
        langchain_tools = self._convert_tools_to_langchain()
        
        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent (Note: In production, handle tool conversion properly)
        # For now, we'll use direct tool execution
        self.agent_executor = None  # Would be: create_openai_tools_agent(...)
    
    def _convert_tools_to_langchain(self):
        """Convert ATLAS tools to LangChain format."""
        # In production: properly convert tools
        return []
    
    async def execute(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a task.
        
        Args:
            task: Task to execute
            context: Additional context
            
        Returns:
            Execution result
        """
        self.update_state(is_busy=True, current_task=task.id)
        
        try:
            # Build execution prompt
            prompt = self._build_execution_prompt(task, context)
            
            # Execute with tool support
            if self.agent_executor:
                result = await self._execute_with_agent(prompt)
            else:
                result = await self._execute_direct(task, prompt)
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            
            self.execution_count += 1
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            await self.handle_error(task, e, context)
            raise
            
        finally:
            self.update_state(is_busy=False, current_task=None)
    
    async def _process(
        self,
        messages: List[Any],
        **kwargs
    ) -> Any:
        """Process messages to execute task."""
        response = await self.llm.ainvoke(messages)
        return response.content
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for executor."""
        available_tools = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools
        ])
        
        return f"""You are an expert AI execution agent. Your role is to complete tasks efficiently and accurately.

Available Tools:
{available_tools if available_tools else "No tools available - use reasoning and knowledge"}

Guidelines:
1. Understand the task requirements thoroughly
2. Choose the most appropriate tools and methods
3. Execute step-by-step with clear reasoning
4. Handle errors gracefully with fallback strategies
5. Provide clear, actionable results
6. Be precise and thorough

If you need to use a tool, explain your reasoning first, then use it.
Always verify your work before reporting completion."""
    
    def _build_execution_prompt(
        self,
        task: Task,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for task execution."""
        prompt_parts = [
            f"Task: {task.description}",
            f"\nPriority: {task.priority.value}",
        ]
        
        if context:
            prompt_parts.append(f"\nContext: {context}")
        
        if task.context:
            prompt_parts.append(f"\nAdditional Context: {task.context}")
        
        prompt_parts.append("\nExecute this task and provide the result.")
        
        return "\n".join(prompt_parts)
    
    async def _execute_with_agent(self, prompt: str) -> str:
        """Execute using agent executor with tools."""
        # In production: use full agent executor
        result = await self.agent_executor.ainvoke({"input": prompt})
        return result["output"]
    
    async def _execute_direct(
        self,
        task: Task,
        prompt: str
    ) -> str:
        """Execute directly without agent framework."""
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute a specific tool.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            
        Returns:
            Tool execution result
        """
        if tool_name not in self.tool_map:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool = self.tool_map[tool_name]
        tool_call = ToolCall(
            tool_name=tool_name,
            parameters=parameters
        )
        
        result = await tool.execute(tool_call)
        
        # Track tool usage
        self.state.tool_calls.append(tool_call)
        self.state.tool_results.append(result)
        
        return result
    
    async def execute_with_retry(
        self,
        task: Task,
        max_retries: int = 3,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute task with automatic retry on failure.
        
        Args:
            task: Task to execute
            max_retries: Maximum retry attempts
            context: Additional context
            
        Returns:
            Execution result
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                task.retry_count = attempt
                result = await self.execute(task, context)
                return result
                
            except Exception as e:
                last_error = e
                task.status = TaskStatus.RETRYING
                
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        # All retries failed
        task.status = TaskStatus.FAILED
        task.error = f"Failed after {max_retries} attempts: {last_error}"
        raise last_error
    
    def add_tool(self, tool: BaseTool):
        """Add a tool to the executor."""
        self.tools.append(tool)
        self.tool_map[tool.name] = tool
        
        # Reinitialize agent if tools changed
        if self.tools:
            self._initialize_agent_executor()
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.tool_map.keys())
