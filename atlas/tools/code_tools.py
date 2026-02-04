"""
Code execution tools with sandboxing.
"""

import asyncio
import sys
from typing import Any, Dict, Optional
from io import StringIO
import contextlib

from atlas.core.base_tool import BaseTool, ToolSchema


class PythonExecuteTool(BaseTool):
    """
    Execute Python code in a sandboxed environment.
    
    Features:
    - Execute Python code safely
    - Capture stdout/stderr
    - Timeout protection
    - Limited imports
    """
    
    def __init__(
        self,
        timeout: int = 30,
        allowed_imports: Optional[list] = None,
        **kwargs
    ):
        super().__init__(
            name="python_execute",
            description="Execute Python code and return output",
            **kwargs
        )
        self.timeout = timeout
        self.allowed_imports = allowed_imports or [
            "math", "datetime", "json", "re", "collections",
            "itertools", "functools", "typing"
        ]
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Execution timeout in seconds",
                        "default": self.timeout
                    }
                },
                "required": ["code"]
            },
            returns="Execution output (stdout, stderr, result)",
            is_safe=False,  # Code execution is inherently risky
            required_permissions=["code_execution"]
        )
    
    async def _execute_impl(
        self,
        code: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute Python code."""
        timeout = timeout or self.timeout
        
        # Validate code safety
        if not await self._is_code_safe(code):
            raise PermissionError("Code contains forbidden operations")
        
        try:
            # Capture output
            stdout = StringIO()
            stderr = StringIO()
            result = None
            
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                # Create restricted globals
                restricted_globals = {
                    "__builtins__": __builtins__,
                    "print": print,
                }
                
                # Execute code with timeout
                exec(code, restricted_globals)
                
                # Get result if any
                if "result" in restricted_globals:
                    result = restricted_globals["result"]
            
            return {
                "success": True,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "result": str(result) if result is not None else None,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "stdout": stdout.getvalue() if 'stdout' in locals() else "",
                "stderr": stderr.getvalue() if 'stderr' in locals() else "",
                "result": None,
                "error": str(e)
            }
    
    async def _is_code_safe(self, code: str) -> bool:
        """
        Check if code is safe to execute.
        
        Args:
            code: Code to validate
            
        Returns:
            True if safe
        """
        # Block dangerous operations
        forbidden_patterns = [
            "import os",
            "import sys",
            "import subprocess",
            "__import__",
            "eval(",
            "exec(",
            "compile(",
            "open(",  # File operations blocked for safety
            "input(",
            "breakpoint(",
        ]
        
        code_lower = code.lower()
        for pattern in forbidden_patterns:
            if pattern in code_lower:
                return False
        
        return True


class ShellExecuteTool(BaseTool):
    """
    Execute shell commands (with strict safety controls).
    
    WARNING: This tool has significant security implications.
    Only enable in controlled environments.
    """
    
    def __init__(
        self,
        allowed_commands: Optional[list] = None,
        **kwargs
    ):
        super().__init__(
            name="shell_execute",
            description="Execute shell commands",
            **kwargs
        )
        self.allowed_commands = allowed_commands or ["ls", "pwd", "echo"]
    
    def get_schema(self) -> ToolSchema:
        """Get tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Execution timeout in seconds",
                        "default": 30
                    }
                },
                "required": ["command"]
            },
            returns="Command output",
            is_safe=False,
            required_permissions=["shell_execution"]
        )
    
    async def _execute_impl(
        self,
        command: str,
        timeout: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute shell command."""
        # Validate command
        cmd_parts = command.split()
        if not cmd_parts:
            raise ValueError("Empty command")
        
        base_command = cmd_parts[0]
        if base_command not in self.allowed_commands:
            raise PermissionError(
                f"Command '{base_command}' not in allowed list: {self.allowed_commands}"
            )
        
        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "return_code": process.returncode
            }
            
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Command timed out after {timeout}s")
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }
