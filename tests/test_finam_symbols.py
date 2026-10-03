import pytest

from finam_client.symbols import validate_finam_symbol
from finam_client.errors import FinamError


def test_validate_finam_symbol_ok():
    assert validate_finam_symbol("CRM6@MISX") == "CRM6@MISX"
    assert validate_finam_symbol(" SBER@MISX ") == "SBER@MISX"


def test_validate_finam_symbol_rejects_bare_ticker():
    with pytest.raises(FinamError, match="ticker@mic"):
        validate_finam_symbol("CRM6")


@pytest.mark.parametrize(
    "symbol",
    ["EURUSD@#WWCP", "(USD+EUR)CB@#RCBR", "$DJUSEN@_SCI", "BRK/B@XNYS", "SGD @#WWCP", "A@B@_CRYP"],
)
def test_validate_finam_symbol_accepts_real_world_symbols(symbol):
    assert validate_finam_symbol(symbol) == symbol


@pytest.mark.parametrize("symbol", ["", "@MISX", "SBER@", "SBER", "SBER@MI SX"])
def test_validate_finam_symbol_rejects_malformed(symbol):
    with pytest.raises(FinamError):
        validate_finam_symbol(symbol)
