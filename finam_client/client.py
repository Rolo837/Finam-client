from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from queue import SimpleQueue
from typing import Any, Callable, Iterator

from finam_client.grpc_imports import (
    AccountsServiceStub,
    AssetsServiceStub,
    AuthServiceStub,
    MarketDataServiceStub,
    OrdersServiceStub,
    ReportsServiceStub,
    UsageMetricsServiceStub,
    accounts_service,
    assets_service,
    auth_service,
    marketdata_service,
    orders_service,
    reports_service,
    usage_metrics_service,
)
from google.protobuf import timestamp_pb2
from google.type import interval_pb2
from grpc import RpcError, StatusCode, secure_channel, ssl_channel_credentials

from finam_client.config import ClientConfig, read_secret_file
from finam_client.errors import ErrorCategory, ErrorFactory, FinamError, default_error_factory
from finam_client.proto_values import timestamp_to_datetime
from finam_client.symbols import validate_finam_symbol

logger = logging.getLogger(__name__)

# Substrings (case-insensitive) in a Finam error detail that mean the
# rejection is specific to the opening-auction window, not a permanent
# rejection of the order itself — same pattern as finam_arena/rest_client.py's
# _classify_broker_code. Confirmed live: deal-d90e-4c2d-be3d's MARKET+DAY
# entry got "(14302) FOK и IOC заявки запрещены в аукционе открытия" and was
# cancelled outright — engine._is_transient_place_error didn't recognize the
# code (a plain INVALID_ARGUMENT) as retryable.
_RETRYABLE_CODES = frozenset(
    {StatusCode.UNAVAILABLE, StatusCode.DEADLINE_EXCEEDED, StatusCode.RESOURCE_EXHAUSTED}
)
_AUCTION_ONLY_MARKERS = ("(14302)", "аукцион", "auction")


def _classify_broker_code(detail: str) -> str | None:
    lowered = (detail or "").lower()
    if any(marker in lowered for marker in _AUCTION_ONLY_MARKERS):
        return "auction_only"
    return None


