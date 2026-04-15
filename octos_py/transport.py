"""
Transport abstraction — supports dora, ROS2, or mixed deployments.

Transport: abstract base with request, publish, subscribe, action.
ActionHandle: abstract base with wait, cancel, feedback for long-running actions.
"""

from abc import ABC, abstractmethod
from typing import Callable, Iterator
import json
import time


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


class DoraActionHandle(ActionHandle):
    """ActionHandle that wraps a blocking request (dora has no native actions)."""

    def __init__(self, result: dict):
        self._result = result

    def wait(self, timeout: float = 30.0) -> dict:
        return self._result

    def cancel(self) -> None:
        pass

    def feedback(self) -> Iterator[dict]:
        return iter([])


class DoraTransport(Transport):
    """Transport backed by a dora Node -- wraps send_output/next pattern."""

    def __init__(self, node):
        self._node = node

    @staticmethod
    def _to_pa_uint8(raw: bytes):
        import pyarrow as pa
        return pa.array(list(raw), type=pa.uint8())

    def request(self, tool_name: str, args: dict, timeout: float = 30.0) -> dict:
        request_data = {"tool": tool_name, "args": args}
        raw = json.dumps(request_data).encode("utf-8")
        self._node.send_output("skill_request", self._to_pa_uint8(raw))
        deadline = time.time() + timeout
        while time.time() < deadline:
            event = self._node.next(timeout=1.0)
            if event is None:
                continue
            if event["type"] == "INPUT" and event["id"] == "skill_result":
                raw_resp = bytes(event["value"].to_pylist())
                return json.loads(raw_resp.decode("utf-8"))
        return {"error": "timeout"}

    def publish(self, channel: str, data: dict) -> None:
        raw = json.dumps(data).encode("utf-8")
        self._node.send_output(channel, self._to_pa_uint8(raw))

    def subscribe(self, channel: str, callback: Callable[[dict], None]) -> None:
        raise NotImplementedError(
            "DoraTransport.subscribe() not supported -- "
            "dora subscriptions are handled via the dataflow event loop"
        )

    def action(self, tool_name: str, args: dict) -> ActionHandle:
        result = self.request(tool_name, args)
        return DoraActionHandle(result)
