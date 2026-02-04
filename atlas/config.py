"""
Configuration management for ATLAS.
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import os


class LLMConfig(BaseModel):
    """LLM configuration."""
    provider: str = "openai"  # openai, anthropic, local
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    persist_dir: Path = Field(default=Path("data/memory"))
    vector_store: str = "faiss"  # faiss, chroma
    embedding_model: str = "text-embedding-ada-002"
    short_term_ttl: int = 3600  # 1 hour
    short_term_max: int = 100
    long_term_min_importance: float = 0.3


class AgentConfig(BaseModel):
    """Agent configuration."""
    max_retries: int = 3
    quality_threshold: float = 7.0
    enable_self_reflection: bool = True
    parallel_execution: bool = False


class ToolConfig(BaseModel):
    """Tool configuration."""
    enable_web_search: bool = True
    enable_file_ops: bool = True
    enable_code_execution: bool = False  # Disabled by default for safety
    enable_shell_execution: bool = False
    allowed_file_paths: list[str] = Field(default_factory=lambda: ["./workspace"])
    code_execution_timeout: int = 30


class ObservabilityConfig(BaseModel):
    """Observability configuration."""
    enable_logging: bool = True
    log_level: str = "INFO"
    log_file: Optional[Path] = Field(default=Path("logs/atlas.log"))
    enable_tracing: bool = True
    enable_metrics: bool = True
    metrics_port: int = 9090


class APIConfig(BaseModel):
    """API configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    api_key: Optional[str] = None


class AtlasConfig(BaseSettings):
    """
    Main ATLAS configuration.
    
    Loads from environment variables and .env file.
    """
    # General
    environment: str = Field(default="development", env="ATLAS_ENV")
    debug: bool = Field(default=False, env="ATLAS_DEBUG")
    
    # LLM
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    # Memory
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    
    # Agents
    agent: AgentConfig = Field(default_factory=AgentConfig)
    
    # Tools
    tool: ToolConfig = Field(default_factory=ToolConfig)
    
    # Observability
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    
    # API
    api: APIConfig = Field(default_factory=APIConfig)
    
    # API Keys (loaded from environment)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


def load_config(config_path: Optional[Path] = None) -> AtlasConfig:
    """
    Load ATLAS configuration.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Loaded configuration
    """
    if config_path and config_path.exists():
        # Load from file
        import json
        with open(config_path) as f:
            config_data = json.load(f)
        return AtlasConfig(**config_data)
    
    # Load from environment
    return AtlasConfig()


def save_config(config: AtlasConfig, config_path: Path):
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save
        config_path: Path to save to
    """
    import json
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config.model_dump(), f, indent=2, default=str)


# Global config instance
_config: Optional[AtlasConfig] = None


def get_config() -> AtlasConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
