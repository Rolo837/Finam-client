"""Venue translation between our catalog identity and Finam's.

Our catalog identifies an instrument by ``(MIC, board, ticker)`` where MOEX
futures are ``MISX:RFUD``. Finam trades the same futures under
``mic=RTSX, board=FUT``. This module is the single place that knows the
difference; AFB and BF both import it.

The table is PRELIMINARY: only ``MISX:RFUD <-> RTSX:FUT`` is confirmed. The
remaining pairs (currency market ``CETS``, indices, other boards) are verified
against GetAsset by ``scripts/verify_finam_venue.py`` and added here.
Tickers are never touched: they are case-sensitive on both sides.
"""
from __future__ import annotations

from typing import NamedTuple

MISX_FORTS_BOARD_AFB = "RFUD"
MISX_FORTS_BOARD_FINAM = "FUT"


class Venue(NamedTuple):
    mic: str
    board: str


# (our mic, our board) -> (finam mic, finam board). Pairs not listed map to themselves.
_TO_FINAM: dict[tuple[str, str], tuple[str, str]] = {
    ("MISX", MISX_FORTS_BOARD_AFB): ("RTSX", MISX_FORTS_BOARD_FINAM),
}
_FROM_FINAM: dict[tuple[str, str], tuple[str, str]] = {v: k for k, v in _TO_FINAM.items()}

# Finam mic whose boards are not in the table fall back to this catalog mic
# (BF historically folded RTSX into MISX).
_MIC_FALLBACK_FROM_FINAM: dict[str, str] = {"RTSX": "MISX"}


def _code(value: str) -> str:
    return str(value or "").strip().upper()


def to_finam_venue(mic: str, board: str) -> Venue:
    """Catalog ``(mic, board)`` -> Finam ``(mic, board)``."""
    key = (_code(mic), _code(board))
    mic_f, board_f = _TO_FINAM.get(key, key)
    return Venue(mic_f, board_f)


def from_finam_venue(finam_mic: str, finam_board: str) -> Venue:
    """Finam ``(mic, board)`` -> catalog ``(mic, board)``."""
    key = (_code(finam_mic), _code(finam_board))
    if key in _FROM_FINAM:
        return Venue(*_FROM_FINAM[key])
    return Venue(_MIC_FALLBACK_FROM_FINAM.get(key[0], key[0]), key[1])


def finam_board_from_venue(exchange: str, venue_board: str) -> str:
    """Finam board for a catalog ``(exchange, board)`` (BF publish lookup)."""
    return to_finam_venue(exchange, venue_board).board
