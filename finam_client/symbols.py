"""Finam Trade API symbol format (ticker@mic)."""
from __future__ import annotations

from finam_client.errors import ErrorCategory, FinamError

def _is_symbol(value: str) -> bool:
    # Real Finam symbols are not limited to [A-Za-z0-9._-]: 2.3% of AllAssets (2.6% of active) have
    # tickers with '/', ' ', '+', '$', '(', '&', CJK, even '@', and mics such as
    # '#WWCP' or '_CRYP' (verified 2026-10-03, scripts/verify_finam_venue.py). The
    # mic never contains '@', so split on the last one. Only a bare ticker is rejected.
    ticker, sep, mic = value.rpartition("@")
    return bool(sep and ticker and mic and not any(ch.isspace() or ord(ch) < 32 for ch in mic))


def validate_finam_symbol(symbol: str) -> str:
    """Return the normalized symbol or raise FinamError(VALIDATION)."""
    value = str(symbol or "").strip()
    if not value or not _is_symbol(value):
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
