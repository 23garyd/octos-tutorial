#!/usr/bin/env python3
"""Octos agent node — mixed dora + ROS2 transport.

Uses TransportRouter to route tool calls to either dora or an external
ROS2 bridge based on tool_transport.yaml config.

Env vars:
  OCTOS_PIPELINE:      Path to .dot pipeline file
  USER_COMMAND:        Command description
  TRANSPORT_CONFIG:    Path to tool_transport.yaml
  ROS2_BRIDGE_SOCKET:  Unix socket path for ROS2 bridge
"""

import json
import os
import sys
import time
import subprocess

from dora import Node

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from octos_py.agent import Agent, AgentConfig
from octos_py.provider import MockProvider
from octos_py.pipeline import Pipeline
from octos_py.transport import DoraTransport, Ros2Transport, TransportRouter


def main():
    pipeline_path = os.environ.get("OCTOS_PIPELINE", "patrol_mixed.dot")
    user_command = os.environ.get("USER_COMMAND", "Execute mixed patrol")
    config_path = os.environ.get("TRANSPORT_CONFIG", "tool_transport.yaml")
    ros2_socket = os.environ.get("ROS2_BRIDGE_SOCKET", "/tmp/octos_ros2_bridge.sock")

    print("=" * 50)
    print("  Octos Agent — Mixed Transport (Dora + ROS2)")
    print("  Pipeline: {}".format(pipeline_path))
    print("  Transport config: {}".format(config_path))
    print("  ROS2 bridge: {}".format(ros2_socket))
    print("=" * 50)

    node = Node()

    transports = {
        "dora": DoraTransport(node),
        "ros2": Ros2Transport(socket_path=ros2_socket),
    }

    router = TransportRouter(config_path, transports)
    registry = router.registry

    print("\nTools registered: {}".format(registry.names()))

    pipeline = Pipeline.from_dot_file(pipeline_path)
    print("Pipeline: {} ({} steps)".format(pipeline.name, len(pipeline.nodes)))

    config = AgentConfig(max_iterations=50, max_timeout_secs=300.0, temperature=0.1)
    agent = Agent(
        provider=MockProvider(),
        registry=registry,
        config=config,
        pipeline=pipeline,
    )

    def tool_executor(tool_name, args):
        tool = registry.get(tool_name)
        if tool is None:
            return json.dumps({"error": "Unknown tool: {}".format(tool_name)})
        return tool.execute(args).output

    print("\nExecuting: {}\n".format(user_command))
    response = agent.process_message(user_command, tool_executor)
    print("\n" + "=" * 50)
    print("  Complete!")
    print("=" * 50)

    time.sleep(1)
    subprocess.Popen(["dora", "stop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
