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
