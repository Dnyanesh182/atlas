"""
LangGraph-based orchestration for ATLAS.
State machine for agent coordination.
"""

from typing import Any, Dict, TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage

from atlas.core.schemas import Task, TaskStatus


class AtlasState(TypedDict):
    """
    State for ATLAS execution graph.
    
    Tracks:
    - Current task
    - Messages and history
    - Agent outputs
    - Execution metrics
    """
    task: Task
    messages: Annotated[list[BaseMessage], operator.add]
    plan: Dict[str, Any]
    execution_result: Any
    critique: Dict[str, Any]
    retry_count: int
    should_retry: bool
    context: Dict[str, Any]


def create_atlas_graph(orchestrator) -> StateGraph:
    """
    Create the ATLAS execution graph.
    
    Graph structure:
    START -> plan -> execute -> critique -> [retry?] -> learn -> END
    
    Args:
        orchestrator: Orchestrator agent instance
        
    Returns:
        Compiled state graph
    """
    
    # Define node functions
    async def plan_node(state: AtlasState) -> AtlasState:
        """Planning node - creates execution plan."""
        task = state["task"]
        context = state.get("context", {})
        
        plan = await orchestrator.planner.execute(task, context)
        
        return {
            **state,
            "plan": plan.dict()
        }
    
    async def execute_node(state: AtlasState) -> AtlasState:
        """Execution node - executes the plan."""
        task = state["task"]
        context = state.get("context", {})
        
        result = await orchestrator.executor.execute(task, context)
        
        return {
            **state,
            "execution_result": result,
            "task": {**task.dict(), "result": result}
        }
    
    async def critique_node(state: AtlasState) -> AtlasState:
        """Critique node - evaluates results."""
        task = state["task"]
        context = state.get("context", {})
        
        critique = await orchestrator.critic.execute(task, context)
        
        # Determine if retry needed
        should_retry = (
            not critique.passed and
            state.get("retry_count", 0) < task.max_retries
        )
        
        return {
            **state,
            "critique": critique.dict(),
            "should_retry": should_retry
        }
    
    async def learn_node(state: AtlasState) -> AtlasState:
        """Learning node - stores experience in memory."""
        task = state["task"]
        critique = state.get("critique", {})
        
        # Store in episodic memory
        # (Would create proper ExecutionTrace in production)
        
        return state
    
    def should_retry(state: AtlasState) -> str:
        """Conditional edge - determine if retry needed."""
        if state.get("should_retry", False):
            return "retry"
        return "learn"
    
    # Build graph
    workflow = StateGraph(AtlasState)
    
    # Add nodes
    workflow.add_node("plan", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("learn", learn_node)
    
    # Add edges
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "execute")
    workflow.add_edge("execute", "critique")
    
    # Conditional edge for retry
    workflow.add_conditional_edges(
        "critique",
        should_retry,
        {
            "retry": "plan",  # Retry from planning
            "learn": "learn"
        }
    )
    
    workflow.add_edge("learn", END)
    
    # Compile
    return workflow.compile()


class LangGraphOrchestrator:
    """
    LangGraph-based orchestrator for ATLAS.
    
    Uses state graph for complex workflow coordination.
    """
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.graph = create_atlas_graph(orchestrator)
    
    async def execute_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute task using LangGraph workflow.
        
        Args:
            task: Task to execute
            context: Additional context
            
        Returns:
            Execution result
        """
        # Initialize state
        initial_state = AtlasState(
            task=task,
            messages=[],
            plan={},
            execution_result=None,
            critique={},
            retry_count=0,
            should_retry=False,
            context=context or {}
        )
        
        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)
        
        return final_state.get("execution_result")
