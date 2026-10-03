# Finam-client

Общий клиент Finam Trade API (gRPC) для **AFB** и **BF**. Официальные proto,
сгенерированные stubs, тонкий клиент с JWT/retry, нейтральные модели ответов и
таблица трансляции площадок «наш каталог ↔ Finam» живут в одном месте.

Модель репозитория — как у [AFB-BF-protocol](../AFB-BF-protocol): ветка `develop`
для разработки, `main` для выпущенных версий; потребители пинят `@develop`, сборка
образов берёт соседнюю папку (диск) или `main` с GitHub.

## Состав

| Модуль | Назначение |
|---|---|
| `finam_client.client.FinamApiClient` | gRPC-клиент: JWT (Auth, фоновое обновление), retry/re-auth, unary и stream методы Auth/Accounts/Assets/Orders/MarketData/Reports |
| `finam_client.config` | `ClientConfig`, `GrpcTuning` (dataclass, без pydantic) |
| `finam_client.errors` | `FinamError`, `ErrorCategory`; `error_factory` позволяет потребителю бросать свой тип ошибок |
| `finam_client.symbols` | валидация `ticker@mic` |
| `finam_client.venue` | трансляция `(mic, board)` каталога ↔ Finam (`MISX:RFUD ↔ RTSX:FUT`) |
| `finam_client.assets` | `AssetListItem` (Assets/AllAssets, без board), `AssetInfo` (GetAsset, с board), `AssetParams` (GetAssetParams, с `price_type`), `Bar` |
| `finam_client.proto_values` | Decimal/Money/Timestamp/Date, словарь таймфреймов |
| `finam_client.grpc_gen` | сгенерированные stubs (в git) |

Пакет не зависит от `afb_bf_protocol`, `belphegor` и AFB.

## Разработка

```bash
pyenv activate fc-3_14_7-env        # .python-version
pip install -e ".[dev]"
pytest
```

Обновление proto брокера — [`docs/FINAM_PROTO_VERSION.md`](docs/FINAM_PROTO_VERSION.md).
Версии и релиз — [`VERSIONING.md`](VERSIONING.md), [`run/README.md`](run/README.md).

## Подключение в потребителе

```
finam-client @ git+https://github.com/Rolo837/Finam-client.git@develop
```

Пины и версии выставляет владелец репозитория.
