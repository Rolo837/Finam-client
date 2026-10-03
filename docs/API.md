# API Finam-client

> Файл сгенерирован `scripts/generate_docs.py` из кода клиента и proto и не редактируется
> вручную. Как пользоваться - в [USAGE.md](USAGE.md); поля всех структур - в
> [STRUCTURES.md](STRUCTURES.md).

```python
from finam_client import ClientConfig, FinamApiClient

client = FinamApiClient(ClientConfig(secret_file="secrets/finam_ro.token"))
asset = client.get_asset("SBER@MISX", account_id)   # -> assets_service.GetAssetResponse
```

Методы возвращают **protobuf-сообщения** (как есть). Нейтральные модели в `finam_client.assets`
строятся из них мапперами (раздел «Нейтральные модели»). Все унарные вызовы повторяются при
`UNAVAILABLE`, `DEADLINE_EXCEEDED`, `RESOURCE_EXHAUSTED`, а при `UNAUTHENTICATED` перевыпускается
JWT; вызовы заявок (`place_order`, `place_sltp_order`) **не** повторяются. Ошибки приходят как
[`FinamError`](#ошибки).

## Содержание

| Метод | RPC | Тип | Повтор |
|---|---|---|---|
| [`token_details`](#token_details) | AuthService.TokenDetails | unary | да |
| [`subscribe_jwt_renewal`](#subscribe_jwt_renewal) | AuthService.SubscribeJwtRenewal | stream | - |
| [`get_account`](#get_account) | AccountsService.GetAccount | unary | да |
| [`trades`](#trades) | AccountsService.Trades | unary | да |
| [`transactions`](#transactions) | AccountsService.Transactions | unary | да |
| [`subscribe_account`](#subscribe_account) | AccountsService.SubscribeAccount | stream | - |
| [`assets`](#assets) | AssetsService.Assets | unary | да |
| [`all_assets`](#all_assets) | AssetsService.AllAssets | unary | да |
| [`iter_all_assets`](#iter_all_assets) | - | хелпер | - |
| [`fetch_all_assets`](#fetch_all_assets) | - | хелпер | - |
| [`get_asset`](#get_asset) | AssetsService.GetAsset | unary | да |
| [`get_asset_params`](#get_asset_params) | AssetsService.GetAssetParams | unary | да |
| [`schedule`](#schedule) | AssetsService.Schedule | unary | да |
| [`clock`](#clock) | AssetsService.Clock | unary | да |
| [`place_order`](#place_order) | OrdersService.PlaceOrder | unary | нет |
| [`cancel_order`](#cancel_order) | OrdersService.CancelOrder | unary | да |
| [`get_order`](#get_order) | OrdersService.GetOrder | unary | да |
| [`get_orders`](#get_orders) | OrdersService.GetOrders | unary | да |
| [`place_sltp_order`](#place_sltp_order) | OrdersService.PlaceSLTPOrder | unary | нет |
| [`subscribe_order_trade_stream`](#subscribe_order_trade_stream) | OrdersService.SubscribeOrderTrade | stream | - |
| [`subscribe_order_trade`](#subscribe_order_trade) | - | хелпер | - |
| [`unsubscribe_order_trade`](#unsubscribe_order_trade) | - | хелпер | - |
| [`subscribe_orders`](#subscribe_orders) | OrdersService.SubscribeOrders | stream | - |
| [`subscribe_trades`](#subscribe_trades) | OrdersService.SubscribeTrades | stream | - |
| [`last_quote`](#last_quote) | MarketDataService.LastQuote | unary | да |
| [`order_book`](#order_book) | MarketDataService.OrderBook | unary | да |
| [`bars`](#bars) | MarketDataService.Bars | unary | да |
| [`subscribe_quote`](#subscribe_quote) | MarketDataService.SubscribeQuote | stream | - |
| [`subscribe_order_book`](#subscribe_order_book) | MarketDataService.SubscribeOrderBook | stream | - |
| [`subscribe_bars`](#subscribe_bars) | MarketDataService.SubscribeBars | stream | - |
| [`latest_trades`](#latest_trades) | MarketDataService.LatestTrades | unary | да |
| [`create_account_report`](#create_account_report) | ReportsService.CreateAccountReport | unary | да |
| [`get_account_report_info`](#get_account_report_info) | ReportsService.GetAccountReportInfo | unary | да |
| [`subscribe_account_report_info`](#subscribe_account_report_info) | ReportsService.SubscribeAccountReportInfo | stream | - |
| [`get_usage_metrics`](#get_usage_metrics) | UsageMetricsService.GetUsageMetrics | unary | да |

## Auth - сессия и токен

<a id="token_details"></a>
### `token_details`

```python
token_details() -> auth_service.TokenDetailsResponse
```

- **RPC:** `AuthService.TokenDetails` (unary)
- **Запрос:** [`auth.TokenDetailsRequest`](STRUCTURES.md#auth-tokendetailsrequest)
- **Ответ:** [`auth.TokenDetailsResponse`](STRUCTURES.md#auth-tokendetailsresponse)
- **Повтор при ошибках транспорта:** да

Получение информации о токене сессии

Информация о токене: срок действия, права рыночных данных, счета, признак `readonly`. JWT передаётся в теле запроса, без заголовка `authorization`.

**Поля запроса** `auth.TokenDetailsRequest`

| Поле | Тип | Описание |
|---|---|---|
| `token` | `string` | JWT-токен |

**Поля ответа** `auth.TokenDetailsResponse`

| Поле | Тип | Описание |
|---|---|---|
| `created_at` | `Timestamp` | Дата и время создания |
| `expires_at` | `Timestamp` | Дата и время экспирации |
| `md_permissions` | список [`auth.MDPermission`](STRUCTURES.md#auth-mdpermission) | Информация о доступе к рыночным данным |
| `account_ids` | список `string` | Идентификаторы аккаунтов |
| `readonly` | `bool` | Сессия и торговые счета в токене будут помечены readonly |

<a id="subscribe_jwt_renewal"></a>
### `subscribe_jwt_renewal`

```python
subscribe_jwt_renewal()
```

- **RPC:** `AuthService.SubscribeJwtRenewal` (server-stream)
- **Запрос:** [`auth.SubscribeJwtRenewalRequest`](STRUCTURES.md#auth-subscribejwtrenewalrequest)
- **Ответ:** [`auth.SubscribeJwtRenewalResponse`](STRUCTURES.md#auth-subscribejwtrenewalresponse) (поток сообщений)
- **Повтор при ошибках транспорта:** нет

Подписка на обновление JWT токена. Стрим метод

Стрим SubscribeJwtRenewal: в запросе только secret (см. Finam Trade API).

**Поля запроса** `auth.SubscribeJwtRenewalRequest`

| Поле | Тип | Описание |
|---|---|---|
| `secret` | `string` | API токен (secret key) |
| `source_app_id` | `string` | Идентификатор приложения-источника запроса |

**Поля ответа** `auth.SubscribeJwtRenewalResponse` (приходит потоком сообщений)

| Поле | Тип | Описание |
|---|---|---|
| `token` | `string` | Полученный JWT-токен |

## Accounts - счета, сделки, транзакции

<a id="get_account"></a>
### `get_account`

```python
get_account(account_id: str) -> accounts_service.GetAccountResponse
```

- **RPC:** `AccountsService.GetAccount` (unary)
- **Запрос:** [`accounts.GetAccountRequest`](STRUCTURES.md#accounts-getaccountrequest)
- **Ответ:** [`accounts.GetAccountResponse`](STRUCTURES.md#accounts-getaccountresponse)
- **Повтор при ошибках транспорта:** да

Получение информации по конкретному аккаунту

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |

**Поля запроса** `accounts.GetAccountRequest`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |

**Поля ответа** `accounts.GetAccountResponse`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |
| `type` | `string` | Тип аккаунта |
| `status` | `string` | Статус аккаунта |
| `equity` | `Decimal` | Доступные средства плюс стоимость открытых позиций |
| `unrealized_profit` | `Decimal` | Нереализованная прибыль |
| `positions` | список [`accounts.Position`](STRUCTURES.md#accounts-position) | Позиции. Открытые, плюс теоретические (по неисполненным активным заявкам) |
| `cash` | список `Money` | Сумма собственных денежных средств на счете, доступная для торговли. Не включает маржинальные средства. |
| `portfolio_mc` | [`accounts.MC`](STRUCTURES.md#accounts-mc) | Общий тип для счетов Московской Биржи. Включает в себя как единые, так и моно счета. |
| `portfolio_mct` | [`accounts.MCT`](STRUCTURES.md#accounts-mct) | Тип портфеля для счетов на американских рынках. |
| `portfolio_forts` | [`accounts.FORTS`](STRUCTURES.md#accounts-forts) | Тип портфеля для торговли на срочном рынке Московской Биржи. |
| `open_account_date` | `Timestamp` | Дата открытия счета |
| `first_trade_date` | `Timestamp` | Дата первой торговой транзакции |
| `first_non_trade_date` | `Timestamp` | Дата первой неторговой транзакции |

<a id="trades"></a>
### `trades`

```python
trades(account_id: str, start: datetime, end: datetime, limit: int=50) -> accounts_service.TradesResponse
```

- **RPC:** `AccountsService.Trades` (unary)
- **Запрос:** [`accounts.TradesRequest`](STRUCTURES.md#accounts-tradesrequest)
- **Ответ:** [`accounts.TradesResponse`](STRUCTURES.md#accounts-tradesresponse)
- **Повтор при ошибках транспорта:** да

Получение истории по сделкам аккаунта

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |
| `start` | `datetime` |  |
| `end` | `datetime` |  |
| `limit` | `int` | `50` |

**Поля запроса** `accounts.TradesRequest`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |
| `limit` | `int32` | Лимит количества сделок |
| `interval` | `Interval` | Начало и окончание запрашиваемого периода, Unix epoch time |

**Поля ответа** `accounts.TradesResponse`

| Поле | Тип | Описание |
|---|---|---|
| `trades` | список [`AccountTrade`](STRUCTURES.md#accounttrade) | Сделки по аккаунту |

<a id="transactions"></a>
### `transactions`

```python
transactions(account_id: str, start: datetime, end: datetime, limit: int=50) -> accounts_service.TransactionsResponse
```

- **RPC:** `AccountsService.Transactions` (unary)
- **Запрос:** [`accounts.TransactionsRequest`](STRUCTURES.md#accounts-transactionsrequest)
- **Ответ:** [`accounts.TransactionsResponse`](STRUCTURES.md#accounts-transactionsresponse)
- **Повтор при ошибках транспорта:** да

Получение списка транзакций аккаунта

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |
| `start` | `datetime` |  |
| `end` | `datetime` |  |
| `limit` | `int` | `50` |

**Поля запроса** `accounts.TransactionsRequest`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |
| `limit` | `int32` | Лимит количества транзакций |
| `interval` | `Interval` | Начало и окончание запрашиваемого периода, Unix epoch time |

**Поля ответа** `accounts.TransactionsResponse`

| Поле | Тип | Описание |
|---|---|---|
| `transactions` | список [`accounts.Transaction`](STRUCTURES.md#accounts-transaction) | Транзакции по аккаунту |

<a id="subscribe_account"></a>
### `subscribe_account`

```python
subscribe_account(account_id: str)
```

- **RPC:** `AccountsService.SubscribeAccount` (server-stream)
- **Запрос:** [`accounts.GetAccountRequest`](STRUCTURES.md#accounts-getaccountrequest)
- **Ответ:** [`accounts.GetAccountResponse`](STRUCTURES.md#accounts-getaccountresponse) (поток сообщений)
- **Повтор при ошибках транспорта:** нет

Подписка на информацию по аккаунту. Стрим метод

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |

**Поля запроса** `accounts.GetAccountRequest`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |

**Поля ответа** `accounts.GetAccountResponse` (приходит потоком сообщений)

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |
| `type` | `string` | Тип аккаунта |
| `status` | `string` | Статус аккаунта |
| `equity` | `Decimal` | Доступные средства плюс стоимость открытых позиций |
| `unrealized_profit` | `Decimal` | Нереализованная прибыль |
| `positions` | список [`accounts.Position`](STRUCTURES.md#accounts-position) | Позиции. Открытые, плюс теоретические (по неисполненным активным заявкам) |
| `cash` | список `Money` | Сумма собственных денежных средств на счете, доступная для торговли. Не включает маржинальные средства. |
| `portfolio_mc` | [`accounts.MC`](STRUCTURES.md#accounts-mc) | Общий тип для счетов Московской Биржи. Включает в себя как единые, так и моно счета. |
| `portfolio_mct` | [`accounts.MCT`](STRUCTURES.md#accounts-mct) | Тип портфеля для счетов на американских рынках. |
| `portfolio_forts` | [`accounts.FORTS`](STRUCTURES.md#accounts-forts) | Тип портфеля для торговли на срочном рынке Московской Биржи. |
| `open_account_date` | `Timestamp` | Дата открытия счета |
| `first_trade_date` | `Timestamp` | Дата первой торговой транзакции |
| `first_non_trade_date` | `Timestamp` | Дата первой неторговой транзакции |

## Assets - каталог инструментов

<a id="assets"></a>
### `assets`

```python
assets() -> assets_service.AssetsResponse
```

- **RPC:** `AssetsService.Assets` (unary)
- **Запрос:** [`assets.AssetsRequest`](STRUCTURES.md#assets-assetsrequest)
- **Ответ:** [`assets.AssetsResponse`](STRUCTURES.md#assets-assetsresponse)
- **Повтор при ошибках транспорта:** да

Получение списка доступных для торговли инструментов, их описание

**Поля запроса** `assets.AssetsRequest`

_Поля отсутствуют._

**Поля ответа** `assets.AssetsResponse`

| Поле | Тип | Описание |
|---|---|---|
| `assets` | список [`assets.Asset`](STRUCTURES.md#assets-asset) | Информация об инструменте |

<a id="all_assets"></a>
### `all_assets`

```python
all_assets(*, cursor: int=0, only_active: bool=True) -> assets_service.AllAssetsResponse
```

- **RPC:** `AssetsService.AllAssets` (unary)
- **Запрос:** [`assets.AllAssetsRequest`](STRUCTURES.md#assets-allassetsrequest)
- **Ответ:** [`assets.AllAssetsResponse`](STRUCTURES.md#assets-allassetsresponse)
- **Повтор при ошибках транспорта:** да

Получение списка всех инструментов, в том числе индикативных и архивных, их описание

Одна страница AllAssets; для полного каталога — ``iter_all_assets``.

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `cursor` | `int` | `0` |
| `only_active` | `bool` | `True` |

**Поля запроса** `assets.AllAssetsRequest`

| Поле | Тип | Описание |
|---|---|---|
| `cursor` | `int64` | Курсор для пагинации. Указывает sec_id инструмента, с которого должен начинаться список. Для первого запроса оставьте поле пустым (значение 0). Для последующих запросов используйте значение next_cursor из предыдущего ответа. |
| `only_active` | `bool` | Фильтрация по статусу инструмента: выбираются только активные(неархивные) инструменты По умолчанию: false. |
| `only_disabled` | `bool` | Фильтрация по статусу инструмента: выбираются только неактивные(архивные) инструменты По умолчанию: false. |

**Поля ответа** `assets.AllAssetsResponse`

| Поле | Тип | Описание |
|---|---|---|
| `assets` | список [`assets.Asset`](STRUCTURES.md#assets-asset) | Часть списка инструментов |
| `next_cursor` | `int64` | Курсор для получения следующей страницы. Содержит sec_id последнего инструмента в текущем списке. Передайте это значение в поле cursor следующего запроса, чтобы получить следующую часть данных. Если значение 0 или отсутствует — это последняя страница. |

<a id="iter_all_assets"></a>
### `iter_all_assets`

```python
iter_all_assets(*, only_active: bool=True) -> Iterator[assets_service.Asset]
```

Все инструменты AllAssets с пагинацией (cursor=0, далее next_cursor).

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `only_active` | `bool` | `True` |

<a id="fetch_all_assets"></a>
### `fetch_all_assets`

```python
fetch_all_assets(*, only_active: bool=True) -> list[assets_service.Asset]
```

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `only_active` | `bool` | `True` |

<a id="get_asset"></a>
### `get_asset`

```python
get_asset(symbol: str, account_id: str) -> assets_service.GetAssetResponse
```

- **RPC:** `AssetsService.GetAsset` (unary)
- **Запрос:** [`assets.GetAssetRequest`](STRUCTURES.md#assets-getassetrequest)
- **Ответ:** [`assets.GetAssetResponse`](STRUCTURES.md#assets-getassetresponse)
- **Повтор при ошибках транспорта:** да

Получение информации по конкретному инструменту

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbol` | `str` |  |
| `account_id` | `str` |  |

**Поля запроса** `assets.GetAssetRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `account_id` | `string` | ID аккаунта для которого будет подбираться информация по инструменту |

**Поля ответа** `assets.GetAssetResponse`

| Поле | Тип | Описание |
|---|---|---|
| `board` | `string` | Код режима торгов |
| `id` | `string` | Идентификатор инструмента |
| `ticker` | `string` | Тикер инструмента |
| `mic` | `string` | mic идентификатор биржи |
| `isin` | `string` | Isin идентификатор инструмента |
| `type` | `string` | Тип инструмента |
| `name` | `string` | Наименование инструмента |
| `decimals` | `int32` | Кол-во десятичных знаков в цене |
| `min_step` | `int64` | Минимальный шаг цены. Для расчета финального ценового шага: min_step/(10ˆdecimals) |
| `lot_size` | `Decimal` | Кол-во штук в лоте |
| `expiration_date` | `Date` | Дата экспирации фьючерса |
| `quote_currency` | `string` | Валюта котировки, может не совпадать с валютой режима торгов инструмента |
| `future_details` | [`assets.GetAssetResponse.FutureDetails`](STRUCTURES.md#assets-getassetresponse-futuredetails) | Специфичные параметры для инструмента типа "Фьючерс" |
| `option_details` | [`assets.GetAssetResponse.OptionDetails`](STRUCTURES.md#assets-getassetresponse-optiondetails) | Специфичные параметры для инструмента типа "Опцион" |
| `bond_details` | [`assets.GetAssetResponse.BondDetails`](STRUCTURES.md#assets-getassetresponse-bonddetails) | Специфичные параметры для инструмента типа "Облигация" |

<a id="get_asset_params"></a>
### `get_asset_params`

```python
get_asset_params(symbol: str, account_id: str) -> assets_service.GetAssetParamsResponse
```

- **RPC:** `AssetsService.GetAssetParams` (unary)
- **Запрос:** [`assets.GetAssetParamsRequest`](STRUCTURES.md#assets-getassetparamsrequest)
- **Ответ:** [`assets.GetAssetParamsResponse`](STRUCTURES.md#assets-getassetparamsresponse)
- **Повтор при ошибках транспорта:** да

Получение торговых параметров по инструменту

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbol` | `str` |  |
| `account_id` | `str` |  |

**Поля запроса** `assets.GetAssetParamsRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `account_id` | `string` | ID аккаунта для которого будут подбираться торговые параметры |

**Поля ответа** `assets.GetAssetParamsResponse`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `account_id` | `string` | ID аккаунта для которого подбираются торговые параметры |
| `tradeable` | `bool` | Доступны ли торговые операции Старое поле, помечено как устаревшее. Клиентам следует перейти на is_tradeable. |
| `longable` | [`assets.Longable`](STRUCTURES.md#assets-longable) | Доступны ли операции в Лонг |
| `shortable` | [`assets.Shortable`](STRUCTURES.md#assets-shortable) | Доступны ли операции в Шорт |
| `long_risk_rate` | `Decimal` | Ставка риска для операции в Лонг |
| `long_collateral` | `Money` | Сумма обеспечения для поддержания позиции Лонг |
| `short_risk_rate` | `Decimal` | Ставка риска для операции в Шорт |
| `short_collateral` | `Money` | Сумма обеспечения для поддержания позиции Шорт |
| `long_initial_margin` | `Money` | Начальные требования, сколько на счету должно быть свободных денежных средств, чтобы открыть лонг позицию, для FORTS счетов равен биржевому ГО |
| `short_initial_margin` | `Money` | Начальные требования, сколько на счету должно быть свободных денежных средств, чтобы открыть шорт позицию, для FORTS счетов равен биржевому ГО |
| `is_tradable` | `BoolValue` | Доступны ли торговые операции Новое поле. Позволяет различать false и "не установлено". |
| `price_type` | [`assets.PriceType`](STRUCTURES.md#assets-pricetype) | Допустимая цена. Помогает определить можно ли выставлять ордера с отрицательной ценой для финансового инструмента |
| `trade_lot_size` | `int64` | Размер лота инструмента для торговых операций. Если поле равно 0 - значение отсутствует |

<a id="schedule"></a>
### `schedule`

```python
schedule(symbol: str) -> assets_service.ScheduleResponse
```

- **RPC:** `AssetsService.Schedule` (unary)
- **Запрос:** [`assets.ScheduleRequest`](STRUCTURES.md#assets-schedulerequest)
- **Ответ:** [`assets.ScheduleResponse`](STRUCTURES.md#assets-scheduleresponse)
- **Повтор при ошибках транспорта:** да

Получение расписания торгов для инструмента

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbol` | `str` |  |

**Поля запроса** `assets.ScheduleRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |

**Поля ответа** `assets.ScheduleResponse`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `sessions` | список [`assets.ScheduleResponse.Sessions`](STRUCTURES.md#assets-scheduleresponse-sessions) | Сессии инструмента |

<a id="clock"></a>
### `clock`

```python
clock() -> assets_service.ClockResponse
```

- **RPC:** `AssetsService.Clock` (unary)
- **Запрос:** [`assets.ClockRequest`](STRUCTURES.md#assets-clockrequest)
- **Ответ:** [`assets.ClockResponse`](STRUCTURES.md#assets-clockresponse)
- **Повтор при ошибках транспорта:** да

Получение времени на сервере

**Поля запроса** `assets.ClockRequest`

_Поля отсутствуют._

**Поля ответа** `assets.ClockResponse`

| Поле | Тип | Описание |
|---|---|---|
| `timestamp` | `Timestamp` | Метка времени |

## Orders - заявки

<a id="place_order"></a>
### `place_order`

```python
place_order(order: orders_service.Order) -> orders_service.OrderState
```

- **RPC:** `OrdersService.PlaceOrder` (unary)
- **Запрос:** [`orders.Order`](STRUCTURES.md#orders-order)
- **Ответ:** [`orders.OrderState`](STRUCTURES.md#orders-orderstate)
- **Повтор при ошибках транспорта:** нет

Выставление биржевой заявки

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `order` | `orders_service.Order` |  |

**Поля запроса** `orders.Order`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |
| `symbol` | `string` | Символ инструмента |
| `quantity` | `Decimal` | Количество в шт. |
| `side` | [`Side`](STRUCTURES.md#side) | Сторона (long или short) |
| `type` | [`orders.OrderType`](STRUCTURES.md#orders-ordertype) | Тип заявки |
| `time_in_force` | [`orders.TimeInForce`](STRUCTURES.md#orders-timeinforce) | Срок действия заявки |
| `limit_price` | `Decimal` | Необходимо для лимитной и стоп лимитной заявки |
| `stop_price` | `Decimal` | Необходимо для стоп рыночной и стоп лимитной заявки |
| `stop_condition` | [`orders.StopCondition`](STRUCTURES.md#orders-stopcondition) | Необходимо для стоп рыночной и стоп лимитной заявки |
| `legs` | список [`orders.Leg`](STRUCTURES.md#orders-leg) | Необходимо для мульти лег заявки |
| `client_order_id` | `string` | Уникальный идентификатор заявки. Автоматически генерируется, если не отправлен. (максимум 20 символов) |
| `valid_before` | [`orders.ValidBefore`](STRUCTURES.md#orders-validbefore) | Срок действия условной заявки. Заполняется для заявок с типом ORDER_TYPE_STOP, ORDER_TYPE_STOP_LIMIT |
| `comment` | `string` | Метка заявки. (максимум 128 символов) |

**Поля ответа** `orders.OrderState`

| Поле | Тип | Описание |
|---|---|---|
| `order_id` | `string` | Идентификатор заявки |
| `exec_id` | `string` | Идентификатор исполнения |
| `status` | [`orders.OrderStatus`](STRUCTURES.md#orders-orderstatus) | Статус заявки |
| `order` | [`orders.Order`](STRUCTURES.md#orders-order) | Заявка |
| `transact_at` | `Timestamp` | Дата и время выставления заявки |
| `accept_at` | `Timestamp` | Дата и время принятия заявки |
| `withdraw_at` | `Timestamp` | Дата и время  отмены заявки |
| `initial_quantity` | `Decimal` | Начальный объем (заполняется только для биржевой заявки) |
| `executed_quantity` | `Decimal` | Исполненный объем (заполняется только для биржевой заявки) |
| `remaining_quantity` | `Decimal` | Оставшийся объем (заполняется только для биржевой заявки) |
| `sltp_order` | [`orders.SLTPOrder`](STRUCTURES.md#orders-sltporder) | Информация о SL/TP заявке |
| `triggered_order_id` | `string` | Идентификатор биржевой заявки, порожденной в результате срабатывания условия или достижения стоп-цены. |
| `status_description` | `StringValue` | Описание статуса заявки |

<a id="cancel_order"></a>
### `cancel_order`

```python
cancel_order(account_id: str, order_id: str) -> orders_service.OrderState
```

- **RPC:** `OrdersService.CancelOrder` (unary)
- **Запрос:** [`orders.CancelOrderRequest`](STRUCTURES.md#orders-cancelorderrequest)
- **Ответ:** [`orders.OrderState`](STRUCTURES.md#orders-orderstate)
- **Повтор при ошибках транспорта:** да

Отмена биржевой заявки

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |
| `order_id` | `str` |  |

**Поля запроса** `orders.CancelOrderRequest`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |
| `order_id` | `string` | Идентификатор заявки |

**Поля ответа** `orders.OrderState`

| Поле | Тип | Описание |
|---|---|---|
| `order_id` | `string` | Идентификатор заявки |
| `exec_id` | `string` | Идентификатор исполнения |
| `status` | [`orders.OrderStatus`](STRUCTURES.md#orders-orderstatus) | Статус заявки |
| `order` | [`orders.Order`](STRUCTURES.md#orders-order) | Заявка |
| `transact_at` | `Timestamp` | Дата и время выставления заявки |
| `accept_at` | `Timestamp` | Дата и время принятия заявки |
| `withdraw_at` | `Timestamp` | Дата и время  отмены заявки |
| `initial_quantity` | `Decimal` | Начальный объем (заполняется только для биржевой заявки) |
| `executed_quantity` | `Decimal` | Исполненный объем (заполняется только для биржевой заявки) |
| `remaining_quantity` | `Decimal` | Оставшийся объем (заполняется только для биржевой заявки) |
| `sltp_order` | [`orders.SLTPOrder`](STRUCTURES.md#orders-sltporder) | Информация о SL/TP заявке |
| `triggered_order_id` | `string` | Идентификатор биржевой заявки, порожденной в результате срабатывания условия или достижения стоп-цены. |
| `status_description` | `StringValue` | Описание статуса заявки |

<a id="get_order"></a>
### `get_order`

```python
get_order(account_id: str, order_id: str) -> orders_service.OrderState
```

- **RPC:** `OrdersService.GetOrder` (unary)
- **Запрос:** [`orders.GetOrderRequest`](STRUCTURES.md#orders-getorderrequest)
- **Ответ:** [`orders.OrderState`](STRUCTURES.md#orders-orderstate)
- **Повтор при ошибках транспорта:** да

Получение информации о конкретном ордере

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |
| `order_id` | `str` |  |

**Поля запроса** `orders.GetOrderRequest`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |
| `order_id` | `string` | Идентификатор заявки |

**Поля ответа** `orders.OrderState`

| Поле | Тип | Описание |
|---|---|---|
| `order_id` | `string` | Идентификатор заявки |
| `exec_id` | `string` | Идентификатор исполнения |
| `status` | [`orders.OrderStatus`](STRUCTURES.md#orders-orderstatus) | Статус заявки |
| `order` | [`orders.Order`](STRUCTURES.md#orders-order) | Заявка |
| `transact_at` | `Timestamp` | Дата и время выставления заявки |
| `accept_at` | `Timestamp` | Дата и время принятия заявки |
| `withdraw_at` | `Timestamp` | Дата и время  отмены заявки |
| `initial_quantity` | `Decimal` | Начальный объем (заполняется только для биржевой заявки) |
| `executed_quantity` | `Decimal` | Исполненный объем (заполняется только для биржевой заявки) |
| `remaining_quantity` | `Decimal` | Оставшийся объем (заполняется только для биржевой заявки) |
| `sltp_order` | [`orders.SLTPOrder`](STRUCTURES.md#orders-sltporder) | Информация о SL/TP заявке |
| `triggered_order_id` | `string` | Идентификатор биржевой заявки, порожденной в результате срабатывания условия или достижения стоп-цены. |
| `status_description` | `StringValue` | Описание статуса заявки |

<a id="get_orders"></a>
### `get_orders`

```python
get_orders(account_id: str) -> orders_service.OrdersResponse
```

- **RPC:** `OrdersService.GetOrders` (unary)
- **Запрос:** [`orders.OrdersRequest`](STRUCTURES.md#orders-ordersrequest)
- **Ответ:** [`orders.OrdersResponse`](STRUCTURES.md#orders-ordersresponse)
- **Повтор при ошибках транспорта:** да

Получение списка заявок для аккаунта

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |

**Поля запроса** `orders.OrdersRequest`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |

**Поля ответа** `orders.OrdersResponse`

| Поле | Тип | Описание |
|---|---|---|
| `orders` | список [`orders.OrderState`](STRUCTURES.md#orders-orderstate) | Заявки |

<a id="place_sltp_order"></a>
### `place_sltp_order`

```python
place_sltp_order(order: orders_service.SLTPOrder) -> orders_service.OrderState
```

- **RPC:** `OrdersService.PlaceSLTPOrder` (unary)
- **Запрос:** [`orders.SLTPOrder`](STRUCTURES.md#orders-sltporder)
- **Ответ:** [`orders.OrderState`](STRUCTURES.md#orders-orderstate)
- **Повтор при ошибках транспорта:** нет

Выставление SL/TP заявки

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `order` | `orders_service.SLTPOrder` |  |

**Поля запроса** `orders.SLTPOrder`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |
| `symbol` | `string` | Символ инструмента |
| `side` | [`Side`](STRUCTURES.md#side) | Сторона для обеих заявок |
| `quantity_sl` | `Decimal` | Количество в шт для SL |
| `sl_price` | `Decimal` | Параметр условия цены для SL части |
| `limit_price` | `Decimal` | Если указано, после активации SL будет выставлена лимитная заявка с этой ценой |
| `quantity_tp` | `Decimal` | Количество в шт для TP |
| `tp_price` | `Decimal` | Параметр условия цены для TP части |
| `tp_guard_spread` | `Decimal` | Если указано, после активации TP будет выставлена лимитная заявка с учетом защитного спрэда |
| `tp_spread_measure` | [`orders.TPSpreadMeasure`](STRUCTURES.md#orders-tpspreadmeasure) | Единица измерения величины защитного спреда |
| `client_order_id` | `string` | Уникальный идентификатор заявки. Автоматически генерируется, если не отправлен. (максимум 20 символов) |
| `valid_before` | [`orders.ValidBefore`](STRUCTURES.md#orders-validbefore) | Срок действия условной заявки. Если не заполнено, то по умолчанию выставляется VALID_BEFORE_GOOD_TILL_CANCEL |
| `valid_expiry_time` | `Timestamp` | Временная метка прекращения действия SL/TP заявки |
| `comment` | `string` | Метка заявки. (максимум 128 символов) |
| `sl_qty_measure` | [`orders.SLTPQtyMeasure`](STRUCTURES.md#orders-sltpqtymeasure) | Единица измерения объёма для Stop Loss части. Если SLTP_QTY_MEASURE_PERCENT — quantity_sl трактуется как процент (0–100) от позиции на момент исполнения. |
| `tp_qty_measure` | [`orders.SLTPQtyMeasure`](STRUCTURES.md#orders-sltpqtymeasure) | Единица измерения объёма для Take Profit части. Если SLTP_QTY_MEASURE_PERCENT — quantity_tp трактуется как процент (0–100) от позиции на момент исполнения. |
| `sl_guard_time` | `Int32Value` | Защитное время StopLoss, в секундах. Допустимы только неотрицательные целочисленные значения. Если поле не указано, значение принимается равным нулю. |
| `tp_guard_time` | `Int32Value` | Защитное время TakeProfit, в секундах. Допустимы только неотрицательные целочисленные значения. Если поле не указано, значение принимается равным нулю. |

**Поля ответа** `orders.OrderState`

| Поле | Тип | Описание |
|---|---|---|
| `order_id` | `string` | Идентификатор заявки |
| `exec_id` | `string` | Идентификатор исполнения |
| `status` | [`orders.OrderStatus`](STRUCTURES.md#orders-orderstatus) | Статус заявки |
| `order` | [`orders.Order`](STRUCTURES.md#orders-order) | Заявка |
| `transact_at` | `Timestamp` | Дата и время выставления заявки |
| `accept_at` | `Timestamp` | Дата и время принятия заявки |
| `withdraw_at` | `Timestamp` | Дата и время  отмены заявки |
| `initial_quantity` | `Decimal` | Начальный объем (заполняется только для биржевой заявки) |
| `executed_quantity` | `Decimal` | Исполненный объем (заполняется только для биржевой заявки) |
| `remaining_quantity` | `Decimal` | Оставшийся объем (заполняется только для биржевой заявки) |
| `sltp_order` | [`orders.SLTPOrder`](STRUCTURES.md#orders-sltporder) | Информация о SL/TP заявке |
| `triggered_order_id` | `string` | Идентификатор биржевой заявки, порожденной в результате срабатывания условия или достижения стоп-цены. |
| `status_description` | `StringValue` | Описание статуса заявки |

<a id="subscribe_order_trade_stream"></a>
### `subscribe_order_trade_stream`

```python
subscribe_order_trade_stream()
```

- **RPC:** `OrdersService.SubscribeOrderTrade` (bidi-stream)
- **Запрос:** [`orders.OrderTradeRequest`](STRUCTURES.md#orders-ordertraderequest)
- **Ответ:** [`orders.OrderTradeResponse`](STRUCTURES.md#orders-ordertraderesponse) (поток сообщений)
- **Повтор при ошибках транспорта:** нет

Подписка на собственные заявки и сделки. Стрим метод

Open stream-stream SubscribeOrderTrade; enqueue subscribe before calling.

**Поля запроса** `orders.OrderTradeRequest`

| Поле | Тип | Описание |
|---|---|---|
| `action` | [`orders.OrderTradeRequest.Action`](STRUCTURES.md#orders-ordertraderequest-action) | Изменение статуса подписки: подписка/отписка |
| `data_type` | [`orders.OrderTradeRequest.DataType`](STRUCTURES.md#orders-ordertraderequest-datatype) | Подписка только на заявки/ордера или на все сразу |
| `account_id` | `string` | Идентификатор аккаунта |

**Поля ответа** `orders.OrderTradeResponse` (приходит потоком сообщений)

| Поле | Тип | Описание |
|---|---|---|
| `orders` | список [`orders.OrderState`](STRUCTURES.md#orders-orderstate) | Заявки |
| `trades` | список [`AccountTrade`](STRUCTURES.md#accounttrade) | Сделки |

<a id="subscribe_order_trade"></a>
### `subscribe_order_trade`

```python
subscribe_order_trade(account_id: str, *, orders: bool=True, trades: bool=True) -> None
```

Ставит в очередь запрос подписки на заявки и/или сделки счёта.

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |
| `orders` | `bool` | `True` |
| `trades` | `bool` | `True` |

<a id="unsubscribe_order_trade"></a>
### `unsubscribe_order_trade`

```python
unsubscribe_order_trade(account_id: str, *, orders: bool=True, trades: bool=True) -> None
```

Ставит в очередь запрос отписки.

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |
| `orders` | `bool` | `True` |
| `trades` | `bool` | `True` |

<a id="subscribe_orders"></a>
### `subscribe_orders`

```python
subscribe_orders(account_id: str)
```

- **RPC:** `OrdersService.SubscribeOrders` (server-stream)
- **Запрос:** [`orders.SubscribeOrdersRequest`](STRUCTURES.md#orders-subscribeordersrequest)
- **Ответ:** [`orders.SubscribeOrdersResponse`](STRUCTURES.md#orders-subscribeordersresponse) (поток сообщений)
- **Повтор при ошибках транспорта:** нет

Подписка на собственные заявки. Стрим метод

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |

**Поля запроса** `orders.SubscribeOrdersRequest`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |

**Поля ответа** `orders.SubscribeOrdersResponse` (приходит потоком сообщений)

| Поле | Тип | Описание |
|---|---|---|
| `orders` | список [`orders.OrderState`](STRUCTURES.md#orders-orderstate) | Заявки |

<a id="subscribe_trades"></a>
### `subscribe_trades`

```python
subscribe_trades(account_id: str)
```

- **RPC:** `OrdersService.SubscribeTrades` (server-stream)
- **Запрос:** [`orders.SubscribeTradesRequest`](STRUCTURES.md#orders-subscribetradesrequest)
- **Ответ:** [`orders.SubscribeTradesResponse`](STRUCTURES.md#orders-subscribetradesresponse) (поток сообщений)
- **Повтор при ошибках транспорта:** нет

Подписка на собственные сделки. Стрим метод

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `account_id` | `str` |  |

**Поля запроса** `orders.SubscribeTradesRequest`

| Поле | Тип | Описание |
|---|---|---|
| `account_id` | `string` | Идентификатор аккаунта |

**Поля ответа** `orders.SubscribeTradesResponse` (приходит потоком сообщений)

| Поле | Тип | Описание |
|---|---|---|
| `trades` | список [`AccountTrade`](STRUCTURES.md#accounttrade) | Сделки |

## MarketData - котировки и свечи

<a id="last_quote"></a>
### `last_quote`

```python
last_quote(symbol: str) -> marketdata_service.QuoteResponse
```

- **RPC:** `MarketDataService.LastQuote` (unary)
- **Запрос:** [`marketdata.QuoteRequest`](STRUCTURES.md#marketdata-quoterequest)
- **Ответ:** [`marketdata.QuoteResponse`](STRUCTURES.md#marketdata-quoteresponse)
- **Повтор при ошибках транспорта:** да

Получение последней котировки по инструменту

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbol` | `str` |  |

**Поля запроса** `marketdata.QuoteRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |

**Поля ответа** `marketdata.QuoteResponse`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `quote` | [`marketdata.Quote`](STRUCTURES.md#marketdata-quote) | Цена последней сделки |

<a id="order_book"></a>
### `order_book`

```python
order_book(symbol: str) -> marketdata_service.OrderBookResponse
```

- **RPC:** `MarketDataService.OrderBook` (unary)
- **Запрос:** [`marketdata.OrderBookRequest`](STRUCTURES.md#marketdata-orderbookrequest)
- **Ответ:** [`marketdata.OrderBookResponse`](STRUCTURES.md#marketdata-orderbookresponse)
- **Повтор при ошибках транспорта:** да

Получение текущего стакана по инструменту

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbol` | `str` |  |

**Поля запроса** `marketdata.OrderBookRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |

**Поля ответа** `marketdata.OrderBookResponse`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `orderbook` | [`marketdata.OrderBook`](STRUCTURES.md#marketdata-orderbook) | Стакан |

<a id="bars"></a>
### `bars`

```python
bars(symbol: str, timeframe: marketdata_service.TimeFrame.ValueType, start: datetime, end: datetime) -> marketdata_service.BarsResponse
```

- **RPC:** `MarketDataService.Bars` (unary)
- **Запрос:** [`marketdata.BarsRequest`](STRUCTURES.md#marketdata-barsrequest)
- **Ответ:** [`marketdata.BarsResponse`](STRUCTURES.md#marketdata-barsresponse)
- **Повтор при ошибках транспорта:** да

Получение исторических данных по инструменту (агрегированные свечи)

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbol` | `str` |  |
| `timeframe` | `marketdata_service.TimeFrame.ValueType` |  |
| `start` | `datetime` |  |
| `end` | `datetime` |  |

**Поля запроса** `marketdata.BarsRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `timeframe` | [`marketdata.TimeFrame`](STRUCTURES.md#marketdata-timeframe) | Необходимый таймфрейм |
| `interval` | `Interval` | Начало и окончание запрашиваемого периода |

**Поля ответа** `marketdata.BarsResponse`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `bars` | список [`marketdata.Bar`](STRUCTURES.md#marketdata-bar) | Агрегированная свеча |

<a id="subscribe_quote"></a>
### `subscribe_quote`

```python
subscribe_quote(symbols: list[str])
```

- **RPC:** `MarketDataService.SubscribeQuote` (server-stream)
- **Запрос:** [`marketdata.SubscribeQuoteRequest`](STRUCTURES.md#marketdata-subscribequoterequest)
- **Ответ:** [`marketdata.SubscribeQuoteResponse`](STRUCTURES.md#marketdata-subscribequoteresponse) (поток сообщений)
- **Повтор при ошибках транспорта:** нет

Подписка на котировки по инструменту. Стрим метод

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbols` | `list[str]` |  |

**Поля запроса** `marketdata.SubscribeQuoteRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbols` | список `string` | Список символов инструментов |

**Поля ответа** `marketdata.SubscribeQuoteResponse` (приходит потоком сообщений)

| Поле | Тип | Описание |
|---|---|---|
| `quote` | список [`marketdata.Quote`](STRUCTURES.md#marketdata-quote) | Список котировок |
| `error` | [`marketdata.StreamError`](STRUCTURES.md#marketdata-streamerror) | Ошибка стрим сервиса |

<a id="subscribe_order_book"></a>
### `subscribe_order_book`

```python
subscribe_order_book(symbol: str)
```

- **RPC:** `MarketDataService.SubscribeOrderBook` (server-stream)
- **Запрос:** [`marketdata.SubscribeOrderBookRequest`](STRUCTURES.md#marketdata-subscribeorderbookrequest)
- **Ответ:** [`marketdata.SubscribeOrderBookResponse`](STRUCTURES.md#marketdata-subscribeorderbookresponse) (поток сообщений)
- **Повтор при ошибках транспорта:** нет

Подписка на стакан по инструменту. Стрим метод

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbol` | `str` |  |

**Поля запроса** `marketdata.SubscribeOrderBookRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |

**Поля ответа** `marketdata.SubscribeOrderBookResponse` (приходит потоком сообщений)

| Поле | Тип | Описание |
|---|---|---|
| `order_book` | список [`marketdata.StreamOrderBook`](STRUCTURES.md#marketdata-streamorderbook) | Список стакан стримов |

<a id="subscribe_bars"></a>
### `subscribe_bars`

```python
subscribe_bars(symbol: str, timeframe: marketdata_service.TimeFrame.ValueType)
```

- **RPC:** `MarketDataService.SubscribeBars` (server-stream)
- **Запрос:** [`marketdata.SubscribeBarsRequest`](STRUCTURES.md#marketdata-subscribebarsrequest)
- **Ответ:** [`marketdata.SubscribeBarsResponse`](STRUCTURES.md#marketdata-subscribebarsresponse) (поток сообщений)
- **Повтор при ошибках транспорта:** нет

Подписка на агрегированные свечи. Стрим метод

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbol` | `str` |  |
| `timeframe` | `marketdata_service.TimeFrame.ValueType` |  |

**Поля запроса** `marketdata.SubscribeBarsRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `timeframe` | [`marketdata.TimeFrame`](STRUCTURES.md#marketdata-timeframe) | Необходимый таймфрейм |

**Поля ответа** `marketdata.SubscribeBarsResponse` (приходит потоком сообщений)

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `bars` | список [`marketdata.Bar`](STRUCTURES.md#marketdata-bar) | Агрегированная свеча |

<a id="latest_trades"></a>
### `latest_trades`

```python
latest_trades(symbol: str) -> marketdata_service.LatestTradesResponse
```

- **RPC:** `MarketDataService.LatestTrades` (unary)
- **Запрос:** [`marketdata.LatestTradesRequest`](STRUCTURES.md#marketdata-latesttradesrequest)
- **Ответ:** [`marketdata.LatestTradesResponse`](STRUCTURES.md#marketdata-latesttradesresponse)
- **Повтор при ошибках транспорта:** да

Получение списка последних сделок по инструменту

Unary snapshot of PUBLIC trades for `symbol` (not the account's own — see subscribe_trades for that). Фаза C: reserve fallback for MarketActivityTracker.is_trading, not consulted by any decision today — see BrokerPort.get_latest_trades.

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `symbol` | `str` |  |

**Поля запроса** `marketdata.LatestTradesRequest`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |

**Поля ответа** `marketdata.LatestTradesResponse`

| Поле | Тип | Описание |
|---|---|---|
| `symbol` | `string` | Символ инструмента |
| `trades` | список [`marketdata.Trade`](STRUCTURES.md#marketdata-trade) | Список последних сделок |

## Reports - отчёты по счёту

<a id="create_account_report"></a>
### `create_account_report`

```python
create_account_report(request: reports_service.CreateAccountReportRequest)
```

- **RPC:** `ReportsService.CreateAccountReport` (unary)
- **Запрос:** [`reports.CreateAccountReportRequest`](STRUCTURES.md#reports-createaccountreportrequest)
- **Ответ:** [`reports.CreateAccountReportResponse`](STRUCTURES.md#reports-createaccountreportresponse)
- **Повтор при ошибках транспорта:** да

Запустить генерацию отчета по счету за период

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `request` | `reports_service.CreateAccountReportRequest` |  |

**Поля запроса** `reports.CreateAccountReportRequest`

| Поле | Тип | Описание |
|---|---|---|
| `date_range` | [`reports.DateRange`](STRUCTURES.md#reports-daterange) | Временной интервал. Максимальный интервал дат - 92 дня |
| `report_form` | [`reports.ReportForm`](STRUCTURES.md#reports-reportform) | Форма отчета |
| `account_id` | `int64` | Идентификатор счета |

**Поля ответа** `reports.CreateAccountReportResponse`

| Поле | Тип | Описание |
|---|---|---|
| `report_id` | `string` | Идентификатор отчёта |

<a id="get_account_report_info"></a>
### `get_account_report_info`

```python
get_account_report_info(request: reports_service.GetAccountReportInfoRequest)
```

- **RPC:** `ReportsService.GetAccountReportInfo` (unary)
- **Запрос:** [`reports.GetAccountReportInfoRequest`](STRUCTURES.md#reports-getaccountreportinforequest)
- **Ответ:** [`reports.GetAccountReportInfoResponse`](STRUCTURES.md#reports-getaccountreportinforesponse)
- **Повтор при ошибках транспорта:** да

Получение информации о результате генерации отчета по счету

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `request` | `reports_service.GetAccountReportInfoRequest` |  |

**Поля запроса** `reports.GetAccountReportInfoRequest`

| Поле | Тип | Описание |
|---|---|---|
| `report_id` | `string` | Идентификатор отчёта |

**Поля ответа** `reports.GetAccountReportInfoResponse`

| Поле | Тип | Описание |
|---|---|---|
| `info` | [`reports.AccountReportInfo`](STRUCTURES.md#reports-accountreportinfo) | Информация о статусе генерации отчёта |

<a id="subscribe_account_report_info"></a>
### `subscribe_account_report_info`

```python
subscribe_account_report_info(request: reports_service.SubscribeAccountReportInfoRequest)
```

- **RPC:** `ReportsService.SubscribeAccountReportInfo` (server-stream)
- **Запрос:** [`reports.SubscribeAccountReportInfoRequest`](STRUCTURES.md#reports-subscribeaccountreportinforequest)
- **Ответ:** [`reports.SubscribeAccountReportInfoResponse`](STRUCTURES.md#reports-subscribeaccountreportinforesponse) (поток сообщений)
- **Повтор при ошибках транспорта:** нет

Подписка на информацию о результатах генерации отчета по счету. Стрим метод

**Параметры метода**

| Параметр | Тип | По умолчанию |
|---|---|---|
| `request` | `reports_service.SubscribeAccountReportInfoRequest` |  |

**Поля запроса** `reports.SubscribeAccountReportInfoRequest`

| Поле | Тип | Описание |
|---|---|---|
| `report_id` | `string` | Идентификатор отчёта |

**Поля ответа** `reports.SubscribeAccountReportInfoResponse` (приходит потоком сообщений)

| Поле | Тип | Описание |
|---|---|---|
| `info` | [`reports.AccountReportInfo`](STRUCTURES.md#reports-accountreportinfo) | Информация о статусе генерации отчёта |

## Metrics - использование API

<a id="get_usage_metrics"></a>
### `get_usage_metrics`

```python
get_usage_metrics() -> usage_metrics_service.GetUsageMetricsResponse
```

- **RPC:** `UsageMetricsService.GetUsageMetrics` (unary)
- **Запрос:** [`metrics.GetUsageMetricsRequest`](STRUCTURES.md#metrics-getusagemetricsrequest)
- **Ответ:** [`metrics.GetUsageMetricsResponse`](STRUCTURES.md#metrics-getusagemetricsresponse)
- **Повтор при ошибках транспорта:** да

Получение текущих метрик использования для пользователя

**Поля запроса** `metrics.GetUsageMetricsRequest`

_Поля отсутствуют._

**Поля ответа** `metrics.GetUsageMetricsResponse`

| Поле | Тип | Описание |
|---|---|---|
| `quotas` | список [`metrics.GetUsageMetricsResponse.QuotaUsage`](STRUCTURES.md#metrics-getusagemetricsresponse-quotausage) | Список текущих квот и их использование. |

## Сессия и жизненный цикл клиента

| Член | Описание |
|---|---|
| `JWT_REFRESH_SKEW_SEC` | Запас в секундах до истечения JWT, при котором токен обновляется заранее (`GrpcTuning.jwt_refresh_skew_sec`). |
| `TIMEOUT_SEC` | Таймаут одного gRPC-вызова в секундах (`GrpcTuning.timeout_sec`). |
| `GRPC_MAX_ATTEMPTS` | Максимум попыток одного вызова, включая первую (`GrpcTuning.max_attempts`). |
| `jwt_fail_streak` | Сколько обновлений JWT подряд в фоновом потоке завершились ошибкой; сбрасывается успешным обновлением. |
| `ensure_channel()` | Пересоздаёт канал и stubs, если `close()` их закрыл. Вызывать перед первым RPC после переподключения. |
| `refresh_session(*, force: bool=False)` | Получает новый JWT через `Auth` (всегда, параметр `force` игнорируется). Вызывать до торговых вызовов. |
| `jwt_expires_at` | Момент истечения текущего JWT (UTC) или `None`, если токен ещё не выпущен. |
| `set_on_jwt_renewed(callback: Callable[[], None] \| None)` | Регистрирует колбэк, который фоновый поток вызывает после каждого успешного обновления JWT (нужен, чтобы пересоздать долгие стримы с новым токеном). Колбэк выполняется в потоке обновления. |
| `close()` | Останавливает фоновое обновление JWT и закрывает канал. |
| `auth()` | Обменивает secret на JWT (`AuthService.Auth`), возвращает `AuthResponse`. Обычно вызывается неявно через `refresh_session()`. |
| `start_jwt_renewal_background(interval_sec: int)` | Запускает поток `finam-jwt-renewal`, который каждые `interval_sec` секунд обновляет JWT. |
| `stop_jwt_renewal_background()` | Останавливает поток обновления JWT (ждёт до 3 с). |

## Нейтральные модели

`finam_client.assets` - данные брокера без доменных интерпретаций.

#### `AssetListItem`

Строка списка `Assets` / `AllAssets`. Board в списке нет.

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `symbol` | `str` |  | Символ `ticker@mic` |
| `id` | `str` |  | Идентификатор инструмента Finam |
| `ticker` | `str` |  | Тикер |
| `mic` | `str` |  | MIC биржи (`MISX`, `RTSX`, `XNYM`, `#WWCP`, ...) |
| `isin` | `str` |  | ISIN |
| `type` | `str` |  | Тип: `EQUITIES`, `FUTURES`, `INDICES`, `CURRENCIES`, `BONDS`, `FUNDS`, `OPTIONS`, `SPREADS`, `SWAPS`, `OTHER` |
| `name` | `str` |  | Наименование |
| `is_archived` | `bool` |  | Инструмент в архиве (в `Assets` архивных нет, в `AllAssets` есть) |

#### `AssetInfo`

Результат `GetAsset`: статические данные инструмента. Только здесь есть `board`.

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `symbol` | `str` |  | Символ `ticker@mic` |
| `id` | `str` |  | Идентификатор инструмента Finam |
| `ticker` | `str` |  | Тикер |
| `mic` | `str` |  | MIC биржи |
| `board` | `str` |  | Режим торгов (`TQBR`, `FUT`, `CETS`); пуст для зарубежных площадок, индексов и архивных |
| `isin` | `str` |  | ISIN |
| `type` | `str` |  | Тип инструмента (как в `AssetListItem`) |
| `name` | `str` |  | Наименование |
| `decimals` | `int` |  | Знаков после запятой в цене |
| `min_step_raw` | `int` |  | `min_step` из ответа (целое) |
| `price_step` | `Decimal` |  | Шаг цены: `min_step / 10^decimals` |
| `lot_size` | `Decimal` |  | Штук в лоте |
| `quote_currency` | `str` |  | Валюта котировки |
| `expiration_date` | `str \| None` |  | Дата экспирации `YYYY-MM-DD` (у фьючерсов; у непрерывных нет) |
| `future_details` | `dict \| None` |  | Для фьючерса: `contract_size`, `expiration_date` |
| `option_details` | `dict \| None` |  | Для опциона: `contract_size`, `strike`, `expiration_date` |
| `bond_details` | `dict \| None` |  | Для облигации: `bond_face_value`, `currency` |

#### `AssetParams`

Результат `GetAssetParams`: торговые флаги и гарантийное обеспечение; зависят от счёта.

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `symbol` | `str` |  | Символ `ticker@mic` |
| `account_id` | `str` |  | Счёт, для которого получены параметры |
| `tradable` | `bool` |  | Инструмент торгуется (`is_tradable`) |
| `longable` | `bool` |  | Лонг доступен |
| `shortable` | `bool` |  | Шорт доступен (включая `AVAILABLE_STRATEGY`) |
| `long_risk_rate` | `Decimal \| None` |  | Ставка риска для лонга |
| `short_risk_rate` | `Decimal \| None` |  | Ставка риска для шорта |
| `long_initial_margin` | `Decimal \| None` |  | Начальное ГО для лонга |
| `short_initial_margin` | `Decimal \| None` |  | Начальное ГО для шорта |
| `margin_currency` | `str` |  | Валюта ГО |
| `price_type` | `str` |  | Допустимые цены: `UNKNOWN`, `POSITIVE`, `NON_NEGATIVE`, `ANY` |

#### `Bar`

Свеча из `Bars` / `SubscribeBars`.

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `timestamp` | `datetime \| None` |  | Начало свечи (UTC) |
| `open` | `Decimal` |  | Цена открытия |
| `high` | `Decimal` |  | Максимум |
| `low` | `Decimal` |  | Минимум |
| `close` | `Decimal` |  | Цена закрытия |
| `volume` | `Decimal` |  | Объём |

Мапперы из protobuf:

- `asset_list_item_from_proto(asset) -> finam_client.assets.AssetListItem` - `Asset` -> `AssetListItem`.
- `asset_info_from_proto(response, *, symbol: str | None = None) -> finam_client.assets.AssetInfo` - `GetAssetResponse` -> `AssetInfo`; `symbol` по умолчанию `ticker@mic`.
- `asset_params_from_proto(response, account_id: str) -> finam_client.assets.AssetParams` - `GetAssetParamsResponse` -> `AssetParams`.
- `bar_from_proto(bar) -> finam_client.assets.Bar` - `Bar` -> `Bar` (нейтральная).

## Конфигурация

#### `GrpcTuning`

Параметры канала и повторов (значения по умолчанию совпадают с демоном BF).

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `keepalive_time_sec` | `float` | `30.0` | Период keepalive-пингов канала |
| `keepalive_timeout_sec` | `float` | `10.0` | Ожидание ответа на пинг |
| `timeout_sec` | `float` | `10.0` | Таймаут одного вызова |
| `max_attempts` | `int` | `3` | Попыток на вызов (включая первую) |
| `retry_base_sec` | `float` | `0.4` | Базовая пауза между повторами (умножается на номер попытки) |
| `rate_limit_backoff_sec` | `float` | `2.0` | Базовая пауза при `RESOURCE_EXHAUSTED` (лимит Finam ~200 запросов/мин) |
| `min_interval_sec` | `float` | `0.0` | Минимальная пауза между унарными вызовами одного клиента (0 - выключено); для массовых задач 0.4 ≈ 150 запросов/мин |
| `jwt_refresh_skew_sec` | `float` | `90.0` | Запас до истечения JWT, при котором токен обновляется |

#### `ClientConfig`

Конфигурация клиента.

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `secret_file` | `str` |  | Файл с secret-токеном Finam (одна строка) |
| `endpoint` | `str` | `'api.finam.ru:443'` | Адрес gRPC API |
| `grpc_client` | `GrpcTuning` | `GrpcTuning()` | Параметры канала и повторов |

- `read_secret_file(path: pathlib.Path | str) -> str` - Читает secret из файла; пустой файл - `ValueError`.

## Ошибки

`FinamError(category, message, retryable=False, broker_code=None)` - исключение по умолчанию.
Потребитель может передать `error_factory(category, message, *, retryable, broker_code)`,
чтобы клиент бросал собственный тип (BF передаёт `BrokerError`).

| `ErrorCategory` | Значение |
|---|---|
| `AUTH` | `broker_auth` |
| `GRPC` | `broker_grpc` |
| `MARKETDATA` | `marketdata` |
| `ORDER` | `order` |
| `VALIDATION` | `validation` |

`broker_code` - имя gRPC-статуса (`UNAVAILABLE`, `RESOURCE_EXHAUSTED`, `INVALID_ARGUMENT`, ...),
а также `place_timeout` (таймаут заявки: исход неизвестен) и `auction_only`
(отказ из-за аукциона: заявку можно повторить позже).

## Площадки и символы

- `to_finam_venue(mic: str, board: str) -> Venue` - Площадка каталога `(mic, board)` -> площадка Finam (`MISX/RFUD` -> `RTSX/FUT`).
- `from_finam_venue(finam_mic: str, finam_board: str) -> Venue` - Площадка Finam `(mic, board)` -> площадка каталога; незнакомый `RTSX` сворачивается в `MISX`.
- `finam_board_from_venue(exchange: str, venue_board: str) -> str` - Board Finam для пары каталога `(exchange, board)`.

- `validate_finam_symbol(symbol: str) -> str` - Проверяет формат `ticker@mic` (делит по последнему `@`), возвращает символ без пробелов по краям; иначе `FinamError(VALIDATION)`.
- `split_symbol(symbol: str) -> tuple[str, str]` - `SBER@MISX` -> `("SBER", "MISX")`; регистр сохраняется.

## Хелперы значений (`finam_client.proto_values`)

- `from_proto_decimal(value: google.type.decimal_pb2.Decimal | None) -> decimal.Decimal` - `google.type.Decimal` -> `Decimal` (пусто -> 0).
- `to_proto_decimal(price: decimal.Decimal, decimals: int | None = None) -> google.type.decimal_pb2.Decimal` - `Decimal` -> `google.type.Decimal`; `decimals` округляет до знаков.
- `optional_proto_decimal(value: google.type.decimal_pb2.Decimal | None) -> decimal.Decimal | None` - `Decimal` или `None`, если значение не задано.
- `optional_google_money(money: Any) -> decimal.Decimal | None` - `google.type.Money` -> `Decimal` или `None`, если 0.
- `from_google_money(money: Any) -> decimal.Decimal` - `google.type.Money` (`units` + `nanos`) -> `Decimal`.
- `money_currency_code(money: Any) -> str` - Код валюты из `Money` в верхнем регистре.
- `sum_money_list(cash_field: Any) -> decimal.Decimal | None` - Сумма списка `Money` (`GetAccount.cash`) или `None`.
- `money_list_by_currency(cash_field: Any) -> dict[str, decimal.Decimal]` - Список `Money` -> словарь `{валюта: сумма}`.
- `price_step_from_asset(decimals: int, min_step_raw: int) -> decimal.Decimal` - `min_step / 10^decimals`.
- `lots_from_proto(value: google.type.decimal_pb2.Decimal | None) -> int` - `Decimal` из proto -> целое число лотов.
- `decimal_to_json(value: decimal.Decimal | None) -> str | None` - `Decimal` -> строка без хвостовых нулей или `None`.
- `timestamp_to_datetime(ts) -> datetime.datetime | None` - `Timestamp` -> `datetime` (UTC) или `None`, если пуст.
- `proto_calendar_date_to_iso(value) -> str | None` - `google.type.Date` -> `YYYY-MM-DD` (или `YYYY-MM`, `YYYY`).
- `timeframe_to_finam(timeframe: str)` - Строка таймфрейма (`M5`, `1h`, `D1`, ...) -> `TimeFrame`; неизвестная - `ValueError`.

Словарь таймфреймов `TIMEFRAME_MAP`: `M1`, `M5`, `M15`, `M30`, `M60`, `H1`, `H2`, `H4`, `D1`, `5min`, `15min`, `30min`, `1h`, `2h`, `4h`, `1d`.
