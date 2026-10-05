# Finam Trade API — версия proto

Источник: <https://github.com/FinamWeb/finam-trade-api> (каталог `proto/`). Происхождение
скопированных файлов записано в **`proto/UPSTREAM.json`** (тег, коммит, хэш дерева, дата) -
вручную его не правят, его пишет `scripts/proto_sync.py`.

| Параметр | Значение |
| --- | --- |
| Тег / коммит | см. `proto/UPSTREAM.json` |
| Копия proto | `proto/` (весь каталог `proto/` официального репозитория, включая `google/*`) |
| Сгенерированные stubs | `finam_client/grpc_gen/` (закоммичены) |
| Генерация | `scripts/generate.py` |
| Контроль актуальности | `scripts/proto_sync.py` |

## Контроль актуальности

```bash
python scripts/proto_sync.py check            # офлайн: хэш proto/ == записанному, stubs == proto
python scripts/proto_sync.py check --online   # + новый ли релизный тег в upstream (git ls-remote)
python scripts/proto_sync.py check --online --strict   # exit 3, если upstream новее; exit 2, если недоступен
```

Что ловит каждая проверка:

| Проверка | Ловит |
|---|---|
| хэш `proto/` | правки proto вручную, неполное копирование |
| stubs == proto | обновили proto, но не запустили `generate.py` (сравниваются дескрипторы, а не байты, поэтому версия `grpcio-tools` не мешает) |
| `--online` | вышел новый релиз upstream; тег upstream переставили на другой коммит |

Где это запускается автоматически:

- `pytest` - офлайн-проверки (хэш и stubs; stubs пропускаются без `grpcio-tools`);
- `run/release.sh tag|publish` - перед релизом `check --online`: расхождение с записанным
  источником блокирует, новый тег upstream - предупреждение (`PROTO_STRICT=1` - блокировка);
- сборка BF (`BF/run/build.sh`, режим `build`) - предупреждение о новом теге upstream, сборку
  не блокирует.

## Обновление на новую версию API

```bash
python scripts/proto_sync.py update            # последний тег; или --tag 2.23.0
```

Команда клонирует тег, заменяет `proto/`, перезаписывает `proto/UPSTREAM.json`, запускает
`generate.py` и `generate_docs.py` и печатает, какие `.proto` изменились и **удалены ли
объявления** (метка `!!` - возможная ломающая правка). Дальше:

1. посмотреть `git diff`, прогнать `pytest`, а в потребителях (BF, AFB) - их тесты;
2. записать изменения в `CHANGELOG.md` (под `## Unreleased`);
3. поднять версию пакета: MINOR для совместимых изменений, MAJOR - если удалены или
   изменены объявления, которыми пользуется клиент;
4. потребители перепиниваются владельцем.

## Что генерируется

Сервисы `auth`, `accounts`, `assets`, `orders`, `marketdata`, `reports`, `metrics`, общие
`side.proto` / `trade.proto` и gateway-аннотации openapiv2 (нужны service-proto и не входят в
`googleapis-common-protos`). `corporateactions` в upstream есть, но клиентом не используется и
не генерируется. `google/*` не генерируются: stubs используют установленные `protobuf` и
`googleapis-common-protos`.

Пакет proto `grpc.tradeapi.v1.*` конфликтовал бы с модулем `grpc` из grpcio, поэтому
кросс-импорты в сгенерированных файлах перекорневлены под `finam_client.grpc_gen`.
Импортировать нужно через фасад `finam_client/grpc_imports.py`.
