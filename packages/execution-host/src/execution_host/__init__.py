"""Portable execution-host contract public API."""
from execution_host.contracts import *  # noqa: F403
from execution_host.adapter import ExecutionHostAdapter, SyntheticTestAdapter, assert_production_eligible
from execution_host.runtime import (
    AgentBackend,
    BackendEvent,
    BackendHealth,
    BackendOperationResult,
    PROVIDER_OPERATION_FIELDS,
    provider_operation_matrix,
)


def __getattr__(name: str):
    """Load the optional OpenCode backend without creating an adapter cycle."""

    if name == "OpenCodeContainerBackend":
        from execution_host.opencode_backend import OpenCodeContainerBackend

        return OpenCodeContainerBackend
    raise AttributeError(name)
