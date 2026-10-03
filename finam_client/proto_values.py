"""Proto value helpers: decimals, money, timestamps, calendar dates, timeframes.

Pure functions over protobuf messages; no consumer-domain types.
"""
from __future__ import annotations

from datetime import datetime, timezone

from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import Any

from google.type import decimal_pb2


def parse_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal(0)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid decimal value: {value!r}") from exc


def price_step_from_asset(decimals: int, min_step_raw: int) -> Decimal:
    if decimals < 0:
        raise ValueError("decimals must be non-negative")
    return Decimal(min_step_raw) / (Decimal(10) ** decimals)


def proto_decimal_set(value: decimal_pb2.Decimal | None) -> bool:
    return value is not None and hasattr(value, "value") and bool(value.value)


def from_proto_decimal(value: decimal_pb2.Decimal | None) -> Decimal:
    if not proto_decimal_set(value):
        return Decimal(0)
    return parse_decimal(value.value)


def from_google_money(money: Any) -> Decimal:
    """google.type.Money: units + nanos."""
    if money is None:
        return Decimal(0)
    units = int(getattr(money, "units", 0) or 0)
    nanos = int(getattr(money, "nanos", 0) or 0)
    return Decimal(units) + (Decimal(nanos) / Decimal(1_000_000_000))


def optional_google_money(money: Any) -> Decimal | None:
    if money is None:
        return None
    units = int(getattr(money, "units", 0) or 0)
    nanos = int(getattr(money, "nanos", 0) or 0)
    if not units and not nanos:
        return None
    return from_google_money(money)


def money_currency_code(money: Any) -> str:
    """google.type.Money.currency_code — the currency the amount is denominated in."""
    if money is None:
        return ""
    return str(getattr(money, "currency_code", "") or "").strip().upper()


def optional_proto_decimal(value: decimal_pb2.Decimal | None) -> Decimal | None:
    if not proto_decimal_set(value):
        return None
    return from_proto_decimal(value)


def sum_money_list(cash_field: Any) -> Decimal | None:
    """GetAccountResponse.cash — repeated google.type.Money."""
    if cash_field is None:
        return None
    if hasattr(cash_field, "value"):
        return optional_proto_decimal(cash_field)
    items = list(cash_field)
    if not items:
        return None
    return sum((from_google_money(item) for item in items), Decimal(0))


def money_list_by_currency(cash_field: Any) -> dict[str, Decimal]:
    """Aggregate repeated google.type.Money by currency code."""
    if cash_field is None:
        return {}
    if hasattr(cash_field, "value"):
        return {}
    result: dict[str, Decimal] = {}
    for item in cash_field:
        code = str(getattr(item, "currency_code", "") or "").strip().upper()
        if not code:
            continue
        result[code] = result.get(code, Decimal(0)) + from_google_money(item)
    return result


def to_proto_decimal(price: Decimal, decimals: int | None = None) -> decimal_pb2.Decimal:
    if decimals is not None:
        quantized = price.quantize(Decimal(10) ** -decimals)
        text = _decimal_to_str(quantized)
    else:
        text = _decimal_to_str(price)
    return decimal_pb2.Decimal(value=text or "0")


def _decimal_to_str(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def decimal_to_json(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_to_str(value)


def lots_from_proto(value: decimal_pb2.Decimal | None) -> int:
    return int(from_proto_decimal(value))


def timestamp_to_datetime(ts) -> datetime | None:
    if ts is None:
        return None
    seconds = getattr(ts, "seconds", None)
    if seconds is None:
        return None
    nanos = getattr(ts, "nanos", 0) or 0
    if not seconds and not nanos:
        return None
    return datetime.fromtimestamp(seconds + nanos / 1_000_000_000, tz=timezone.utc)


def proto_calendar_date_to_iso(value) -> str | None:
    """Finam Asset.expiration_date: google.type.Date (year/month/day), не Timestamp."""
    if value is None:
        return None
    year = int(getattr(value, "year", 0) or 0)
    month = int(getattr(value, "month", 0) or 0)
    day = int(getattr(value, "day", 0) or 0)
    if year:
        if month and day:
            return f"{year:04d}-{month:02d}-{day:02d}"
        if month:
            return f"{year:04d}-{month:02d}"
        return f"{year:04d}"
    ts = timestamp_to_datetime(value)
    return ts.date().isoformat() if ts else None


# Timeframe vocabulary shared by BF (``M1``..``D1``) and the condition wire
# format (``5min``..``1d``). "10min" has no native Finam bar and is absent.
def _timeframes():
    from finam_client.grpc_imports import marketdata_service as md

    tf = md.TimeFrame
    return {
        "M1": tf.TIME_FRAME_M1,
        "M5": tf.TIME_FRAME_M5,
        "M15": tf.TIME_FRAME_M15,
        "M30": tf.TIME_FRAME_M30,
        "M60": tf.TIME_FRAME_H1,
        "H1": tf.TIME_FRAME_H1,
        "H2": tf.TIME_FRAME_H2,
        "H4": tf.TIME_FRAME_H4,
        "D1": tf.TIME_FRAME_D,
        "5min": tf.TIME_FRAME_M5,
        "15min": tf.TIME_FRAME_M15,
        "30min": tf.TIME_FRAME_M30,
        "1h": tf.TIME_FRAME_H1,
        "2h": tf.TIME_FRAME_H2,
        "4h": tf.TIME_FRAME_H4,
        "1d": tf.TIME_FRAME_D,
    }


TIMEFRAME_MAP = _timeframes()


def timeframe_to_finam(timeframe: str):
    if timeframe not in TIMEFRAME_MAP:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return TIMEFRAME_MAP[timeframe]
