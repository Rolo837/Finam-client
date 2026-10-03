# Как пользоваться Finam-client

Справочник по методам и структурам - [API.md](API.md) и [STRUCTURES.md](STRUCTURES.md)
(генерируются из кода и proto). Здесь - то, что из них не видно: жизненный цикл, лимиты,
форматы и подводные камни, проверенные на живом API (сверка 2026-10-03, read-only токен).

## Подключение

```python
from finam_client import ClientConfig, FinamApiClient

client = FinamApiClient(ClientConfig(secret_file="secrets/finam_ro.token"))
client.refresh_session()                       # Auth -> JWT (иначе JWT выпустится при первом вызове)
account_id = client.token_details().account_ids[0]
```

- `secret_file` - файл с одной строкой: secret-токен Finam. Клиент сам обменивает его на JWT
  и перевыпускает JWT при `UNAUTHENTICATED` и за `jwt_refresh_skew_sec` до истечения.
- Для долгоживущего процесса запустите `client.start_jwt_renewal_background(interval_sec)`
  и (если держите стримы) `client.set_on_jwt_renewed(cb)`: стрим, открытый со старым JWT,
  нужно пересоздать после обновления токена.
- Вызовы синхронные; в `asyncio` их выполняют в executor. gRPC-канал допускает вызовы из
  нескольких потоков (массовая сверка шла в 4 потока), но выпуск JWT клиент блокировкой не
  защищает: при параллельной работе возможен повторный `Auth`, это безвредно.
- `close()` обязателен: останавливает поток обновления JWT и закрывает канал.

### Read-only токен

`token_details().readonly` - признак токена только для чтения. Сервис, который не должен
торговать (AFB), обязан проверять его при старте и не включаться, если он `False`. Токен
`finam_ro.token` отдаёт `readonly=True`, один счёт и рыночные данные примерно по 65 MIC.

## Символы и площадки

- Символ Finam - `ticker@mic`: `SBER@MISX`, `CRZ6@RTSX`, `BZ@IFEU`. Делится по **последнему**
  `@`. Регистр тикера значим.
- Реальные символы не ограничены латиницей и цифрами: `BRK/B@XNYS`, `EURUSD@#WWCP`,
  `(USD+EUR)CB@#RCBR`, `$DJUSEN@_SCI`, тикеры с пробелом. `validate_finam_symbol` отвергает
  только строку без `@` или с пустым тикером/mic.
- **У одного тикера на разных площадках разные символы**, поэтому symbol нельзя вывести из
  `instrument_key`: его нужно брать у брокера (`AllAssets` / `GetAsset`) и хранить.
- `board` приходит **только** в `GetAsset` (`AssetInfo.board`), в `Assets`/`AllAssets` его нет.
  Он пуст для зарубежных площадок, индексов, архивных инструментов и иногда для CETS.
- Площадки каталога и Finam различаются у срочного рынка MOEX: `MISX/RFUD` <-> `RTSX/FUT`.
  Пользуйтесь `to_finam_venue` / `from_finam_venue`. Индексы MOEX публикуются под `MISX` и
  `RTSX` с одинаковыми рядами.

Сопоставление записи каталога с Finam (проверено на 561 листинге, 561/561):

1. кандидаты - символы `AllAssets` с тем же `ticker`;
2. `GetAsset` по каждому; `from_finam_venue(asset.mic, asset.board)` + ticker должны дать
   `(mic, board, ticker)` записи;
3. если board у Finam пуст - сравнивать только `(mic, ticker)`;
4. если подходят несколько - выбрать тот, чей mic предсказывает `to_finam_venue`.

## Каталог инструментов

