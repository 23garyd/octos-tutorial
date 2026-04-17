# 07 — Pure ROS2 (No Dora)

Demonstrates that octos_py works as a **standalone agent framework with zero dora dependency**. All tool calls route through ROS2 via the Unix socket bridge to control turtlesim.

## What You'll Learn

- Running an octos agent without dora — no `dataflow.yaml`, no `dora up`
- `Ros2Transport` + `TransportRouter` with all-ROS2 tool routing
- Extending `Ros2Handler` for real rclpy service calls (turtlesim)
- Thread-safe service call pattern (`call_async` + `Event`)

## Architecture

```
┌─────────────────────────────────┐
│  agent_node.py (pure Python)    │
│  ├─ Agent + MockProvider        │  No dora imports
│  ├─ Ros2Transport               │  Unix socket client
│  └─ TransportRouter             │  YAML-configured tools
└──────────┬──────────────────────┘
           │ Unix socket (JSON)
           ▼
┌─────────────────────────────────┐
│  turtlesim_bridge.py            │
│  ├─ TurtlesimHandler            │  rclpy service clients
│  ├─ Pose subscriber             │  /turtle1/pose
│  └─ BridgeServer                │  Reused from octos_py
└──────────┬──────────────────────┘
           │ ROS2
           ▼
┌─────────────────────────────────┐
│  turtlesim_node (ROS2)          │
│  Services: teleport, set_pen,   │
│            spawn, kill           │
│  Topics: /turtle1/pose,         │
│          /turtle1/cmd_vel        │
└─────────────────────────────────┘
```

## Quick Start

```bash
# All-in-one (manages 3 processes):
cd 07-pure-ros2
./start.sh

# Or manually in 3 terminals:
# Terminal 1: turtlesim
source /opt/ros/humble/setup.bash
ros2 run turtlesim turtlesim_node

# Terminal 2: bridge
source /opt/ros/humble/setup.bash
PYTHONPATH=".." python3 turtlesim_bridge.py --socket /tmp/octos_ros2_bridge.sock

# Terminal 3: agent
PYTHONPATH=".." python3 agent_node.py
```

## Expected Output

The agent executes a 10-step DOT pipeline:
1. Read current pose
2. Set pen to red → teleport to (2,2)
3. Set pen to green → teleport to (8,2)
4. Set pen to blue → teleport to (8,8)
5. Set pen to white → teleport to (2,8)
6. Return home to (5.5, 5.5)

The turtlesim window shows a **colored square** trail (red, green, blue, white sides).

## Files

| File | Purpose |
|------|---------|
| `agent_node.py` | Octos agent — pure Python, no dora |
| `turtlesim_bridge.py` | ROS2 bridge with real turtlesim service calls |
| `tool_transport.yaml` | Maps all tools to `ros2` transport |
| `turtlesim_patrol.dot` | Square patrol pipeline (10 steps) |
| `start.sh` | Launch script for all 3 processes |

## Dependencies

- **ROS2 Humble** with `turtlesim` package
- **Python**: `pyyaml`
- **Not required**: `dora-rs`, `pyarrow`

## Difference from Example 06

| | 06 (Mixed) | 07 (Pure ROS2) |
|---|---|---|
| Dora | Required | Not used |
| Transport | Dora + ROS2 | ROS2 only |
| Dataflow | `dataflow.yaml` | None |
| Launch | `dora up && dora start` | `python3` |
| Bridge handler | MockRos2Handler | TurtlesimHandler (real rclpy) |
