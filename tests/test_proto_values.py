from decimal import Decimal
from types import SimpleNamespace

import pytest
from google.type import decimal_pb2

from finam_client.proto_values import (
    decimal_to_json,
    from_proto_decimal,
    optional_google_money,
    price_step_from_asset,
    proto_calendar_date_to_iso,
    timeframe_to_finam,
    timestamp_to_datetime,
    to_proto_decimal,
)


def test_decimal_roundtrip():
    value = to_proto_decimal(Decimal("12.3400"))
    assert value.value == "12.34"
    assert from_proto_decimal(value) == Decimal("12.34")
    assert from_proto_decimal(decimal_pb2.Decimal()) == Decimal(0)
    assert decimal_to_json(None) is None


def test_price_step_from_asset():
    assert price_step_from_asset(2, 5) == Decimal("0.05")
    with pytest.raises(ValueError):
        price_step_from_asset(-1, 1)


def test_optional_google_money():
    assert optional_google_money(SimpleNamespace(units=0, nanos=0)) is None
    assert optional_google_money(SimpleNamespace(units=10, nanos=500_000_000)) == Decimal("10.5")


def test_timestamp_and_calendar_date():
    assert timestamp_to_datetime(SimpleNamespace(seconds=0, nanos=0)) is None
    assert timestamp_to_datetime(SimpleNamespace(seconds=86400, nanos=0)).date().isoformat() == "1970-01-02"
    assert proto_calendar_date_to_iso(SimpleNamespace(year=2026, month=9, day=1)) == "2026-09-01"
    assert proto_calendar_date_to_iso(SimpleNamespace(year=2026, month=9, day=0)) == "2026-09"
    assert proto_calendar_date_to_iso(None) is None


def test_timeframes_share_enum_between_vocabularies():
    assert timeframe_to_finam("M60") == timeframe_to_finam("1h") == timeframe_to_finam("H1")
    assert timeframe_to_finam("D1") == timeframe_to_finam("1d")
    with pytest.raises(ValueError):
        timeframe_to_finam("10min")
