#!/usr/bin/env python3
"""Provenance, freshness check and update of the vendored Finam proto.

The official proto live in https://github.com/FinamWeb/finam-trade-api (``proto/``). We vendor
a copy in ``proto/`` and commit the generated stubs, so three things can go stale:

  1. the copy itself (upstream released a newer tag);
  2. the copy vs. its recorded origin (hand edits, a partial copy);
  3. the committed stubs vs. the copy (proto updated, ``generate.py`` not re-run).

``proto/UPSTREAM.json`` records the upstream tag, commit and a hash of the copied tree.

  python scripts/proto_sync.py check            # offline: tree hash + stubs match the proto
  python scripts/proto_sync.py check --online   # + is a newer upstream tag out there?
  python scripts/proto_sync.py update [--tag X] # fetch a tag, replace proto/, regenerate stubs+docs
  python scripts/proto_sync.py hash             # print the current tree hash

Exit codes: 0 ok; 1 local inconsistency; 3 newer upstream tag (only with ``--strict``);
2 usage or network error (only with ``--strict``).
Stdlib only, except the stub check (needs grpcio-tools + protobuf; skipped if absent).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

UPSTREAM_URL = "https://github.com/FinamWeb/finam-trade-api.git"
MARKER = "UPSTREAM.json"
TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


# --------------------------------------------------------------------------- helpers
def tree_hash(proto_dir: Path) -> tuple[str, int]:
    """sha256 over (relative path, content hash) of every file, UPSTREAM.json excluded."""
    outer = hashlib.sha256()
    files = sorted(p for p in proto_dir.rglob("*") if p.is_file() and p.name != MARKER)
    for path in files:
        rel = path.relative_to(proto_dir).as_posix()
        outer.update(rel.encode() + b"\0" + hashlib.sha256(path.read_bytes()).hexdigest().encode() + b"\n")
    return outer.hexdigest(), len(files)


def read_marker(proto_dir: Path) -> dict:
    path = proto_dir / MARKER
    if not path.exists():
        raise SystemExit(f"{path} not found: run `python scripts/proto_sync.py update` once")
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, timeout=120).stdout


def remote_tags(url: str = UPSTREAM_URL) -> dict[str, str]:
    """Release tags -> commit sha (peeled for annotated tags), semver tags only."""
    out = git("ls-remote", "--tags", url)
    tags: dict[str, str] = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        name = ref.removeprefix("refs/tags/")
        peeled = name.endswith("^{}")
        name = name.removesuffix("^{}")
        if not TAG_RE.match(name):
            continue
        if peeled or name not in tags:
            tags[name] = sha
    return tags


def tag_key(tag: str) -> tuple[int, int, int]:
    return tuple(int(x) for x in TAG_RE.match(tag).groups())  # type: ignore[return-value]


# --------------------------------------------------------------------------- checks
def check_tree(root: Path) -> list[str]:
    marker = read_marker(root / "proto")
    actual, count = tree_hash(root / "proto")
    problems = []
    if actual != marker["tree_sha256"]:
        problems.append(
            f"proto/ differs from the recorded copy of {marker['tag']} "
            f"(hash {actual[:12]} != {marker['tree_sha256'][:12]}): edited by hand or copied partially"
        )
    if count != marker.get("files"):
        problems.append(f"proto/ has {count} files, recorded {marker.get('files')}")
    return problems


def _strip_json_names(message) -> None:
    """protoc fills ``json_name`` in descriptor sets but strips it from generated stubs."""
    for field in message.field:
        field.ClearField("json_name")
    for field in message.extension:
        field.ClearField("json_name")
    for nested in message.nested_type:
        _strip_json_names(nested)


def check_stubs(root: Path) -> tuple[list[str], str]:
    """Committed stubs must embed exactly the descriptors protoc builds from proto/."""
    try:
        from google.protobuf import descriptor_pb2
        from grpc_tools import protoc
    except ImportError:
        return [], "skipped (grpcio-tools/protobuf not installed)"
    generate = importlib.util.spec_from_file_location("generate", root / "scripts" / "generate.py")
    module = importlib.util.module_from_spec(generate)
    generate.loader.exec_module(module)  # type: ignore[union-attr]
    proto_files: list[str] = module.PROTO_FILES
    with tempfile.TemporaryDirectory() as tmp:
        desc_path = Path(tmp) / "set.pb"
        code = protoc.main(
            ["protoc", f"-I{root / 'proto'}", f"--descriptor_set_out={desc_path}", *proto_files]
        )
        if code != 0:
            return ["protoc failed on proto/"], ""
        raw_set = desc_path.read_bytes()
    problems = []
    sys.path.insert(0, str(root))
    modules = {}
    for name in proto_files:
        mod_name = "finam_client.grpc_gen." + name.removesuffix(".proto").replace("/", ".") + "_pb2"
        try:
            modules[name] = importlib.import_module(mod_name)
        except ImportError as exc:
            problems.append(f"stub {mod_name} cannot be imported: {exc}")
    # Parse only after the stubs are imported: they register the option extensions
    # (google.api.http, openapiv2), so both sides serialize unknown options identically.
    fds = descriptor_pb2.FileDescriptorSet.FromString(raw_set)
    for fdp in fds.file:
        mod = modules.get(fdp.name)
        if mod is None:
            continue
        for message in fdp.message_type:
            _strip_json_names(message)
        for field in fdp.extension:
            field.ClearField("json_name")
        embedded = descriptor_pb2.FileDescriptorProto.FromString(mod.DESCRIPTOR.serialized_pb)
        if embedded.SerializeToString(deterministic=True) != fdp.SerializeToString(deterministic=True):
            problems.append(f"stub for {fdp.name} is stale: run `python scripts/generate.py`")
    return problems, f"{len(fds.file)} files compared"


def check_online(root: Path) -> tuple[str, str]:
    """Returns (status, message): current | outdated | retagged | unknown."""
    marker = read_marker(root / "proto")
    try:
        tags = remote_tags()
    except (subprocess.SubprocessError, OSError) as exc:
        return "unknown", f"cannot reach {UPSTREAM_URL}: {exc}"
    if not tags:
        return "unknown", "no release tags found upstream"
    latest = max(tags, key=tag_key)
    have = marker["tag"]
    if have in tags and tags[have] != marker["commit"]:
        return "retagged", f"upstream tag {have} now points at {tags[have][:12]}, we recorded {marker['commit'][:12]}"
    if tag_key(latest) > tag_key(have):
        newer = sorted((t for t in tags if tag_key(t) > tag_key(have)), key=tag_key)
        return "outdated", f"vendored proto is {have}, upstream has {latest} (newer: {', '.join(newer)})"
    return "current", f"vendored proto {have} is the latest upstream release"


# --------------------------------------------------------------------------- update
DECL_RE = re.compile(r"^\s*(message|enum|oneof|rpc|service)\s+\w+|^\s*(?:repeated\s+|optional\s+)?[\w.<>, ]+\s+\w+\s*=\s*-?\d+\s*;")


def diff_summary(old: Path, new: Path) -> list[str]:
    """Which proto files changed and whether any declaration was removed or renumbered."""
    lines = []
    names = sorted({p.relative_to(old).as_posix() for p in old.rglob("*.proto")}
                   | {p.relative_to(new).as_posix() for p in new.rglob("*.proto")})
    for name in names:
        a, b = old / name, new / name
        if not a.exists():
            lines.append(f"  + {name} (new file)")
            continue
        if not b.exists():
            lines.append(f"  - {name} (REMOVED file)")
            continue
        if a.read_bytes() == b.read_bytes():
            continue
        diff = subprocess.run(["diff", "-u", str(a), str(b)], capture_output=True, text=True).stdout.splitlines()
        added = [l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")]
        removed = [l[1:] for l in diff if l.startswith("-") and not l.startswith("---")]
        gone = [l.strip() for l in removed if DECL_RE.match(l) and l.strip() not in {x.strip() for x in added}]
        decl_added = sum(1 for l in added if DECL_RE.match(l))
        flag = f"  !! {len(gone)} declaration(s) removed or changed" if gone else ""
        lines.append(f"  ~ {name}: +{decl_added} declarations, {len(added)}/{len(removed)} lines +/-{flag}")
        lines += [f"        removed/changed: {g}" for g in gone[:8]]
    return lines


def cmd_update(root: Path, tag: str | None, generate: bool) -> int:
    tags = remote_tags()
    tag = tag or max(tags, key=tag_key)
    if tag not in tags:
        print(f"tag {tag} not found upstream; known: {', '.join(sorted(tags, key=tag_key)[-5:])}", file=sys.stderr)
        return 2
    proto = root / "proto"
    old_marker = json.loads((proto / MARKER).read_text()) if (proto / MARKER).exists() else {}
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "upstream"
        git("clone", "--quiet", "--depth", "1", "--branch", tag, UPSTREAM_URL, str(clone))
        commit = git("rev-parse", "HEAD", cwd=clone).strip()
        if commit != tags[tag]:
            print(f"warning: tag {tag} resolves to {commit[:12]}, ls-remote said {tags[tag][:12]}", file=sys.stderr)
        old_copy = Path(tmp) / "old"
        shutil.copytree(proto, old_copy, ignore=shutil.ignore_patterns(MARKER))
        for child in list(proto.iterdir()):
            if child.name != MARKER:
                shutil.rmtree(child) if child.is_dir() else child.unlink()
        shutil.copytree(clone / "proto", proto, dirs_exist_ok=True)
        summary = diff_summary(old_copy, proto)
    digest, count = tree_hash(proto)
    (proto / MARKER).write_text(
        json.dumps(
            {
                "repo": UPSTREAM_URL,
                "tag": tag,
                "commit": commit,
                "tree_sha256": digest,
                "files": count,
                "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"proto/ updated: {old_marker.get('tag', '?')} -> {tag} ({commit[:12]}), {count} files")
    print("\n".join(summary) if summary else "  (no proto changes)")
    if generate:
        for script in ("generate.py", "generate_docs.py"):
            subprocess.run([sys.executable, str(root / "scripts" / script)], check=True)
    print("\nNext: review `git diff`, run pytest, update docs/FINAM_PROTO_VERSION.md and CHANGELOG.md,"
          "\nbump the package version (MINOR for compatible proto changes).")
    return 0


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--online", action="store_true", help="also compare with the newest upstream release tag")
    c.add_argument("--strict", action="store_true", help="fail (exit 3/2) when outdated or upstream unreachable")
    c.add_argument("--skip-stubs", action="store_true")
    u = sub.add_parser("update")
    u.add_argument("--tag")
    u.add_argument("--no-generate", action="store_true")
    sub.add_parser("hash")
    args = ap.parse_args()
    root: Path = args.root.resolve()

    if args.cmd == "hash":
        digest, count = tree_hash(root / "proto")
        print(f"{digest}  ({count} files)")
        return 0
    if args.cmd == "update":
        return cmd_update(root, args.tag, not args.no_generate)

    marker = read_marker(root / "proto")
    print(f"proto: Finam Trade API {marker['tag']} ({marker['commit'][:12]}, synced {marker.get('synced_at', '?')})")
    problems = check_tree(root)
    if not args.skip_stubs:
        stub_problems, note = check_stubs(root)
        problems += stub_problems
        print(f"stubs: {'OK - ' + note if not stub_problems else 'STALE'}")
    for p in problems:
        print(f"ERROR: {p}", file=sys.stderr)
    if problems:
        return 1
    print("local: OK (proto/ matches its recorded origin)")
    if args.online:
        status, message = check_online(root)
        print(f"upstream: {status.upper()} - {message}")
        if status in ("outdated", "retagged"):
            print("  fix: python scripts/proto_sync.py update", file=sys.stderr)
            return 3 if args.strict else 0
        if status == "unknown":
            return 2 if args.strict else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
