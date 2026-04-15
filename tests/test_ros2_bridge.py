"""Tests for ROS2 bridge process."""
import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import socket
import threading
import time
import pytest

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


def test_bridge_protocol_service(tmp_path):
    sock_path = str(tmp_path / "bridge.sock")
    handler = MockRos2Handler()
    server = BridgeServer(sock_path, handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
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
    server.shutdown()


def test_bridge_protocol_action(tmp_path):
    sock_path = str(tmp_path / "bridge.sock")
    handler = MockRos2Handler()
    server = BridgeServer(sock_path, handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
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
    server.shutdown()
