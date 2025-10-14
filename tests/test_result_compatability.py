from pathlib import Path
import pytest

from ucc_bench.results import SuiteResults

COMPAT_DIR = Path(__file__).parent / "data"


def json_files_in(dirpath: Path):
    return sorted(p for p in dirpath.glob("*.json"))


@pytest.mark.parametrize(
    "path",
    [pytest.param(p, id=p.name) for p in json_files_in(COMPAT_DIR)],
)
def test_old_specs_still_load(path: Path):
    """Test that old benchmark result files can still be loaded."""
    data = path.read_text()
    spec = SuiteResults.model_validate_json(data)
    assert spec is not None
