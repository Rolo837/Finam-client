"""Single re-export point for the Finam Trade API gRPC stubs.

The stubs are generated from the vendored proto/ into :mod:`finam_client.grpc_gen`
(see scripts/generate.py). The legacy module aliases (``orders_service``,
``assets_service``, ``side_pb``, the ``*ServiceStub`` classes) are kept so consumers import
from one place instead of the deep ``grpc_gen.grpc.tradeapi.v1.*`` paths.
"""
from __future__ import annotations

from finam_client.grpc_gen.grpc.tradeapi.v1 import side_pb2 as side_pb
from finam_client.grpc_gen.grpc.tradeapi.v1 import trade_pb2 as trade_pb
from finam_client.grpc_gen.grpc.tradeapi.v1.accounts import (
    accounts_service_pb2 as accounts_service,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.accounts import (
    accounts_service_pb2_grpc as accounts_service_grpc,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.assets import (
    assets_service_pb2 as assets_service,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.assets import (
    assets_service_pb2_grpc as assets_service_grpc,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.auth import (
    auth_service_pb2 as auth_service,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.auth import (
    auth_service_pb2_grpc as auth_service_grpc,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2 as marketdata_service,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2_grpc as marketdata_service_grpc,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.metrics import (
    usage_metrics_service_pb2 as usage_metrics_service,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.metrics import (
    usage_metrics_service_pb2_grpc as usage_metrics_service_grpc,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.orders import (
    orders_service_pb2 as orders_service,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.orders import (
    orders_service_pb2_grpc as orders_service_grpc,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.reports import (
    reports_service_pb2 as reports_service,
)
from finam_client.grpc_gen.grpc.tradeapi.v1.reports import (
    reports_service_pb2_grpc as reports_service_grpc,
)

AccountsServiceStub = accounts_service_grpc.AccountsServiceStub
AssetsServiceStub = assets_service_grpc.AssetsServiceStub
AuthServiceStub = auth_service_grpc.AuthServiceStub
MarketDataServiceStub = marketdata_service_grpc.MarketDataServiceStub
OrdersServiceStub = orders_service_grpc.OrdersServiceStub
ReportsServiceStub = reports_service_grpc.ReportsServiceStub
UsageMetricsServiceStub = usage_metrics_service_grpc.UsageMetricsServiceStub

__all__ = [
    "accounts_service",
    "assets_service",
    "auth_service",
    "marketdata_service",
    "orders_service",
    "reports_service",
    "usage_metrics_service",
    "side_pb",
    "trade_pb",
    "AccountsServiceStub",
    "AssetsServiceStub",
    "AuthServiceStub",
    "MarketDataServiceStub",
    "OrdersServiceStub",
    "ReportsServiceStub",
    "UsageMetricsServiceStub",
]
