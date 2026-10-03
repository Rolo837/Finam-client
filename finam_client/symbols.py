"""Finam Trade API symbol format (ticker@mic)."""
from __future__ import annotations

import re

from finam_client.errors import ErrorCategory, FinamError

FINAM_SYMBOL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_finam_symbol(symbol: str) -> str:
    """Return the normalized symbol or raise FinamError(VALIDATION)."""
    value = str(symbol or "").strip()
    if not value or not FINAM_SYMBOL_RE.fullmatch(value):
        raise FinamError(
            ErrorCategory.VALIDATION,
            f"Finam symbol must be ticker@mic (e.g. SBER@MISX), got {symbol!r}",
            retryable=False,
        )
    return value


def split_symbol(symbol: str) -> tuple[str, str]:
    """``SBER@MISX`` -> ``("SBER", "MISX")``. Case is preserved."""
    value = validate_finam_symbol(symbol)
    ticker, _, mic = value.rpartition("@")
    return ticker, mic
