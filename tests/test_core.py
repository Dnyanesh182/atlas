"""
Test suite for ATLAS core functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from atlas.core.schemas import Task, TaskStatus, Priority, AgentType
from atlas.agents.planner import PlannerAgent
from atlas.agents.executor import ExecutorAgent
from atlas.agents.critic import CriticAgent
from atlas.memory.short_term import ShortTermMemory
from atlas.memory.long_term import LongTermMemory


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = AsyncMock()
    response = Mock()
    response.content = "Test response"
    llm.ainvoke.return_value = response
    return llm


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        description="Test task description",
        priority=Priority.MEDIUM
    )


class TestTask:
    """Test Task model."""
    
    def test_task_creation(self):
        """Test task can be created."""
        task = Task(description="Test")
        assert task.description == "Test"
        assert task.status == TaskStatus.PENDING
        assert task.priority == Priority.MEDIUM
    
    def test_task_with_context(self):
        """Test task with context."""
        task = Task(
            description="Test",
            context={"key": "value"}
        )
        assert task.context["key"] == "value"


class TestPlannerAgent:
    """Test Planner Agent."""
    
    @pytest.mark.asyncio
    async def test_planner_creates_plan(self, mock_llm, sample_task):
        """Test planner can create a plan."""
        planner = PlannerAgent(llm=mock_llm)
        
        # Mock response to return JSON-like string
        mock_llm.ainvoke.return_value.content = '{"steps": [], "dependency_graph": {}}'
        
        plan = await planner.execute(sample_task)
        
        assert plan is not None
        assert hasattr(plan, 'steps')
        assert hasattr(plan, 'dependency_graph')


class TestExecutorAgent:
    """Test Executor Agent."""
    
    @pytest.mark.asyncio
    async def test_executor_executes_task(self, mock_llm, sample_task):
        """Test executor can execute a task."""
        executor = ExecutorAgent(llm=mock_llm)
        
        result = await executor.execute(sample_task)
        
        assert result is not None
        assert mock_llm.ainvoke.called


class TestCriticAgent:
    """Test Critic Agent."""
    
    @pytest.mark.asyncio
    async def test_critic_evaluates_task(self, mock_llm, sample_task):
        """Test critic can evaluate a task."""
        critic = CriticAgent(llm=mock_llm)
        sample_task.result = "Some result"
        
        # Mock critique response
        mock_llm.ainvoke.return_value.content = """
        Score: 8/10
        Pass: Yes
        Feedback: Good work
        Areas for Improvement:
        - Point 1
        - Point 2
        """
        
        critique = await critic.execute(sample_task)
        
        assert critique is not None
        assert critique.score > 0
        assert isinstance(critique.passed, bool)


class TestShortTermMemory:
    """Test Short-Term Memory."""
    
    @pytest.mark.asyncio
    async def test_memory_store_retrieve(self):
        """Test memory can store and retrieve."""
        memory = ShortTermMemory()
        
        # Store
        memory_id = await memory.store("Test content")
        assert memory_id is not None
        
        # Retrieve
        results = await memory.retrieve("Test")
        assert len(results) > 0


class TestLongTermMemory:
    """Test Long-Term Memory."""
    
    @pytest.mark.asyncio
    async def test_long_term_storage(self):
        """Test long-term memory storage."""
        memory = LongTermMemory()
        
        # Store with high importance
        memory_id = await memory.store(
            "Important fact",
            importance=0.9
        )
        assert memory_id is not None
        
        # Low importance should be rejected
        low_id = await memory.store(
            "Unimportant fact",
            importance=0.1
        )
        assert low_id is None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
