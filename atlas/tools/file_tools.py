"""
File system tools for reading and writing files.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import aiofiles
import json

from atlas.core.base_tool import BaseTool, ToolSchema


class FileReadTool(BaseTool):
    """
    Read files from the file system.
    
    Features:
    - Read text files
    - Support multiple formats
    - Safe path validation
    """
    
    def __init__(self, allowed_paths: Optional[list] = None, **kwargs):
        super().__init__(
            name="file_read",
            description="Read content from a file",
            **kwargs
        )
        self.allowed_paths = allowed_paths or []
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["file_path"]
            },
            returns="File content as string",
            is_safe=True
        )
    
    async def _execute_impl(self, file_path: str, **kwargs) -> str:
        """Read file content."""
        try:
            path = Path(file_path)
            
            # Validate path
            if not await self._is_path_allowed(path):
                raise PermissionError(f"Access to {file_path} not allowed")
            
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read file
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            return content
            
        except Exception as e:
            raise Exception(f"Error reading file: {e}")
    
    async def _is_path_allowed(self, path: Path) -> bool:
        """Check if path access is allowed."""
        if not self.allowed_paths:
            return True  # No restrictions
        
        # Check if path is within allowed paths
        for allowed in self.allowed_paths:
            allowed_path = Path(allowed).resolve()
            try:
                path.resolve().relative_to(allowed_path)
                return True
            except ValueError:
                continue
        
        return False


class FileWriteTool(BaseTool):
    """
    Write files to the file system.
    
    Features:
    - Write text files
    - Create directories
    - Safe path validation
    """
    
    def __init__(self, allowed_paths: Optional[list] = None, **kwargs):
        super().__init__(
            name="file_write",
            description="Write content to a file",
            **kwargs
        )
        self.allowed_paths = allowed_paths or []
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Write mode: 'write' or 'append'",
                        "default": "write"
                    }
                },
                "required": ["file_path", "content"]
            },
            returns="Success message with file path",
            is_safe=False  # Modifies system state
        )
    
    async def _execute_impl(
        self,
        file_path: str,
        content: str,
        mode: str = "write",
        **kwargs
    ) -> str:
        """Write content to file."""
        try:
            path = Path(file_path)
            
            # Validate path
            if not await self._is_path_allowed(path):
                raise PermissionError(f"Write access to {file_path} not allowed")
            
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            write_mode = 'a' if mode == 'append' else 'w'
            async with aiofiles.open(path, write_mode, encoding='utf-8') as f:
                await f.write(content)
            
            return f"Successfully wrote to {file_path}"
            
        except Exception as e:
            raise Exception(f"Error writing file: {e}")
    
    async def _is_path_allowed(self, path: Path) -> bool:
        """Check if path write is allowed."""
        if not self.allowed_paths:
            return True
        
        for allowed in self.allowed_paths:
            allowed_path = Path(allowed).resolve()
            try:
                path.resolve().relative_to(allowed_path)
                return True
            except ValueError:
                continue
        
        return False


class FileListTool(BaseTool):
    """
    List files in a directory.
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="file_list",
            description="List files and directories in a path",
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
                    "directory": {
                        "type": "string",
                        "description": "Directory path to list"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter files",
                        "default": "*"
                    }
                },
                "required": ["directory"]
            },
            returns="List of files and directories",
            is_safe=True
        )
    
    async def _execute_impl(
        self,
        directory: str,
        pattern: str = "*",
        **kwargs
    ) -> List[str]:
        """List directory contents."""
        try:
            path = Path(directory)
            
            if not path.exists():
                raise FileNotFoundError(f"Directory not found: {directory}")
            
            if not path.is_dir():
                raise NotADirectoryError(f"Not a directory: {directory}")
            
            # List files
            files = [str(p.relative_to(path)) for p in path.glob(pattern)]
            return sorted(files)
            
        except Exception as e:
            raise Exception(f"Error listing directory: {e}")
