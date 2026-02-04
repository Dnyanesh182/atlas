"""
Example 2: Competitor Research
Deep autonomous competitor analysis.
"""

import asyncio
from atlas.system import AtlasSystem
from atlas.core.schemas import Task, Priority


async def competitor_research():
    """
    Example: Deep competitor analysis for a product launch.
    """
    print("=" * 70)
    print("EXAMPLE 2: AUTONOMOUS COMPETITOR RESEARCH")
    print("=" * 70)
    
    # Initialize ATLAS
    atlas = AtlasSystem()
    await atlas.initialize()
    
    # Create task
    task = Task(
        description="""
        Conduct comprehensive competitor research for a new AI coding assistant product.
        
        Research Requirements:
        1. Identify top 5 competitors (e.g., GitHub Copilot, Cursor, Tabnine)
        2. Analyze their features, pricing, and market positioning
        3. Identify feature gaps and opportunities
        4. Assess their strengths and weaknesses
        5. Recommend differentiation strategy
        6. Provide go-to-market recommendations
        
        Synthesize findings into an executive summary.
        """,
        priority=Priority.HIGH,
        context={
            "product": "AI Coding Assistant",
            "market": "Developer Tools",
            "target_audience": "Professional Developers"
        }
    )
    
    # Execute
    print("\n🔍 Executing Competitor Research...")
    result = await atlas.execute_task(task)
    
    print("\n📊 RESEARCH FINDINGS:")
    print("=" * 70)
    print(result)
    print("=" * 70)
    
    # Get system status
    status = atlas.get_status()
    print(f"\n📈 System Status:")
    print(f"   Active Tasks: {status['active_tasks']}")
    print(f"   Completed: {status['completed_tasks']}")
    print(f"   Memory Entries: {sum(m['total_entries'] for m in status['memory_stats'].values())}")
    
    # Shutdown
    await atlas.shutdown()


if __name__ == "__main__":
    asyncio.run(competitor_research())
