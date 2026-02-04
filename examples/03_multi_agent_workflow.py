"""
Example 3: Multi-Agent Workflow
Complex multi-step task with agent coordination.
"""

import asyncio
from atlas.system import AtlasSystem
from atlas.core.schemas import Task, Priority


async def multi_agent_workflow():
    """
    Example: Complex workflow demonstrating agent coordination.
    """
    print("=" * 70)
    print("EXAMPLE 3: MULTI-AGENT WORKFLOW")
    print("=" * 70)
    
    # Initialize ATLAS
    atlas = AtlasSystem()
    await atlas.initialize()
    
    # Create multiple related tasks
    tasks = [
        Task(
            description="Research current trends in renewable energy technology",
            priority=Priority.HIGH,
            context={"phase": "research"}
        ),
        Task(
            description="Analyze market opportunities for solar panel installation services",
            priority=Priority.HIGH,
            context={"phase": "analysis"}
        ),
        Task(
            description="Create a business plan outline for a solar installation startup",
            priority=Priority.MEDIUM,
            context={"phase": "planning"}
        )
    ]
    
    # Execute tasks
    print("\n🤖 Executing Multi-Agent Workflow...")
    results = []
    
    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/3] Executing: {task.description[:60]}...")
        result = await atlas.execute_task(task)
        results.append(result)
        print(f"✅ Task {i} completed")
    
    # Display results
    print("\n" + "=" * 70)
    print("WORKFLOW RESULTS")
    print("=" * 70)
    
    for i, (task, result) in enumerate(zip(tasks, results), 1):
        print(f"\nTask {i}: {task.description[:50]}...")
        print(f"Status: {task.status}")
        print(f"Result Preview: {str(result)[:200]}...")
        print("-" * 70)
    
    # Agent metrics
    status = atlas.get_status()
    print("\n📊 AGENT PERFORMANCE METRICS:")
    for agent_name, metrics in status['agent_metrics'].items():
        print(f"\n{agent_name.upper()}:")
        print(f"  Executions: {metrics['execution_count']}")
        print(f"  Total Cost: ${metrics['total_cost']:.4f}")
        print(f"  Avg Cost: ${metrics['average_cost']:.4f}")
    
    # Shutdown
    await atlas.shutdown()


if __name__ == "__main__":
    asyncio.run(multi_agent_workflow())
