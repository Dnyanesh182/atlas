"""
Observability: Logging, tracing, and metrics for ATLAS.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import json
from uuid import UUID

from atlas.core.schemas import ExecutionTrace, SystemMetrics


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, "task_id"):
            log_data["task_id"] = str(record.task_id)
        if hasattr(record, "agent_type"):
            log_data["agent_type"] = record.agent_type
        
        return json.dumps(log_data)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = True
) -> logging.Logger:
    """
    Setup logging for ATLAS.
    
    Args:
        log_level: Logging level
        log_file: Optional log file path
        json_format: Use JSON formatting
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger("atlas")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
        
        logger.addHandler(file_handler)
    
    return logger


class TraceCollector:
    """
    Collect execution traces for observability.
    
    Features:
    - Trace collection
    - Trace storage
    - Trace querying
    - Performance analysis
    """
    
    def __init__(self, persist_dir: Optional[Path] = None):
        self.persist_dir = persist_dir or Path("data/traces")
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.traces: list[ExecutionTrace] = []
    
    def add_trace(self, trace: ExecutionTrace):
        """Add an execution trace."""
        self.traces.append(trace)
        
        # Persist to disk
        if self.persist_dir:
            self._persist_trace(trace)
    
    def _persist_trace(self, trace: ExecutionTrace):
        """Persist trace to disk."""
        # Organize by date
        date_dir = self.persist_dir / trace.timestamp.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Write trace
        trace_file = date_dir / f"{trace.id}.json"
        with open(trace_file, 'w') as f:
            json.dump(trace.dict(), f, indent=2, default=str)
    
    def get_traces_for_task(self, task_id: UUID) -> list[ExecutionTrace]:
        """Get all traces for a task."""
        return [t for t in self.traces if t.task_id == task_id]
    
    def get_traces_by_agent(self, agent_type: str) -> list[ExecutionTrace]:
        """Get traces by agent type."""
        return [t for t in self.traces if t.agent_type.value == agent_type]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.traces:
            return {}
        
        total_duration = sum(t.duration for t in self.traces)
        total_cost = sum(t.cost for t in self.traces)
        total_tokens = sum(t.tokens for t in self.traces)
        
        return {
            "total_traces": len(self.traces),
            "total_duration": total_duration,
            "average_duration": total_duration / len(self.traces),
            "total_cost": total_cost,
            "average_cost": total_cost / len(self.traces),
            "total_tokens": total_tokens,
            "errors": len([t for t in self.traces if t.error])
        }


class MetricsCollector:
    """
    Collect system metrics.
    
    Features:
    - Real-time metrics
    - Aggregation
    - Historical data
    """
    
    def __init__(self):
        self.metrics: list[SystemMetrics] = []
        self.start_time = datetime.utcnow()
    
    def record_metrics(self, metrics: SystemMetrics):
        """Record system metrics."""
        self.metrics.append(metrics)
    
    def get_current_metrics(self) -> SystemMetrics:
        """Get most recent metrics."""
        if self.metrics:
            return self.metrics[-1]
        return SystemMetrics()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        if not self.metrics:
            return {}
        
        latest = self.metrics[-1]
        
        return {
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "total_tasks": latest.total_tasks,
            "completed_tasks": latest.completed_tasks,
            "failed_tasks": latest.failed_tasks,
            "success_rate": latest.completed_tasks / max(latest.total_tasks, 1),
            "active_agents": latest.active_agents,
            "total_cost": latest.total_cost,
            "total_tokens": latest.total_tokens,
            "average_task_time": latest.average_task_time
        }


class ObservabilityManager:
    """
    Unified observability manager.
    
    Coordinates:
    - Logging
    - Tracing
    - Metrics
    """
    
    def __init__(
        self,
        log_level: str = "INFO",
        log_file: Optional[Path] = None,
        trace_dir: Optional[Path] = None
    ):
        self.logger = setup_logging(log_level, log_file)
        self.trace_collector = TraceCollector(trace_dir)
        self.metrics_collector = MetricsCollector()
    
    def log(self, level: str, message: str, **kwargs):
        """Log a message with extra context."""
        log_func = getattr(self.logger, level.lower())
        log_func(message, extra=kwargs)
    
    def trace(self, trace: ExecutionTrace):
        """Record an execution trace."""
        self.trace_collector.add_trace(trace)
    
    def metrics(self, metrics: SystemMetrics):
        """Record system metrics."""
        self.metrics_collector.record_metrics(metrics)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get full observability summary."""
        return {
            "traces": self.trace_collector.get_performance_stats(),
            "metrics": self.metrics_collector.get_metrics_summary()
        }
