"""Tests for ROS2 bridge process."""
import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import socket
import threading
import time
import uuid
from pathlib import Path

import pytest


def _short_sock() -> str:
    """Unique /tmp path short enough for macOS sun_path (104 bytes)."""
    return f"/tmp/octos-{uuid.uuid4().hex[:8]}.sock"


def _unlink(path: str) -> None:
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass

# Import ros2_bridge directly to avoid __init__.py pulling in deps
# that require Python 3.10+ union syntax on older interpreters.
_base = os.path.join(os.path.dirname(__file__), "..", "octos_py")
_spec = importlib.util.spec_from_file_location(
    "octos_py.ros2_bridge",
    os.path.join(_base, "ros2_bridge.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
MockRos2Handler = _mod.MockRos2Handler
BridgeServer = _mod.BridgeServer


def test_bridge_protocol_service():
    sock_path = _short_sock()
    handler = MockRos2Handler()
    server = BridgeServer(sock_path, handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        time.sleep(0.3)

        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.connect(sock_path)
        request = {"id": "req-001", "pattern": "service", "endpoint": "/get_state", "args": {}}
        conn.sendall(json.dumps(request).encode())
        conn.shutdown(socket.SHUT_WR)
        data = conn.recv(65536)
        conn.close()

        resp = json.loads(data.decode())
        assert resp["id"] == "req-001"
        assert resp["status"] == "success"
        assert resp["result"]["mock"] is True
    finally:
        server.shutdown()
        _unlink(sock_path)


def test_bridge_protocol_action():
    sock_path = _short_sock()
    handler = MockRos2Handler()
    server = BridgeServer(sock_path, handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        time.sleep(0.3)

        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.connect(sock_path)
        request = {"id": "act-001", "pattern": "action", "endpoint": "/navigate_to_pose", "args": {"x": 5.0}}
        conn.sendall(json.dumps(request).encode())
        conn.shutdown(socket.SHUT_WR)
        data = conn.recv(65536)
        conn.close()

        resp = json.loads(data.decode())
        assert resp["id"] == "act-001"
        assert resp["status"] == "success"
    finally:
        server.shutdown()
        _unlink(sock_path)
