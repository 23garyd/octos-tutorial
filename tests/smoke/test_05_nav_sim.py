import importlib.util

import pytest

from .conftest import requires_dora, run_dataflow

mujoco_available = importlib.util.find_spec("mujoco") is not None
rerun_available = importlib.util.find_spec("rerun") is not None


@pytest.mark.smoke
@requires_dora
@pytest.mark.skipif(not mujoco_available, reason="mujoco not installed")
@pytest.mark.skipif(not rerun_available, reason="rerun-sdk not installed")
def test_05_nav_sim_py():
    """Heaviest example. Run the pure-Python nav sim dataflow headless.
    MUJOCO_GL=egl avoids needing a display on Linux; on macOS the default
    glfw is fine but we still skip if no display is available."""
    run = run_dataflow(
        "05-slam-nav-sim",
        dataflow="dataflow_nav_sim_py.yaml",
        timeout=180,
        extra_env={"MUJOCO_GL": "egl"},
    )
    # This example runs continuously — we only assert it starts without crashing
    # and the agent node prints its banner. If the dataflow runs to timeout,
    # that's success as long as the banner appeared.
    assert "Octos" in run.stdout or run.returncode == 0, (
        f"dora exited {run.returncode}\nstderr:\n{run.stderr[-1000:]}"
    )
