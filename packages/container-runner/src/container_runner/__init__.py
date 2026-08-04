"""Validated isolated execution plans; no Docker side effects."""

from container_runner.contract import ExecutionPlan
from container_runner.executor import (
    ContainerExecutor,
    ExecutorError,
    ExecutorResult,
    is_immutable_image_reference,
)

__all__ = [
    "ExecutionPlan",
    "ContainerExecutor",
    "ExecutorError",
    "ExecutorResult",
    "is_immutable_image_reference",
]
