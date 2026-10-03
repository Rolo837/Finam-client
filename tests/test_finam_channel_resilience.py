from __future__ import annotations

from unittest.mock import patch

import pytest
from grpc import RpcError, StatusCode

from finam_client.client import FinamApiClient
from finam_client.config import ClientConfig
from finam_client.errors import FinamError


class _FakeRpcError(RpcError):
    def __init__(self, code, details: str = "boom"):
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


@pytest.fixture
def grpc_client():
    with patch("finam_client.client.secure_channel") as secure_channel_mock:
        client = FinamApiClient(ClientConfig(secret_file="unused"), secret="secret")
        client._ensure_jwt = lambda: None  # bypass real Auth for these tests
        client._test_secure_channel_mock = secure_channel_mock
        yield client
        client.close()


def test_channel_created_with_keepalive_options(grpc_client):
    mock = grpc_client._test_secure_channel_mock
    assert mock.call_count == 1
    _, kwargs = mock.call_args
    options = dict(kwargs["options"])
    assert options["grpc.keepalive_time_ms"] == 30000
    assert options["grpc.keepalive_timeout_ms"] == 10000
    assert options["grpc.keepalive_permit_without_calls"] == 1


def test_ensure_channel_is_noop_while_open(grpc_client):
    mock = grpc_client._test_secure_channel_mock
    grpc_client.ensure_channel()
    assert mock.call_count == 1


def test_ensure_channel_rebuilds_after_close(grpc_client):
    mock = grpc_client._test_secure_channel_mock
    grpc_client.close()
    assert grpc_client._channel is None

    grpc_client.ensure_channel()

    assert mock.call_count == 2
    assert grpc_client._channel is not None
    assert grpc_client.marketdata_stub is not None


def _install_place_order_failure(client, error: RpcError):
    calls: list[dict] = []

    def _place_order(**kwargs):
        calls.append(kwargs)
        raise error

    client.orders_stub.PlaceOrder.with_call = _place_order
    return calls


@pytest.mark.parametrize("code", [StatusCode.DEADLINE_EXCEEDED, StatusCode.UNAVAILABLE])
def test_place_order_never_retries_transient_errors(grpc_client, code):
    """A retried DEADLINE_EXCEEDED/UNAVAILABLE on PlaceOrder could double-submit
    if the first attempt actually reached the broker — must fail on first try."""
    calls = _install_place_order_failure(grpc_client, _FakeRpcError(code))

    with pytest.raises(FinamError) as excinfo:
        grpc_client.place_order(object())

    assert len(calls) == 1
    assert excinfo.value.retryable is False


def test_place_order_timeout_reports_place_timeout_broker_code(grpc_client):
    calls = _install_place_order_failure(grpc_client, _FakeRpcError(StatusCode.DEADLINE_EXCEEDED))

    with pytest.raises(FinamError) as excinfo:
        grpc_client.place_order(object())

    assert len(calls) == 1
    assert excinfo.value.broker_code == "place_timeout"


def test_unary_call_still_retries_deadline_exceeded(grpc_client):
    """Non-order unary calls keep the original idempotent retry/backoff behavior."""
    calls: list[dict] = []

    def _get_account(**kwargs):
        calls.append(kwargs)
        raise _FakeRpcError(StatusCode.DEADLINE_EXCEEDED)

    grpc_client.accounts_stub.GetAccount.with_call = _get_account

    with patch("time.sleep"):
        with pytest.raises(FinamError) as excinfo:
            grpc_client.get_account("acc-1")

    assert len(calls) == grpc_client.GRPC_MAX_ATTEMPTS
    assert excinfo.value.retryable is True


def test_rate_limit_is_retried_with_its_own_backoff(grpc_client):
    """RESOURCE_EXHAUSTED (Finam ~200 req/min) retries on idempotent calls, with the
    rate-limit backoff rather than the sub-second transport one."""
    calls: list[dict] = []

    def _get_account(**kwargs):
        calls.append(kwargs)
        raise _FakeRpcError(StatusCode.RESOURCE_EXHAUSTED, "Too Many Requests")

    grpc_client.accounts_stub.GetAccount.with_call = _get_account

    with patch("time.sleep") as sleep:
        with pytest.raises(FinamError) as excinfo:
            grpc_client.get_account("acc-1")

    assert len(calls) == grpc_client.GRPC_MAX_ATTEMPTS
    assert excinfo.value.retryable is True
    assert excinfo.value.broker_code == "RESOURCE_EXHAUSTED"
    assert [c.args[0] for c in sleep.call_args_list] == [2.0, 4.0]


def test_place_order_does_not_retry_rate_limit(grpc_client):
    calls = _install_place_order_failure(grpc_client, _FakeRpcError(StatusCode.RESOURCE_EXHAUSTED))

    with pytest.raises(FinamError) as excinfo:
        grpc_client.place_order(object())

    assert len(calls) == 1
    assert excinfo.value.retryable is False
