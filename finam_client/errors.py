"""Errors raised by :class:`finam_client.client.FinamApiClient`.

Consumers that already have their own error type (BF: ``BrokerError``) pass an
``error_factory`` to the client; the factory receives the same arguments as
:class:`FinamError` and returns the exception to raise.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from grpc import StatusCode


class ErrorCategory(str, Enum):
    AUTH = "broker_auth"
    GRPC = "broker_grpc"
    MARKETDATA = "marketdata"
    ORDER = "order"
    VALIDATION = "validation"


@dataclass(slots=True)
class FinamError(Exception):
    category: ErrorCategory
    message: str
    retryable: bool = False
    broker_code: str | None = None
    grpc_status: str | None = None
    native_code: int | None = None
    native_message: str | None = None
    outcome_unknown: bool = False

    def __str__(self) -> str:
        return self.message


ErrorFactory = Callable[..., Exception]


def default_error_factory(
    category: ErrorCategory,
    message: str,
    *,
    retryable: bool = False,
    broker_code: str | None = None,
    grpc_status: str | None = None,
    native_code: int | None = None,
    native_message: str | None = None,
    outcome_unknown: bool = False,
) -> FinamError:
    return FinamError(
        category,
        message,
        retryable=retryable,
        broker_code=broker_code,
        grpc_status=grpc_status,
        native_code=native_code,
        native_message=native_message,
        outcome_unknown=outcome_unknown,
    )


@dataclass(frozen=True, slots=True)
class RpcErrorFacts:
    """Структурированные факты об ошибке Finam; без решений и словаря потребителя."""

    grpc_status: str
    native_code: int | None
    native_message: str
    outcome_unknown: bool = False


_GRPC_PREFIX = "gRPC error:"
_STATUS_NAMES = frozenset(c.name for c in StatusCode)
_STATUS_PREFIX_RE = re.compile(r"^\s*([A-Z_]+)\s*:\s*")
_NATIVE_CODE_RE = re.compile(r"^\s*[\[(](\d+)[\])]\s*")


def parse_native_detail(detail: str | None) -> tuple[int | None, str]:
    """Разбирает detail Finam в ``(native_code, native_message)``.

    Снимает префикс ``gRPC error:`` и имя gRPC-статуса, затем номер ``[N]``/``(N)``
    в начале. Сегменты через form feed (английский и русский) сохраняются все,
    разделитель заменяется на перевод строки.
    """
    text = (detail or "").strip()
    if text.startswith(_GRPC_PREFIX):
        text = text[len(_GRPC_PREFIX):].lstrip()
    match = _STATUS_PREFIX_RE.match(text)
    if match and match.group(1) in _STATUS_NAMES:
        text = text[match.end():]
    native_code: int | None = None
    match = _NATIVE_CODE_RE.match(text)
    if match:
        native_code = int(match.group(1))
        text = text[match.end():]
    segments = [seg.strip() for seg in text.split("\f")]
    return native_code, "\n".join(seg for seg in segments if seg)


def parse_rpc_error(exc: Any, *, placement: bool = False) -> RpcErrorFacts:
    """Единая точка разбора ``grpc.RpcError`` (унарные вызовы, auth, стримы).

    ``placement=True`` - ошибка пришла от размещения заявки (не идемпотентный
    вызов): таймаут тогда означает неизвестный исход (``outcome_unknown``).
    """
    try:
        code = exc.code()
        status = code.name if code is not None else "UNKNOWN"
    except Exception:
        code, status = None, "UNKNOWN"
    try:
        detail = exc.details()
    except Exception:
        detail = None
    if detail is None:
        detail = str(exc)
    native_code, native_message = parse_native_detail(detail)
    return RpcErrorFacts(
        grpc_status=status,
        native_code=native_code,
        native_message=native_message,
        outcome_unknown=placement and code == StatusCode.DEADLINE_EXCEEDED,
    )
