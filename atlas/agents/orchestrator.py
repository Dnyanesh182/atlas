"""
Orchestrator Agent - Coordinates all agents and manages workflows.

Responsibilities:
- Own global execution state
- Coordinate agent interactions
- Handle retries and failures
- Manage execution flow
- Track system state
"""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.language_models import BaseChatModel

from atlas.core.base_agent import BaseAgent
from atlas.core.schemas import (
    AgentType,
    Task,
    TaskStatus,
    Plan,
    ExecutionTrace,
)
from atlas.agents.planner import PlannerAgent
from atlas.agents.executor import ExecutorAgent
from atlas.agents.critic import CriticAgent
from atlas.agents.memory_agent import MemoryAgent
from atlas.agents.tool_agent import ToolAgent


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - Global workflow coordination.
    
    Coordinates all other agents to accomplish complex goals.
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        planner: PlannerAgent,
        executor: ExecutorAgent,
        critic: CriticAgent,
        memory: MemoryAgent,
        tool_agent: ToolAgent,
        **kwargs
    ):
        super().__init__(
            agent_type=AgentType.ORCHESTRATOR,
            llm=llm,
            name="OrchestratorAgent",
            **kwargs
        )
        
        # Agent references
        self.planner = planner
        self.executor = executor
        self.critic = critic
        self.memory = memory
        self.tool_agent = tool_agent
        
        # Execution state
        self.active_tasks: Dict[UUID, Task] = {}
        self.completed_tasks: List[Task] = []
        self.failed_tasks: List[Task] = []
    
    async def execute(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a high-level task by coordinating agents.
        
        Args:
            task: Task to execute
            context: Additional context
            
        Returns:
            Final result
        """
        self.update_state(is_busy=True, current_task=task.id)
        self.active_tasks[task.id] = task
        
        try:
            # Phase 1: Planning
            task.status = TaskStatus.PLANNING
            plan = await self._planning_phase(task, context)
            
            # Phase 2: Execution
            task.status = TaskStatus.EXECUTING
            result = await self._execution_phase(task, plan, context)
            
            # Phase 3: Critique
            task.status = TaskStatus.CRITIQUING
            critique = await self._critique_phase(task, result, context)
            
            # Phase 4: Retry if needed
            if not critique.passed and task.retry_count < task.max_retries:
                return await self._retry_phase(task, critique, context)
            
            # Phase 5: Learning
            await self._learning_phase(task, result, critique, context)
            
            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.result = result
            self.completed_tasks.append(task)
            
            self.execution_count += 1
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.failed_tasks.append(task)
            await self.handle_error(task, e, context)
            raise
            
        finally:
            self.update_state(is_busy=False, current_task=None)
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
    
    async def _process(
        self,
        messages: List[Any],
        **kwargs
    ) -> Any:
        """Process messages for orchestration."""
        response = await self.llm.ainvoke(messages)
        return response
    
    async def _planning_phase(
        self,
        task: Task,
        context: Optional[Dict[str, Any]]
    ) -> Plan:
        """Phase 1: Create execution plan."""
        # Get relevant context from memory
        memory_context = await self.memory.get_context_for_task(task)
        
        # Augment context
        full_context = {
            **(context or {}),
            "memory_context": memory_context
        }
        
        # Generate plan
        plan = await self.planner.execute(task, full_context)
        
        return plan
    
    async def _execution_phase(
        self,
        task: Task,
        plan: Plan,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Phase 2: Execute the plan."""
        if not plan.steps:
            # Simple execution
            return await self.executor.execute(task, context)
        
        # Execute plan steps
        results = []
        for step in plan.steps:
            step_result = await self.executor.execute(step, context)
            results.append(step_result)
        
        # Combine results
        combined_result = "\n\n".join(str(r) for r in results)
        return combined_result
    
    async def _critique_phase(
        self,
        task: Task,
        result: Any,
        context: Optional[Dict[str, Any]]
    ):
        """Phase 3: Critique the result."""
        # Update task with result
        task.result = result
        
        # Get critique
        critique = await self.critic.execute(task, context)
        
        return critique
    
    async def _retry_phase(
        self,
        task: Task,
        critique,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Phase 4: Retry with improvements."""
        task.retry_count += 1
        task.status = TaskStatus.RETRYING
        
        # Add critique feedback to context
        retry_context = {
            **(context or {}),
            "previous_attempt": task.result,
            "feedback": critique.feedback,
            "improvements_needed": critique.areas_for_improvement
        }
        
        # Re-execute
        return await self.execute(task, retry_context)
    
    async def _learning_phase(
        self,
        task: Task,
        result: Any,
        critique,
        context: Optional[Dict[str, Any]]
    ):
        """Phase 5: Learn from execution."""
        # Create execution trace
        trace = ExecutionTrace(
            task_id=task.id,
            agent_type=self.agent_type,
            action="orchestrate",
            input_data={"description": task.description},
            output_data={"result": str(result)[:500]},
            duration=0.0,  # Would be calculated
            cost=task.actual_cost or 0.0
        )
        
        # Store in memory
        outcome = "success" if critique.passed else "partial_success"
        await self.memory.memory_manager.remember_task_execution(
            task=task,
            trace=trace,
            outcome=outcome,
            lessons_learned=critique.feedback
        )
    
    async def execute_multi_task(
        self,
        tasks: List[Task],
        parallel: bool = False
    ) -> List[Any]:
        """
        Execute multiple tasks.
        
        Args:
            tasks: List of tasks to execute
            parallel: Execute in parallel if True
            
        Returns:
            List of results
        """
        if parallel:
            # Execute in parallel
            results = await asyncio.gather(*[
                self.execute(task)
                for task in tasks
            ], return_exceptions=True)
        else:
            # Execute sequentially
            results = []
            for task in tasks:
                try:
                    result = await self.execute(task)
                    results.append(result)
                except Exception as e:
                    results.append(e)
        
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "agent_metrics": {
                "planner": self.planner.get_metrics(),
                "executor": self.executor.get_metrics(),
                "critic": self.critic.get_metrics(),
                "memory": self.memory.get_metrics(),
                "tool_agent": self.tool_agent.get_metrics(),
            },
            "memory_stats": self.memory.get_memory_stats()
        }
