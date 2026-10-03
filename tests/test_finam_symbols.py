import pytest

from finam_client.symbols import validate_finam_symbol
from finam_client.errors import FinamError


def test_validate_finam_symbol_ok():
    assert validate_finam_symbol("CRM6@MISX") == "CRM6@MISX"
    assert validate_finam_symbol(" SBER@MISX ") == "SBER@MISX"


def test_validate_finam_symbol_rejects_bare_ticker():
    with pytest.raises(FinamError, match="ticker@mic"):
        validate_finam_symbol("CRM6")