class FinamApiClient:
    """Thin wrapper over Finam Trade API gRPC methods."""

    # Fallback JWT TTL used only when TokenDetails after Auth doesn't return
    # expires_at — a fact about Finam's own token-issuing policy, not an
    # operator tuning knob (see config.GrpcClientConfig for the rest).
    JWT_TTL_SEC = 15 * 60

    @property
    def JWT_REFRESH_SKEW_SEC(self) -> float:
        return self._config.grpc_client.jwt_refresh_skew_sec

    @property
    def TIMEOUT_SEC(self) -> float:
        return self._config.grpc_client.timeout_sec

    @property
    def GRPC_MAX_ATTEMPTS(self) -> int:
        return self._config.grpc_client.max_attempts

    def _keepalive_channel_options(self) -> list[tuple[str, int]]:
        # Idle server-streaming subscriptions otherwise have no
        # application-level keepalive: a half-open TCP connection (dead
        # NAT/LB entry, no RST) can sit silent forever with no exception
        # raised. These PINGs force it to surface as an error so
        # StreamSupervisor can reconnect.
        grpc_cfg = self._config.grpc_client
        return [
            ("grpc.keepalive_time_ms", int(grpc_cfg.keepalive_time_sec * 1000)),
            ("grpc.keepalive_timeout_ms", int(grpc_cfg.keepalive_timeout_sec * 1000)),
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.max_pings_without_data", 0),
        ]

    def __init__(
        self,
        config: ClientConfig,
        secret: str | None = None,
        *,
        error_factory: ErrorFactory | None = None,
    ):
        self._config = config
        self._error_factory = error_factory or default_error_factory
        self._pace_lock = threading.Lock()
        self._pace_next = 0.0
        self._secret = secret or read_secret_file(config.secret_file)
        self._channel = None
        self._build_channel()
        self._jwt_token = ""
        self._jwt_issued = 0
        self._jwt_expires_at: datetime | None = None
        self._metadata: tuple[str, str] = ("authorization", "")
        self._renewal_thread: threading.Thread | None = None
        self._renewal_stop = threading.Event()
        self._jwt_fail_streak = 0
        # Фаза 3 (typed-swinging-newell.md): fired from the renewal thread
        # after a *successful* refresh_session() inside the background
        # worker — the signal the adapter uses to recreate the slow streams
        # (account/orders/trades) with the new token. Optional: unset when
        # nothing has registered (e.g. Arena's own client, or in tests).
        self._on_jwt_renewed: Callable[[], None] | None = None
        self._order_trade_queue: SimpleQueue[orders_service.OrderTradeRequest] = SimpleQueue()

    def _error(
        self,
        category: ErrorCategory,
        message: str,
        *,
        retryable: bool = False,
        broker_code: str | None = None,
    ) -> Exception:
        return self._error_factory(
            category, message, retryable=retryable, broker_code=broker_code
        )

    def _symbol(self, symbol: str) -> str:
        """Validate ticker@mic, raising through ``error_factory``."""
        try:
            return validate_finam_symbol(symbol)
        except FinamError as exc:
            raise self._error(
                exc.category,
                exc.message,
                retryable=exc.retryable,
                broker_code=exc.broker_code,
            ) from exc

    @property
    def jwt_fail_streak(self) -> int:
        return self._jwt_fail_streak

    def _build_channel(self) -> None:
        self._channel = secure_channel(
            self._config.endpoint,
            ssl_channel_credentials(),
            options=self._keepalive_channel_options(),
        )
        self.auth_stub = AuthServiceStub(self._channel)
        self.accounts_stub = AccountsServiceStub(self._channel)
        self.assets_stub = AssetsServiceStub(self._channel)
        self.orders_stub = OrdersServiceStub(self._channel)
        self.marketdata_stub = MarketDataServiceStub(self._channel)
        self.reports_stub = ReportsServiceStub(self._channel)
        self.usage_metrics_stub = UsageMetricsServiceStub(self._channel)

    def ensure_channel(self) -> None:
        """Re-create the gRPC channel and stubs if ``close()`` tore them down.

        ``close()``/``connect()`` cycle previously reused the same closed
        channel, so every RPC after a reconnect raised ``ValueError("... closed
        channel")`` forever. Call this before any RPC on the reconnect path.
        """
        if self._channel is not None:
            return
        self._build_channel()

    def _invalidate_jwt(self) -> None:
        self._jwt_token = ""
        self._jwt_issued = 0
        self._jwt_expires_at = None
        self._metadata = ("authorization", "")

    def _jwt_still_valid(self) -> bool:
        if not self._jwt_token:
            return False
        now = datetime.now(timezone.utc)
        if self._jwt_expires_at is not None:
            skew = timedelta(seconds=self.JWT_REFRESH_SKEW_SEC)
            return now < self._jwt_expires_at - skew
        return (now.timestamp() - self._jwt_issued) < (self.JWT_TTL_SEC - self.JWT_REFRESH_SKEW_SEC)

    def _load_expires_at_from_token_details(self) -> None:
        # TokenDetails authenticates via request body only — do NOT send
        # `authorization` metadata (HTTP Authorization). Finam proto/docs put
        # the JWT in TokenDetailsRequest.token; pairing it with the header is
        # rejected by the gateway (see AuthService.TokenDetails comments).
        if not self._jwt_token:
            return
        try:
            response, _ = self.auth_stub.TokenDetails.with_call(
                request=auth_service.TokenDetailsRequest(token=self._jwt_token),
                timeout=self.TIMEOUT_SEC,
            )
            expires = timestamp_to_datetime(response.expires_at)
            if expires is not None:
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                self._jwt_expires_at = expires.astimezone(timezone.utc)
                logger.debug("JWT expires_at=%s", self._jwt_expires_at.isoformat())
                return
        except RpcError as exc:
            logger.debug("TokenDetails after auth failed: %s", exc.details())
        except Exception as exc:
            logger.debug("TokenDetails after auth failed: %s", exc)
        self._jwt_expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.JWT_TTL_SEC - 120)

    def _refresh_jwt(self) -> None:
        now = datetime.now(timezone.utc)
        try:
            response, _ = self.auth_stub.Auth.with_call(
                request=auth_service.AuthRequest(secret=self._secret),
                timeout=self.TIMEOUT_SEC,
            )
        except RpcError as exc:
            retryable = exc.code() in {StatusCode.UNAVAILABLE, StatusCode.DEADLINE_EXCEEDED}
            raise self._error(
                ErrorCategory.AUTH,
                f"Auth failed: {exc.details()}",
                retryable=retryable,
            ) from exc
        self._jwt_token = response.token
        self._jwt_issued = int(now.timestamp())
        self._metadata = ("authorization", self._jwt_token)
        self._load_expires_at_from_token_details()
        logger.debug("JWT issued, expires_at=%s", self._jwt_expires_at)

    def refresh_session(self, *, force: bool = False) -> None:
        """Получить/обновить JWT до любых торговых gRPC-вызовов."""
        del force
        logger.debug("obtaining JWT via Auth")
        self._refresh_jwt()
        self._jwt_fail_streak = 0

    @property
    def jwt_expires_at(self) -> datetime | None:
        return self._jwt_expires_at

    def set_on_jwt_renewed(self, callback: Callable[[], None] | None) -> None:
        """Фаза 3 (typed-swinging-newell.md): register the hook fired after
        every successful ``refresh_session()`` inside the background renewal
        worker (see ``start_jwt_renewal_background``) — the adapter uses it
        to recreate the slow streams (account/orders/trades) with the fresh
        token. Called from the worker's own thread; the callback itself is
        responsible for crossing back into the asyncio loop if it needs to
        (see ``FinamBrokerAdapter.start_token_renewal``)."""
        self._on_jwt_renewed = callback

    def close(self) -> None:
        self.stop_jwt_renewal_background()
        if self._channel is not None:
            self._channel.close()
            self._channel = None

    def _ensure_jwt(self) -> None:
        if self._jwt_still_valid():
            return
        self._refresh_jwt()

    @staticmethod
    def _grpc_method_name(func) -> str:
        method = getattr(func, "_method", None)
        if method:
            return method.decode() if isinstance(method, bytes) else str(method)
        return getattr(func, "__name__", repr(func))

    @staticmethod
    def _request_log_params(request: Any) -> str:
        """Compact key=value summary of common unary request fields for debug.log."""
        parts: list[str] = []
        for attr in ("symbol", "account_id", "order_id", "client_order_id"):
            value = getattr(request, attr, None)
            if value:
                parts.append(f"{attr}={value}")
        symbols = getattr(request, "symbols", None)
        if symbols:
            try:
                parts.append(f"symbols={list(symbols)}")
            except TypeError:
                parts.append(f"symbols={symbols}")
        return " ".join(parts)

    def _pace(self) -> None:
        """Keep unary calls at least ``min_interval_sec`` apart (shared by all threads)."""
        interval = self._config.grpc_client.min_interval_sec
        if interval <= 0:
            return
        with self._pace_lock:
            now = time.monotonic()
            wait = max(0.0, self._pace_next - now)
            self._pace_next = max(now, self._pace_next) + interval
        if wait:
            time.sleep(wait)

    def _call(self, func, request: Any, *, idempotent: bool = True, auth_metadata: bool = True) -> Any:
        """Invoke a unary gRPC call with retry/backoff/re-auth.

        ``idempotent=False`` marks calls (order placement) where a retried
        DEADLINE_EXCEEDED/UNAVAILABLE could double-submit if the first
        attempt actually reached the broker: such calls never retry a
        transient failure and are always reported non-retryable, leaving
        reconciliation-by-client_order_id to the caller. UNAUTHENTICATED
        still retries either way — the request never reached the OMS if
        auth itself was rejected.

        ``auth_metadata=False`` omits the ``authorization`` gRPC metadata
        (HTTP Authorization). Required for TokenDetails: JWT goes only in
        the request body per Finam AuthService contract.
        """
        method = self._grpc_method_name(func)
        params = self._request_log_params(request)
        if params:
            logger.debug("gRPC call %s %s", method, params)
        else:
            logger.debug("gRPC call %s", method)
        last_exc: RpcError | None = None
        for attempt in range(self.GRPC_MAX_ATTEMPTS):
            self._pace()
            self._ensure_jwt()
            try:
                call_kwargs: dict[str, Any] = {
                    "request": request,
                    "timeout": self.TIMEOUT_SEC,
                }
                if auth_metadata:
                    call_kwargs["metadata"] = (self._metadata,)
                response, _ = func.with_call(**call_kwargs)
                logger.debug("gRPC ok %s", method)
                return response
            except RpcError as exc:
                last_exc = exc
                logger.debug("gRPC error %s code=%s details=%s", method, exc.code(), exc.details())
                if exc.code() == StatusCode.UNAUTHENTICATED and attempt < self.GRPC_MAX_ATTEMPTS - 1:
                    self._invalidate_jwt()
                    self._refresh_jwt()
                    continue
                if (
                    idempotent
                    and exc.code() in _RETRYABLE_CODES
                    and attempt < self.GRPC_MAX_ATTEMPTS - 1
                ):
                    # RESOURCE_EXHAUSTED = Finam's ~200 req/min limit; a sub-second
                    # backoff cannot outwait it.
                    base = (
                        self._config.grpc_client.rate_limit_backoff_sec
                        if exc.code() == StatusCode.RESOURCE_EXHAUSTED
                        else self._config.grpc_client.retry_base_sec
                    )
                    time.sleep(base * (attempt + 1))
                    continue
                retryable = idempotent and exc.code() in _RETRYABLE_CODES
                category = ErrorCategory.GRPC
                if exc.code() == StatusCode.UNAUTHENTICATED:
                    category = ErrorCategory.AUTH
                broker_code = exc.code().name
                if not idempotent and exc.code() == StatusCode.DEADLINE_EXCEEDED:
                    broker_code = "place_timeout"
                classified = _classify_broker_code(exc.details())
                if classified is not None:
                    broker_code = classified
                raise self._error(
                    category,
                    f"gRPC error: {exc.details()}",
                    retryable=retryable,
                    broker_code=broker_code,
                ) from exc
        if last_exc is not None:
            raise self._error(
                ErrorCategory.GRPC,
                f"gRPC error: {last_exc.details()}",
                retryable=False,
                broker_code=last_exc.code().name,
            ) from last_exc
        raise self._error(ErrorCategory.AUTH, "gRPC retry exhausted", retryable=False)

    # Auth
    def auth(self) -> auth_service.AuthResponse:
        logger.debug("gRPC Auth")
        self._refresh_jwt()
        return auth_service.AuthResponse(token=self._jwt_token)

    def token_details(self) -> auth_service.TokenDetailsResponse:
        self._ensure_jwt()
        return self._call(
            self.auth_stub.TokenDetails,
            auth_service.TokenDetailsRequest(token=self._jwt_token),
            auth_metadata=False,
        )

    def subscribe_jwt_renewal(self):
        """Стрим SubscribeJwtRenewal: в запросе только secret (см. Finam Trade API)."""
        logger.debug("gRPC stream SubscribeJwtRenewal")
        return self.auth_stub.SubscribeJwtRenewal(
            request=auth_service.SubscribeJwtRenewalRequest(secret=self._secret),
        )

    def start_jwt_renewal_background(self, interval_sec: int) -> None:
        if self._renewal_thread and self._renewal_thread.is_alive():
            return
        self._renewal_stop.clear()

        def _worker() -> None:
            logger.debug("JWT renewal worker started, interval=%ss", interval_sec)
            while not self._renewal_stop.is_set():
                logger.debug("JWT periodic renewal attempt")
                try:
                    self.refresh_session()
                except Exception as exc:
                    self._jwt_fail_streak += 1
                    logger.warning("JWT renewal failed: %s", exc)
                else:
                    # Фаза 3 (typed-swinging-newell.md): only a *successful*
                    # renewal signals the adapter to recreate the slow
                    # streams — a failed attempt leaves the old (still
                    # valid, not-yet-expired) token and streams in place.
                    if self._on_jwt_renewed is not None:
                        try:
                            self._on_jwt_renewed()
                        except Exception:
                            logger.exception("on_jwt_renewed callback failed")
                if self._renewal_stop.wait(interval_sec):
                    break
            logger.debug("JWT renewal worker stopped")

        self._renewal_thread = threading.Thread(target=_worker, name="finam-jwt-renewal", daemon=True)
        self._renewal_thread.start()

    def stop_jwt_renewal_background(self) -> None:
        self._renewal_stop.set()
        thread = self._renewal_thread
        if thread and thread.is_alive():
            thread.join(timeout=3.0)

    # Accounts
    def get_account(self, account_id: str) -> accounts_service.GetAccountResponse:
        return self._call(
            self.accounts_stub.GetAccount,
            accounts_service.GetAccountRequest(account_id=account_id),
        )

    def trades(
        self,
        account_id: str,
        start: datetime,
        end: datetime,
        limit: int = 50,
    ) -> accounts_service.TradesResponse:
        return self._call(
            self.accounts_stub.Trades,
            accounts_service.TradesRequest(
                account_id=account_id,
                limit=limit,
                interval=_interval(start, end),
            ),
        )

    def transactions(
        self,
        account_id: str,
        start: datetime,
        end: datetime,
        limit: int = 50,
    ) -> accounts_service.TransactionsResponse:
        return self._call(
            self.accounts_stub.Transactions,
            accounts_service.TransactionsRequest(
                account_id=account_id,
                limit=limit,
                interval=_interval(start, end),
            ),
        )

    def subscribe_account(self, account_id: str):
        logger.debug("gRPC stream SubscribeAccount account_id=%s", account_id)
        self._ensure_jwt()
        return self.accounts_stub.SubscribeAccount(
            request=accounts_service.GetAccountRequest(account_id=account_id),
            metadata=(self._metadata,),
        )

    # Orders
    def place_order(self, order: orders_service.Order) -> orders_service.OrderState:
        return self._call(self.orders_stub.PlaceOrder, order, idempotent=False)

    def cancel_order(self, account_id: str, order_id: str) -> orders_service.OrderState:
        return self._call(
            self.orders_stub.CancelOrder,
            orders_service.CancelOrderRequest(account_id=account_id, order_id=order_id),
        )

    def get_order(self, account_id: str, order_id: str) -> orders_service.OrderState:
        return self._call(
            self.orders_stub.GetOrder,
            orders_service.GetOrderRequest(account_id=account_id, order_id=order_id),
        )

    def get_orders(self, account_id: str) -> orders_service.OrdersResponse:
        return self._call(
            self.orders_stub.GetOrders,
            orders_service.OrdersRequest(account_id=account_id),
        )

    def place_sltp_order(self, order: orders_service.SLTPOrder) -> orders_service.OrderState:
        return self._call(self.orders_stub.PlaceSLTPOrder, order, idempotent=False)

    def _order_trade_request_iterator(self) -> Iterator[orders_service.OrderTradeRequest]:
        while True:
            yield self._order_trade_queue.get()

    def subscribe_order_trade_stream(self):
        """Open stream-stream SubscribeOrderTrade; enqueue subscribe before calling."""
        self._ensure_jwt()
        return self.orders_stub.SubscribeOrderTrade(
            request_iterator=self._order_trade_request_iterator(),
            metadata=(self._metadata,),
        )

    def subscribe_order_trade(
        self,
        account_id: str,
        *,
        orders: bool = True,
        trades: bool = True,
    ) -> None:
        if orders and trades:
            data_type = orders_service.OrderTradeRequest.DataType.DATA_TYPE_ALL
        elif orders:
            data_type = orders_service.OrderTradeRequest.DataType.DATA_TYPE_ORDERS
        else:
            data_type = orders_service.OrderTradeRequest.DataType.DATA_TYPE_TRADES
        self._order_trade_queue.put(
            orders_service.OrderTradeRequest(
                action=orders_service.OrderTradeRequest.Action.ACTION_SUBSCRIBE,
                data_type=data_type,
                account_id=account_id,
            )
        )

    def unsubscribe_order_trade(
        self,
        account_id: str,
        *,
        orders: bool = True,
        trades: bool = True,
    ) -> None:
        if orders and trades:
            data_type = orders_service.OrderTradeRequest.DataType.DATA_TYPE_ALL
        elif orders:
            data_type = orders_service.OrderTradeRequest.DataType.DATA_TYPE_ORDERS
        else:
            data_type = orders_service.OrderTradeRequest.DataType.DATA_TYPE_TRADES
        self._order_trade_queue.put(
            orders_service.OrderTradeRequest(
                action=orders_service.OrderTradeRequest.Action.ACTION_UNSUBSCRIBE,
                data_type=data_type,
                account_id=account_id,
            )
        )

    def subscribe_orders(self, account_id: str):
        self._ensure_jwt()
        logger.debug("gRPC stream SubscribeOrders account_id=%s", account_id)
        return self.orders_stub.SubscribeOrders(
            request=orders_service.SubscribeOrdersRequest(account_id=account_id),
            metadata=(self._metadata,),
        )

    def subscribe_trades(self, account_id: str):
        self._ensure_jwt()
        logger.debug("gRPC stream SubscribeTrades account_id=%s", account_id)
        return self.orders_stub.SubscribeTrades(
            request=orders_service.SubscribeTradesRequest(account_id=account_id),
            metadata=(self._metadata,),
        )

    # Market data
    def last_quote(self, symbol: str) -> marketdata_service.QuoteResponse:
        symbol = self._symbol(symbol)
        return self._call(
            self.marketdata_stub.LastQuote,
            marketdata_service.QuoteRequest(symbol=symbol),
        )

    def order_book(self, symbol: str) -> marketdata_service.OrderBookResponse:
        symbol = self._symbol(symbol)
        return self._call(
            self.marketdata_stub.OrderBook,
            marketdata_service.OrderBookRequest(symbol=symbol),
        )

    def bars(
        self,
        symbol: str,
        timeframe: marketdata_service.TimeFrame.ValueType,
        start: datetime,
        end: datetime,
    ) -> marketdata_service.BarsResponse:
        symbol = self._symbol(symbol)
        return self._call(
            self.marketdata_stub.Bars,
            marketdata_service.BarsRequest(
                symbol=symbol,
                timeframe=timeframe,
                interval=_interval(start, end),
            ),
        )

    def subscribe_quote(self, symbols: list[str]):
        validated = [self._symbol(item) for item in symbols]
        self._ensure_jwt()
        logger.debug("gRPC stream SubscribeQuote symbols=%s", validated)
        return self.marketdata_stub.SubscribeQuote(
            request=marketdata_service.SubscribeQuoteRequest(symbols=validated),
            metadata=(self._metadata,),
        )

    def subscribe_order_book(self, symbol: str):
        symbol = self._symbol(symbol)
        self._ensure_jwt()
        logger.debug("gRPC stream SubscribeOrderBook symbol=%s", symbol)
        return self.marketdata_stub.SubscribeOrderBook(
            request=marketdata_service.SubscribeOrderBookRequest(symbol=symbol),
            metadata=(self._metadata,),
        )

    def subscribe_bars(self, symbol: str, timeframe: marketdata_service.TimeFrame.ValueType):
        symbol = self._symbol(symbol)
        self._ensure_jwt()
        logger.debug("gRPC stream SubscribeBars symbol=%s timeframe=%s", symbol, timeframe)
        return self.marketdata_stub.SubscribeBars(
            request=marketdata_service.SubscribeBarsRequest(symbol=symbol, timeframe=timeframe),
            metadata=(self._metadata,),
        )

    def latest_trades(self, symbol: str) -> marketdata_service.LatestTradesResponse:
        """Unary snapshot of PUBLIC trades for `symbol` (not the account's
        own — see subscribe_trades for that). Фаза C: reserve fallback for
        MarketActivityTracker.is_trading, not consulted by any decision
        today — see BrokerPort.get_latest_trades."""
        symbol = self._symbol(symbol)
        return self._call(
            self.marketdata_stub.LatestTrades,
            marketdata_service.LatestTradesRequest(symbol=symbol),
        )

    # Assets
    def assets(self) -> assets_service.AssetsResponse:
        return self._call(self.assets_stub.Assets, assets_service.AssetsRequest())

    def all_assets(
        self,
        *,
        cursor: int = 0,
        only_active: bool = True,
    ) -> assets_service.AllAssetsResponse:
        """Одна страница AllAssets; для полного каталога — ``iter_all_assets``."""
        return self._call(
            self.assets_stub.AllAssets,
            assets_service.AllAssetsRequest(cursor=cursor, only_active=only_active),
        )

    def iter_all_assets(self, *, only_active: bool = True) -> Iterator[assets_service.Asset]:
        """Все инструменты AllAssets с пагинацией (cursor=0, далее next_cursor)."""
        cursor = 0
        while True:
            response = self.all_assets(cursor=cursor, only_active=only_active)
            yield from response.assets
            next_cursor = int(response.next_cursor)
            if next_cursor == 0 or next_cursor == cursor:
                break
            cursor = next_cursor

    def fetch_all_assets(self, *, only_active: bool = True) -> list[assets_service.Asset]:
        return list(self.iter_all_assets(only_active=only_active))

    def get_asset(self, symbol: str, account_id: str) -> assets_service.GetAssetResponse:
        symbol = self._symbol(symbol)
        return self._call(
            self.assets_stub.GetAsset,
            assets_service.GetAssetRequest(symbol=symbol, account_id=account_id),
        )

    def get_asset_params(self, symbol: str, account_id: str) -> assets_service.GetAssetParamsResponse:
        symbol = self._symbol(symbol)
        return self._call(
            self.assets_stub.GetAssetParams,
            assets_service.GetAssetParamsRequest(symbol=symbol, account_id=account_id),
        )

    def schedule(self, symbol: str) -> assets_service.ScheduleResponse:
        symbol = self._symbol(symbol)
        return self._call(
            self.assets_stub.Schedule,
            assets_service.ScheduleRequest(symbol=symbol),
        )

    def clock(self) -> assets_service.ClockResponse:
        return self._call(self.assets_stub.Clock, assets_service.ClockRequest())

    # Reports
    def create_account_report(self, request: reports_service.CreateAccountReportRequest):
        return self._call(self.reports_stub.CreateAccountReport, request)

    def get_account_report_info(self, request: reports_service.GetAccountReportInfoRequest):
        return self._call(self.reports_stub.GetAccountReportInfo, request)

    def subscribe_account_report_info(self, request: reports_service.SubscribeAccountReportInfoRequest):
        self._ensure_jwt()
        return self.reports_stub.SubscribeAccountReportInfo(
            request=request,
            metadata=(self._metadata,),
        )

    # Usage metrics
    def get_usage_metrics(self) -> usage_metrics_service.GetUsageMetricsResponse:
        return self._call(
            self.usage_metrics_stub.GetUsageMetrics,
            usage_metrics_service.GetUsageMetricsRequest(),
        )


def _interval(start: datetime, end: datetime) -> interval_pb2.Interval:
    return interval_pb2.Interval(
        start_time=_to_timestamp(start),
        end_time=_to_timestamp(end),
    )


def _to_timestamp(value: datetime) -> timestamp_pb2.Timestamp:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(value.astimezone(timezone.utc))
    return ts

