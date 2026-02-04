"""
Example 1: AI CTO Analysis
Autonomous AI agent acting as a startup CTO.
"""

import asyncio
from atlas.system import AtlasSystem
from atlas.core.schemas import Task, Priority


async def ai_cto_analysis():
    """
    Example: AI agent analyzes a startup idea and provides CTO-level insights.
    """
    print("=" * 70)
    print("EXAMPLE 1: AI CTO ANALYSIS")
    print("=" * 70)
    
    # Initialize ATLAS
    atlas = AtlasSystem()
    await atlas.initialize()
    
    # Create task
    task = Task(
        description="""
        Act as an experienced CTO for a startup building a B2B SaaS platform
        for restaurant management. Analyze:
        
        1. Technology stack recommendations
        2. Architecture decisions (microservices vs monolith)
        3. Database choices
        4. Security considerations
        5. Scalability strategy
        6. Cost projections for first year
        7. Team composition and hiring plan
        
        Provide a comprehensive technical roadmap.
        """,
        priority=Priority.HIGH,
        context={
            "role": "CTO",
            "domain": "B2B SaaS",
            "industry": "Restaurant Tech"
        }
    )
    
    # Execute
    print("\n🚀 Executing AI CTO Analysis...")
    result = await atlas.execute_task(task)
    
    print("\n📊 ANALYSIS RESULTS:")
    print("=" * 70)
    print(result)
    print("=" * 70)
    
    # Get task status
    task_info = atlas.get_task(task.id)
    print(f"\n✅ Task Status: {task_info.status}")
    print(f"📈 Retry Count: {task_info.retry_count}")
    
    # Shutdown
    await atlas.shutdown()


if __name__ == "__main__":
    asyncio.run(ai_cto_analysis())
