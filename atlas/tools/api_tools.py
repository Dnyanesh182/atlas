"""
API and HTTP request tools.
"""

from typing import Any, Dict, Optional
import aiohttp
import json

from atlas.core.base_tool import BaseTool, ToolSchema


class HTTPRequestTool(BaseTool):
    """
    Make HTTP requests to APIs.
    
    Features:
    - GET, POST, PUT, DELETE support
    - Header and auth management
    - JSON and form data
    - Response parsing
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="http_request",
            description="Make HTTP requests to APIs",
            **kwargs
        )
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to request"
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE)",
                        "default": "GET"
                    },
                    "headers": {
                        "type": "object",
                        "description": "HTTP headers",
                        "default": {}
                    },
                    "data": {
                        "type": "object",
                        "description": "Request body data",
                        "default": None
                    }
                },
                "required": ["url"]
            },
            returns="HTTP response with status, headers, and body",
            is_safe=True
        )
    
    async def _execute_impl(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request."""
        try:
            async with aiohttp.ClientSession() as session:
                request_kwargs = {
                    "headers": headers or {},
                    "timeout": aiohttp.ClientTimeout(total=30)
                }
                
                if data:
                    request_kwargs["json"] = data
                
                async with session.request(method, url, **request_kwargs) as response:
                    # Parse response
                    try:
                        body = await response.json()
                    except:
                        body = await response.text()
                    
                    return {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "body": body,
                        "success": 200 <= response.status < 300
                    }
        except Exception as e:
            return {
                "status_code": 0,
                "headers": {},
                "body": None,
                "success": False,
                "error": str(e)
            }


class DatabaseQueryTool(BaseTool):
    """
    Execute database queries (read-only by default).
    
    Features:
    - SQL query execution
    - Result formatting
    - Connection pooling
    - Query timeout
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        read_only: bool = True,
        **kwargs
    ):
        super().__init__(
            name="database_query",
            description="Execute database queries",
            **kwargs
        )
        self.connection_string = connection_string
        self.read_only = read_only
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Query parameters",
                        "default": {}
                    }
                },
                "required": ["query"]
            },
            returns="Query results as list of dictionaries",
            is_safe=self.read_only,
            required_permissions=["database_access"]
        )
    
    async def _execute_impl(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute database query."""
        # Validate query if read-only
        if self.read_only and not self._is_read_only_query(query):
            raise PermissionError("Only SELECT queries allowed in read-only mode")
        
        # In production: use actual database connection
        # For now, return mock results
        
        return {
            "success": True,
            "rows": [],
            "row_count": 0,
            "query": query,
            "note": "Mock database - not connected"
        }
    
    def _is_read_only_query(self, query: str) -> bool:
        """Check if query is read-only."""
        query_upper = query.strip().upper()
        write_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER"]
        
        for keyword in write_keywords:
            if query_upper.startswith(keyword):
                return False
        
        return True
