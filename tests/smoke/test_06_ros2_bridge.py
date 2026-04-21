import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from .conftest import REPO_ROOT, assert_markers, requires_dora, run_dataflow
from .expected_markers import EXAMPLE_06


@pytest.fixture
def ros2_bridge_mock():
    """Spawn the ROS2 bridge in --mock mode on a short unix socket path.

    macOS limits AF_UNIX sun_path to ~104 bytes, and pytest's tmp_path is
    already too long — so we use /tmp/octos-<uuid>.sock instead.
    """
    sock = Path(f"/tmp/octos-{uuid.uuid4().hex[:8]}.sock")
    if sock.exists():
        sock.unlink()
    proc = subprocess.Popen(
        [sys.executable, "-m", "octos_py.ros2_bridge", "--mock", "--socket", str(sock)],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # Wait for socket to appear (bridge is quick to boot).
    for _ in range(50):
        if sock.exists():
            break
        time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("ros2 bridge --mock did not create socket")
    yield str(sock)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    if sock.exists():
        try:
            sock.unlink()
        except OSError:
            pass


@pytest.mark.smoke
@requires_dora
def test_06_ros2_bridge_mixed(dora_daemon, ros2_bridge_mock):
    run = run_dataflow(
        "06-ros2-bridge",
        timeout=120,
        extra_env={"ROS2_BRIDGE_SOCKET": ros2_bridge_mock},
    )
    assert run.returncode == 0, f"dora exited {run.returncode}\nstderr:\n{run.stderr[-1000:]}"
    assert_markers(run.stdout, EXAMPLE_06)
