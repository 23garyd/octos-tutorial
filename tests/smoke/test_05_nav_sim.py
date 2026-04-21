import importlib.util
import platform

import pytest

from .conftest import requires_dora, run_dataflow_until

mujoco_available = importlib.util.find_spec("mujoco") is not None
rerun_available = importlib.util.find_spec("rerun") is not None

# road-lane-publisher logs this once the 1065-waypoint path loads and
# the first pose arrives — proves mujoco-sim + pub-road + road-lane-pub
# are all alive.
PATH_LOADED_MARKER = "Road lane: 1065 waypoints"


@pytest.mark.smoke
@requires_dora
@pytest.mark.skipif(not mujoco_available, reason="mujoco not installed")
@pytest.mark.skipif(not rerun_available, reason="rerun-sdk not installed")
def test_05_nav_sim_py(dora_daemon):
    """Heaviest example — 9 nodes with MuJoCo + Rerun. Runs continuously;
    assert the path-loaded marker appears within 90s, then stop the
    dataflow."""
    mujoco_gl = "glfw" if platform.system() == "Darwin" else "egl"
    run = run_dataflow_until(
        "05-slam-nav-sim",
        dataflow="dataflow_nav_sim_py.yaml",
        marker=PATH_LOADED_MARKER,
        timeout=90,
        extra_env={"MUJOCO_GL": mujoco_gl},
    )
    assert PATH_LOADED_MARKER in run.stdout
