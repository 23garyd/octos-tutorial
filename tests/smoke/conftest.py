"""Smoke-test harness for running dora dataflows end-to-end.

Each test runs `dora start <dataflow>.yaml --attach` in the example's
directory with a timeout, captures stdout, and asserts the expected markers
appear. The harness is deliberately minimal — it does not parse the dataflow
or inspect dora internals; it just proves the example completes and prints
its sign-off lines.

Tests are marked `smoke` and skipped if the dora CLI is not on PATH, so the
default `pytest` run (unit-only) still passes on machines without dora.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
# MockProvider in examples 01-04 loops through ~15-20 iterations before
# concluding; a clean 0.3.13 run of example 01 takes ~100s. Leave generous
# headroom so slow CI machines don't time out.
DEFAULT_TIMEOUT = 240  # seconds per example


@dataclass
class DataflowRun:
    returncode: int
    stdout: str
    stderr: str


def _have_dora() -> bool:
    return shutil.which("dora") is not None


requires_dora = pytest.mark.skipif(not _have_dora(), reason="dora CLI not on PATH")


def _dora(*args: str, cwd: Path | None = None, timeout: int = 30,
          env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["dora", *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(scope="session")
def dora_daemon():
    """Ensure `dora up` has been called. `dora up` is idempotent on 0.3.x;
    behavior on v1.0.0-rc.1 is untested at time of writing — if the second
    invocation errors, the fixture logs but does not fail, and the per-test
    `dora start` call will surface the real problem."""
    if not _have_dora():
        pytest.skip("dora CLI not on PATH")
    try:
        _dora("up", timeout=30)
    except subprocess.TimeoutExpired:
        pytest.skip("`dora up` timed out")
    yield
    # Best-effort teardown. Ignore failures — the daemon may already be gone.
    try:
        _dora("destroy", timeout=15)
    except Exception:
        pass


def run_dataflow(example_dir: str, dataflow: str = "dataflow.yaml",
                 timeout: int = DEFAULT_TIMEOUT,
                 extra_env: dict | None = None) -> DataflowRun:
    """Run `dora start <dataflow> --attach` inside an example dir.

    `--attach` blocks until the dataflow exits. All examples fire `dora stop`
    from the agent node once the pipeline completes, which causes attach to
    return. The outer timeout is a safety net for hangs.
    """
    cwd = REPO_ROOT / example_dir
    assert cwd.is_dir(), f"example directory missing: {cwd}"
    assert (cwd / dataflow).is_file(), f"dataflow missing: {cwd / dataflow}"

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    # Best-effort cleanup of any prior run.
    try:
        _dora("stop", cwd=cwd, timeout=10)
    except Exception:
        pass

    proc = subprocess.run(
        ["dora", "start", dataflow, "--attach"],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return DataflowRun(proc.returncode, proc.stdout, proc.stderr)


def assert_markers(stdout: str, markers: Iterable[str]) -> None:
    missing = [m for m in markers if m not in stdout]
    assert not missing, (
        f"expected markers not found in dataflow stdout: {missing}\n"
        f"---stdout---\n{stdout[-2000:]}"
    )


def run_dataflow_until(example_dir: str, dataflow: str, marker: str,
                       timeout: int = 90,
                       extra_env: dict | None = None) -> DataflowRun:
    """Run a continuous dataflow until `marker` appears in stdout, then stop.

    Use for examples (like 05) that never exit on their own. Launches with
    Popen, polls stdout line by line, and issues `dora stop` once the marker
    is seen. Returns whatever stdout was captured up to that point.
    """
    cwd = REPO_ROOT / example_dir
    assert cwd.is_dir(), f"example directory missing: {cwd}"
    assert (cwd / dataflow).is_file(), f"dataflow missing: {cwd / dataflow}"

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    try:
        _dora("stop", cwd=cwd, timeout=10)
    except Exception:
        pass

    proc = subprocess.Popen(
        ["dora", "start", dataflow, "--attach"],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    collected = []
    deadline = time.monotonic() + timeout
    found = False
    try:
        while time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue
            collected.append(line)
            if marker in line:
                found = True
                break
    finally:
        try:
            _dora("stop", cwd=cwd, timeout=15)
        except Exception:
            pass
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        try:
            rest = proc.stdout.read()
            if rest:
                collected.append(rest)
        except Exception:
            pass
        stderr = ""
        try:
            stderr = proc.stderr.read() or ""
        except Exception:
            pass

    stdout = "".join(collected)
    assert found, (
        f"marker {marker!r} not seen within {timeout}s\n"
        f"---stdout tail---\n{stdout[-2000:]}\n"
        f"---stderr tail---\n{stderr[-1000:]}"
    )
    return DataflowRun(proc.returncode or 0, stdout, stderr)
