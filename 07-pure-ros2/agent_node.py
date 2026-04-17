#!/usr/bin/env python3
"""Octos agent — pure ROS2, no dora dependency.

Demonstrates that octos_py works standalone with only Ros2Transport.
All tools route through the ROS2 bridge to turtlesim.

Env vars:
  OCTOS_PIPELINE:      Path to .dot pipeline (default: turtlesim_patrol.dot)
  USER_COMMAND:         Command description
  TRANSPORT_CONFIG:     Path to tool_transport.yaml
  ROS2_BRIDGE_SOCKET:   Unix socket for bridge
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from octos_py.agent import Agent, AgentConfig
from octos_py.provider import MockProvider
from octos_py.pipeline import Pipeline
from octos_py.transport import Ros2Transport, TransportRouter


def main():
    pipeline_path = os.environ.get("OCTOS_PIPELINE", "turtlesim_patrol.dot")
    user_command = os.environ.get(
        "USER_COMMAND",
        "Patrol turtlesim waypoints A, B, C, D in a square, then return home",
    )
    config_path = os.environ.get("TRANSPORT_CONFIG", "tool_transport.yaml")
    ros2_socket = os.environ.get("ROS2_BRIDGE_SOCKET", "/tmp/octos_ros2_bridge.sock")

    print("=" * 55)
    print("  Octos Agent — Pure ROS2 (No Dora)")
    print("  Pipeline: {}".format(pipeline_path))
    print("  Transport: {}".format(config_path))
    print("  Bridge:    {}".format(ros2_socket))
    print("=" * 55)

    transports = {
        "ros2": Ros2Transport(socket_path=ros2_socket),
    }

    router = TransportRouter(config_path, transports)
    registry = router.registry

    print("\nTools: {}".format(registry.names()))

    pipeline = Pipeline.from_dot_file(pipeline_path)
    print("Pipeline: {} ({} steps)".format(pipeline.name, len(pipeline.nodes)))

    config = AgentConfig(max_iterations=12, max_timeout_secs=120.0, temperature=0.1)
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
    print("\n" + "=" * 55)
    print("  Complete!")
    print("=" * 55)


if __name__ == "__main__":
    main()
