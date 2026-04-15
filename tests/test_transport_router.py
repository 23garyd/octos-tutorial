# tests/test_transport_router.py
import sys, os, importlib, json, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import transport module directly
_base = os.path.join(os.path.dirname(__file__), "..", "octos_py")

_tools_spec = importlib.util.spec_from_file_location("octos_py.tools", os.path.join(_base, "tools.py"))
_tools_mod = importlib.util.module_from_spec(_tools_spec)
sys.modules["octos_py.tools"] = _tools_mod  # register so transport.py's relative import works
_tools_spec.loader.exec_module(_tools_mod)

_spec = importlib.util.spec_from_file_location("octos_py.transport", os.path.join(_base, "transport.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Transport = _mod.Transport
TransportBridgeTool = _mod.TransportBridgeTool
TransportRouter = _mod.TransportRouter
DoraActionHandle = _mod.DoraActionHandle

class FakeTransport(Transport):
    def __init__(self):
        self.last_request = None
    def request(self, tool_name, args, timeout=30.0):
        self.last_request = (tool_name, args)
        return {"status": "ok", "tool": tool_name}
    def publish(self, channel, data):
        pass
    def subscribe(self, channel, callback):
        pass
    def action(self, tool_name, args):
        self.last_request = (tool_name, args)
        return DoraActionHandle({"status": "ok", "tool": tool_name})

def test_transport_bridge_tool_request():
    transport = FakeTransport()
    tool = TransportBridgeTool(
        tool_name="get_map", tool_description="Get station map",
        transport=transport, pattern="request",
    )
    assert tool.name() == "get_map"
    assert tool.description() == "Get station map"
    result = tool.execute({})
    assert "ok" in result.output
    assert transport.last_request == ("get_map", {})

def test_transport_bridge_tool_action():
    transport = FakeTransport()
    tool = TransportBridgeTool(
        tool_name="navigate_to", tool_description="Navigate",
        transport=transport, pattern="action", endpoint="/navigate_to_pose",
    )
    result = tool.execute({"x": 5.0})
    assert transport.last_request == ("/navigate_to_pose", {"x": 5.0})

def test_transport_router_loads_config(tmp_path):
    config_content = """
transports:
  fake:
    type: fake
tools:
  get_map:
    transport: fake
    pattern: request
    description: Get station map
  navigate_to:
    transport: fake
    pattern: action
    endpoint: /navigate_to_pose
    description: Navigate to a pose
"""
    config_path = tmp_path / "tool_transport.yaml"
    config_path.write_text(config_content)
    fake = FakeTransport()
    router = TransportRouter(str(config_path), {"fake": fake})
    assert "get_map" in router.registry.names()
    assert "navigate_to" in router.registry.names()
    tool = router.registry.get("get_map")
    result = tool.execute({})
    assert "ok" in result.output

def test_transport_router_missing_transport(tmp_path):
    config_content = """
transports:
  missing:
    type: missing
tools:
  test_tool:
    transport: missing
    pattern: request
    description: Test tool
"""
    config_path = tmp_path / "tool_transport.yaml"
    config_path.write_text(config_content)
    with pytest.raises(KeyError):
        TransportRouter(str(config_path), {})
