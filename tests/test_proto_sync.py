"""Provenance / freshness tooling for the vendored Finam proto."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("proto_sync", ROOT / "scripts" / "proto_sync.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ps = _load()


def test_vendored_proto_matches_recorded_origin():
    assert ps.check_tree(ROOT) == []


def test_committed_stubs_match_the_proto():
    pytest.importorskip("grpc_tools")
    problems, note = ps.check_stubs(ROOT)
    assert problems == [], problems


def test_hand_edit_of_proto_is_detected(tmp_path):
    shutil.copytree(ROOT / "proto", tmp_path / "proto")
    target = next((tmp_path / "proto" / "grpc").rglob("assets_service.proto"))
    target.write_text(target.read_text() + "\n// edited by hand\n")
    problems = ps.check_tree(tmp_path)
    assert problems and "differs from the recorded copy" in problems[0]


def test_stale_stubs_are_detected(tmp_path):
    pytest.importorskip("grpc_tools")
    shutil.copytree(ROOT / "proto", tmp_path / "proto")
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "generate.py", tmp_path / "scripts" / "generate.py")
    target = next((tmp_path / "proto" / "grpc").rglob("marketdata_service.proto"))
    # add a field to a message: proto no longer matches the committed stubs
    target.write_text(target.read_text().replace("message BarsRequest {", "message BarsRequest {\n  string extra_field = 99;", 1))
    problems, _ = ps.check_stubs(tmp_path)
    assert any("marketdata_service.proto is stale" in p for p in problems), problems


def test_online_check_reports_newer_release(monkeypatch):
    marker = json.loads((ROOT / "proto" / ps.MARKER).read_text())
    have = marker["tag"]
    major, minor, patch = ps.tag_key(have)
    newer = f"{major}.{minor + 1}.0"
    monkeypatch.setattr(ps, "remote_tags", lambda url=ps.UPSTREAM_URL: {have: marker["commit"], newer: "f" * 40})
    status, message = ps.check_online(ROOT)
    assert status == "outdated" and newer in message


def test_online_check_current_and_retagged(monkeypatch):
    marker = json.loads((ROOT / "proto" / ps.MARKER).read_text())
    have = marker["tag"]
    monkeypatch.setattr(ps, "remote_tags", lambda url=ps.UPSTREAM_URL: {have: marker["commit"]})
    assert ps.check_online(ROOT)[0] == "current"
    monkeypatch.setattr(ps, "remote_tags", lambda url=ps.UPSTREAM_URL: {have: "0" * 40})
    assert ps.check_online(ROOT)[0] == "retagged"


def test_online_check_tolerates_unreachable_upstream(monkeypatch):
    def boom(url=ps.UPSTREAM_URL):
        raise OSError("offline")

    monkeypatch.setattr(ps, "remote_tags", boom)
    assert ps.check_online(ROOT)[0] == "unknown"


def test_tags_are_ordered_numerically():
    assert max(["2.9.0", "2.23.0", "2.16.0"], key=ps.tag_key) == "2.23.0"


def test_diff_summary_flags_removed_declarations(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    for d in (old, new):
        d.mkdir()
    (old / "a.proto").write_text("message A {\n  string x = 1;\n  string y = 2;\n}\n")
    (new / "a.proto").write_text("message A {\n  string x = 1;\n  string z = 3;\n}\n")
    summary = "\n".join(ps.diff_summary(old, new))
    assert "!!" in summary and "string y = 2;" in summary
