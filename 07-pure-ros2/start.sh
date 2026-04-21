#!/usr/bin/env bash
# start.sh — Launch the pure ROS2 turtlesim example (no dora).
#
# Usage:
#   ./start.sh          # Start turtlesim + bridge + agent
#   ./start.sh stop     # Kill background processes
#
# Prerequisites:
#   - ROS2 Humble (source /opt/ros/humble/setup.bash)
#   - turtlesim (sudo apt install ros-humble-turtlesim)
#   - pip install pyyaml

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOCKET="/tmp/octos_ros2_bridge.sock"

# Source ROS2
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
else
    echo "ERROR: /opt/ros/humble/setup.bash not found. Install ROS2 Humble."
    exit 1
fi

# Handle stop
if [ "${1:-}" = "stop" ]; then
    echo "Stopping processes..."
    pkill -f "turtlesim_node" 2>/dev/null || true
    pkill -f "turtlesim_bridge.py" 2>/dev/null || true
    rm -f "$SOCKET"
    echo "Done."
    exit 0
fi

# Clean up on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill "$TURTLESIM_PID" 2>/dev/null || true
    kill "$BRIDGE_PID" 2>/dev/null || true
    rm -f "$SOCKET"
}
trap cleanup EXIT INT TERM

cd "$SCRIPT_DIR"

echo "============================================"
echo "  07 — Pure ROS2 Turtlesim Patrol"
echo "  No dora. No dataflow.yaml."
echo "============================================"
echo ""

# 1. Start turtlesim
echo "[1/3] Starting turtlesim_node..."
ros2 run turtlesim turtlesim_node &
TURTLESIM_PID=$!
sleep 2

# 2. Start bridge
echo "[2/3] Starting turtlesim bridge..."
PYTHONPATH="$SCRIPT_DIR/..:$PYTHONPATH" python3 "$SCRIPT_DIR/turtlesim_bridge.py" \
    --socket "$SOCKET" &
BRIDGE_PID=$!
sleep 1

# 3. Run agent (foreground)
echo "[3/3] Running agent..."
echo ""
PYTHONPATH="$SCRIPT_DIR/..:$PYTHONPATH" python3 "$SCRIPT_DIR/agent_node.py"

echo ""
echo "Agent finished. Turtlesim window stays open for inspection."
echo "Press Ctrl+C to close everything."
wait
