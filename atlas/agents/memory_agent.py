"""
Memory Agent - Manages memory systems and retrieval.

Responsibilities:
- Store experiences and knowledge
- Retrieve relevant memories
- Consolidate and organize memories
- Learn from past executions
- Provide context for tasks
"""

from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel

from atlas.core.base_agent import BaseAgent
from atlas.core.schemas import AgentType, Task, MemoryEntry, ExecutionTrace
from atlas.memory.manager import MemoryManager


class MemoryAgent(BaseAgent):
    """
    Memory Agent - Memory management and retrieval.
    
    Coordinates memory systems and provides context.
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        memory_manager: MemoryManager,
        **kwargs
    ):
        super().__init__(
            agent_type=AgentType.MEMORY,
            llm=llm,
            name="MemoryAgent",
            **kwargs
        )
        self.memory_manager = memory_manager
    
    async def execute(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute memory-related operations.
        
        Args:
            task: Memory task (store, retrieve, etc.)
            context: Additional context
            
        Returns:
            Memory operation result
        """
        self.update_state(is_busy=True, current_task=task.id)
        
        try:
            operation = task.context.get("operation", "retrieve")
            
            if operation == "store":
                result = await self._store_memory(task, context)
            elif operation == "retrieve":
                result = await self._retrieve_memories(task, context)
            elif operation == "consolidate":
                result = await self._consolidate_memories(task, context)
            elif operation == "learn":
                result = await self._learn_from_task(task, context)
            else:
                result = await self._retrieve_memories(task, context)
            
            self.execution_count += 1
            return result
            
        finally:
            self.update_state(is_busy=False, current_task=None)
    
    async def _process(
        self,
        messages: List[Any],
        **kwargs
    ) -> Any:
        """Process messages for memory operations."""
        response = await self.llm.ainvoke(messages)
        return response
    
    async def _store_memory(
        self,
        task: Task,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Store a memory."""
        content = task.context.get("content", task.description)
        memory_type = task.context.get("memory_type", "short_term")
        importance = task.context.get("importance", 0.5)
        
        memory_id = await self.memory_manager.remember(
            content=content,
            memory_type=memory_type,
            metadata=task.context.get("metadata", {}),
            importance=importance
        )
        
        return f"Stored memory: {memory_id}"
    
    async def _retrieve_memories(
        self,
        task: Task,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, List[MemoryEntry]]:
        """Retrieve relevant memories."""
        query = task.context.get("query", task.description)
        memory_types = task.context.get("memory_types", None)
        top_k = task.context.get("top_k", 5)
        
        memories = await self.memory_manager.recall(
            query=query,
            memory_types=memory_types,
            top_k=top_k
        )
        
        return memories
    
    async def _consolidate_memories(
        self,
        task: Task,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Consolidate memory systems."""
        stats = await self.memory_manager.consolidate_all()
        return stats
    
    async def _learn_from_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Learn from task execution."""
        # Extract learning from context
        trace = context.get("trace") if context else None
        outcome = context.get("outcome", "unknown")
        
        # Generate lessons learned
        lessons = await self._generate_lessons_learned(task, outcome, trace)
        
        # Store in episodic memory
        if trace:
            memory_id = await self.memory_manager.remember_task_execution(
                task=task,
                trace=trace,
                outcome=outcome,
                lessons_learned=lessons
            )
            return f"Learned from task: {memory_id}"
        
        return "Learning stored"
    
    async def _generate_lessons_learned(
        self,
        task: Task,
        outcome: str,
        trace: Optional[ExecutionTrace]
    ) -> str:
        """Generate lessons learned from task execution."""
        prompt = f"""Analyze this task execution and extract key learnings:

Task: {task.description}
Status: {task.status}
Outcome: {outcome}

What are the key lessons learned? What should be remembered for future similar tasks?
Be concise and actionable."""
        
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content="You extract insights from task executions."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def get_context_for_task(
        self,
        task: Task
    ) -> str:
        """
        Get relevant context for a task.
        
        Args:
            task: Task to get context for
            
        Returns:
            Formatted context string
        """
        return await self.memory_manager.get_context_for_task(task)
    
    async def store_fact(
        self,
        fact: str,
        category: str,
        source: Optional[str] = None
    ) -> str:
        """Store a fact in semantic memory."""
        memory_id = await self.memory_manager.learn_fact(
            fact=fact,
            category=category,
            source=source
        )
        return f"Fact stored: {memory_id}"
    
    async def recall_similar_tasks(
        self,
        task_description: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Recall similar past tasks."""
        similar_tasks = await self.memory_manager.episodic.get_similar_past_tasks(
            task_description=task_description,
            limit=limit
        )
        return similar_tasks
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return self.memory_manager.get_stats()
