"""End-to-end test: TransportRouter + mock transports + BridgeServer."""
import sys
import os
import importlib
import json
import socket
import threading
import time
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import modules via importlib to avoid __init__.py on Python 3.8
_base = os.path.join(os.path.dirname(__file__), "..", "octos_py")

_tools_spec = importlib.util.spec_from_file_location("octos_py.tools", os.path.join(_base, "tools.py"))
_tools_mod = importlib.util.module_from_spec(_tools_spec)
sys.modules.setdefault("octos_py.tools", _tools_mod)
_tools_spec.loader.exec_module(_tools_mod)

_transport_spec = importlib.util.spec_from_file_location("octos_py.transport", os.path.join(_base, "transport.py"))
_transport_mod = importlib.util.module_from_spec(_transport_spec)
_transport_spec.loader.exec_module(_transport_mod)

DoraTransport = _transport_mod.DoraTransport
Ros2Transport = _transport_mod.Ros2Transport
TransportRouter = _transport_mod.TransportRouter

_bridge_spec = importlib.util.spec_from_file_location("octos_py.ros2_bridge", os.path.join(_base, "ros2_bridge.py"))
_bridge_mod = importlib.util.module_from_spec(_bridge_spec)
_bridge_spec.loader.exec_module(_bridge_mod)

MockRos2Handler = _bridge_mod.MockRos2Handler
BridgeServer = _bridge_mod.BridgeServer


def _short_sock() -> str:
    """Unique /tmp path short enough for macOS sun_path (104 bytes)."""
    import uuid
    return f"/tmp/octos-{uuid.uuid4().hex[:8]}.sock"


@pytest.fixture
def bridge_server():
    """Start a mock ROS2 bridge server."""
    sock_path = _short_sock()
    handler = MockRos2Handler()
    server = BridgeServer(sock_path, handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    try:
        yield sock_path
    finally:
        server.shutdown()
        try:
            os.unlink(sock_path)
        except FileNotFoundError:
            pass


@pytest.fixture
def transport_config(tmp_path, bridge_server):
    """Create a tool_transport.yaml pointing to the mock bridge."""
    config = """
transports:
  dora:
    type: dora
  ros2:
    type: ros2
    socket: {socket}

tools:
  navigate_to:
    transport: ros2
    pattern: action
    endpoint: /navigate_to_pose
    description: Navigate to a pose
  get_map:
    transport: dora
    pattern: request
    description: Get station map
""".format(socket=bridge_server)
    path = tmp_path / "tool_transport.yaml"
    path.write_text(config)
    return str(path)


def _make_mock_dora_node(response_data):
    node = MagicMock()
    raw = json.dumps(response_data).encode("utf-8")
    mock_value = MagicMock()
    mock_value.to_pylist.return_value = list(raw)
    node.next.return_value = {
        "type": "INPUT",
        "id": "skill_result",
        "value": mock_value,
    }
    return node


def test_mixed_transport_routing(transport_config, bridge_server):
    """Verify tools route to correct transports."""
    dora_response = ["Map: stations A, B, home", {"stations": {}}]
    mock_node = _make_mock_dora_node(dora_response)

    transports = {
        "dora": DoraTransport(mock_node),
        "ros2": Ros2Transport(socket_path=bridge_server),
    }
    router = TransportRouter(transport_config, transports)

    # Dora tool
    map_tool = router.registry.get("get_map")
    result = json.loads(map_tool.execute({}).output)
    assert result == dora_response

    # ROS2 tool
    nav_tool = router.registry.get("navigate_to")
    result = json.loads(nav_tool.execute({"x": 5.0}).output)
    assert result["status"] == "success"


def test_all_dora_config(tmp_path):
    """Verify all-dora deployment works."""
    config = """
transports:
  dora:
    type: dora

tools:
  navigate_to:
    transport: dora
    pattern: request
    description: Navigate
  get_map:
    transport: dora
    pattern: request
    description: Map
"""
    path = tmp_path / "all_dora.yaml"
    path.write_text(config)

    dora_response = {"status": "ok"}
    mock_node = _make_mock_dora_node(dora_response)
    transports = {"dora": DoraTransport(mock_node)}
    router = TransportRouter(str(path), transports)

    assert len(router.registry.names()) == 2
    result = json.loads(router.registry.get("navigate_to").execute({}).output)
    assert result == dora_response
