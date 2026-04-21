import pytest

from .conftest import assert_markers, requires_dora, run_dataflow
from .expected_markers import EXAMPLE_01


@pytest.mark.smoke
@requires_dora
def test_01_pipeline_basics(dora_daemon):
    run = run_dataflow("01-pipeline-basics")
    assert run.returncode == 0, f"dora exited {run.returncode}\nstderr:\n{run.stderr[-1000:]}"
    assert_markers(run.stdout, EXAMPLE_01)
