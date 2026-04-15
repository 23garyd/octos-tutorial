"""Tests for Transport ABC and ActionHandle ABC."""

import sys
import os
import importlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

# Import transport module directly to avoid __init__.py pulling in deps
# that require Python 3.10+ union syntax on older interpreters.
_spec = importlib.util.spec_from_file_location(
    "octos_py.transport",
    os.path.join(os.path.dirname(__file__), "..", "octos_py", "transport.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
Transport = _mod.Transport
ActionHandle = _mod.ActionHandle
DoraTransport = _mod.DoraTransport
DoraActionHandle = _mod.DoraActionHandle


def test_transport_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Transport()


def test_action_handle_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ActionHandle()


def test_transport_subclass_must_implement_all_methods():
    class Incomplete(Transport):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_transport_subclass_works_when_complete():
    class Complete(Transport):
        def request(self, tool_name, args, timeout=30.0):
            return {"ok": True}

        def publish(self, channel, data):
            pass

        def subscribe(self, channel, callback):
            pass

        def action(self, tool_name, args):
            return None

    t = Complete()
    assert t.request("test", {}) == {"ok": True}


# --- DoraTransport / DoraActionHandle tests ---

from unittest.mock import MagicMock
import json


def _make_mock_node(response_data=None):
    """Create a mock dora Node that returns one skill_result event."""
    node = MagicMock()
    if response_data is not None:
        raw = json.dumps(response_data).encode("utf-8")
        mock_value = MagicMock()
        mock_value.to_pylist.return_value = list(raw)
        node.next.return_value = {
            "type": "INPUT",
            "id": "skill_result",
            "value": mock_value,
        }
    else:
        node.next.return_value = None
    return node


def test_dora_transport_request():
    response = ["Arrived at A", {"position": "A"}]
    node = _make_mock_node(response)
    transport = DoraTransport(node)
    result = transport.request("navigate_to", {"waypoint": "A"})
    assert result == response
    node.send_output.assert_called_once()


def test_dora_transport_request_timeout():
    node = _make_mock_node(None)
    transport = DoraTransport(node)
    result = transport.request("navigate_to", {"waypoint": "A"}, timeout=0.5)
    assert result == {"error": "timeout"}


def test_dora_transport_publish():
    node = MagicMock()
    transport = DoraTransport(node)
    transport.publish("my_output", {"speed": 1.0})
    node.send_output.assert_called_once()


def test_dora_transport_action_falls_back_to_request():
    response = ["Done", {"ok": True}]
    node = _make_mock_node(response)
    transport = DoraTransport(node)
    handle = transport.action("navigate_to", {"waypoint": "A"})
    result = handle.wait()
    assert result == response
