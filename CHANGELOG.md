# Changelog

## Unreleased

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
  mic вида `#WWCP`/`_CRYP`): строгая регулярка отвергала 6% AllAssets;
- `RESOURCE_EXHAUSTED` (лимит Finam ~200 запросов/мин) повторяется для идемпотентных
  вызовов с собственной паузой `GrpcTuning.rate_limit_backoff_sec`; ордера по-прежнему
  не повторяются;
- `scripts/verify_finam_venue.py` — read-only сверка каталога с Finam (этап 0).
