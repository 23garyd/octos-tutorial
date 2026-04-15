"""
Transport abstraction — supports dora, ROS2, or mixed deployments.

Transport: abstract base with request, publish, subscribe, action.
ActionHandle: abstract base with wait, cancel, feedback for long-running actions.
"""

from abc import ABC, abstractmethod
from typing import Callable, Iterator
import json
import socket as _socket
import time
import uuid


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


# ---------------------------------------------------------------------------
# ROS2 bridge transport (Unix socket + JSON, one-shot pattern)
# ---------------------------------------------------------------------------

def _send_socket_request(sock_path: str, request: dict, timeout: float = 30.0) -> dict:
    """Send a JSON request over a Unix socket and return the JSON response."""
    try:
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(sock_path)
    except (FileNotFoundError, ConnectionRefusedError, OSError) as e:
        raise ConnectionError(
            "Cannot connect to ROS2 bridge at {}: {}".format(sock_path, e)
        )
    try:
        sock.sendall(json.dumps(request).encode("utf-8"))
        sock.shutdown(_socket.SHUT_WR)  # signal end of request
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
        return json.loads(b"".join(chunks).decode("utf-8"))
    finally:
        sock.close()


class Ros2ActionHandle(ActionHandle):
    """ActionHandle backed by a ROS2 bridge action call over Unix socket."""

    def __init__(self, sock_path, request_id, endpoint, args):
        self._sock_path = sock_path
        self._request_id = request_id
        self._endpoint = endpoint
        self._args = args
        self._result = None

    def wait(self, timeout: float = 30.0) -> dict:
        if self._result is not None:
            return self._result
        resp = _send_socket_request(
            self._sock_path,
            {
                "id": self._request_id,
                "pattern": "action",
                "endpoint": self._endpoint,
                "args": self._args,
            },
            timeout=timeout,
        )
        self._result = resp
        return resp

    def cancel(self) -> None:
        _send_socket_request(
            self._sock_path,
            {"id": self._request_id, "pattern": "cancel"},
            timeout=5.0,
        )

    def feedback(self) -> Iterator[dict]:
        return iter([])


class Ros2Transport(Transport):
    """Transport backed by an external ROS2 bridge process via Unix socket."""

    def __init__(self, socket_path: str):
        self._socket_path = socket_path

    def request(self, tool_name: str, args: dict, timeout: float = 30.0) -> dict:
        request_id = "req-{}".format(uuid.uuid4().hex[:8])
        return _send_socket_request(
            self._socket_path,
            {
                "id": request_id,
                "pattern": "service",
                "endpoint": tool_name,
                "args": args,
            },
            timeout=timeout,
        )

    def publish(self, channel: str, data: dict) -> None:
        request_id = "pub-{}".format(uuid.uuid4().hex[:8])
        try:
            _send_socket_request(
                self._socket_path,
                {
                    "id": request_id,
                    "pattern": "publish",
                    "endpoint": channel,
                    "args": data,
                },
                timeout=5.0,
            )
        except ConnectionError:
            pass  # fire-and-forget

    def subscribe(self, channel: str, callback: Callable[[dict], None]) -> None:
        raise NotImplementedError(
            "Ros2Transport.subscribe() requires a persistent connection. "
            "Use the ROS2 bridge's push mechanism instead."
        )

    def action(self, tool_name: str, args: dict) -> ActionHandle:
        request_id = "act-{}".format(uuid.uuid4().hex[:8])
        return Ros2ActionHandle(
            self._socket_path, request_id, tool_name, args
        )
