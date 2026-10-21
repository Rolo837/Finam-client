from unittest.mock import patch

import pytest

from finam_client.client import FinamApiClient
from finam_client.config import ClientConfig
from finam_client.errors import ErrorCategory, FinamError


class _Custom(Exception):
    def __init__(self, category, message, *, retryable=False, broker_code=None):
        super().__init__(message)
        self.category, self.retryable, self.broker_code = category, retryable, broker_code


def _client(**kwargs):
    with patch("finam_client.client.secure_channel"):
        return FinamApiClient(ClientConfig(secret_file="unused"), secret="s", **kwargs)


def test_default_errors_are_finam_error():
    with pytest.raises(FinamError) as exc:
        _client().last_quote("SBER")
    assert exc.value.category is ErrorCategory.VALIDATION


def test_symbol_validation_goes_through_error_factory():
    with pytest.raises(_Custom) as exc:
        _client(error_factory=_Custom).get_asset("SBER", "acc")
    assert exc.value.category is ErrorCategory.VALIDATION
    assert exc.value.retryable is False


def test_legacy_factory_receives_no_fact_kwargs():
    with patch("finam_client.client.secure_channel"):
        client = FinamApiClient(ClientConfig(secret_file="unused"), secret="s", error_factory=_Custom)
    err = client._error(
        ErrorCategory.GRPC, "m", broker_code="X", grpc_status="INVALID_ARGUMENT", native_code=1
    )
    assert err.broker_code == "X"


def test_default_factory_gets_facts():
    with patch("finam_client.client.secure_channel"):
        client = FinamApiClient(ClientConfig(secret_file="unused"), secret="s")
    err = client._error(
        ErrorCategory.GRPC, "m", grpc_status="NOT_FOUND", native_code=7, native_message="t", outcome_unknown=True
    )
    assert (err.grpc_status, err.native_code, err.native_message, err.outcome_unknown) == ("NOT_FOUND", 7, "t", True)
