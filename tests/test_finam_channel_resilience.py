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


def test_min_interval_paces_unary_calls():
    from finam_client.config import GrpcTuning

    with patch("finam_client.client.secure_channel"):
        client = FinamApiClient(
            ClientConfig(secret_file="unused", grpc_client=GrpcTuning(min_interval_sec=0.5)), secret="s"
        )
    client._ensure_jwt = lambda: None
    client.accounts_stub.GetAccount.with_call = lambda **kw: (object(), None)
    clock = [100.0]

    def fake_sleep(sec):
        clock[0] += sec

    with patch("time.monotonic", lambda: clock[0]), patch("time.sleep", fake_sleep):
        for _ in range(3):
            client.get_account("acc")
    # first call is free, the next two each wait one interval
    assert clock[0] == pytest.approx(101.0)
    client.close()


def test_pacing_is_off_by_default(grpc_client):
    grpc_client.accounts_stub.GetAccount.with_call = lambda **kw: (object(), None)
    with patch("time.sleep") as sleep:
        for _ in range(3):
            grpc_client.get_account("acc")
    sleep.assert_not_called()


def test_unary_error_carries_facts(grpc_client):
    detail = "INVALID_ARGUMENT: [145]No enough coverage. You need 1 RUR\x0cНедостаток обеспечения"
    _install_place_order_failure(grpc_client, _FakeRpcError(StatusCode.INVALID_ARGUMENT, detail))

    with pytest.raises(FinamError) as excinfo:
        grpc_client.place_order(object())

    err = excinfo.value
    assert err.grpc_status == "INVALID_ARGUMENT"
    assert err.native_code == 145
    assert err.native_message == "No enough coverage. You need 1 RUR\nНедостаток обеспечения"
    assert err.outcome_unknown is False
    assert err.broker_code == "INVALID_ARGUMENT"
    assert "[145]" in err.message


def test_place_timeout_sets_outcome_unknown(grpc_client):
    _install_place_order_failure(grpc_client, _FakeRpcError(StatusCode.DEADLINE_EXCEEDED))

    with pytest.raises(FinamError) as excinfo:
        grpc_client.place_order(object())

    assert excinfo.value.outcome_unknown is True
    assert excinfo.value.broker_code == "place_timeout"


def test_refresh_jwt_error_carries_facts(grpc_client):
    def _auth(**kwargs):
        raise _FakeRpcError(StatusCode.UNAUTHENTICATED, "Api token could not be verified")

    grpc_client.auth_stub.Auth.with_call = _auth
    with pytest.raises(FinamError) as excinfo:
        grpc_client._refresh_jwt()

    err = excinfo.value
    assert err.message == "Auth failed: Api token could not be verified"
    assert err.grpc_status == "UNAUTHENTICATED"
    assert err.native_code is None
    assert err.native_message == "Api token could not be verified"


def test_legacy_factory_without_fact_kwargs_still_works():
    from finam_client.client import _accepted_fact_kwargs

    def legacy(category, message, *, retryable=False, broker_code=None):
        return None

    def modern(category, message, *, retryable=False, broker_code=None, native_code=None, **kw):
        return None

    assert _accepted_fact_kwargs(legacy) == frozenset()
    assert "native_code" in _accepted_fact_kwargs(modern)
