from datetime import datetime, timezone
from decimal import Decimal

from google.protobuf import timestamp_pb2
from google.type import decimal_pb2, money_pb2

from finam_client.assets import (
    asset_info_from_proto,
    asset_list_item_from_proto,
    asset_params_from_proto,
    bar_from_proto,
)
from finam_client.grpc_imports import assets_service, marketdata_service


def test_list_item_has_no_board():
    item = asset_list_item_from_proto(
        assets_service.Asset(symbol="SBER@MISX", ticker="SBER", mic="MISX", type="EQUITIES", is_archived=True)
    )
    assert item.symbol == "SBER@MISX" and item.is_archived is True
    assert not hasattr(item, "board")


def test_asset_info_carries_board_and_future_details():
    expiry = timestamp_pb2.Timestamp()
    expiry.FromDatetime(datetime(2026, 12, 15, tzinfo=timezone.utc))
    response = assets_service.GetAssetResponse(
        board="FUT",
        ticker="CRZ6",
        mic="RTSX",
        type="FUTURES",
        decimals=3,
        min_step=1,
        lot_size=decimal_pb2.Decimal(value="1"),
        quote_currency="RUB",
        future_details=assets_service.GetAssetResponse.FutureDetails(
            expiration_date=expiry, contract_size=decimal_pb2.Decimal(value="1000")
        ),
    )
    info = asset_info_from_proto(response)
    assert (info.mic, info.board, info.ticker) == ("RTSX", "FUT", "CRZ6")
    assert info.symbol == "CRZ6@RTSX"
    assert info.price_step == Decimal("0.001")
    assert info.future_details == {"contract_size": "1000", "expiration_date": "2026-12-15"}
    assert info.option_details is None and info.bond_details is None


def test_asset_params_include_price_type():
    response = assets_service.GetAssetParamsResponse(
        symbol="SBER@MISX",
        long_initial_margin=money_pb2.Money(currency_code="RUB", units=100),
        price_type=assets_service.PriceType.NON_NEGATIVE,
    )
    params = asset_params_from_proto(response, "acc-1")
    assert params.price_type == "NON_NEGATIVE"
    assert params.long_initial_margin == Decimal(100)
    assert params.margin_currency == "RUB"
    assert params.tradable is False and params.longable is False


def test_bar_mapping():
    bar = marketdata_service.Bar(
        open=decimal_pb2.Decimal(value="1.5"),
        close=decimal_pb2.Decimal(value="2"),
        volume=decimal_pb2.Decimal(value="10"),
    )
    mapped = bar_from_proto(bar)
    assert mapped.open == Decimal("1.5") and mapped.volume == Decimal(10)
