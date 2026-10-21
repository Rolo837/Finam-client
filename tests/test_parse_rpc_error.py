from __future__ import annotations

import pytest
from grpc import RpcError, StatusCode

from finam_client import parse_rpc_error
from finam_client.errors import RpcErrorFacts, parse_native_detail


class _Rpc(RpcError):
    def __init__(self, code, details):
        self._code, self._details = code, details

    def code(self):
        return self._code

    def details(self):
        return self._details


CASES = [
    (
        StatusCode.INVALID_ARGUMENT,
        "INVALID_ARGUMENT: [145]No enough coverage. You need 396726.50 RUR\x0cНедостаток обеспечения в сумме 396726.50 RUR",
        145,
        "No enough coverage. You need 396726.50 RUR\nНедостаток обеспечения в сумме 396726.50 RUR",
    ),
    (
        StatusCode.INVALID_ARGUMENT,
        "[90]NOTE: Wrong parameters\x0cВНИМАНИЕ! Неверно заданы параметры",
        90,
        "NOTE: Wrong parameters\nВНИМАНИЕ! Неверно заданы параметры",
    ),
    (
        StatusCode.INVALID_ARGUMENT,
        "(10003)Session is not available\x0cСейчас торги недоступны",
        10003,
        "Session is not available\nСейчас торги недоступны",
    ),
    (
        StatusCode.INVALID_ARGUMENT,
        "gRPC error: INVALID_ARGUMENT: (14302)FOK и IOC заявки запрещены в аукционе открытия",
        14302,
        "FOK и IOC заявки запрещены в аукционе открытия",
    ),
    (StatusCode.NOT_FOUND, "NOT_FOUND: Security not found", None, "Security not found"),
    (StatusCode.UNAUTHENTICATED, "Api token could not be verified", None, "Api token could not be verified"),
    (StatusCode.UNAVAILABLE, "Stream removed (Deadline Exceeded)", None, "Stream removed (Deadline Exceeded)"),
    (
        StatusCode.UNAVAILABLE,
        "failed to connect to all addresses; last error: UNKNOWN: ipv4:1.2.3.4:443: No route to host",
        None,
        "failed to connect to all addresses; last error: UNKNOWN: ipv4:1.2.3.4:443: No route to host",
    ),
    (
        StatusCode.UNAVAILABLE,
        "DNS resolution failed for api.finam.ru:443: C-ares status is not ARES_SUCCESS",
        None,
        "DNS resolution failed for api.finam.ru:443: C-ares status is not ARES_SUCCESS",
    ),
]


@pytest.mark.parametrize("code,detail,native_code,native_message", CASES)
def test_parse_rpc_error_table(code, detail, native_code, native_message):
    facts = parse_rpc_error(_Rpc(code, detail))
    assert facts == RpcErrorFacts(code.name, native_code, native_message, False)


def test_all_form_feed_segments_are_kept():
    _, message = parse_native_detail("[1]a\x0cb\x0cc")
    assert message == "a\nb\nc"


def test_unknown_prefix_is_not_stripped():
    assert parse_native_detail("FOO: bar") == (None, "FOO: bar")


def test_outcome_unknown_only_for_placement_timeout():
    exc = _Rpc(StatusCode.DEADLINE_EXCEEDED, "Deadline Exceeded")
    assert parse_rpc_error(exc, placement=True).outcome_unknown is True
    assert parse_rpc_error(exc).outcome_unknown is False
    assert parse_rpc_error(_Rpc(StatusCode.UNAVAILABLE, "x"), placement=True).outcome_unknown is False


def test_exception_without_code_or_details():
    facts = parse_rpc_error(RpcError("weird"))
    assert facts.grpc_status == "UNKNOWN"
    assert facts.native_message == "weird"
