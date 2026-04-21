"""Tests for Ros2Transport and Ros2ActionHandle."""

import sys
import os
import importlib
import json
import socket
import threading
import uuid
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def _short_sock() -> str:
    """Unique /tmp path short enough for macOS sun_path (104 bytes)."""
    return f"/tmp/octos-{uuid.uuid4().hex[:8]}.sock"

# Import transport module directly to avoid __init__.py pulling in deps
# that require Python 3.10+ union syntax on older interpreters.
_base = os.path.join(os.path.dirname(__file__), "..", "octos_py")

# Pre-register tools module so transport.py's relative import resolves
_tools_spec = importlib.util.spec_from_file_location("octos_py.tools", os.path.join(_base, "tools.py"))
_tools_mod = importlib.util.module_from_spec(_tools_spec)
sys.modules.setdefault("octos_py.tools", _tools_mod)
_tools_spec.loader.exec_module(_tools_mod)

_spec = importlib.util.spec_from_file_location(
    "octos_py.transport",
    os.path.join(_base, "transport.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
Ros2Transport = _mod.Ros2Transport


def _start_mock_server(sock_path, responses):
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(5)
    server.settimeout(5.0)

    def serve():
        while True:
            try:
                conn, _ = server.accept()
            except (socket.timeout, OSError):
                break
            try:
                # Read until the client shuts down write-side (matches the
                # real BridgeServer protocol). Without this loop the server
                # can race the client's shutdown(SHUT_WR) and close the
                # socket before the client finishes, producing ENOTCONN.
                chunks = []
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                data = b"".join(chunks)
                if not data:
                    continue
                req = json.loads(data.decode())
                req_id = req.get("id", "")
                if req_id in responses:
                    resp = responses[req_id]
                else:
                    resp = {"id": req_id, "status": "success", "result": req}
                conn.sendall(json.dumps(resp).encode())
                conn.shutdown(socket.SHUT_WR)
            finally:
                conn.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return server


@pytest.fixture
def mock_server():
    sock_path = _short_sock()
    responses = {}  # empty = echo back
    server = _start_mock_server(sock_path, responses)
    try:
        yield sock_path
    finally:
        server.close()
        try:
            Path(sock_path).unlink()
        except FileNotFoundError:
            pass


def test_ros2_transport_request(mock_server):
    transport = Ros2Transport(socket_path=mock_server)
    result = transport.request("navigate_to", {"x": 5.0}, timeout=5.0)
    assert result["status"] == "success"


def test_ros2_transport_publish(mock_server):
    transport = Ros2Transport(socket_path=mock_server)
    transport.publish("/cmd_vel", {"linear_x": 1.0})  # should not raise


def test_ros2_transport_connection_error():
    transport = Ros2Transport(socket_path="/tmp/nonexistent_socket_test.sock")
    with pytest.raises(ConnectionError):
        transport.request("test", {})
