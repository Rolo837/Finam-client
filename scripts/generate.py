#!/usr/bin/env python3
"""Generate Finam Trade API gRPC stubs from the vendored finam-trade-api proto.

Source of truth: ``proto/`` (vendored copy of the official proto, see
docs/FINAM_PROTO_VERSION.md for tag and commit).
Output: ``finam_client/grpc_gen/`` — committed to the repo so that
runtime/Docker never calls protoc.

The official proto use the package ``grpc.tradeapi.v1.*``; a naive ``--python_out``
would collide with the ``grpc`` module shipped by grpcio. We keep the proto
directory layout but re-root the *generated* cross-imports under
``finam_client.grpc_gen`` so ``import grpc`` keeps resolving to grpcio.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTO_ROOT = REPO_ROOT / "proto"
OUT_DIR = REPO_ROOT / "finam_client" / "grpc_gen"
PKG_PREFIX = "finam_client.grpc_gen"

# proto files the client needs (relative to PROTO_ROOT). ``corporateactions`` is
# intentionally out of scope (see plan). google/* stay pointing at the installed
# protobuf / googleapis-common-protos packages, so they are NOT generated here.
PROTO_FILES = [
    "grpc/tradeapi/v1/side.proto",
    "grpc/tradeapi/v1/trade.proto",
    "grpc/tradeapi/v1/auth/auth_service.proto",
    "grpc/tradeapi/v1/accounts/accounts_service.proto",
    "grpc/tradeapi/v1/assets/assets_service.proto",
    "grpc/tradeapi/v1/orders/orders_service.proto",
    "grpc/tradeapi/v1/marketdata/marketdata_service.proto",
    "grpc/tradeapi/v1/reports/reports_service.proto",
    "grpc/tradeapi/v1/metrics/usage_metrics_service.proto",
    # openapiv2 gateway annotations are referenced by every *_service.proto above
    # and are NOT shipped by googleapis-common-protos, so generate them locally.
    "grpc/gateway/protoc_gen_openapiv2/options/openapiv2.proto",
    "grpc/gateway/protoc_gen_openapiv2/options/annotations.proto",
]

# Re-root only the vendored proto packages (grpc.tradeapi.*, grpc.gateway.*).
# A bare ``import grpc`` (grpcio) and any ``from grpc._...`` stay untouched.
LOCAL_IMPORT_RE = re.compile(r"^from (grpc\.(?:tradeapi|gateway)\b[\w.]*) import", re.M)


def clean_output() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)


def run_protoc() -> None:
    args = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{PROTO_ROOT}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        *[str(PROTO_ROOT / f) for f in PROTO_FILES],
    ]
    subprocess.run(args, check=True, cwd=REPO_ROOT)


def fix_imports() -> None:
    for path in OUT_DIR.rglob("*.py"):
        text = path.read_text()
        new = LOCAL_IMPORT_RE.sub(rf"from {PKG_PREFIX}.\1 import", text)
        if new != text:
            path.write_text(new)


def write_init_files() -> None:
    dirs = [OUT_DIR, *(p for p in OUT_DIR.rglob("*") if p.is_dir())]
    for d in dirs:
        init = d / "__init__.py"
        if not init.exists():
            init.write_text("")


def main() -> None:
    if not PROTO_ROOT.exists():
        sys.exit(
            "Vendor proto not found at "
            f"{PROTO_ROOT}."
        )
    clean_output()
    run_protoc()
    fix_imports()
    write_init_files()
    print(f"Generated Finam gRPC stubs in {OUT_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
