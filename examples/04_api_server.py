"""
Example 4: API Server
Run ATLAS as a production API server.
"""

import uvicorn
from atlas.config import get_config

def run_api_server():
    """
    Run ATLAS as a FastAPI server.
    
    Access:
    - API Docs: http://localhost:8000/docs
    - Health: http://localhost:8000/health
    - Tasks: http://localhost:8000/tasks
    """
    print("=" * 70)
    print("ATLAS API SERVER")
    print("=" * 70)
    print("\n🚀 Starting API server...")
    print("\n📚 Available endpoints:")
    print("   • API Documentation: http://localhost:8000/docs")
    print("   • Health Check: http://localhost:8000/health")
    print("   • Create Task: POST http://localhost:8000/tasks")
    print("   • Get Task: GET http://localhost:8000/tasks/{task_id}")
    print("   • System Status: GET http://localhost:8000/status")
    print("   • Memory Store: POST http://localhost:8000/memory/store")
    print("   • Memory Recall: POST http://localhost:8000/memory/recall")
    print("\n" + "=" * 70 + "\n")
    
    config = get_config()
    
    uvicorn.run(
        "atlas.api:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        workers=config.api.workers,
        log_level="info"
    )


if __name__ == "__main__":
    run_api_server()
