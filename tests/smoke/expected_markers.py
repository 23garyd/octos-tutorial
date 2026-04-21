"""Stdout markers expected from each example after a successful run.

Sourced by grep'ing print() statements in every example's node files on the
0.3.13 baseline. Each marker is a substring that must appear in the captured
stdout of `dora start <dataflow.yaml> --attach` for the example to be
considered passing. Keep markers short and invariant — avoid anything that
contains paths, timestamps, or numeric counts that can shift.
"""

EXAMPLE_01 = [
    "Octos Agent \u2014 Pipeline Basics",
    "[mock-robot] Ready",
    "Complete!",
    "[mock-robot] Stopped",
]

EXAMPLE_02 = [
    "Octos Agent \u2014 Safety Tiers Demo",
    "[safe-robot] Ready",
    "Complete!",
    "[safe-robot] Stopped",
]

EXAMPLE_03 = [
    "Octos Agent \u2014 LLM Reasoning",
    "[mock-robot] Ready",
    "Agent response:",
    "[mock-robot] Stopped",
]

EXAMPLE_04 = [
    "Octos Agent \u2014 Human Gate Demo",
    "[mock-robot] Ready",
    "Mission Summary",
    "[mock-robot] Stopped",
]

EXAMPLE_06 = [
    "Octos Agent \u2014 Mixed Transport (Dora + ROS2)",
    "Tools registered:",
    "Complete!",
]
