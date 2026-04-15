"""
ROS2 Bridge Process — standalone Unix socket server translating JSON to ROS2.

Only file that imports rclpy. Run as separate process:
    python -m octos_py.ros2_bridge --socket /tmp/octos_ros2_bridge.sock
    python -m octos_py.ros2_bridge --mock --socket /tmp/octos_ros2_bridge.sock
"""

import argparse
import json
import os
import socket
import threading
from abc import ABC, abstractmethod


class Ros2Handler(ABC):
    @abstractmethod
    def handle_service(self, endpoint, args):
        ...
    @abstractmethod
    def handle_action(self, endpoint, args):
        ...
    @abstractmethod
    def handle_publish(self, endpoint, args):
        ...


class MockRos2Handler(Ros2Handler):
    """Mock handler for testing without rclpy."""
    def handle_service(self, endpoint, args):
        return {"endpoint": endpoint, "args": args, "mock": True}
    def handle_action(self, endpoint, args):
        return {"endpoint": endpoint, "args": args, "mock": True}
    def handle_publish(self, endpoint, args):
        pass


class BridgeServer:
    def __init__(self, socket_path, handler):
        self._socket_path = socket_path
        self._handler = handler
        self._running = False
        self._server = None

    def serve_forever(self):
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self._socket_path)
        self._server.listen(5)
        self._server.settimeout(1.0)
        self._running = True
        while self._running:
            try:
                conn, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                data = conn.recv(65536)
                if not data:
                    conn.close()
                    continue
                request = json.loads(data.decode().strip())
                req_id = request.get("id", "")
                pattern = request.get("pattern", "service")
                endpoint = request.get("endpoint", "")
                args = request.get("args", {})
                if pattern in ("service", "request"):
                    result = self._handler.handle_service(endpoint, args)
                    response = {"id": req_id, "status": "success", "result": result}
                elif pattern == "action":
                    result = self._handler.handle_action(endpoint, args)
                    response = {"id": req_id, "status": "success", "result": result}
                elif pattern == "publish":
                    self._handler.handle_publish(endpoint, args)
                    response = {"id": req_id, "status": "success", "result": {}}
                elif pattern == "cancel":
                    response = {"id": req_id, "status": "cancelled"}
                else:
                    response = {"id": req_id, "status": "error", "error": "Unknown pattern: {}".format(pattern)}
                conn.sendall(json.dumps(response).encode())
            except Exception as e:
                err_resp = {"id": request.get("id", ""), "status": "error", "error": str(e)}
                conn.sendall(json.dumps(err_resp).encode())
            finally:
                conn.close()

    def shutdown(self):
        self._running = False
        if self._server:
            self._server.close()
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass


def _create_rclpy_handler(node_name="octos_ros2_bridge"):
    import rclpy
    from rclpy.node import Node
    rclpy.init()
    node = Node(node_name)
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    class RclpyHandler(Ros2Handler):
        def __init__(self, ros_node):
            self._node = ros_node
        def handle_service(self, endpoint, args):
            self._node.get_logger().info("Service call: {}({})".format(endpoint, args))
            return {"endpoint": endpoint, "args": args, "note": "extend RclpyHandler for your services"}
        def handle_action(self, endpoint, args):
            self._node.get_logger().info("Action goal: {}({})".format(endpoint, args))
            return {"endpoint": endpoint, "args": args, "note": "extend RclpyHandler for your actions"}
        def handle_publish(self, endpoint, args):
            self._node.get_logger().info("Publish: {}({})".format(endpoint, args))

    return RclpyHandler(node)


def main():
    parser = argparse.ArgumentParser(description="Octos ROS2 Bridge")
    parser.add_argument("--socket", default="/tmp/octos_ros2_bridge.sock")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--node-name", default="octos_ros2_bridge")
    args = parser.parse_args()
    if args.mock:
        handler = MockRos2Handler()
        print("[ros2-bridge] Starting with MOCK handler on {}".format(args.socket))
    else:
        handler = _create_rclpy_handler(args.node_name)
        print("[ros2-bridge] Starting with rclpy handler on {}".format(args.socket))
    server = BridgeServer(args.socket, handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[ros2-bridge] Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
