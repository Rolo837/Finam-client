"""Errors raised by :class:`finam_client.client.FinamApiClient`.

Consumers that already have their own error type (BF: ``BrokerError``) pass an
``error_factory`` to the client; the factory receives the same arguments as
:class:`FinamError` and returns the exception to raise.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


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

    def __str__(self) -> str:
        return self.message


ErrorFactory = Callable[..., Exception]


def default_error_factory(
    category: ErrorCategory,
    message: str,
    *,
    retryable: bool = False,
    broker_code: str | None = None,
) -> FinamError:
    return FinamError(category, message, retryable=retryable, broker_code=broker_code)
