import re
from pathlib import Path

import finam_client

ROOT = Path(__file__).resolve().parent.parent


def test_version_files_in_sync():
    canon = (ROOT / "VERSION").read_text().strip()
    pyproject = re.search(r'(?m)^version\s*=\s*"([^"]+)"', (ROOT / "pyproject.toml").read_text()).group(1)
    assert canon == pyproject == finam_client.__version__
