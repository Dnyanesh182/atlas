"""
Critic Agent - Quality assessment and validation.

Responsibilities:
- Evaluate task outputs
- Score quality and correctness
- Provide constructive feedback
- Enforce quality standards
- Trigger re-execution when needed
"""

from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from atlas.core.base_agent import BaseAgent
from atlas.core.schemas import AgentType, Task, CritiqueResult


class CriticAgent(BaseAgent):
    """
    Critic Agent - Quality assurance and validation.
    
    Evaluates task outputs and enforces quality standards.
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        quality_threshold: float = 7.0,
        **kwargs
    ):
        super().__init__(
            agent_type=AgentType.CRITIC,
            llm=llm,
            name="CriticAgent",
            **kwargs
        )
        self.quality_threshold = quality_threshold
    
    async def execute(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> CritiqueResult:
        """
        Evaluate a completed task.
        
        Args:
            task: Task to critique
            context: Additional context
            
        Returns:
            Critique result with score and feedback
        """
        self.update_state(is_busy=True, current_task=task.id)
        
        try:
            # Build critique prompt
            prompt = self._build_critique_prompt(task, context)
            
            # Get critique
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            critique = await self._parse_critique_response(
                task.id,
                response.content
            )
            
            self.execution_count += 1
            return critique
            
        finally:
            self.update_state(is_busy=False, current_task=None)
    
    async def _process(
        self,
        messages: List[Any],
        **kwargs
    ) -> Any:
        """Process messages to generate critique."""
        response = await self.llm.ainvoke(messages)
        return response
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for critic."""
        return f"""You are an expert AI critic and quality assessor. Your role is to evaluate task outputs objectively and constructively.

Evaluation Criteria:
1. **Correctness**: Is the output factually accurate and logically sound?
2. **Completeness**: Does it fully address the task requirements?
3. **Quality**: Is the output well-structured and clear?
4. **Efficiency**: Was the approach reasonable and optimal?
5. **Safety**: Are there any risks or issues?

Quality Threshold: {self.quality_threshold}/10

For each evaluation:
1. Analyze the task and its output thoroughly
2. Score from 0-10 (be honest and calibrated)
3. Determine if it passes (≥{self.quality_threshold})
4. Provide specific, actionable feedback
5. List concrete areas for improvement

Be firm but fair. High standards produce excellent results.

Format your response as:
Score: X/10
Pass: Yes/No
Feedback: [detailed analysis]
Areas for Improvement:
- [specific point 1]
- [specific point 2]"""
    
    def _build_critique_prompt(
        self,
        task: Task,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for critique."""
        prompt_parts = [
            "Evaluate the following task execution:",
            f"\n**Task**: {task.description}",
            f"\n**Status**: {task.status.value}",
            f"\n**Priority**: {task.priority.value}",
        ]
        
        if task.result:
            prompt_parts.append(f"\n**Output**:\n{task.result}")
        
        if task.error:
            prompt_parts.append(f"\n**Error**: {task.error}")
        
        if context:
            prompt_parts.append(f"\n**Context**: {context}")
        
        prompt_parts.append("\nProvide your detailed critique.")
        
        return "\n".join(prompt_parts)
    
    async def _parse_critique_response(
        self,
        task_id,
        response: str
    ) -> CritiqueResult:
        """Parse critique response into structured result."""
        import re
        
        # Extract score
        score_match = re.search(r'Score:\s*(\d+(?:\.\d+)?)', response, re.IGNORECASE)
        score = float(score_match.group(1)) if score_match else 5.0
        
        # Extract pass/fail
        pass_match = re.search(r'Pass:\s*(Yes|No)', response, re.IGNORECASE)
        passed = pass_match.group(1).lower() == 'yes' if pass_match else score >= self.quality_threshold
        
        # Extract areas for improvement
        improvements = []
        improvement_section = re.search(
            r'Areas for Improvement:(.+?)(?=\n\n|\Z)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if improvement_section:
            improvement_text = improvement_section.group(1)
            improvements = [
                line.strip('- ').strip()
                for line in improvement_text.split('\n')
                if line.strip().startswith('-')
            ]
        
        return CritiqueResult(
            task_id=task_id,
            score=min(max(score, 0.0), 10.0),  # Clamp to 0-10
            passed=passed,
            feedback=response,
            areas_for_improvement=improvements
        )
    
    async def quick_check(
        self,
        output: str,
        expected_criteria: List[str]
    ) -> bool:
        """
        Quick validation check.
        
        Args:
            output: Output to check
            expected_criteria: List of criteria to verify
            
        Returns:
            True if passes quick check
        """
        prompt = f"""Quick validation check:

Output: {output[:500]}

Required criteria:
{chr(10).join(f"- {c}" for c in expected_criteria)}

Does this output meet all criteria? Respond with just "YES" or "NO"."""
        
        messages = [
            SystemMessage(content="You are a quick validation checker."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        return "yes" in response.content.lower()
    
    async def compare_outputs(
        self,
        outputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare multiple outputs and rank them.
        
        Args:
            outputs: List of outputs to compare
            
        Returns:
            Ranking and analysis
        """
        prompt = "Compare these outputs and rank them by quality:\n\n"
        
        for i, output in enumerate(outputs, 1):
            prompt += f"\n**Output {i}**:\n{output.get('content', '')[:300]}\n"
        
        prompt += "\nProvide ranking (best to worst) with brief justification."
        
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        return {
            "ranking_analysis": response.content,
            "outputs_count": len(outputs)
        }
    
    async def suggest_improvements(
        self,
        task: Task,
        current_output: str
    ) -> List[str]:
        """
        Suggest specific improvements for output.
        
        Args:
            task: Original task
            current_output: Current output
            
        Returns:
            List of improvement suggestions
        """
        prompt = f"""Task: {task.description}

Current Output:
{current_output[:500]}

Suggest 3-5 specific, actionable improvements to make this output excellent.
Format as a bullet list."""
        
        messages = [
            SystemMessage(content="You are an expert at improving outputs."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # Parse suggestions
        import re
        suggestions = [
            line.strip('- ').strip()
            for line in response.content.split('\n')
            if line.strip().startswith('-')
        ]
        
        return suggestions[:5]
