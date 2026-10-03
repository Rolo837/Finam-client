# Структуры запросов и ответов

> Файл сгенерирован `scripts/generate_docs.py` из proto и не редактируется вручную.
> Методы клиента, которые принимают и возвращают эти структуры, - в [API.md](API.md).

Все сообщения - protobuf-классы из `finam_client.grpc_gen`; импортировать их удобно через
фасад `finam_client.grpc_imports` (`assets_service.GetAssetRequest(...)` и т.д.).
Поля `Decimal`, `Money`, `Timestamp` и др. описаны в разделе «Общие типы Google».

## Общие типы Google

| Тип | Смысл |
|---|---|
| `google.type.Decimal` | десятичное число строкой (`value`), например `"12.34"` |
| `google.type.Money` | сумма: `currency_code`, `units` (целая часть), `nanos` (доля, 1e-9) |
| `google.type.Interval` | интервал времени `[start_time, end_time)` |
| `google.type.Date` | календарная дата `year`/`month`/`day` (часть может быть 0) |
| `google.protobuf.Timestamp` | момент времени: `seconds`, `nanos` (UTC) |
| `google.protobuf.BoolValue` | обёртка над bool: `value`; различает «не задано» и `false` |
| `google.protobuf.StringValue` | обёртка над string: `value` |
| `google.protobuf.Int32Value` | обёртка над int32: `value` |
| `google.protobuf.Int64Value` | обёртка над int64: `value` |
| `google.protobuf.Empty` | пустое сообщение |

## Общие типы Finam

<a id="side"></a>
#### `Side` (enum)

Сторона сделки

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `SIDE_UNSPECIFIED` | Сторона сделки не указана |
| 1 | `SIDE_BUY` | Покупка |
| 2 | `SIDE_SELL` | Продажа |

<a id="accounttrade"></a>
#### `AccountTrade`

