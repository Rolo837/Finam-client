"""Neutral dataclasses and mappers for Assets / MarketData responses.

They carry only what the broker returns; consumer-domain meaning (markets,
exchanges, catalog keys) is added by AFB/BF on top.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from finam_client.grpc_imports import assets_service
from finam_client.proto_values import (
    decimal_to_json,
    from_proto_decimal,
    money_currency_code,
    optional_google_money,
    price_step_from_asset,
    proto_calendar_date_to_iso,
    proto_decimal_set,
    timestamp_to_datetime,
)


@dataclass(frozen=True, slots=True)
class AssetListItem:
    """One row of Assets / AllAssets. Carries no board."""

    symbol: str
    id: str
    ticker: str
    mic: str
    isin: str
    type: str
    name: str
    is_archived: bool


@dataclass(frozen=True, slots=True)
class AssetInfo:
    """GetAsset: static instrument data. The only place that has ``board``."""

    symbol: str
    id: str
    ticker: str
    mic: str
    board: str
    isin: str
    type: str
    name: str
    decimals: int
    min_step_raw: int
    price_step: Decimal
    lot_size: Decimal
    quote_currency: str
    expiration_date: str | None
    future_details: dict | None
    option_details: dict | None
    bond_details: dict | None


@dataclass(frozen=True, slots=True)
class AssetParams:
    """GetAssetParams: dynamic trading flags and margins (per account)."""

    symbol: str
    account_id: str
    tradable: bool
    longable: bool
    shortable: bool
    long_risk_rate: Decimal | None
    short_risk_rate: Decimal | None
    long_initial_margin: Decimal | None
    short_initial_margin: Decimal | None
    margin_currency: str
    price_type: str


@dataclass(frozen=True, slots=True)
class Bar:
    timestamp: datetime | None
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


def asset_list_item_from_proto(asset) -> AssetListItem:
    return AssetListItem(
        symbol=str(asset.symbol),
        id=str(asset.id),
        ticker=str(asset.ticker),
        mic=str(asset.mic),
        isin=str(asset.isin),
        type=str(asset.type),
        name=str(asset.name),
        is_archived=bool(asset.is_archived),
    )


def _details(details, *, decimals=(), dates=(), strings=()) -> dict | None:
    if details is None or not getattr(details, "ListFields", lambda: [])():
        return None
    payload: dict = {}
    for name in decimals:
        value = getattr(details, name, None)
        if proto_decimal_set(value):
            payload[name] = decimal_to_json(from_proto_decimal(value))
    for name in dates:
        value = timestamp_to_datetime(getattr(details, name, None))
        if value is not None:
            payload[name] = value.date().isoformat()
    for name in strings:
        value = str(getattr(details, name, "") or "")
        if value:
            payload[name] = value
    return payload or None


def asset_info_from_proto(response, *, symbol: str | None = None) -> AssetInfo:
    decimals = int(response.decimals)
    min_step_raw = int(response.min_step)
    return AssetInfo(
        symbol=symbol or f"{response.ticker}@{response.mic}",
        id=str(response.id),
        ticker=str(response.ticker),
        mic=str(response.mic),
        board=str(response.board),
        isin=str(response.isin),
        type=str(response.type),
        name=str(response.name),
        decimals=decimals,
        min_step_raw=min_step_raw,
        price_step=price_step_from_asset(decimals, min_step_raw),
        lot_size=from_proto_decimal(response.lot_size),
        quote_currency=str(response.quote_currency),
        expiration_date=proto_calendar_date_to_iso(getattr(response, "expiration_date", None)),
        future_details=_details(
            response.future_details if response.HasField("future_details") else None,
            decimals=("contract_size",),
            dates=("expiration_date",),
        ),
        option_details=_details(
            response.option_details if response.HasField("option_details") else None,
            decimals=("contract_size", "strike"),
            dates=("expiration_date",),
        ),
        bond_details=_details(
            response.bond_details if response.HasField("bond_details") else None,
            decimals=("bond_face_value",),
            strings=("currency",),
        ),
    )


def asset_params_from_proto(response, account_id: str) -> AssetParams:
    return AssetParams(
        symbol=str(response.symbol),
        account_id=account_id,
        tradable=bool(getattr(response.is_tradable, "value", False)),
        longable=int(response.longable.value) in {assets_service.Longable.AVAILABLE},
        shortable=int(response.shortable.value)
        in {assets_service.Shortable.AVAILABLE, assets_service.Shortable.AVAILABLE_STRATEGY},
        long_risk_rate=from_proto_decimal(response.long_risk_rate)
        if proto_decimal_set(response.long_risk_rate)
        else None,
        short_risk_rate=from_proto_decimal(response.short_risk_rate)
        if proto_decimal_set(response.short_risk_rate)
        else None,
        long_initial_margin=optional_google_money(response.long_initial_margin),
        short_initial_margin=optional_google_money(response.short_initial_margin),
        margin_currency=(
            money_currency_code(response.long_initial_margin)
            or money_currency_code(response.short_initial_margin)
        ),
        price_type=assets_service.PriceType.Name(response.price_type),
    )


def bar_from_proto(bar) -> Bar:
    return Bar(
        timestamp=timestamp_to_datetime(bar.timestamp),
        open=from_proto_decimal(bar.open),
        high=from_proto_decimal(bar.high),
        low=from_proto_decimal(bar.low),
        close=from_proto_decimal(bar.close),
        volume=from_proto_decimal(bar.volume),
    )
