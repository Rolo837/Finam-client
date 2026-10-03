"""Client configuration (plain dataclasses, no pydantic dependency)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GrpcTuning:
    """gRPC keepalive / retry profile (same defaults as the BF daemon)."""

    keepalive_time_sec: float = 30.0
    keepalive_timeout_sec: float = 10.0
    timeout_sec: float = 10.0
    max_attempts: int = 3
    retry_base_sec: float = 0.4
    # Time before JWT expiry at which a refresh is forced.
    jwt_refresh_skew_sec: float = 90.0


@dataclass(frozen=True, slots=True)
class ClientConfig:
    secret_file: str
    endpoint: str = "api.finam.ru:443"
    grpc_client: GrpcTuning = field(default_factory=GrpcTuning)


def read_secret_file(path: Path | str) -> str:
    secret_path = Path(path)
    secret = secret_path.read_text(encoding="utf-8").strip()
    if not secret:
        raise ValueError(f"Secret file is empty: {secret_path}")
    return secret
