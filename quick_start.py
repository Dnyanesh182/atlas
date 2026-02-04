"""
Quick start script - demonstrates basic ATLAS usage.
"""

import asyncio
from atlas.system import AtlasSystem
from atlas.core.schemas import Task, Priority


async def quick_start():
    """
    Quick start example showing basic ATLAS usage.
    """
    print("\n" + "=" * 70)
    print("ATLAS QUICK START")
    print("Autonomous Task Learning & Agent System")
    print("=" * 70 + "\n")
    
    # Step 1: Initialize system
    print("Step 1: Initializing ATLAS...")
    atlas = AtlasSystem()
    await atlas.initialize()
    print("✅ System initialized\n")
    
    # Step 2: Create a simple task
    print("Step 2: Creating task...")
    task = Task(
        description="""
        Create a brief 3-point marketing strategy for a new AI productivity tool
        targeting software developers. Focus on differentiation and value proposition.
        """,
        priority=Priority.HIGH
    )
    print(f"✅ Task created: {task.id}\n")
    
    # Step 3: Execute task
    print("Step 3: Executing task (this may take a moment)...")
    result = await atlas.execute_task(task)
    print("✅ Task completed\n")
    
    # Step 4: Display results
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(result)
    print("=" * 70 + "\n")
    
    # Step 5: Show metrics
    print("Step 4: System metrics...")
    status = atlas.get_status()
    print(f"  Completed Tasks: {status['completed_tasks']}")
    print(f"  System Uptime: {status['uptime_seconds']:.1f}s")
    print(f"  Active Agents: {status['active_agents']}")
    print("✅ Done\n")
    
    # Shutdown
    await atlas.shutdown()
    
    print("=" * 70)
    print("🎉 Success! ATLAS is working correctly.")
    print("\nNext steps:")
    print("  • Try examples: python examples/01_ai_cto_analysis.py")
    print("  • Start API: python examples/04_api_server.py")
    print("  • Read docs: See README.md")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(quick_start())
