# run/ — версионирование и релиз Finam-client

Канон semver-версии — корневой файл [`../VERSION`](../VERSION). Скрипты держат в
синхроне ещё 2 места: `pyproject.toml` и `finam_client/version.py`. Правила уровней —
[`../VERSIONING.md`](../VERSIONING.md).

## Модель веток

| Ветка | Роль |
|-------|------|
| `develop` | Разработка. Одна «покоящаяся» версия (последняя выпущенная), **не** тегируется покоммитно. AFB и BF в git пинят `@develop`. |
| `main` | Выпущенные версии. Каждый релиз — тег `vX.Y.Z`, достижимый из `main` после merge. `build.sh push` у AFB/BF тянет пакет с `main`. |

## Скрипты

| Скрипт | Назначение |
|--------|-----------|
| `run/version.sh` | bump `patch`/`minor` / `set` / `show`; commit+push (`--no-commit` — только файлы) |
| `run/check-version.sh` | read-only проверка синхрона |
| `run/release.sh` | `tag` (тег на `develop`) / `publish` (merge `develop→main` + GitHub Release) |

Скрипты скопированы из `AFB-BF-protocol/run` и адаптированы; пины потребителей они не
правят.

## Обычный релиз

```bash
pytest && ./run/check-version.sh
./run/version.sh minor              # или patch; оформит CHANGELOG, commit+push
./run/release.sh tag                # тег на develop
./run/release.sh publish            # merge develop→main + GitHub Release
```

`--dry-run` есть у `tag` и `publish`. Записи об изменениях — в `CHANGELOG.md` под
`## Unreleased`.