Информация о сделке

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `trade_id` | `string` | Идентификатор сделки |
| 2 | `symbol` | `string` | Символ инструмента |
| 3 | `price` | `Decimal` | Цена исполнения |
| 4 | `size` | `Decimal` | Размер в шт. |
| 5 | `side` | [`Side`](STRUCTURES.md#side) | Сторона сделки (long или short) |
| 6 | `timestamp` | `Timestamp` | Метка времени |
| 7 | `order_id` | `string` | Идентификатор заявки |
| 8 | `account_id` | `string` | Идентификатор аккаунта |
| 9 | `comment` | `string` | Метка заявки. (максимум 128 символов) |
| 10 | `accrued_interest` | `Decimal` | НКД (заполняется на следующий день после даты совершения сделки) |
| 11 | `currency` | `string` | Валюта цены (например, RUB, USD, EUR) Примечание: поле заполняется только при использовании метода Trades Для SubscribeTrades данное поле может быть пустым в связи с различиями в источниках данных. При обработке сделок из подписки рекомендуется учитывать возможность пустого значения. |

## Auth - сессия и токен

<a id="auth-mdpermission-quotelevel"></a>
#### `auth.MDPermission.QuoteLevel` (enum)

Уровень котировок

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `QUOTE_LEVEL_UNSPECIFIED` | Значение не указано |
| 1 | `QUOTE_LEVEL_LAST_PRICE` | Последняя цена |
| 2 | `QUOTE_LEVEL_BEST_BID_OFFER` | Бид аск |
| 3 | `QUOTE_LEVEL_DEPTH_OF_MARKET` | Агрегированный стакан |
| 4 | `QUOTE_LEVEL_DEPTH_OF_BOOK` | Полный стакан |
| 5 | `QUOTE_LEVEL_ACCESS_FORBIDDEN` | Доступ запрещен |

<a id="auth-authrequest"></a>
#### `auth.AuthRequest`

Запрос авторизации

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `secret` | `string` | API токен (secret key) |
| 2 | `source_app_id` | `string` | Идентификатор приложения-источника запроса |

<a id="auth-authresponse"></a>
#### `auth.AuthResponse`

Информация об авторизации

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `token` | `string` | Полученный JWT-токен |

<a id="auth-tokendetailsrequest"></a>
#### `auth.TokenDetailsRequest`

Запрос информации о токене

Используется в: `token_details (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `token` | `string` | JWT-токен |

<a id="auth-tokendetailsresponse"></a>
#### `auth.TokenDetailsResponse`

Информация о токене

Используется в: `token_details (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `created_at` | `Timestamp` | Дата и время создания |
| 2 | `expires_at` | `Timestamp` | Дата и время экспирации |
| 3 | `md_permissions` | список [`auth.MDPermission`](STRUCTURES.md#auth-mdpermission) | Информация о доступе к рыночным данным |
| 4 | `account_ids` | список `string` | Идентификаторы аккаунтов |
| 5 | `readonly` | `bool` | Сессия и торговые счета в токене будут помечены readonly |

<a id="auth-mdpermission"></a>
#### `auth.MDPermission`

Информация о доступе к рыночным данным

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `quote_level` | [`auth.MDPermission.QuoteLevel`](STRUCTURES.md#auth-mdpermission-quotelevel) | Уровень котировок |
| 2 | `delay_minutes` | `int32` | Задержка в минутах |
| 3 | `mic` | `string` | Идентификатор биржи mic _(oneof `condition`)_ |
| 4 | `country` | `string` | Страна _(oneof `condition`)_ |
| 5 | `continent` | `string` | Континент _(oneof `condition`)_ |
| 6 | `worldwide` | `bool` | Весь мир _(oneof `condition`)_ |

<a id="auth-subscribejwtrenewalrequest"></a>
#### `auth.SubscribeJwtRenewalRequest`

Запрос подписки на обновление JWT токена

Используется в: `subscribe_jwt_renewal (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `secret` | `string` | API токен (secret key) |
| 2 | `source_app_id` | `string` | Идентификатор приложения-источника запроса |

<a id="auth-subscribejwtrenewalresponse"></a>
#### `auth.SubscribeJwtRenewalResponse`

Обновленный токен. Стрим

Используется в: `subscribe_jwt_renewal (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `token` | `string` | Полученный JWT-токен |

## Accounts - счета, сделки, транзакции

<a id="accounts-transaction-transactioncategory"></a>
#### `accounts.Transaction.TransactionCategory` (enum)

Категории транзакции.

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `OTHERS` | Прочее |
| 1 | `DEPOSIT` | Ввод ДС |
| 2 | `WITHDRAW` | Вывод ДС |
| 5 | `INCOME` | Доход |
| 7 | `COMMISSION` | Комиссия |
| 8 | `TAX` | Налог |
| 9 | `INHERITANCE` | Наследство |
| 11 | `TRANSFER` | Перевод ДС |
| 12 | `CONTRACT_TERMINATION` | Расторжение договора |
| 13 | `OUTCOMES` | Расходы |
| 15 | `FINE` | Штраф |
| 19 | `LOAN` | Займ |

<a id="accounts-getaccountrequest"></a>
#### `accounts.GetAccountRequest`

Запрос получения информации по конкретному аккаунту

Используется в: `get_account (запрос)`, `subscribe_account (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |

<a id="accounts-getaccountresponse"></a>
#### `accounts.GetAccountResponse`

Информация о конкретном аккаунте

Используется в: `get_account (ответ)`, `subscribe_account (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |
| 2 | `type` | `string` | Тип аккаунта |
| 3 | `status` | `string` | Статус аккаунта |
| 4 | `equity` | `Decimal` | Доступные средства плюс стоимость открытых позиций |
| 5 | `unrealized_profit` | `Decimal` | Нереализованная прибыль |
| 6 | `positions` | список [`accounts.Position`](STRUCTURES.md#accounts-position) | Позиции. Открытые, плюс теоретические (по неисполненным активным заявкам) |
| 7 | `cash` | список `Money` | Сумма собственных денежных средств на счете, доступная для торговли. Не включает маржинальные средства. |
| 8 | `portfolio_mc` | [`accounts.MC`](STRUCTURES.md#accounts-mc) | Общий тип для счетов Московской Биржи. Включает в себя как единые, так и моно счета. _(oneof `portfolio`)_ |
| 9 | `portfolio_mct` | [`accounts.MCT`](STRUCTURES.md#accounts-mct) | Тип портфеля для счетов на американских рынках. _(oneof `portfolio`)_ |
| 10 | `portfolio_forts` | [`accounts.FORTS`](STRUCTURES.md#accounts-forts) | Тип портфеля для торговли на срочном рынке Московской Биржи. _(oneof `portfolio`)_ |
| 11 | `open_account_date` | `Timestamp` | Дата открытия счета |
| 12 | `first_trade_date` | `Timestamp` | Дата первой торговой транзакции |
| 13 | `first_non_trade_date` | `Timestamp` | Дата первой неторговой транзакции |

<a id="accounts-mc"></a>
#### `accounts.MC`

Общий тип для счетов Московской Биржи. Включает в себя как единые, так и специализированные (моно) счета для разных секций биржи. Единый торговый счет (ЕТС): Позволяет торговать на нескольких рынках (фондовый, валютный. срочный, spb, иностранные бумаги, иностранные фьючерсы) с единой денежной позиции. Моно-счет фондового рынка MOEX: Изолированный счет для торговли акциями, облигациями и паями. Моно-счет валютного рынка MOEX: Изолированный счет для операций с валютными парами (например, CNYRUB_TOM).

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `available_cash` | `Decimal` | Сумма собственных денежных средств на счете, доступная для торговли. Включает маржинальные средства. |
| 2 | `initial_margin` | `Decimal` | Начальная маржа |
| 3 | `maintenance_margin` | `Decimal` | Минимальная маржа |

<a id="accounts-mct"></a>
#### `accounts.MCT`

Тип портфеля для счетов на американских рынках. Предоставляет доступ к биржам США: NYSE, NASDAQ, CBOE, CME, сделки с американскими акциями, фьючерсами и опционами.

_Пустое сообщение._

<a id="accounts-forts"></a>
#### `accounts.FORTS`

Тип портфеля для торговли на срочном рынке Московской Биржи. Предназначен для работы с производными финансовыми инструментами: фьючерсами и опционами.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `available_cash` | `Decimal` | Сумма собственных денежных средств на счете, доступная для торговли. Включает маржинальные средства. |
| 2 | `money_reserved` | `Decimal` | Минимальная маржа (необходимая сумма обеспечения под открытые позиции) |

<a id="accounts-tradesrequest"></a>
#### `accounts.TradesRequest`

Запрос получения истории по сделкам

Используется в: `trades (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |
| 2 | `limit` | `int32` | Лимит количества сделок |
| 3 | `interval` | `Interval` | Начало и окончание запрашиваемого периода, Unix epoch time |

<a id="accounts-tradesresponse"></a>
#### `accounts.TradesResponse`

История по сделкам

Используется в: `trades (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `trades` | список [`AccountTrade`](STRUCTURES.md#accounttrade) | Сделки по аккаунту |

<a id="accounts-transactionsrequest"></a>
#### `accounts.TransactionsRequest`

Запрос получения списка транзакций

Используется в: `transactions (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |
| 2 | `limit` | `int32` | Лимит количества транзакций |
| 3 | `interval` | `Interval` | Начало и окончание запрашиваемого периода, Unix epoch time |

<a id="accounts-transactionsresponse"></a>
#### `accounts.TransactionsResponse`

Список транзакций

Используется в: `transactions (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `transactions` | список [`accounts.Transaction`](STRUCTURES.md#accounts-transaction) | Транзакции по аккаунту |

<a id="accounts-position"></a>
#### `accounts.Position`

Информация о позиции

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `quantity` | `Decimal` | Количество в шт., значение со знаком определяющее (long-short) |
| 3 | `average_price` | `Decimal` | Средняя цена. Не заполняется для FORTS позиций |
| 4 | `current_price` | `Decimal` | Текущая цена |
| 5 | `maintenance_margin` | `Decimal` | Поддерживающее гарантийное обеспечение. Заполняется только для FORTS позиций |
| 6 | `daily_pnl` | `Decimal` | Прибыль или убыток за текущий день (PnL). Не заполняется для FORTS позиций |
| 7 | `unrealized_pnl` | `Decimal` | Суммарная нереализованная прибыль или убыток (PnL) текущей позиции |

<a id="accounts-transaction"></a>
#### `accounts.Transaction`

Информация о транзакции

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `id` | `string` | Идентификатор транзакции |
| 2 | `category` | `string` | Тип транзакции из TransactionCategory |
| 4 | `timestamp` | `Timestamp` | Метка времени |
| 5 | `symbol` | `string` | Символ инструмента |
| 6 | `change` | `Money` | Изменение в деньгах |
| 7 | `trade` | [`accounts.Transaction.Trade`](STRUCTURES.md#accounts-transaction-trade) | Информация о сделке |
| 8 | `transaction_category` | [`accounts.Transaction.TransactionCategory`](STRUCTURES.md#accounts-transaction-transactioncategory) | Категория транзакции из TransactionCategory. |
| 9 | `transaction_name` | `string` | Наименование транзакции |
| 10 | `change_qty` | `Decimal` | Изменение в штуках, только для трансфера бумаг (для TransactionCategory = TRANSFER) |

<a id="accounts-transaction-trade"></a>
#### `accounts.Transaction.Trade`

Объект заполняется для торговых типов транзакций

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `size` | `Decimal` | Количество в шт. |
| 2 | `price` | `Decimal` | Цена сделки за штуку. Цена исполнения/Размер премии по опциону. Это цена заключения, значение берется из сделки. |
| 3 | `accrued_interest` | `Decimal` | НКД. Заполнено если в сделке есть НКД |

## Assets - каталог инструментов

<a id="assets-pricetype"></a>
#### `assets.PriceType` (enum)

Допустимая цена

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `UNKNOWN` | Неизвестно |
| 1 | `POSITIVE` | Положительная. Больше нуля |
| 2 | `NON_NEGATIVE` | Неотрицательная. Больше или равна нулю |
| 3 | `ANY` | Любая |

<a id="assets-option-type"></a>
#### `assets.Option.Type` (enum)

Тип опциона

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `TYPE_UNSPECIFIED` | Неопределенное значение |
| 1 | `TYPE_CALL` | Колл |
| 2 | `TYPE_PUT` | Пут |

<a id="assets-longable-status"></a>
#### `assets.Longable.Status` (enum)

Статус

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `NOT_AVAILABLE` | Не доступен |
| 1 | `AVAILABLE` | Доступен |
| 2 | `ACCOUNT_NOT_APPROVED` | Запрещено на уровне счета |

<a id="assets-shortable-status"></a>
#### `assets.Shortable.Status` (enum)

Статус

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `NOT_AVAILABLE` | Не доступен |
| 1 | `AVAILABLE` | Доступен |
| 2 | `HTB` | Признак того, что бумага Hard To Borrow (если есть) |
| 3 | `ACCOUNT_NOT_APPROVED` | Запрещено на уровне счета |
| 4 | `AVAILABLE_STRATEGY` | Разрешено в составе стратегии |

<a id="assets-exchangesrequest"></a>
#### `assets.ExchangesRequest`

Запрос получения списка доступных бирж

_Пустое сообщение._

<a id="assets-exchangesresponse"></a>
#### `assets.ExchangesResponse`

Список доступных бирж

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `exchanges` | список [`assets.Exchange`](STRUCTURES.md#assets-exchange) | Информация о бирже |

<a id="assets-assetsrequest"></a>
#### `assets.AssetsRequest`

Запрос получения списка доступных инструментов

Используется в: `assets (запрос)`.

_Пустое сообщение._

<a id="assets-assetsresponse"></a>
#### `assets.AssetsResponse`

Список доступных инструментов

Используется в: `assets (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `assets` | список [`assets.Asset`](STRUCTURES.md#assets-asset) | Информация об инструменте |

<a id="assets-allassetsrequest"></a>
#### `assets.AllAssetsRequest`

Запрос получения списка доступных инструментов

Используется в: `all_assets (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `cursor` | `int64` | Курсор для пагинации. Указывает sec_id инструмента, с которого должен начинаться список. Для первого запроса оставьте поле пустым (значение 0). Для последующих запросов используйте значение next_cursor из предыдущего ответа. |
| 2 | `only_active` | `bool` | Фильтрация по статусу инструмента: выбираются только активные(неархивные) инструменты По умолчанию: false. |
| 3 | `only_disabled` | `bool` | Фильтрация по статусу инструмента: выбираются только неактивные(архивные) инструменты По умолчанию: false. |

<a id="assets-allassetsresponse"></a>
#### `assets.AllAssetsResponse`

Ответ, содержащий часть доступных инструментов.

Используется в: `all_assets (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `assets` | список [`assets.Asset`](STRUCTURES.md#assets-asset) | Часть списка инструментов |
| 2 | `next_cursor` | `int64` | Курсор для получения следующей страницы. Содержит sec_id последнего инструмента в текущем списке. Передайте это значение в поле cursor следующего запроса, чтобы получить следующую часть данных. Если значение 0 или отсутствует — это последняя страница. |

<a id="assets-getassetrequest"></a>
#### `assets.GetAssetRequest`

Запрос получения информации по конкретному инструменту

Используется в: `get_asset (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `account_id` | `string` | ID аккаунта для которого будет подбираться информация по инструменту |

<a id="assets-getassetresponse"></a>
#### `assets.GetAssetResponse`

Список информации по конкретному инструменту

Используется в: `get_asset (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `board` | `string` | Код режима торгов |
| 2 | `id` | `string` | Идентификатор инструмента |
| 3 | `ticker` | `string` | Тикер инструмента |
| 4 | `mic` | `string` | mic идентификатор биржи |
| 5 | `isin` | `string` | Isin идентификатор инструмента |
| 6 | `type` | `string` | Тип инструмента |
| 7 | `name` | `string` | Наименование инструмента |
| 10 | `decimals` | `int32` | Кол-во десятичных знаков в цене |
| 11 | `min_step` | `int64` | Минимальный шаг цены. Для расчета финального ценового шага: min_step/(10ˆdecimals) |
| 9 | `lot_size` | `Decimal` | Кол-во штук в лоте |
| 12 | `expiration_date` | `Date` | Дата экспирации фьючерса |
| 13 | `quote_currency` | `string` | Валюта котировки, может не совпадать с валютой режима торгов инструмента |
| 14 | `future_details` | [`assets.GetAssetResponse.FutureDetails`](STRUCTURES.md#assets-getassetresponse-futuredetails) | Специфичные параметры для инструмента типа "Фьючерс" _(oneof `asset_details`)_ |
| 15 | `option_details` | [`assets.GetAssetResponse.OptionDetails`](STRUCTURES.md#assets-getassetresponse-optiondetails) | Специфичные параметры для инструмента типа "Опцион" _(oneof `asset_details`)_ |
| 16 | `bond_details` | [`assets.GetAssetResponse.BondDetails`](STRUCTURES.md#assets-getassetresponse-bonddetails) | Специфичные параметры для инструмента типа "Облигация" _(oneof `asset_details`)_ |

<a id="assets-getassetresponse-futuredetails"></a>
#### `assets.GetAssetResponse.FutureDetails`

Специфичные параметры для инструмента типа "Фьючерс"

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `expiration_date` | `Timestamp` | Дата и время экспирации (исполнения) фьючерсного контракта. |
| 2 | `contract_size` | `Decimal` | Размер контракта (мультипликатор) — количество единиц базового актива в одном контракте. |

<a id="assets-getassetresponse-optiondetails"></a>
#### `assets.GetAssetResponse.OptionDetails`

Специфичные параметры для инструмента типа "Опцион"

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `expiration_date` | `Timestamp` | Дата и время экспирации (исполнения) опционного контракта. |
| 2 | `contract_size` | `Decimal` | Размер контракта (мультипликатор) — количество единиц базового актива в одном контракте. |
| 3 | `strike` | `Decimal` | Цена исполнения (страйк) опциона. |

<a id="assets-getassetresponse-bonddetails"></a>
#### `assets.GetAssetResponse.BondDetails`

Специфичные параметры для инструмента типа "Облигация"

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `bond_face_value` | `Decimal` | Текущая номинальная стоимость одной облигации. |
| 2 | `currency` | `string` | Символьный код валюты номинала облигации (например, RUB, USD). |

<a id="assets-getassetparamsrequest"></a>
#### `assets.GetAssetParamsRequest`

Запрос торговых параметров инструмента

Используется в: `get_asset_params (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `account_id` | `string` | ID аккаунта для которого будут подбираться торговые параметры |

<a id="assets-getassetparamsresponse"></a>
#### `assets.GetAssetParamsResponse`

Торговые параметры инструмента

Используется в: `get_asset_params (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `account_id` | `string` | ID аккаунта для которого подбираются торговые параметры |
| 3 | `tradeable` | `bool` | Доступны ли торговые операции Старое поле, помечено как устаревшее. Клиентам следует перейти на is_tradeable. |
| 4 | `longable` | [`assets.Longable`](STRUCTURES.md#assets-longable) | Доступны ли операции в Лонг |
| 5 | `shortable` | [`assets.Shortable`](STRUCTURES.md#assets-shortable) | Доступны ли операции в Шорт |
| 6 | `long_risk_rate` | `Decimal` | Ставка риска для операции в Лонг |
| 7 | `long_collateral` | `Money` | Сумма обеспечения для поддержания позиции Лонг |
| 8 | `short_risk_rate` | `Decimal` | Ставка риска для операции в Шорт |
| 9 | `short_collateral` | `Money` | Сумма обеспечения для поддержания позиции Шорт |
| 10 | `long_initial_margin` | `Money` | Начальные требования, сколько на счету должно быть свободных денежных средств, чтобы открыть лонг позицию, для FORTS счетов равен биржевому ГО |
| 11 | `short_initial_margin` | `Money` | Начальные требования, сколько на счету должно быть свободных денежных средств, чтобы открыть шорт позицию, для FORTS счетов равен биржевому ГО |
| 12 | `is_tradable` | `BoolValue` | Доступны ли торговые операции Новое поле. Позволяет различать false и "не установлено". |
| 13 | `price_type` | [`assets.PriceType`](STRUCTURES.md#assets-pricetype) | Допустимая цена. Помогает определить можно ли выставлять ордера с отрицательной ценой для финансового инструмента |

<a id="assets-optionschainrequest"></a>
#### `assets.OptionsChainRequest`

Запрос получения цепочки опционов

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `underlying_symbol` | `string` | Символ базового актива опциона |
| 2 | `root` | `string` | Опциональный параметр. Актуален для опционов на фьючерсы, по типу (недельные, месячные). Если параметр не указан, будут возвращены опционы с ближайшей датой экспирации. |
| 3 | `expiration_date` | `Date` | Опциональный фильтр по дате экспирации опционов. Если параметр не указан, будут возвращены опционы с ближайшей датой экспирации. |

<a id="assets-optionschainresponse"></a>
#### `assets.OptionsChainResponse`

Информация о цепочке опционов

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ базового актива опциона |
| 2 | `options` | список [`assets.Option`](STRUCTURES.md#assets-option) | Информация об опционе |

<a id="assets-schedulerequest"></a>
#### `assets.ScheduleRequest`

Запрос получения расписания инструмента

Используется в: `schedule (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |

<a id="assets-scheduleresponse"></a>
#### `assets.ScheduleResponse`

Расписание инструмента

Используется в: `schedule (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `sessions` | список [`assets.ScheduleResponse.Sessions`](STRUCTURES.md#assets-scheduleresponse-sessions) | Сессии инструмента |

<a id="assets-scheduleresponse-sessions"></a>
#### `assets.ScheduleResponse.Sessions`

Сессии

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `type` | `string` | Тип сессии |
| 2 | `interval` | `Interval` | Интервал сессии |

<a id="assets-clockrequest"></a>
#### `assets.ClockRequest`

Запрос получения времени на сервере

Используется в: `clock (запрос)`.

_Пустое сообщение._

<a id="assets-clockresponse"></a>
#### `assets.ClockResponse`

Время на сервере

Используется в: `clock (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `timestamp` | `Timestamp` | Метка времени |

<a id="assets-exchange"></a>
#### `assets.Exchange`

Информация о бирже

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `mic` | `string` | Идентификатор биржи mic |
| 2 | `name` | `string` | Наименование биржи |

<a id="assets-asset"></a>
#### `assets.Asset`

Информация об инструменте

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента ticker@mic |
| 2 | `id` | `string` | Идентификатор инструмента |
| 3 | `ticker` | `string` | Тикер инструмента |
| 4 | `mic` | `string` | mic идентификатор биржи |
| 5 | `isin` | `string` | Isin идентификатор инструмента |
| 6 | `type` | `string` | Тип инструмента |
| 7 | `name` | `string` | Наименование инструмента |
| 8 | `is_archived` | `bool` | Архивный инструмент или нет |

<a id="assets-option"></a>
#### `assets.Option`

Информация об опционе

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `type` | [`assets.Option.Type`](STRUCTURES.md#assets-option-type) | Тип инструмента |
| 4 | `contract_size` | `Decimal` | Лот, количество базового актива в инструменте |
| 5 | `trade_first_day` | `Date` | Дата старта торговли |
| 6 | `trade_last_day` | `Date` | Дата окончания торговли |
| 7 | `strike` | `Decimal` | Цена исполнения опциона |
| 9 | `multiplier` | `Decimal` | Множитель опциона |
| 10 | `expiration_first_day` | `Date` | Дата начала экспирации |
| 11 | `expiration_last_day` | `Date` | Дата окончания экспирации |

<a id="assets-longable"></a>
#### `assets.Longable`

Доступны ли операции в Лонг

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `value` | [`assets.Longable.Status`](STRUCTURES.md#assets-longable-status) | Статус инструмента |
| 2 | `halted_days` | `int32` | Сколько дней действует запрет на операции в Лонг (если есть) |

<a id="assets-shortable"></a>
#### `assets.Shortable`

Доступны ли операции в Шорт

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `value` | [`assets.Shortable.Status`](STRUCTURES.md#assets-shortable-status) | Статус инструмента |
| 2 | `halted_days` | `int32` | Сколько дней действует запрет на операции в Шорт (если есть) |

<a id="assets-getconstituentsrequest"></a>
#### `assets.GetConstituentsRequest`

Запрос на получение состава индекса

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символьный код индекса (например, "SPX@_SP", "NDX@_SCI") |
| 2 | `cursor` | `int64` | Курсор для пагинации. Указывает sec_id инструмента, с которого должен начинаться список. Для первого запроса оставьте поле пустым (значение 0). Для последующих запросов используйте значение next_cursor из предыдущего ответа. |

<a id="assets-getconstituentsresponse"></a>
#### `assets.GetConstituentsResponse`

Результат запроса состава индекса

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `constituents` | список [`assets.Constituents`](STRUCTURES.md#assets-constituents) | Список компонентов (ценных бумаг), входящих в базу расчета запрошенного индекса |
| 2 | `next_cursor` | `int64` | Курсор для получения следующей страницы. Содержит sec_id последнего инструмента в текущем списке. Передайте это значение в поле cursor следующего запроса, чтобы получить следующую часть данных. Если значение 0 или отсутствует — это последняя страница |

<a id="assets-constituents"></a>
#### `assets.Constituents`

Информация о компоненте (ценной бумаге), входящем в индекс

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символьный код инструмента |
| 2 | `name` | `string` | Полное наименование компании-эмитента |
| 3 | `sector` | `string` | Глобальный сектор экономики, к которому относится компания (например, "Technology", "Healthcare") |
| 4 | `sub_sector` | `string` | Отрасль (подотрасль) деятельности компании (например, "Software - Application") |
| 5 | `cik` | `string` | Уникальный идентификатор компании в базе данных SEC США (Central Index Key) |
| 6 | `index_inclusion_date` | `Date` | Дата добавления бумаги в индекс |

## Orders - заявки

<a id="orders-ordertype"></a>
#### `orders.OrderType` (enum)

Тип заявки

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `ORDER_TYPE_UNSPECIFIED` | Значение не указано |
| 1 | `ORDER_TYPE_MARKET` | Рыночная |
| 2 | `ORDER_TYPE_LIMIT` | Лимитная |
| 3 | `ORDER_TYPE_STOP` | Стоп заявка рыночная |
| 4 | `ORDER_TYPE_STOP_LIMIT` | Стоп заявка лимитная |
| 5 | `ORDER_TYPE_MULTI_LEG` | Мульти лег заявка |

<a id="orders-timeinforce"></a>
#### `orders.TimeInForce` (enum)

Срок действия заявки

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `TIME_IN_FORCE_UNSPECIFIED` | Значение не указано |
| 1 | `TIME_IN_FORCE_DAY` | До конца дня |
| 2 | `TIME_IN_FORCE_GOOD_TILL_CANCEL` | Действителен до отмены |
| 3 | `TIME_IN_FORCE_GOOD_TILL_CROSSING` | Действителен до пересечения |
| 4 | `TIME_IN_FORCE_EXT` | Внебиржевая торговля |
| 5 | `TIME_IN_FORCE_ON_OPEN` | На открытии биржи |
| 6 | `TIME_IN_FORCE_ON_CLOSE` | На закрытии биржи |
| 7 | `TIME_IN_FORCE_IOC` | Исполнить немедленно или отменить |
| 8 | `TIME_IN_FORCE_FOK` | Исполнить полностью или отменить |

<a id="orders-stopcondition"></a>
#### `orders.StopCondition` (enum)

Условие срабатывания стоп заявки

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `STOP_CONDITION_UNSPECIFIED` | Значение не указано |
| 1 | `STOP_CONDITION_LAST_UP` | Цена срабатывания больше текущей цены |
| 2 | `STOP_CONDITION_LAST_DOWN` | Цена срабатывания меньше текущей цены |

<a id="orders-orderstatus"></a>
#### `orders.OrderStatus` (enum)

Статус заявки

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `ORDER_STATUS_UNSPECIFIED` | Неопределенное значение |
| 1 | `ORDER_STATUS_NEW` | Новая заявка |
| 2 | `ORDER_STATUS_PARTIALLY_FILLED` | Частично исполненная |
| 3 | `ORDER_STATUS_FILLED` | Исполненная |
| 4 | `ORDER_STATUS_DONE_FOR_DAY` | Действует в течение дня |
| 5 | `ORDER_STATUS_CANCELED` | Отменена |
| 6 | `ORDER_STATUS_REPLACED` | Заменена на другую |
| 7 | `ORDER_STATUS_PENDING_CANCEL` | Ожидает отмены |
| 9 | `ORDER_STATUS_REJECTED` | Отклонена |
| 10 | `ORDER_STATUS_SUSPENDED` | Приостановлена |
| 11 | `ORDER_STATUS_PENDING_NEW` | В ожидании новой |
| 13 | `ORDER_STATUS_EXPIRED` | Истекла |
| 16 | `ORDER_STATUS_FAILED` | Ошибка |
| 17 | `ORDER_STATUS_FORWARDING` | Пересылка |
| 18 | `ORDER_STATUS_WAIT` | Ожидает |
| 19 | `ORDER_STATUS_DENIED_BY_BROKER` | Отклонено брокером |
| 20 | `ORDER_STATUS_REJECTED_BY_EXCHANGE` | Отклонено биржей |
| 21 | `ORDER_STATUS_WATCHING` | Наблюдение |
| 22 | `ORDER_STATUS_EXECUTED` | Исполнена |
| 23 | `ORDER_STATUS_DISABLED` | Отключена |
| 24 | `ORDER_STATUS_LINK_WAIT` | Ожидание ссылки |
| 27 | `ORDER_STATUS_SL_GUARD_TIME` | Защитное время SL |
| 28 | `ORDER_STATUS_SL_EXECUTED` | Исполнена по SL |
| 29 | `ORDER_STATUS_SL_FORWARDING` | Пересылка SL |
| 30 | `ORDER_STATUS_TP_GUARD_TIME` | Защитное время TP |
| 31 | `ORDER_STATUS_TP_EXECUTED` | Исполнена по TP |
| 32 | `ORDER_STATUS_TP_CORRECTION` | Коррекция TP |
| 33 | `ORDER_STATUS_TP_FORWARDING` | Пересылка TP |
| 34 | `ORDER_STATUS_TP_CORR_GUARD_TIME` | Коррекция TP в защитное время |

<a id="orders-validbefore"></a>
#### `orders.ValidBefore` (enum)

Срок действия условной заявки

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `VALID_BEFORE_UNSPECIFIED` | Значение не указано |
| 1 | `VALID_BEFORE_END_OF_DAY` | До конца торгового дня |
| 2 | `VALID_BEFORE_GOOD_TILL_CANCEL` | До отмены |
| 3 | `VALID_BEFORE_GOOD_TILL_DATE` | До указанной даты-времени. Данный тип поддерживается только при выставлении SL/TP заявок |

<a id="orders-tpspreadmeasure"></a>
#### `orders.TPSpreadMeasure` (enum)

Единица измерения величины защитного спреда для цены исполнения TP

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `TP_SPREAD_MEASURE_UNDEFINED` | Значение не указано |
| 1 | `TP_SPREAD_MEASURE_VALUE` | в единицах цены |
| 2 | `TP_SPREAD_MEASURE_PERCENT` | в процентах, с максимальной точностью до сотых процента |

<a id="orders-ordertraderequest-action"></a>
#### `orders.OrderTradeRequest.Action` (enum)

Доступные действия

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `ACTION_SUBSCRIBE` | Подписаться |
| 1 | `ACTION_UNSUBSCRIBE` | Отписаться |

<a id="orders-ordertraderequest-datatype"></a>
#### `orders.OrderTradeRequest.DataType` (enum)

Тип подписки

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `DATA_TYPE_ALL` | Все: заявки и сделки |
| 1 | `DATA_TYPE_ORDERS` | Заявки |
| 2 | `DATA_TYPE_TRADES` | Сделки |

<a id="orders-ordertraderequest"></a>
#### `orders.OrderTradeRequest`

Запрос подписки на собственные заявки и сделки. Стрим

Используется в: `subscribe_order_trade_stream (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `action` | [`orders.OrderTradeRequest.Action`](STRUCTURES.md#orders-ordertraderequest-action) | Изменение статуса подписки: подписка/отписка |
| 2 | `data_type` | [`orders.OrderTradeRequest.DataType`](STRUCTURES.md#orders-ordertraderequest-datatype) | Подписка только на заявки/ордера или на все сразу |
| 3 | `account_id` | `string` | Идентификатор аккаунта |

<a id="orders-ordertraderesponse"></a>
#### `orders.OrderTradeResponse`

Список собственных заявок и сделок

Используется в: `subscribe_order_trade_stream (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `orders` | список [`orders.OrderState`](STRUCTURES.md#orders-orderstate) | Заявки |
| 2 | `trades` | список [`AccountTrade`](STRUCTURES.md#accounttrade) | Сделки |

<a id="orders-subscribeordersrequest"></a>
#### `orders.SubscribeOrdersRequest`

Запрос подписки на собственные заявки. Стрим

Используется в: `subscribe_orders (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |

<a id="orders-subscribeordersresponse"></a>
#### `orders.SubscribeOrdersResponse`

Список собственных заявок

Используется в: `subscribe_orders (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `orders` | список [`orders.OrderState`](STRUCTURES.md#orders-orderstate) | Заявки |

<a id="orders-subscribetradesrequest"></a>
#### `orders.SubscribeTradesRequest`

Запрос подписки на собственные сделки. Стрим

Используется в: `subscribe_trades (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |

<a id="orders-subscribetradesresponse"></a>
#### `orders.SubscribeTradesResponse`

Список собственных сделок

Используется в: `subscribe_trades (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `trades` | список [`AccountTrade`](STRUCTURES.md#accounttrade) | Сделки |

<a id="orders-getorderrequest"></a>
#### `orders.GetOrderRequest`

Запрос на получение конкретного ордера

Используется в: `get_order (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |
| 2 | `order_id` | `string` | Идентификатор заявки |

<a id="orders-order"></a>
#### `orders.Order`

Информация о заявке

Используется в: `place_order (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |
| 2 | `symbol` | `string` | Символ инструмента |
| 3 | `quantity` | `Decimal` | Количество в шт. |
| 4 | `side` | [`Side`](STRUCTURES.md#side) | Сторона (long или short) |
| 5 | `type` | [`orders.OrderType`](STRUCTURES.md#orders-ordertype) | Тип заявки |
| 6 | `time_in_force` | [`orders.TimeInForce`](STRUCTURES.md#orders-timeinforce) | Срок действия заявки |
| 7 | `limit_price` | `Decimal` | Необходимо для лимитной и стоп лимитной заявки |
| 8 | `stop_price` | `Decimal` | Необходимо для стоп рыночной и стоп лимитной заявки |
| 9 | `stop_condition` | [`orders.StopCondition`](STRUCTURES.md#orders-stopcondition) | Необходимо для стоп рыночной и стоп лимитной заявки |
| 10 | `legs` | список [`orders.Leg`](STRUCTURES.md#orders-leg) | Необходимо для мульти лег заявки |
| 11 | `client_order_id` | `string` | Уникальный идентификатор заявки. Автоматически генерируется, если не отправлен. (максимум 20 символов) |
| 12 | `valid_before` | [`orders.ValidBefore`](STRUCTURES.md#orders-validbefore) | Срок действия условной заявки. Заполняется для заявок с типом ORDER_TYPE_STOP, ORDER_TYPE_STOP_LIMIT |
| 13 | `comment` | `string` | Метка заявки. (максимум 128 символов) |

<a id="orders-leg"></a>
#### `orders.Leg`

Лег

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `quantity` | `Decimal` | Количество |
| 3 | `side` | [`Side`](STRUCTURES.md#side) | Сторона |

<a id="orders-orderstate"></a>
#### `orders.OrderState`

Состояние заявки

Используется в: `place_order (ответ)`, `cancel_order (ответ)`, `get_order (ответ)`, `place_sltp_order (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `order_id` | `string` | Идентификатор заявки |
| 2 | `exec_id` | `string` | Идентификатор исполнения |
| 3 | `status` | [`orders.OrderStatus`](STRUCTURES.md#orders-orderstatus) | Статус заявки |
| 4 | `order` | [`orders.Order`](STRUCTURES.md#orders-order) | Заявка |
| 5 | `transact_at` | `Timestamp` | Дата и время выставления заявки |
| 6 | `accept_at` | `Timestamp` | Дата и время принятия заявки |
| 7 | `withdraw_at` | `Timestamp` | Дата и время  отмены заявки |
| 8 | `initial_quantity` | `Decimal` | Начальный объем (заполняется только для биржевой заявки) |
| 9 | `executed_quantity` | `Decimal` | Исполненный объем (заполняется только для биржевой заявки) |
| 10 | `remaining_quantity` | `Decimal` | Оставшийся объем (заполняется только для биржевой заявки) |
| 11 | `sltp_order` | [`orders.SLTPOrder`](STRUCTURES.md#orders-sltporder) | Информация о SL/TP заявке |

<a id="orders-ordersrequest"></a>
#### `orders.OrdersRequest`

Запрос получения списка торговых заявок

Используется в: `get_orders (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |

<a id="orders-ordersresponse"></a>
#### `orders.OrdersResponse`

Список торговых заявок

Используется в: `get_orders (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `orders` | список [`orders.OrderState`](STRUCTURES.md#orders-orderstate) | Заявки |

<a id="orders-cancelorderrequest"></a>
#### `orders.CancelOrderRequest`

Запрос отмены торговой заявки

Используется в: `cancel_order (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |
| 2 | `order_id` | `string` | Идентификатор заявки |

<a id="orders-sltporder"></a>
#### `orders.SLTPOrder`

Информация о SL/TP заявке

Используется в: `place_sltp_order (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `account_id` | `string` | Идентификатор аккаунта |
| 2 | `symbol` | `string` | Символ инструмента |
| 3 | `side` | [`Side`](STRUCTURES.md#side) | Сторона для обеих заявок |
| 4 | `quantity_sl` | `Decimal` | Количество в шт для SL |
| 5 | `sl_price` | `Decimal` | Параметр условия цены для SL части |
| 6 | `limit_price` | `Decimal` | Если указано, после активации SL будет выставлена лимитная заявка с этой ценой |
| 10 | `quantity_tp` | `Decimal` | Количество в шт для TP |
| 11 | `tp_price` | `Decimal` | Параметр условия цены для TP части |
| 12 | `tp_guard_spread` | `Decimal` | Если указано, после активации TP будет выставлена лимитная заявка с учетом защитного спрэда |
| 13 | `tp_spread_measure` | [`orders.TPSpreadMeasure`](STRUCTURES.md#orders-tpspreadmeasure) | Единица измерения величины защитного спреда |
| 20 | `client_order_id` | `string` | Уникальный идентификатор заявки. Автоматически генерируется, если не отправлен. (максимум 20 символов) |
| 21 | `valid_before` | [`orders.ValidBefore`](STRUCTURES.md#orders-validbefore) | Срок действия условной заявки. Если не заполнено, то по умолчанию выставляется VALID_BEFORE_GOOD_TILL_CANCEL |
| 22 | `valid_expiry_time` | `Timestamp` | Временная метка прекращения действия SL/TP заявки |
| 23 | `comment` | `string` | Метка заявки. (максимум 128 символов) |

## MarketData - котировки и свечи

<a id="marketdata-timeframe"></a>
#### `marketdata.TimeFrame` (enum)

Доступные таймфреймы для свечей

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `TIME_FRAME_UNSPECIFIED` | Таймфрейм не указан |
| 1 | `TIME_FRAME_M1` | 1 минута. Глубина данных 7 дней. |
| 5 | `TIME_FRAME_M5` | 5 минут. Глубина данных 30 дней. |
| 9 | `TIME_FRAME_M15` | 15 минут. Глубина данных 30 дней. |
| 11 | `TIME_FRAME_M30` | 30 минут. Глубина данных 30 дней. |
| 12 | `TIME_FRAME_H1` | 1 час. Глубина данных 30 дней. |
| 13 | `TIME_FRAME_H2` | 2 часа. Глубина данных 30 дней. |
| 15 | `TIME_FRAME_H4` | 4 часа. Глубина данных 30 дней. |
| 17 | `TIME_FRAME_H8` | 8 часов. Глубина данных 30 дней. |
| 19 | `TIME_FRAME_D` | День. Глубина данных 365 дней. |
| 20 | `TIME_FRAME_W` | Неделя. Глубина данных 365*5 дней. |
| 21 | `TIME_FRAME_MN` | Месяц. Глубина данных 365*5 дней. |
| 22 | `TIME_FRAME_QR` | Квартал. Глубина данных 365*5 дней. |

<a id="marketdata-orderbook-row-action"></a>
#### `marketdata.OrderBook.Row.Action` (enum)

Команда

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `ACTION_UNSPECIFIED` | Действие не указано |
| 1 | `ACTION_REMOVE` | Удалить |
| 2 | `ACTION_ADD` | Добавить |
| 3 | `ACTION_UPDATE` | Обновить |

<a id="marketdata-streamorderbook-row-action"></a>
#### `marketdata.StreamOrderBook.Row.Action` (enum)

Команда

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `ACTION_UNSPECIFIED` | Действие не указано |
| 1 | `ACTION_REMOVE` | Удалить |
| 2 | `ACTION_ADD` | Добавить |
| 3 | `ACTION_UPDATE` | Обновить |

<a id="marketdata-barsrequest"></a>
#### `marketdata.BarsRequest`

Запрос получения исторических данных по инструменту (агрегированные свечи)

Используется в: `bars (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `timeframe` | [`marketdata.TimeFrame`](STRUCTURES.md#marketdata-timeframe) | Необходимый таймфрейм |
| 3 | `interval` | `Interval` | Начало и окончание запрашиваемого периода |

<a id="marketdata-barsresponse"></a>
#### `marketdata.BarsResponse`

Список агрегированных свеч

Используется в: `bars (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `bars` | список [`marketdata.Bar`](STRUCTURES.md#marketdata-bar) | Агрегированная свеча |

<a id="marketdata-quoterequest"></a>
#### `marketdata.QuoteRequest`

Запрос получения последней котировки по инструменту

Используется в: `last_quote (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |

<a id="marketdata-quoteresponse"></a>
#### `marketdata.QuoteResponse`

Последняя котировка по инструменту

Используется в: `last_quote (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `quote` | [`marketdata.Quote`](STRUCTURES.md#marketdata-quote) | Цена последней сделки |

<a id="marketdata-orderbookrequest"></a>
#### `marketdata.OrderBookRequest`

Запрос получения текущего стакана по инструменту

Используется в: `order_book (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |

<a id="marketdata-orderbookresponse"></a>
#### `marketdata.OrderBookResponse`

Текущий стакан по инструменту

Используется в: `order_book (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `orderbook` | [`marketdata.OrderBook`](STRUCTURES.md#marketdata-orderbook) | Стакан |

<a id="marketdata-latesttradesrequest"></a>
#### `marketdata.LatestTradesRequest`

Запрос списка последних сделок по инструменту

Используется в: `latest_trades (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |

<a id="marketdata-latesttradesresponse"></a>
#### `marketdata.LatestTradesResponse`

Список последних сделок по инструменту

Используется в: `latest_trades (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `trades` | список [`marketdata.Trade`](STRUCTURES.md#marketdata-trade) | Список последних сделок |

<a id="marketdata-subscribequoterequest"></a>
#### `marketdata.SubscribeQuoteRequest`

Запрос подписки на котировки по инструменту. Стрим

Используется в: `subscribe_quote (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbols` | список `string` | Список символов инструментов |

<a id="marketdata-subscribequoteresponse"></a>
#### `marketdata.SubscribeQuoteResponse`

Котировки по инструменту. Стрим

Используется в: `subscribe_quote (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `quote` | список [`marketdata.Quote`](STRUCTURES.md#marketdata-quote) | Список котировок |
| 2 | `error` | [`marketdata.StreamError`](STRUCTURES.md#marketdata-streamerror) | Ошибка стрим сервиса |

<a id="marketdata-subscribeorderbookrequest"></a>
#### `marketdata.SubscribeOrderBookRequest`

Запрос подписки на стакан по инструменту. Стрим

Используется в: `subscribe_order_book (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |

<a id="marketdata-subscribeorderbookresponse"></a>
#### `marketdata.SubscribeOrderBookResponse`

Стакан по инструменту. Стрим

Используется в: `subscribe_order_book (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `order_book` | список [`marketdata.StreamOrderBook`](STRUCTURES.md#marketdata-streamorderbook) | Список стакан стримов |

<a id="marketdata-subscribebarsrequest"></a>
#### `marketdata.SubscribeBarsRequest`

Запрос подписки на агрегированные свечи. Стрим

Используется в: `subscribe_bars (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `timeframe` | [`marketdata.TimeFrame`](STRUCTURES.md#marketdata-timeframe) | Необходимый таймфрейм |

<a id="marketdata-subscribebarsresponse"></a>
#### `marketdata.SubscribeBarsResponse`

Список агрегированных свеч. Стрим

Используется в: `subscribe_bars (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `bars` | список [`marketdata.Bar`](STRUCTURES.md#marketdata-bar) | Агрегированная свеча |

<a id="marketdata-bar"></a>
#### `marketdata.Bar`

Информация об агрегированной свече

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `timestamp` | `Timestamp` | Метка времени |
| 2 | `open` | `Decimal` | Цена открытия свечи |
| 3 | `high` | `Decimal` | Максимальная цена свечи |
| 4 | `low` | `Decimal` | Минимальная цена свечи |
| 5 | `close` | `Decimal` | Цена закрытия свечи |
| 6 | `volume` | `Decimal` | Объём торгов за свечу в шт. |

<a id="marketdata-quote"></a>
#### `marketdata.Quote`

Информация о котировке

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `timestamp` | `Timestamp` | Метка времени |
| 3 | `ask` | `Decimal` | Аск. 0 при отсутствии активного аска |
| 4 | `ask_size` | `Decimal` | Размер аска |
| 5 | `bid` | `Decimal` | Бид. 0 при отсутствии активного бида |
| 6 | `bid_size` | `Decimal` | Размер бида |
| 7 | `last` | `Decimal` | Цена последней сделки |
| 8 | `last_size` | `Decimal` | Размер последней сделки |
| 9 | `volume` | `Decimal` | Дневной объем сделок |
| 10 | `turnover` | `Decimal` | Дневной оборот сделок |
| 11 | `open` | `Decimal` | Цена открытия. Дневная |
| 12 | `high` | `Decimal` | Максимальная цена. Дневная |
| 13 | `low` | `Decimal` | Минимальная цена. Дневная |
| 14 | `close` | `Decimal` | Цена закрытия. Дневная |
| 15 | `change` | `Decimal` | Изменение цены (last минус close) |
| 16 | `open_interest` | `Decimal` | Открытый интерес. Общее количество незакрытых (активных) контрактов по деривативу. |
| 50 | `option` | [`marketdata.Quote.Option`](STRUCTURES.md#marketdata-quote-option) | Информация об опционе _(oneof `additions`)_ |

<a id="marketdata-quote-option"></a>
#### `marketdata.Quote.Option`

Информация об опционе

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `open_interest` | `Decimal` | Открытый интерес |
| 2 | `implied_volatility` | `Decimal` | Подразумеваемая волатильность |
| 3 | `theoretical_price` | `Decimal` | Теоретическая цена |
| 4 | `delta` | `Decimal` | Delta |
| 5 | `gamma` | `Decimal` | Gamma |
| 6 | `theta` | `Decimal` | Theta |
| 7 | `vega` | `Decimal` | Vega |
| 8 | `rho` | `Decimal` | Rho |

<a id="marketdata-orderbook"></a>
#### `marketdata.OrderBook`

Информация о стакане

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `rows` | список [`marketdata.OrderBook.Row`](STRUCTURES.md#marketdata-orderbook-row) | Уровни стакана |

<a id="marketdata-orderbook-row"></a>
#### `marketdata.OrderBook.Row`

Информация об уровне в стакане (строке)

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `price` | `Decimal` | Цена |
| 2 | `sell_size` | `Decimal` | Размер на продажу _(oneof `side`)_ |
| 3 | `buy_size` | `Decimal` | Размер на покупку _(oneof `side`)_ |
| 4 | `action` | [`marketdata.OrderBook.Row.Action`](STRUCTURES.md#marketdata-orderbook-row-action) | Команда |
| 5 | `mpid` | `string` | Идентификатор участника рынка |
| 6 | `timestamp` | `Timestamp` | Метка времени |

<a id="marketdata-trade"></a>
#### `marketdata.Trade`

Информация о сделке

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `trade_id` | `string` | Идентификатор сделки, отправленный биржей |
| 2 | `mpid` | `string` | Идентификатор участника рынка |
| 3 | `timestamp` | `Timestamp` | Метка времени |
| 4 | `price` | `Decimal` | Цена сделки |
| 5 | `size` | `Decimal` | Размер сделки |
| 6 | `side` | [`Side`](STRUCTURES.md#side) | Сторона сделки (buy или sell) |
| 7 | `open_interest` | `Decimal` | Открытый интерес на момент совершения сделки. |

<a id="marketdata-streamerror"></a>
#### `marketdata.StreamError`

Ошибка стрим сервиса

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `code` | `int32` | Код ошибки |
| 2 | `description` | `string` | Описание ошибки |

<a id="marketdata-streamorderbook"></a>
#### `marketdata.StreamOrderBook`

Стакан по инструменту. Стрим

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `rows` | список [`marketdata.StreamOrderBook.Row`](STRUCTURES.md#marketdata-streamorderbook-row) | Уровни стакана |

<a id="marketdata-streamorderbook-row"></a>
#### `marketdata.StreamOrderBook.Row`

Информация об уровне в стакане (строке)

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `price` | `Decimal` | Цена |
| 2 | `sell_size` | `Decimal` | Размер на продажу _(oneof `side`)_ |
| 3 | `buy_size` | `Decimal` | Размер на покупку _(oneof `side`)_ |
| 4 | `action` | [`marketdata.StreamOrderBook.Row.Action`](STRUCTURES.md#marketdata-streamorderbook-row-action) | Команда |
| 5 | `mpid` | `string` | Идентификатор участника рынка |
| 6 | `timestamp` | `Timestamp` | Метка времени |

<a id="marketdata-subscribelatesttradesrequest"></a>
#### `marketdata.SubscribeLatestTradesRequest`

Запрос списка последних сделок по инструменту. Стрим

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |

<a id="marketdata-subscribelatesttradesresponse"></a>
#### `marketdata.SubscribeLatestTradesResponse`

Список последних сделок по инструменту. Стрим

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `symbol` | `string` | Символ инструмента |
| 2 | `trades` | список [`marketdata.Trade`](STRUCTURES.md#marketdata-trade) | Список сделок |

## Reports - отчёты по счёту

<a id="reports-reportform"></a>
#### `reports.ReportForm` (enum)

Форма отчета

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `REPORT_FORM_UNKNOWN` | Не указана |
| 1 | `REPORT_FORM_SHORT` | Краткая |
| 2 | `REPORT_FORM_LONG` | Полная |

<a id="reports-reportcreationstatus"></a>
#### `reports.ReportCreationStatus` (enum)

Статус генерации отчёта

| Значение | Имя | Описание |
|--:|---|---|
| 0 | `NOT_FOUND` | Не найден |
| 1 | `PENDING` | Ожидает генерации |
| 2 | `IN_PROGRESS` | Генерация запущена |
| 3 | `SUCCESS` | Генерация завершена успешно |
| 4 | `ERROR` | Генерация завершена с ошибкой |

<a id="reports-createaccountreportrequest"></a>
#### `reports.CreateAccountReportRequest`

Запрос на генерацию отчёта по счёту за период

Используется в: `create_account_report (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `date_range` | [`reports.DateRange`](STRUCTURES.md#reports-daterange) | Временной интервал. Максимальный интервал дат - 92 дня |
| 2 | `report_form` | [`reports.ReportForm`](STRUCTURES.md#reports-reportform) | Форма отчета |
| 3 | `account_id` | `int64` | Идентификатор счета |

<a id="reports-createaccountreportresponse"></a>
#### `reports.CreateAccountReportResponse`

Информация о генерируемом отчёте

Используется в: `create_account_report (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `report_id` | `string` | Идентификатор отчёта |

<a id="reports-getaccountreportinforequest"></a>
#### `reports.GetAccountReportInfoRequest`

Запрос на получение статуса генерации отчёта

Используется в: `get_account_report_info (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `report_id` | `string` | Идентификатор отчёта |

<a id="reports-getaccountreportinforesponse"></a>
#### `reports.GetAccountReportInfoResponse`

Информация о статусе генерации отчёта

Используется в: `get_account_report_info (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `info` | [`reports.AccountReportInfo`](STRUCTURES.md#reports-accountreportinfo) | Информация о статусе генерации отчёта |

<a id="reports-subscribeaccountreportinforequest"></a>
#### `reports.SubscribeAccountReportInfoRequest`

Запрос подписки на получение статуса генерации отчёта

Используется в: `subscribe_account_report_info (запрос)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `report_id` | `string` | Идентификатор отчёта |

<a id="reports-subscribeaccountreportinforesponse"></a>
#### `reports.SubscribeAccountReportInfoResponse`

Информация о статусе генерации отчёта. Стрим

Используется в: `subscribe_account_report_info (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `info` | [`reports.AccountReportInfo`](STRUCTURES.md#reports-accountreportinfo) | Информация о статусе генерации отчёта |

<a id="reports-accountreportinfo"></a>
#### `reports.AccountReportInfo`

Информация о статусе генерации отчёта

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `report_id` | `string` | Идентификатор отчёта |
| 2 | `status` | [`reports.ReportCreationStatus`](STRUCTURES.md#reports-reportcreationstatus) | Статус генерации отчёта |
| 3 | `date_range` | [`reports.DateRange`](STRUCTURES.md#reports-daterange) | Временной интервал отчёта. Берётся из запроса на генерацию отчёта |
| 4 | `report_form` | [`reports.ReportForm`](STRUCTURES.md#reports-reportform) | Форма отчета. Берётся из запроса на генерацию отчёта |
| 5 | `account_id` | `int64` | Идентификатор счета. Берётся из запроса на генерацию отчёта |
| 6 | `url` | `StringValue` | Ссылка на скачивание отчёта. Появляется только в случае успешной генерации отчёта (ReportCreationStatus = SUCCESS) |

<a id="reports-daterange"></a>
#### `reports.DateRange`

Временной интервал

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `date_begin` | `Timestamp` | Дата начала временного интервала |
| 2 | `date_end` | `Timestamp` | Дата конца временного интервала |

## Metrics - использование API

<a id="metrics-getusagemetricsrequest"></a>
#### `metrics.GetUsageMetricsRequest`

Запрос получения текущих метрик использования

Используется в: `get_usage_metrics (запрос)`.

_Пустое сообщение._

<a id="metrics-getusagemetricsresponse"></a>
#### `metrics.GetUsageMetricsResponse`

Информация о текущих метриках использования

Используется в: `get_usage_metrics (ответ)`.

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `quotas` | список [`metrics.GetUsageMetricsResponse.QuotaUsage`](STRUCTURES.md#metrics-getusagemetricsresponse-quotausage) | Список текущих квот и их использование. |

<a id="metrics-getusagemetricsresponse-quotausage"></a>
#### `metrics.GetUsageMetricsResponse.QuotaUsage`

Квота

| № | Поле | Тип | Описание |
|--:|---|---|---|
| 1 | `name` | `string` | Название метода |
| 2 | `limit` | `int64` | Общий лимит по данной квоте. |
| 3 | `remaining` | `int64` | Сколько осталось доступных единиц в текущем окне. |
| 4 | `reset_time` | `Timestamp` | Время, когда счетчик квоты будет сброшен (начало нового окна). |
