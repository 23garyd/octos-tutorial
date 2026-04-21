import pytest

from .conftest import assert_markers, requires_dora, run_dataflow
from .expected_markers import EXAMPLE_02


@pytest.mark.smoke
@requires_dora
def test_02_safety_tiers(dora_daemon):
    run = run_dataflow("02-safety-tiers")
    assert run.returncode == 0, f"dora exited {run.returncode}\nstderr:\n{run.stderr[-1000:]}"
    assert_markers(run.stdout, EXAMPLE_02)