| Вызов | Что вернёт | Заметки |
|---|---|---|
| `assets()` | торгуемые инструменты (~17 тыс.) | без архивных, без пагинации |
| `all_assets(cursor, only_active)` | одна страница | `next_cursor == 0` - конец |
| `iter_all_assets(only_active=False)` | все страницы потоком | ~282-287 тыс. строк, ~96 страниц, ~6-9 с без лимита |
| `get_asset(symbol, account_id)` | `board`, шаг цены, лот, экспирация | единственный источник `board` |
| `get_asset_params(symbol, account_id)` | торгуемость, ГО, `price_type` | зависит от счёта |

`only_active=False` включает индикативные и архивные инструменты (более половины записей).
`GetAsset` по архивному symbol отвечает, но `board` пуст и свечей нет.

## Свечи

```python
from datetime import datetime, timedelta, timezone
from finam_client.grpc_imports import marketdata_service as md

end = datetime.now(timezone.utc)
resp = client.bars("SBER@MISX", md.TimeFrame.TIME_FRAME_H1, end - timedelta(days=30), end)
```

Максимальная длина запрашиваемого интервала (шире - `INVALID_ARGUMENT: Invalid date range`):

| Таймфрейм | Максимум |
|---|---|
| M1 | 7 дней |
| M5, M15, M30, H1, H2, H4, H8 | 30 дней |
| D | 365 дней |
| W, MN, QR | 1825 дней |

Для истории длиннее запрашивайте кусками. Таймфрейма 10 минут у Finam нет (BF собирает его ресемплом из M5).
`SubscribeBars` открывается и в выходной день. Свечи отдаются не только по акциям и
фьючерсам, но и по индексам (`MOEXOG@MISX`, `IBOV@BVMF`), непрерывным фьючерсам на сырьё
(`BZ@IFEU`, `CL@XNYM`, `GC@XCEC`) и `GC@#WWCP` (XAU/USD); по части индексов баров нет
(`MTZGC@RTSX`) - проверяйте `len(resp.bars)`.

## Ошибки и лимиты

- Все ошибки - `FinamError` (или тип из `error_factory`) с `category`, `retryable`, `broker_code`.
- **Лимит Finam - около 200 запросов в минуту на токен.** Превышение даёт
  `RESOURCE_EXHAUSTED` ("Too Many Requests"). Клиент повторяет идемпотентные вызовы с паузой
  `rate_limit_backoff_sec * номер_попытки`, но для массовых задач (сотни `GetAsset`) нужен
  свой троттлинг порядка 150 запросов в минуту: на этом уровне 852 вызова прошли без отказов.
- `place_order` и `place_sltp_order` не повторяются. `broker_code == "place_timeout"` -
  таймаут заявки, исход неизвестен; сверяйтесь по `client_order_id`.
- `broker_code == "auction_only"` - отказ из-за аукциона, заявку можно повторить после него.

## Стримы

`subscribe_*` возвращают gRPC-итератор (блокирующий). Стрим не переподключается сам:
после ошибки или смены JWT его нужно открыть заново. `subscribe_order_trade_stream`
работает вместе с `subscribe_order_trade` / `unsubscribe_order_trade`, которые ставят запросы в
очередь.

```python
for event in client.subscribe_bars("SBER@MISX", md.TimeFrame.TIME_FRAME_M1):
    handle(event)           # SubscribeBarsResponse
```

## Нейтральные модели

Если не нужен protobuf, используйте мапперы из `finam_client.assets`:

```python
from finam_client.assets import asset_info_from_proto, asset_params_from_proto

info = asset_info_from_proto(client.get_asset("SBER@MISX", account_id))
params = asset_params_from_proto(client.get_asset_params("SBER@MISX", account_id), account_id)
print(info.board, info.price_step, params.tradable, params.price_type)
```

## Обновление proto и документации

- Новая версия proto - [FINAM_PROTO_VERSION.md](FINAM_PROTO_VERSION.md).
- После изменения клиента или proto: `python scripts/generate_docs.py`.
  `tests/test_docs_in_sync.py` падает, если `API.md` / `STRUCTURES.md` устарели.
