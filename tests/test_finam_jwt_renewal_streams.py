from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from grpc import RpcError, StatusCode

from finam_client.client import FinamApiClient
from finam_client.config import ClientConfig

_QUOTE_SYMBOL = "SBER@MISX"


def _quote_event(price: float):
    return SimpleNamespace(quote=[SimpleNamespace(symbol=_QUOTE_SYMBOL, last=price)])


def _install_auth_mock(client, *, tokens: list[str] | None = None) -> list[str]:
    issued: list[str] = list(tokens or [])

    def _auth_with_call(**_kwargs):
        token = f"token-{len(issued) + 1}"
        issued.append(token)
        return SimpleNamespace(token=token), None

    client.auth_stub.Auth.with_call = _auth_with_call
    client._load_expires_at_from_token_details = lambda: setattr(
        client,
        "_jwt_expires_at",
        datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    return issued


def _install_quote_stream_mock(client, *, pause_before_second: threading.Event) -> list[tuple[str, str]]:
    """SubscribeQuote yields one event, waits for renewal, then yields another."""
    open_calls: list[tuple[str, str]] = []

    def _subscribe_quote(request, metadata):
        open_calls.append(metadata[0][1])
        events = [_quote_event(100.0), _quote_event(101.0)]

        def _gen():
            yield events[0]
            if not pause_before_second.wait(timeout=3.0):
                raise TimeoutError("renewal was not triggered before second stream event")
            yield events[1]

        return _gen()

    client.marketdata_stub.SubscribeQuote = _subscribe_quote
    return open_calls


@pytest.fixture
def grpc_client():
    with patch("finam_client.client.secure_channel") as secure_channel_mock:
        client = FinamApiClient(ClientConfig(secret_file="unused"), secret="secret")
        client._test_secure_channel_mock = secure_channel_mock
        yield client
        client.close()


def test_periodic_renewal_calls_refresh_session(grpc_client):
    refresh_calls: list[str] = []
    original = grpc_client.refresh_session

    def _tracked_refresh() -> None:
        refresh_calls.append(grpc_client._jwt_token or "empty")
        original()

    grpc_client.refresh_session = _tracked_refresh  # type: ignore[method-assign]
    _install_auth_mock(grpc_client)

    grpc_client.start_jwt_renewal_background(interval_sec=1)
    time.sleep(2.5)
    grpc_client.stop_jwt_renewal_background()

    assert len(refresh_calls) >= 2


def test_quote_stream_survives_jwt_refresh(grpc_client):
    renewal_gate = threading.Event()
    open_calls = _install_quote_stream_mock(grpc_client, pause_before_second=renewal_gate)
    tokens = _install_auth_mock(grpc_client)

    grpc_client.refresh_session()
    stream_token = grpc_client._jwt_token
    received: list[float] = []
    errors: list[BaseException] = []

    def _consume() -> None:
        try:
            stream = grpc_client.subscribe_quote([_QUOTE_SYMBOL])
            for event in stream:
                for quote in event.quote:
                    received.append(float(quote.last))
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=_consume, name="test-quote-stream", daemon=True)
    worker.start()

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and not received:
        time.sleep(0.05)
    assert received == [100.0]

    grpc_client.refresh_session(force=True)
    assert grpc_client._jwt_token != stream_token
    assert len(tokens) == 2
    renewal_gate.set()

    worker.join(timeout=3.0)
    assert not errors, errors
    assert received == [100.0, 101.0]
    assert open_calls == [stream_token]
    assert stream_token == tokens[0]


def test_jwt_fail_streak_increments_in_background_worker_and_resets_on_success(grpc_client):
    """Streak is a symptom of the periodic renewal worker, not of every direct
    refresh_session() call (placement-path calls shouldn't skew it) — it only
    increments in the worker's except branch, and only resets once a renewal
    actually succeeds."""
    _install_auth_mock(grpc_client)
    assert grpc_client.jwt_fail_streak == 0

    def _boom(**_kwargs):
        raise RuntimeError("auth unreachable")

    grpc_client.auth_stub.Auth.with_call = _boom

    grpc_client.start_jwt_renewal_background(interval_sec=1)
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and grpc_client.jwt_fail_streak < 2:
        time.sleep(0.05)
    grpc_client.stop_jwt_renewal_background()

    assert grpc_client.jwt_fail_streak >= 2

    tokens = _install_auth_mock(grpc_client)
    grpc_client.refresh_session(force=True)
    assert tokens  # the recovery Auth call actually happened
    assert grpc_client.jwt_fail_streak == 0


class _FakeRpcError(RpcError):
    def code(self):
        return StatusCode.UNAUTHENTICATED

    def details(self):
        return "token revoked"


def test_quote_stream_fails_when_broker_invalidates_old_token(grpc_client):
    """Documents reactivation requirement if Finam closes streams on new Auth."""
    renewal_gate = threading.Event()
    _install_auth_mock(grpc_client)

    grpc_client.refresh_session()
    received: list[float] = []
    errors: list[BaseException] = []

    def _subscribe_quote(request, metadata):
        def _gen():
            yield _quote_event(100.0)
            renewal_gate.wait(timeout=3.0)
            raise _FakeRpcError()

        return _gen()

    grpc_client.marketdata_stub.SubscribeQuote = _subscribe_quote

    def _consume() -> None:
        try:
            stream = grpc_client.subscribe_quote([_QUOTE_SYMBOL])
            for event in stream:
                for quote in event.quote:
                    received.append(float(quote.last))
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=_consume, name="test-quote-stream-fail", daemon=True)
    worker.start()

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and not received:
        time.sleep(0.05)
    assert received == [100.0]

    grpc_client.refresh_session(force=True)
    renewal_gate.set()
    worker.join(timeout=3.0)

    assert errors
    assert isinstance(errors[0], RpcError)
    assert errors[0].code() == StatusCode.UNAUTHENTICATED
