# Changelog

## Unreleased

## v1.0.1 — 2026-10-05

**Первая версия пакета (1.0.0).** Общий клиент Finam Trade API для AFB и BF, вынесенный
из BF (`belphegor/brokers/finam`):
- vendored proto Finam Trade API 2.16.0 и скрипт `scripts/generate.py`; stubs в
  `finam_client/grpc_gen`;
- `FinamApiClient` без зависимостей от BF: `ClientConfig`/`GrpcTuning` вместо pydantic-конфига,
  `error_factory` вместо жёсткого `BrokerError`;
- `finam_client.assets`: нейтральные модели `AssetListItem`, `AssetInfo` (с `board`),
  `AssetParams` (с `price_type`), `Bar`;
- `finam_client.venue`: трансляция площадок каталога и Finam (предварительная таблица,
  подтверждённая пара `MISX:RFUD ↔ RTSX:FUT`);
- `finam_client.proto_values`: Decimal/Money/Timestamp/Date и словарь таймфреймов;
- скрипты версионирования и релиза скопированы из AFB-BF-protocol.
- таблица `finam_client.venue` подтверждена сверкой по всем активным листингам каталога
  AFB (561/561); правила сопоставления при пустом board — в докстринге модуля;
- `validate_finam_symbol` принимает реальные символы Finam (`/`, пробел, `+`, `$`, `(`, CJK,
  mic вида `#WWCP`/`_CRYP`): строгая регулярка отвергала 2,3% AllAssets (2,6% активных);
- `RESOURCE_EXHAUSTED` (лимит Finam ~200 запросов/мин) повторяется для идемпотентных
  вызовов с собственной паузой `GrpcTuning.rate_limit_backoff_sec`; ордера по-прежнему
  не повторяются;
- `scripts/verify_finam_venue.py` — read-only сверка каталога с Finam (этап 0).
- документация: `docs/API.md` (методы клиента с параметрами, RPC, полями запроса и ответа),
  `docs/STRUCTURES.md` (все структуры и enum из proto с описаниями полей), `docs/USAGE.md`
  (подключение, символы, свечи, лимиты). `API.md` и `STRUCTURES.md` генерирует
  `scripts/generate_docs.py`, `tests/test_docs_in_sync.py` проверяет актуальность.
- proto обновлены с Finam Trade API 2.16.0 до **2.23.0** (изменения только добавляющие, удалённых объявлений нет): `Position`/`trade`: `current_price_currency`, `average_price_currency`, `change_original`, `symbols`, `trade_lot_size`, `is_data_snapshot` в потоках; `SLTPQtyMeasure` и `sl_qty_measure`/`tp_qty_measure`, `sl_guard_time`/`tp_guard_time`, `triggered_order_id`, `status_description` у заявок; `commission` у сделок; в `corporateactions` - RPC `GetFutureBondsEvents`/`GetPastBondsEvents` (сервис не генерируется клиентом). Stubs перегенерированы, `docs/API.md` и `docs/STRUCTURES.md` обновлены.
- контроль актуальности proto: `proto/UPSTREAM.json` (тег, коммит upstream и хэш скопированного дерева), `scripts/proto_sync.py` - `check` (хэш proto/ и соответствие stubs дескрипторам, офлайн), `check --online` (есть ли более новый релизный тег в FinamWeb/finam-trade-api), `update [--tag]` (забрать тег, заменить proto/, перегенерировать stubs и документацию, показать удалённые/изменённые объявления). Проверка офлайн входит в `pytest`; `run/release.sh` сверяется с upstream перед `tag`/`publish` (новый тег - предупреждение, `PROTO_STRICT=1` - ошибка).
- `GrpcTuning.min_interval_sec`: минимальная пауза между унарными вызовами одного клиента (общая для потоков; по умолчанию 0 - выключено). Нужна массовым задачам под лимит Finam ~200 запросов/мин (AFB ставит 0.4 с).
