# Finam Trade API — версия proto

| Параметр | Значение |
| --- | --- |
| Репозиторий | <https://github.com/FinamWeb/finam-trade-api> |
| Тег | **2.16.0** |
| Commit | `3cec0896fa19936b164fb15561515f63e2e72df1` |
| Копия proto | `proto/` (только каталог `proto/` официального репозитория) |
| Сгенерированные stubs | `finam_client/grpc_gen/` (закоммичены) |
| Скрипт генерации | `scripts/generate.py` |

В отличие от BF, официальный репозиторий не подключён submodule: пакет копируется
в образы целиком (`cp -a`), поэтому в нём лежит только нужный каталог `proto/`.

## Что генерируется

Сервисы `auth`, `accounts`, `assets`, `orders`, `marketdata`, `reports`, `metrics`,
общие `side.proto` / `trade.proto` и gateway-аннотации openapiv2 (нужны service-proto и
не входят в `googleapis-common-protos`). `corporateactions` не генерируется.
`google/*` не генерируются: stubs используют установленные `protobuf` и
`googleapis-common-protos`.

Пакет proto `grpc.tradeapi.v1.*` конфликтовал бы с модулем `grpc` из grpcio, поэтому
кросс-импорты в сгенерированных файлах перекорневлены под `finam_client.grpc_gen`.
Импортировать нужно через фасад `finam_client/grpc_imports.py`.

## Обновление на новую версию API

1. Заменить содержимое `proto/` содержимым `proto/` нового тега официального репозитория.
2. `python scripts/generate.py` (нужен `grpcio-tools`, dev-зависимость).
3. Просмотреть diff `finam_client/grpc_gen/`, прогнать `pytest`; обновить таблицу выше.
4. Если поля изменились, поправить `finam_client/assets.py` и поднять версию пакета
   (MINOR при совместимых изменениях).
5. Потребители (AFB, BF) перепиниваются владельцем.
