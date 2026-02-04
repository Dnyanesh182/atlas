"""
Planner Agent - Converts goals into executable plans.

Responsibilities:
- Break down complex goals into subtasks
- Create dependency graphs
- Estimate cost and complexity
- Assess risks
- Generate execution strategies
"""

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from atlas.core.base_agent import BaseAgent
from atlas.core.schemas import AgentType, Task, Plan, Priority, TaskStatus


class PlannerAgent(BaseAgent):
    """
    Planner Agent - Strategic task decomposition and planning.
    
    Converts ambiguous goals into structured, executable plans.
    """
    
    def __init__(self, llm: BaseChatModel, **kwargs):
        super().__init__(
            agent_type=AgentType.PLANNER,
            llm=llm,
            name="PlannerAgent",
            **kwargs
        )
        self.output_parser = JsonOutputParser()
    
    async def execute(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """
        Create an execution plan for the task.
        
        Args:
            task: Task to plan
            context: Additional context
            
        Returns:
            Structured execution plan
        """
        self.update_state(is_busy=True, current_task=task.id)
        
        try:
            # Build planning prompt
            prompt = self._build_planning_prompt(task, context)
            
            # Generate plan
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            plan_data = await self._parse_plan_response(response.content)
            
            # Create Plan object
            plan = self._create_plan_from_data(task, plan_data)
            
            self.execution_count += 1
            return plan
            
        finally:
            self.update_state(is_busy=False, current_task=None)
    
    async def _process(
        self,
        messages: List[Any],
        **kwargs
    ) -> Any:
        """Process messages to generate plan."""
        response = await self.llm.ainvoke(messages)
        return response
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for planner."""
        return """You are an expert AI planning agent. Your role is to break down complex goals into actionable, well-structured plans.

For each goal, you must:
1. Analyze the requirements and constraints
2. Decompose into logical subtasks
3. Identify dependencies between tasks
4. Estimate complexity, cost, and time
5. Assess risks and suggest mitigations
6. Create an optimal execution order

Output a structured JSON plan with:
- steps: List of subtasks (each with id, description, priority, dependencies)
- dependency_graph: Map of task dependencies
- risk_assessment: Analysis of potential issues
- estimated_total_cost: Estimated cost in USD
- estimated_total_time: Estimated time in seconds

Be thorough, realistic, and strategic."""
    
    def _build_planning_prompt(
        self,
        task: Task,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for plan generation."""
        prompt_parts = [
            f"Goal: {task.description}",
            f"\nPriority: {task.priority.value}",
        ]
        
        if context:
            prompt_parts.append(f"\nContext: {context}")
        
        if task.context:
            prompt_parts.append(f"\nTask Context: {task.context}")
        
        prompt_parts.append("""

Create a detailed execution plan. Consider:
- What are the logical steps?
- What dependencies exist between steps?
- What could go wrong?
- How can we optimize the execution?

Return your plan in the following JSON format:
{
    "steps": [
        {
            "id": "step_1",
            "description": "...",
            "priority": "high|medium|low",
            "estimated_complexity": 0.1-1.0,
            "estimated_cost": 0.01,
            "dependencies": []
        }
    ],
    "dependency_graph": {
        "step_1": [],
        "step_2": ["step_1"]
    },
    "risk_assessment": "...",
    "estimated_total_cost": 0.05,
    "estimated_total_time": 120
}""")
        
        return "\n".join(prompt_parts)
    
    async def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into plan data."""
        try:
            # Try to extract JSON from response
            import json
            import re
            
            # Find JSON in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
                return plan_data
            else:
                # Fallback: create simple plan
                return self._create_fallback_plan(response)
        except Exception as e:
            # Fallback plan
            return self._create_fallback_plan(response)
    
    def _create_fallback_plan(self, description: str) -> Dict[str, Any]:
        """Create a simple fallback plan."""
        return {
            "steps": [
                {
                    "id": "step_1",
                    "description": description,
                    "priority": "medium",
                    "estimated_complexity": 0.5,
                    "estimated_cost": 0.01,
                    "dependencies": []
                }
            ],
            "dependency_graph": {"step_1": []},
            "risk_assessment": "Simple single-step plan",
            "estimated_total_cost": 0.01,
            "estimated_total_time": 60
        }
    
    def _create_plan_from_data(
        self,
        original_task: Task,
        plan_data: Dict[str, Any]
    ) -> Plan:
        """Create Plan object from parsed data."""
        # Create subtasks
        steps = []
        for step_data in plan_data.get("steps", []):
            subtask = Task(
                description=step_data["description"],
                priority=Priority(step_data.get("priority", "medium")),
                estimated_complexity=step_data.get("estimated_complexity", 0.5),
                estimated_cost=step_data.get("estimated_cost", 0.01),
                dependencies=[
                    UUID(dep) if isinstance(dep, str) else dep
                    for dep in step_data.get("dependencies", [])
                ],
                parent_id=original_task.id
            )
            steps.append(subtask)
        
        # Create plan
        plan = Plan(
            goal=original_task.description,
            steps=steps,
            dependency_graph=plan_data.get("dependency_graph", {}),
            estimated_total_cost=plan_data.get("estimated_total_cost", 0.01),
            estimated_total_time=plan_data.get("estimated_total_time", 60),
            risk_assessment=plan_data.get("risk_assessment", "")
        )
        
        return plan
    
    async def refine_plan(
        self,
        plan: Plan,
        feedback: str
    ) -> Plan:
        """
        Refine a plan based on feedback.
        
        Args:
            plan: Original plan
            feedback: Feedback for refinement
            
        Returns:
            Refined plan
        """
        prompt = f"""
        Original Plan:
        Goal: {plan.goal}
        Steps: {len(plan.steps)}
        Risk Assessment: {plan.risk_assessment}
        
        Feedback: {feedback}
        
        Refine the plan to address the feedback. Maintain JSON format.
        """
        
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        plan_data = await self._parse_plan_response(response.content)
        
        # Create task from goal
        task = Task(description=plan.goal)
        
        return self._create_plan_from_data(task, plan_data)
