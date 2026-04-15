"""
Transport abstraction — supports dora, ROS2, or mixed deployments.

Transport: abstract base with request, publish, subscribe, action.
ActionHandle: abstract base with wait, cancel, feedback for long-running actions.
"""

from abc import ABC, abstractmethod
from typing import Callable, Iterator


class ActionHandle(ABC):
    """Abstract handle for a long-running action."""

    @abstractmethod
    def wait(self, timeout: float = 30.0) -> dict:
        ...

    @abstractmethod
    def cancel(self) -> None:
        ...

    @abstractmethod
    def feedback(self) -> Iterator[dict]:
        ...


class Transport(ABC):
    """Abstract transport — mirrors octos_agent::transport::Transport trait."""

    @abstractmethod
    def request(self, tool_name: str, args: dict, timeout: float = 30.0) -> dict:
        """Send a request and wait for a response (tool calls, ROS2 services)."""
        ...

    @abstractmethod
    def publish(self, channel: str, data: dict) -> None:
        """Publish data to a channel (fire-and-forget)."""
        ...

    @abstractmethod
    def subscribe(self, channel: str, callback: Callable[[dict], None]) -> None:
        """Subscribe to a channel with a callback."""
        ...

    @abstractmethod
    def action(self, tool_name: str, args: dict) -> ActionHandle:
        """Start a long-running action and return a handle."""
        ...
