# 06 — ROS2 Bridge (Mixed Transport)

Demonstrates running an octos agent with tools routed to **both dora and ROS2**.

## What You'll Learn

- Transport abstraction: same agent code, different communication backends
- Per-tool routing via `tool_transport.yaml`
- ROS2 bridge process for translating JSON ↔ ROS2

## Architecture

```
┌──────────────────┐     skill_request/result    ┌────────────────┐
│   Octos Agent    │ ─────── (dora) ──────────── │  Mock Robot    │
│                  │                              │  (dora node)   │
│  TransportRouter │     JSON / Unix socket       └────────────────┘
│  ┌─────┬───────┐ │ ──────────────────────────── ┌────────────────┐
│  │dora │ ros2  │ │                              │  ROS2 Bridge   │
│  └─────┴───────┘ │                              │  (subprocess)  │
└──────────────────┘                              └────────┬───────┘
                                                           │ rclpy
                                                  ┌────────┴───────┐
                                                  │  ROS2 Topics   │
                                                  │  Services      │
                                                  │  Actions       │
                                                  └────────────────┘
```

## Quick Start (Mock Mode)

No ROS2 installation needed — uses a mock handler:

```bash
# Terminal 1: Start the ROS2 bridge in mock mode
python -m octos_py.ros2_bridge --mock --socket /tmp/octos_ros2_bridge.sock

# Terminal 2: Run the agent
cd 06-ros2-bridge
dora up && dora start dataflow.yaml --attach
```

## With Real ROS2

1. Source your ROS2 workspace
2. Start the bridge with rclpy:
   ```bash
   python -m octos_py.ros2_bridge --socket /tmp/octos_ros2_bridge.sock
   ```
3. Extend `RclpyHandler` in `octos_py/ros2_bridge.py` for your specific services/actions
4. Run the agent as above

## Transport Config

`tool_transport.yaml` maps each tool to a transport:

```yaml
tools:
  navigate_to:
    transport: ros2      # routed to ROS2 bridge
    pattern: action
  get_map:
    transport: dora      # routed to dora mock-robot node
    pattern: request
```

## Dependencies

- `dora-rs`, `pyarrow`, `numpy` (core)
- `pyyaml` (transport config)
- `rclpy` (only for real ROS2 mode, not needed for mock)
