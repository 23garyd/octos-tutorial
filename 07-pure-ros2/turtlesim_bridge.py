#!/usr/bin/env python3
"""Turtlesim ROS2 bridge — translates JSON requests into real rclpy calls.

Extends Ros2Handler from octos_py.ros2_bridge with actual turtlesim
service clients and topic pub/sub.

Usage:
    python turtlesim_bridge.py --socket /tmp/octos_ros2_bridge.sock

Requires: ROS2 Humble, turtlesim package, rclpy.
"""

import argparse
import os
import sys
import threading

import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn, Kill, TeleportAbsolute, TeleportRelative, SetPen
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from octos_py.ros2_bridge import Ros2Handler, BridgeServer


SERVICE_TYPES = {
    "/spawn": Spawn,
    "/kill": Kill,
    "/turtle1/teleport_absolute": TeleportAbsolute,
    "/turtle1/teleport_relative": TeleportRelative,
    "/turtle1/set_pen": SetPen,
}


class TurtlesimHandler(Ros2Handler):
    """ROS2 bridge handler for turtlesim with real rclpy service calls."""

    def __init__(self, node):
        self._node = node
        self._pose = None
        self._clients = {}
        self._pose_sub = node.create_subscription(
            Pose, "/turtle1/pose", self._pose_cb, 10
        )
        self._cmd_vel_pub = node.create_publisher(Twist, "/turtle1/cmd_vel", 10)

    def _pose_cb(self, msg):
        self._pose = {
            "x": msg.x,
            "y": msg.y,
            "theta": msg.theta,
            "linear_velocity": msg.linear_velocity,
            "angular_velocity": msg.angular_velocity,
        }

    def _get_client(self, endpoint, service_type):
        if endpoint not in self._clients:
            client = self._node.create_client(service_type, endpoint)
            client.wait_for_service(timeout_sec=5.0)
            self._clients[endpoint] = client
        return self._clients[endpoint]

    def _call_service(self, client, request, timeout=10.0):
        """Thread-safe synchronous service call (runs on BridgeServer thread)."""
        event = threading.Event()
        result = [None]
        error = [None]

        def done_cb(future):
            try:
                result[0] = future.result()
            except Exception as e:
                error[0] = str(e)
            event.set()

        future = client.call_async(request)
        future.add_done_callback(done_cb)
        if not event.wait(timeout):
            return {"error": "service call timed out"}
        if error[0]:
            return {"error": error[0]}
        return result[0]

    def handle_service(self, endpoint, args):
        if endpoint == "/turtle1/get_pose":
            if self._pose is None:
                return {"error": "no pose received yet"}
            return dict(self._pose)

        service_type = SERVICE_TYPES.get(endpoint)
        if service_type is None:
            return {"error": "unknown service: {}".format(endpoint)}

        client = self._get_client(endpoint, service_type)
        req = service_type.Request()

        if endpoint == "/spawn":
            req.x = float(args.get("x", 5.0))
            req.y = float(args.get("y", 5.0))
            req.theta = float(args.get("theta", 0.0))
            if "name" in args:
                req.name = args["name"]
            resp = self._call_service(client, req)
            if isinstance(resp, dict):
                return resp
            return {"name": resp.name}

        if endpoint == "/kill":
            req.name = args.get("name", "turtle1")
            self._call_service(client, req)
            return {"status": "ok"}

        if endpoint == "/turtle1/teleport_absolute":
            req.x = float(args.get("x", 0.0))
            req.y = float(args.get("y", 0.0))
            req.theta = float(args.get("theta", 0.0))
            self._call_service(client, req)
            return {"status": "ok", "x": req.x, "y": req.y, "theta": req.theta}

        if endpoint == "/turtle1/teleport_relative":
            req.linear = float(args.get("linear", 0.0))
            req.angular = float(args.get("angular", 0.0))
            self._call_service(client, req)
            return {"status": "ok"}

        if endpoint == "/turtle1/set_pen":
            req.r = int(args.get("r", 255))
            req.g = int(args.get("g", 255))
            req.b = int(args.get("b", 255))
            req.width = int(args.get("width", 1))
            req.off = int(args.get("off", 0))
            self._call_service(client, req)
            return {"status": "ok"}

        return {"error": "unhandled service: {}".format(endpoint)}

    def handle_action(self, endpoint, args):
        return self.handle_service(endpoint, args)

    def handle_publish(self, endpoint, args):
        if endpoint == "/turtle1/cmd_vel":
            msg = Twist()
            msg.linear.x = float(args.get("linear_x", 0.0))
            msg.angular.z = float(args.get("angular_z", 0.0))
            self._cmd_vel_pub.publish(msg)


def main():
    parser = argparse.ArgumentParser(description="Turtlesim ROS2 Bridge")
    parser.add_argument("--socket", default="/tmp/octos_ros2_bridge.sock")
    parser.add_argument("--node-name", default="octos_turtlesim_bridge")
    args = parser.parse_args()

    rclpy.init()
    node = Node(args.node_name)

    def _spin_quiet(n):
        try:
            rclpy.spin(n)
        except Exception:
            pass

    spin_thread = threading.Thread(target=_spin_quiet, args=(node,), daemon=True)
    spin_thread.start()

    handler = TurtlesimHandler(node)
    print("[turtlesim-bridge] Listening on {}".format(args.socket))

    server = BridgeServer(args.socket, handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[turtlesim-bridge] Shutting down")
        server.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
