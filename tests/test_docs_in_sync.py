"""docs/API.md and docs/STRUCTURES.md are generated; they must not go stale."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _generator():
    spec = importlib.util.spec_from_file_location("generate_docs", ROOT / "scripts" / "generate_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_docs_are_up_to_date():
    for rel, text in _generator().generate().items():
        assert (ROOT / rel).read_text(encoding="utf-8") == text, (
            f"{rel} is stale: run `python scripts/generate_docs.py`"
        )


def test_every_public_client_method_is_documented():
    api = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    for method in _generator().client_methods():
        assert f"`{method['name']}" in api, f"{method['name']} missing from docs/API.md"
