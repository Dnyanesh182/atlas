"""
Example 5: Memory and Learning
Demonstrate memory systems and learning from experience.
"""

import asyncio
from atlas.system import AtlasSystem
from atlas.core.schemas import Task, Priority


async def memory_and_learning():
    """
    Example: Demonstrate memory systems and learning.
    """
    print("=" * 70)
    print("EXAMPLE 5: MEMORY AND LEARNING")
    print("=" * 70)
    
    # Initialize ATLAS
    atlas = AtlasSystem()
    await atlas.initialize()
    
    # Store some knowledge
    print("\n📚 Storing knowledge in semantic memory...")
    
    facts = [
        ("Python is a high-level programming language known for readability", "programming"),
        ("FastAPI is a modern web framework for building APIs with Python", "web_frameworks"),
        ("LangChain is a framework for developing LLM-powered applications", "ai_tools"),
        ("Vector databases enable semantic search over embeddings", "databases"),
    ]
    
    for fact, category in facts:
        await atlas.memory_manager.learn_fact(
            fact=fact,
            category=category,
            confidence=0.9
        )
        print(f"  ✅ Stored: {fact[:60]}...")
    
    # Execute a task that can leverage memory
    print("\n🤔 Executing task with memory context...")
    
    task = Task(
        description="""
        Explain how to build a modern AI-powered API service.
        Include technology choices and best practices.
        """,
        priority=Priority.MEDIUM,
        context={"use_memory": True}
    )
    
    result = await atlas.execute_task(task)
    
    print("\n📝 RESULT:")
    print("=" * 70)
    print(result)
    print("=" * 70)
    
    # Query memory
    print("\n🔍 Querying memory systems...")
    
    memories = await atlas.memory_manager.recall(
        query="API development with AI",
        top_k=3
    )
    
    print("\n💭 RELEVANT MEMORIES:")
    for mem_type, entries in memories.items():
        if entries:
            print(f"\n{mem_type.upper()}:")
            for entry in entries:
                print(f"  • {entry.content[:80]}...")
    
    # Memory statistics
    stats = atlas.memory_manager.get_stats()
    print("\n📊 MEMORY STATISTICS:")
    for mem_type, stat in stats.items():
        print(f"\n{mem_type.upper()}:")
        print(f"  Total Entries: {stat['total_entries']}")
        print(f"  Average Importance: {stat['average_importance']:.2f}")
    
    # Shutdown
    await atlas.shutdown()


if __name__ == "__main__":
    asyncio.run(memory_and_learning())
