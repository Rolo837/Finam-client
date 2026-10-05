#!/usr/bin/env python3
"""Generate docs/API.md and docs/STRUCTURES.md.

Sources of truth:
  * ``finam_client/client.py`` (AST)      - public client methods and signatures;
  * ``finam_client/grpc_gen`` descriptors - services, RPCs, message/enum structure;
  * ``proto/**/*.proto``                  - comments (descriptors do not keep them);
  * ``finam_client`` modules (inspect)    - neutral models, config, errors, helpers.

Run ``python scripts/generate_docs.py`` after changing the client or the proto;
``tests/test_docs_in_sync.py`` fails when the committed files are stale.
"""
from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from google.protobuf.descriptor import FieldDescriptor as FD  # noqa: E402

PROTO_ROOT = ROOT / "proto"
TRADEAPI = "grpc.tradeapi.v1."

# stub attribute prefix -> (pb2 module, service name)
SERVICES = {
    "auth": ("auth.auth_service_pb2", "AuthService"),
    "accounts": ("accounts.accounts_service_pb2", "AccountsService"),
    "assets": ("assets.assets_service_pb2", "AssetsService"),
    "orders": ("orders.orders_service_pb2", "OrdersService"),
    "marketdata": ("marketdata.marketdata_service_pb2", "MarketDataService"),
    "reports": ("reports.reports_service_pb2", "ReportsService"),
    "usage_metrics": ("metrics.usage_metrics_service_pb2", "UsageMetricsService"),
}
SERVICE_TITLES = {
    "auth": "Auth - сессия и токен",
    "accounts": "Accounts - счета, сделки, транзакции",
    "assets": "Assets - каталог инструментов",
    "orders": "Orders - заявки",
    "marketdata": "MarketData - котировки и свечи",
    "reports": "Reports - отчёты по счёту",
    "usage_metrics": "Metrics - использование API",
}
SCALARS = {
    FD.TYPE_STRING: "string", FD.TYPE_BOOL: "bool", FD.TYPE_BYTES: "bytes",
    FD.TYPE_INT32: "int32", FD.TYPE_INT64: "int64", FD.TYPE_UINT32: "uint32",
    FD.TYPE_UINT64: "uint64", FD.TYPE_DOUBLE: "double", FD.TYPE_FLOAT: "float",
    FD.TYPE_SINT32: "sint32", FD.TYPE_SINT64: "sint64", FD.TYPE_FIXED32: "fixed32",
    FD.TYPE_FIXED64: "fixed64", FD.TYPE_SFIXED32: "sfixed32", FD.TYPE_SFIXED64: "sfixed64",
}
# google.* types that are documented once, with a short Russian note.
WELL_KNOWN = {
    "google.type.Decimal": "десятичное число строкой (`value`), например `\"12.34\"`",
    "google.type.Money": "сумма: `currency_code`, `units` (целая часть), `nanos` (доля, 1e-9)",
    "google.type.Interval": "интервал времени `[start_time, end_time)`",
    "google.type.Date": "календарная дата `year`/`month`/`day` (часть может быть 0)",
    "google.protobuf.Timestamp": "момент времени: `seconds`, `nanos` (UTC)",
    "google.protobuf.BoolValue": "обёртка над bool: `value`; различает «не задано» и `false`",
    "google.protobuf.StringValue": "обёртка над string: `value`",
    "google.protobuf.Int32Value": "обёртка над int32: `value`",
    "google.protobuf.Int64Value": "обёртка над int64: `value`",
    "google.protobuf.Empty": "пустое сообщение",
}
# Notes for client methods that have no docstring of their own.
METHOD_NOTES = {
    "auth": "Обменивает secret на JWT. Обычно вызывается неявно через `refresh_session()`.",
    "token_details": "Информация о токене: срок действия, права рыночных данных, счета, признак `readonly`. JWT передаётся в теле запроса, без заголовка `authorization`.",
    "subscribe_jwt_renewal": "Серверный стрим обновлений JWT (stream).",
    "subscribe_order_trade_stream": "Открывает двунаправленный стрим `SubscribeOrderTrade`; запросы берутся из внутренней очереди, которую наполняют `subscribe_order_trade` / `unsubscribe_order_trade`.",
    "subscribe_order_trade": "Ставит в очередь запрос подписки на заявки и/или сделки счёта.",
    "unsubscribe_order_trade": "Ставит в очередь запрос отписки.",
}


LIFECYCLE_NOTES = {
    "JWT_REFRESH_SKEW_SEC": "Запас в секундах до истечения JWT, при котором токен обновляется заранее (`GrpcTuning.jwt_refresh_skew_sec`).",
    "TIMEOUT_SEC": "Таймаут одного gRPC-вызова в секундах (`GrpcTuning.timeout_sec`).",
    "GRPC_MAX_ATTEMPTS": "Максимум попыток одного вызова, включая первую (`GrpcTuning.max_attempts`).",
    "jwt_fail_streak": "Сколько обновлений JWT подряд в фоновом потоке завершились ошибкой; сбрасывается успешным обновлением.",
    "ensure_channel": "Пересоздаёт канал и stubs, если `close()` их закрыл. Вызывать перед первым RPC после переподключения.",
    "refresh_session": "Получает новый JWT через `Auth` (всегда, параметр `force` игнорируется). Вызывать до торговых вызовов.",
    "jwt_expires_at": "Момент истечения текущего JWT (UTC) или `None`, если токен ещё не выпущен.",
    "set_on_jwt_renewed": "Регистрирует колбэк, который фоновый поток вызывает после каждого успешного обновления JWT (нужен, чтобы пересоздать долгие стримы с новым токеном). Колбэк выполняется в потоке обновления.",
    "close": "Останавливает фоновое обновление JWT и закрывает канал.",
    "auth": "Обменивает secret на JWT (`AuthService.Auth`), возвращает `AuthResponse`. Обычно вызывается неявно через `refresh_session()`.",
    "start_jwt_renewal_background": "Запускает поток `finam-jwt-renewal`, который каждые `interval_sec` секунд обновляет JWT.",
    "stop_jwt_renewal_background": "Останавливает поток обновления JWT (ждёт до 3 с).",
}
FIELD_NOTES = {
    "AssetListItem": {
        "symbol": "Символ `ticker@mic`", "id": "Идентификатор инструмента Finam", "ticker": "Тикер",
        "mic": "MIC биржи (`MISX`, `RTSX`, `XNYM`, `#WWCP`, ...)", "isin": "ISIN",
        "type": "Тип: `EQUITIES`, `FUTURES`, `INDICES`, `CURRENCIES`, `BONDS`, `FUNDS`, `OPTIONS`, `SPREADS`, `SWAPS`, `OTHER`",
        "name": "Наименование", "is_archived": "Инструмент в архиве (в `Assets` архивных нет, в `AllAssets` есть)",
    },
    "AssetInfo": {
        "symbol": "Символ `ticker@mic`", "id": "Идентификатор инструмента Finam", "ticker": "Тикер", "mic": "MIC биржи",
        "board": "Режим торгов (`TQBR`, `FUT`, `CETS`); пуст для зарубежных площадок, индексов и архивных",
        "isin": "ISIN", "type": "Тип инструмента (как в `AssetListItem`)", "name": "Наименование",
        "decimals": "Знаков после запятой в цене", "min_step_raw": "`min_step` из ответа (целое)",
        "price_step": "Шаг цены: `min_step / 10^decimals`", "lot_size": "Штук в лоте",
        "quote_currency": "Валюта котировки", "expiration_date": "Дата экспирации `YYYY-MM-DD` (у фьючерсов; у непрерывных нет)",
        "future_details": "Для фьючерса: `contract_size`, `expiration_date`", "option_details": "Для опциона: `contract_size`, `strike`, `expiration_date`",
        "bond_details": "Для облигации: `bond_face_value`, `currency`",
    },
    "AssetParams": {
        "symbol": "Символ `ticker@mic`", "account_id": "Счёт, для которого получены параметры",
        "tradable": "Инструмент торгуется (`is_tradable`)", "longable": "Лонг доступен", "shortable": "Шорт доступен (включая `AVAILABLE_STRATEGY`)",
        "long_risk_rate": "Ставка риска для лонга", "short_risk_rate": "Ставка риска для шорта",
        "long_initial_margin": "Начальное ГО для лонга", "short_initial_margin": "Начальное ГО для шорта",
        "margin_currency": "Валюта ГО", "price_type": "Допустимые цены: `UNKNOWN`, `POSITIVE`, `NON_NEGATIVE`, `ANY`",
    },
    "Bar": {
        "timestamp": "Начало свечи (UTC)", "open": "Цена открытия", "high": "Максимум", "low": "Минимум",
        "close": "Цена закрытия", "volume": "Объём",
    },
    "GrpcTuning": {
        "keepalive_time_sec": "Период keepalive-пингов канала", "keepalive_timeout_sec": "Ожидание ответа на пинг",
        "timeout_sec": "Таймаут одного вызова", "max_attempts": "Попыток на вызов (включая первую)",
        "retry_base_sec": "Базовая пауза между повторами (умножается на номер попытки)",
        "rate_limit_backoff_sec": "Базовая пауза при `RESOURCE_EXHAUSTED` (лимит Finam ~200 запросов/мин)",
        "min_interval_sec": "Минимальная пауза между унарными вызовами одного клиента (0 - выключено); для массовых задач 0.4 ≈ 150 запросов/мин",
        "jwt_refresh_skew_sec": "Запас до истечения JWT, при котором токен обновляется",
    },
    "ClientConfig": {
        "secret_file": "Файл с secret-токеном Finam (одна строка)", "endpoint": "Адрес gRPC API", "grpc_client": "Параметры канала и повторов",
    },
}
CLASS_NOTES = {
    "AssetListItem": "Строка списка `Assets` / `AllAssets`. Board в списке нет.",
    "AssetInfo": "Результат `GetAsset`: статические данные инструмента. Только здесь есть `board`.",
    "AssetParams": "Результат `GetAssetParams`: торговые флаги и гарантийное обеспечение; зависят от счёта.",
    "Bar": "Свеча из `Bars` / `SubscribeBars`.",
    "GrpcTuning": "Параметры канала и повторов (значения по умолчанию совпадают с демоном BF).",
    "ClientConfig": "Конфигурация клиента.",
}
FUNC_NOTES = {
    "asset_list_item_from_proto": "`Asset` -> `AssetListItem`.",
    "asset_info_from_proto": "`GetAssetResponse` -> `AssetInfo`; `symbol` по умолчанию `ticker@mic`.",
    "asset_params_from_proto": "`GetAssetParamsResponse` -> `AssetParams`.",
    "bar_from_proto": "`Bar` -> `Bar` (нейтральная).",
    "read_secret_file": "Читает secret из файла; пустой файл - `ValueError`.",
    "to_finam_venue": "Площадка каталога `(mic, board)` -> площадка Finam (`MISX/RFUD` -> `RTSX/FUT`).",
    "from_finam_venue": "Площадка Finam `(mic, board)` -> площадка каталога; незнакомый `RTSX` сворачивается в `MISX`.",
    "finam_board_from_venue": "Board Finam для пары каталога `(exchange, board)`.",
    "validate_finam_symbol": "Проверяет формат `ticker@mic` (делит по последнему `@`), возвращает символ без пробелов по краям; иначе `FinamError(VALIDATION)`.",
    "split_symbol": "`SBER@MISX` -> `(\"SBER\", \"MISX\")`; регистр сохраняется.",
    "from_proto_decimal": "`google.type.Decimal` -> `Decimal` (пусто -> 0).",
    "to_proto_decimal": "`Decimal` -> `google.type.Decimal`; `decimals` округляет до знаков.",
    "optional_proto_decimal": "`Decimal` или `None`, если значение не задано.",
    "optional_google_money": "`google.type.Money` -> `Decimal` или `None`, если 0.",
    "from_google_money": "`google.type.Money` (`units` + `nanos`) -> `Decimal`.",
    "money_currency_code": "Код валюты из `Money` в верхнем регистре.",
    "sum_money_list": "Сумма списка `Money` (`GetAccount.cash`) или `None`.",
    "money_list_by_currency": "Список `Money` -> словарь `{валюта: сумма}`.",
    "price_step_from_asset": "`min_step / 10^decimals`.",
    "lots_from_proto": "`Decimal` из proto -> целое число лотов.",
    "decimal_to_json": "`Decimal` -> строка без хвостовых нулей или `None`.",
    "timestamp_to_datetime": "`Timestamp` -> `datetime` (UTC) или `None`, если пуст.",
    "proto_calendar_date_to_iso": "`google.type.Date` -> `YYYY-MM-DD` (или `YYYY-MM`, `YYYY`).",
    "timeframe_to_finam": "Строка таймфрейма (`M5`, `1h`, `D1`, ...) -> `TimeFrame`; неизвестная - `ValueError`.",
}

# --------------------------------------------------------------------------- proto comments
class ProtoComments:
    """Parses ``//`` comments in .proto files, keyed by dotted full name."""

    def __init__(self) -> None:
        self.by_name: dict[str, str] = {}
        for path in sorted(PROTO_ROOT.rglob("*.proto")):
            self._parse(path)

    def get(self, full_name: str) -> str:
        return self.by_name.get(full_name, "")

    def _parse(self, path: Path) -> None:
        package = ""
        stack: list[tuple[str, str]] = []  # (kind, name)
        pending: list[str] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("//"):
                pending.append(line[2:].strip())
                continue
            if not line:
                pending = []
                continue
            if line.startswith("package "):
                package = line.split()[1].rstrip(";")
                pending = []
                continue
            named = {kind: re.match(rf"{kind}\s+(\w+)\s*\{{", line) for kind in ("message", "enum", "service", "oneof")}
            kind = next((k for k, m in named.items() if m), None)
            if kind:
                name = named[kind].group(1)
                if kind != "oneof":
                    self._store(package, stack, name, pending)
                stack.append((kind, name))
                pending = []
                if line.endswith("}"):
                    stack.pop()
                continue
            rpc = re.match(r"rpc\s+(\w+)\s*\(", line)
            if rpc:
                self._store(package, stack, rpc.group(1), pending)
                pending = []
                if line.endswith("{"):
                    stack.append(("rpcopts", rpc.group(1)))
                continue
            top = stack[-1][0] if stack else ""
            field = re.match(r"(?:repeated\s+|optional\s+)?(?:map<[^>]+>|[\w.]+)\s+(\w+)\s*=\s*\d+", line)
            if field and top in ("message", "oneof"):
                self._store(package, stack, field.group(1), pending)
                pending = []
            elif top == "enum":
                value = re.match(r"(\w+)\s*=\s*-?\d+", line)
                if value:
                    self._store(package, stack, value.group(1), pending)
                pending = []
            else:
                pending = []
            opens, closes = line.count("{"), line.count("}")
            for _ in range(opens - closes if opens > closes else 0):
                stack.append(("block", ""))
            for _ in range(closes - opens if closes > opens else 0):
                if stack:
                    stack.pop()

    def _store(self, package: str, stack: list[tuple[str, str]], name: str, pending: list[str]) -> None:
        if not pending:
            return
        parts = [n for k, n in stack if k in ("message", "enum", "service")]
        full = ".".join([package, *parts, name])
        self.by_name[full] = " ".join(p for p in pending if p).strip()


# --------------------------------------------------------------------------- descriptors
def load_services():
    out = {}
    for key, (module, service) in SERVICES.items():
        mod = importlib.import_module(f"finam_client.grpc_gen.grpc.tradeapi.v1.{module}")
        out[key] = (mod, mod.DESCRIPTOR.services_by_name[service])
    return out


def short(full_name: str) -> str:
    return full_name[len(TRADEAPI):] if full_name.startswith(TRADEAPI) else full_name


def anchor(full_name: str) -> str:
    return short(full_name).replace(".", "-").lower()


def type_ref(field, *, link: bool = True) -> str:
    if field.type == FD.TYPE_MESSAGE:
        mt = field.message_type
        if mt.GetOptions().map_entry:
            k, v = mt.fields_by_name["key"], mt.fields_by_name["value"]
            return f"map&lt;{type_ref(k, link=link)}, {type_ref(v, link=link)}&gt;"
        name = mt.full_name
        if name in WELL_KNOWN:
            return f"`{name.split('.')[-1]}`"
        label = short(name)
        return f"[`{label}`](STRUCTURES.md#{anchor(name)})" if link else f"`{label}`"
    if field.type == FD.TYPE_ENUM:
        name = field.enum_type.full_name
        label = short(name)
        return f"[`{label}`](STRUCTURES.md#{anchor(name)})" if link else f"`{label}`"
    return f"`{SCALARS.get(field.type, str(field.type))}`"


def message_ref(desc) -> str:
    if desc.full_name in WELL_KNOWN:
        return f"`{desc.name}`"
    return f"[`{short(desc.full_name)}`](STRUCTURES.md#{anchor(desc.full_name)})"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- client AST
def client_methods():
    src = (ROOT / "finam_client" / "client.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FinamApiClient")
    methods = []
    for fn in cls.body:
        if not isinstance(fn, ast.FunctionDef) or fn.name.startswith("_"):
            continue
        is_prop = any(isinstance(d, ast.Name) and d.id == "property" for d in fn.decorator_list)
        stub = None
        for n in ast.walk(fn):
            if (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute)
                    and n.value.attr.endswith("_stub")):
                stub = (n.value.attr[: -len("_stub")], n.attr)
        idempotent_false = any(
            k.arg == "idempotent" and isinstance(k.value, ast.Constant) and k.value.value is False
            for n in ast.walk(fn) if isinstance(n, ast.Call) for k in n.keywords
        )
        args = ast.unparse(fn.args)
        a = fn.args
        positional = [*a.posonlyargs, *a.args]
        pos_defaults = [None] * (len(positional) - len(a.defaults)) + list(a.defaults)
        params = []
        for arg, default in zip(positional, pos_defaults):
            params.append((arg.arg, ast.unparse(arg.annotation) if arg.annotation else "", ast.unparse(default) if default else ""))
        for arg, default in zip(a.kwonlyargs, a.kw_defaults):
            params.append((arg.arg, ast.unparse(arg.annotation) if arg.annotation else "", ast.unparse(default) if default else "", ))
        params = [p for p in params if p[0] != "self"]
        methods.append(
            {
                "name": fn.name,
                "args": args,
                "returns": ast.unparse(fn.returns) if fn.returns else "",
                "doc": (ast.get_docstring(fn) or "").strip(),
                "params": params,
                "stub": stub,
                "property": is_prop,
                "idempotent": not idempotent_false,
            }
        )
    return methods


def rpc_summary(comment: str) -> str:
    """First paragraph of an RPC comment, before the HTTP examples."""
    out = []
    for part in comment.split("  "):
        pass
    words = comment
    for marker in (" Пример", " Параметры:", " Authorization:", " Пример HTTP"):
        if marker in words:
            words = words.split(marker)[0]
    return words.strip()


def render_fields_table(desc, comments: ProtoComments) -> list[str]:
    """Top-level fields of a request/response message, for the method sections."""
    if not desc.fields:
        return ["_Поля отсутствуют._", ""]
    lines = ["| Поле | Тип | Описание |", "|---|---|---|"]
    for f in desc.fields:
        t = type_ref(f)
        if f.is_repeated and not (f.type == FD.TYPE_MESSAGE and f.message_type.GetOptions().map_entry):
            t = f"список {t}"
        lines.append(f"| `{f.name}` | {t} | {cell(comments.get(f'{desc.full_name}.{f.name}'))} |")
    lines.append("")
    return lines


# --------------------------------------------------------------------------- STRUCTURES.md
def render_message(desc, comments: ProtoComments, used_by: dict[str, list[str]]) -> list[str]:
    lines = [f'<a id="{anchor(desc.full_name)}"></a>', f"#### `{short(desc.full_name)}`", ""]
    doc = comments.get(desc.full_name)
    if doc:
        lines += [doc, ""]
    users = used_by.get(desc.full_name)
    if users:
        lines += ["Используется в: " + ", ".join(f"`{u}`" for u in users) + ".", ""]
    if not desc.fields:
        lines += ["_Пустое сообщение._", ""]
        return lines
    lines += ["| № | Поле | Тип | Описание |", "|--:|---|---|---|"]
    for f in desc.fields:
        t = type_ref(f)
        if f.is_repeated and not (f.type == FD.TYPE_MESSAGE and f.message_type.GetOptions().map_entry):
            t = f"список {t}"
        note = comments.get(f"{desc.full_name}.{f.name}")
        extras = []
        if f.containing_oneof is not None:
            extras.append(f"oneof `{f.containing_oneof.name}`")
        if f.has_presence and f.type != FD.TYPE_MESSAGE and f.containing_oneof is None and f.label != FD.LABEL_REPEATED:
            extras.append("optional")
        text = note + (f" _({', '.join(extras)})_" if extras else "")
        lines.append(f"| {f.number} | `{f.name}` | {t} | {cell(text)} |")
    lines.append("")
    return lines


def render_enum(desc, comments: ProtoComments) -> list[str]:
    lines = [f'<a id="{anchor(desc.full_name)}"></a>', f"#### `{short(desc.full_name)}` (enum)", ""]
    doc = comments.get(desc.full_name)
    if doc:
        lines += [doc, ""]
    lines += ["| Значение | Имя | Описание |", "|--:|---|---|"]
    for v in desc.values:
        lines.append(f"| {v.number} | `{v.name}` | {cell(comments.get(f'{desc.full_name}.{v.name}'))} |")
    lines.append("")
    return lines


def collect_nested(desc, msgs: list, enums: list) -> None:
    for e in desc.enum_types:
        enums.append(e)
    for m in desc.nested_types:
        if m.GetOptions().map_entry:
            continue
        msgs.append(m)
        collect_nested(m, msgs, enums)


def build_structures(services, comments: ProtoComments, used_by) -> str:
    out = [
        "# Структуры запросов и ответов",
        "",
        "> Файл сгенерирован `scripts/generate_docs.py` из proto и не редактируется вручную.",
        "> Методы клиента, которые принимают и возвращают эти структуры, - в [API.md](API.md).",
        "",
        "Все сообщения - protobuf-классы из `finam_client.grpc_gen`; импортировать их удобно через",
        "фасад `finam_client.grpc_imports` (`assets_service.GetAssetRequest(...)` и т.д.).",
        "Поля `Decimal`, `Money`, `Timestamp` и др. описаны в разделе «Общие типы Google».",
        "",
        "## Общие типы Google",
        "",
        "| Тип | Смысл |",
        "|---|---|",
    ]
    for name, text in WELL_KNOWN.items():
        out.append(f"| `{name}` | {text} |")
    out.append("")
    # shared files first (side, trade)
    shared = importlib.import_module("finam_client.grpc_gen.grpc.tradeapi.v1.side_pb2")
    trade = importlib.import_module("finam_client.grpc_gen.grpc.tradeapi.v1.trade_pb2")
    groups = [("Общие типы Finam", [shared, trade])]
    for key, (mod, _svc) in services.items():
        groups.append((SERVICE_TITLES[key], [mod]))
    for title, modules in groups:
        out += [f"## {title}", ""]
        for mod in modules:
            msgs, enums = [], []
            for e in mod.DESCRIPTOR.enum_types_by_name.values():
                enums.append(e)
            for m in mod.DESCRIPTOR.message_types_by_name.values():
                msgs.append(m)
                collect_nested(m, msgs, enums)
            for e in enums:
                out += render_enum(e, comments)
            for m in msgs:
                out += render_message(m, comments, used_by)
    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------------------- API.md
def fmt_type(tp) -> str:
    if tp is dataclasses.MISSING or tp is inspect.Parameter.empty:
        return ""
    return tp if isinstance(tp, str) else getattr(tp, "__name__", str(tp))


def render_dataclass(cls) -> list[str]:
    lines = [f"#### `{cls.__name__}`", ""]
    lines += [CLASS_NOTES.get(cls.__name__, ""), ""]
    lines += ["| Поле | Тип | По умолчанию | Описание |", "|---|---|---|---|"]
    notes = FIELD_NOTES.get(cls.__name__, {})
    for f in dataclasses.fields(cls):
        default = ""
        if f.default is not dataclasses.MISSING:
            default = f"`{f.default!r}`"
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            default = "`" + getattr(f.default_factory, "__name__", "factory") + "()`"
        lines.append(f"| `{f.name}` | `{cell(fmt_type(f.type))}` | {cell(default)} | {cell(notes.get(f.name, ''))} |")
    lines.append("")
    return lines


def render_functions(module_name: str, names: list[str]) -> list[str]:
    mod = importlib.import_module(module_name)
    lines = []
    for name in names:
        fn = getattr(mod, name)
        sig = str(inspect.signature(fn, eval_str=True)).replace("finam_client.venue.", "")
        doc = FUNC_NOTES.get(name) or (inspect.getdoc(fn) or "").split("\n\n")[0].replace("\n", " ")
        lines.append(f"- `{name}{sig}`" + (f" - {doc}" if doc else ""))
    lines.append("")
    return lines


def build_api(services, comments: ProtoComments, used_by) -> str:
    methods = client_methods()
    by_service: dict[str, list[dict]] = {k: [] for k in SERVICES}
    lifecycle, other = [], []
    for m in methods:
        if m["stub"] and m["stub"][0] in SERVICES:
            by_service[m["stub"][0]].append(m)
        elif m["name"] in ("iter_all_assets", "fetch_all_assets"):
            by_service["assets"].append(m)
        elif m["name"] in ("subscribe_order_trade", "unsubscribe_order_trade"):
            by_service["orders"].append(m)
        else:
            lifecycle.append(m)

    out = [
        "# API Finam-client",
        "",
        "> Файл сгенерирован `scripts/generate_docs.py` из кода клиента и proto и не редактируется",
        "> вручную. Как пользоваться - в [USAGE.md](USAGE.md); поля всех структур - в",
        "> [STRUCTURES.md](STRUCTURES.md).",
        "",
        "```python",
        "from finam_client import ClientConfig, FinamApiClient",
        "",
        'client = FinamApiClient(ClientConfig(secret_file="secrets/finam_ro.token"))',
        'asset = client.get_asset("SBER@MISX", account_id)   # -> assets_service.GetAssetResponse',
        "```",
        "",
        "Методы возвращают **protobuf-сообщения** (как есть). Нейтральные модели в `finam_client.assets`",
        "строятся из них мапперами (раздел «Нейтральные модели»). Все унарные вызовы повторяются при",
        "`UNAVAILABLE`, `DEADLINE_EXCEEDED`, `RESOURCE_EXHAUSTED`, а при `UNAUTHENTICATED` перевыпускается",
        "JWT; вызовы заявок (`place_order`, `place_sltp_order`) **не** повторяются. Ошибки приходят как",
        "[`FinamError`](#ошибки).",
        "",
        "## Содержание",
        "",
        "| Метод | RPC | Тип | Повтор |",
        "|---|---|---|---|",
    ]
    for key, (mod, svc) in services.items():
        rpcs = {m.name: m for m in svc.methods}
        for m in by_service[key]:
            if m["stub"]:
                rpc = rpcs[m["stub"][1]]
                kind = "stream" if rpc.server_streaming or rpc.client_streaming else "unary"
                rpc_name = f"{svc.name}.{rpc.name}"
            else:
                kind, rpc_name = "хелпер", "-"
            retry = "нет" if not m["idempotent"] else ("да" if kind == "unary" else "-")
            out.append(f"| [`{m['name']}`](#{m['name']}) | {rpc_name} | {kind} | {retry} |")
    out.append("")

    for key, (mod, svc) in services.items():
        out += [f"## {SERVICE_TITLES[key]}", ""]
        rpcs = {m.name: m for m in svc.methods}
        for m in by_service[key]:
            out += [f'<a id="{m["name"]}"></a>', f"### `{m['name']}`", ""]
            sig = f"{m['name']}({m['args'].replace('self, ', '').replace('self', '')})"
            ret = f" -> {m['returns']}" if m["returns"] else ""
            out += ["```python", sig + ret, "```", ""]
            if m["stub"]:
                rpc = rpcs[m["stub"][1]]
                kind = "server-stream" if rpc.server_streaming and not rpc.client_streaming else (
                    "bidi-stream" if rpc.client_streaming else "unary")
                out.append(f"- **RPC:** `{svc.name}.{rpc.name}` ({kind})")
                out.append(f"- **Запрос:** {message_ref(rpc.input_type)}")
                out.append(f"- **Ответ:** {message_ref(rpc.output_type)}"
                           + (" (поток сообщений)" if rpc.server_streaming else ""))
                out.append("- **Повтор при ошибках транспорта:** " + ("да" if m["idempotent"] and kind == "unary" else "нет"))
                out.append("")
                summary = rpc_summary(comments.get(rpc.full_name))
                if summary:
                    out += [summary, ""]
            note = m["doc"] or METHOD_NOTES.get(m["name"], "")
            if note:
                out += [note.replace("\n", " "), ""]
            if m["params"]:
                out += ["**Параметры метода**", "", "| Параметр | Тип | По умолчанию |", "|---|---|---|"]
                for name, ann, default in m["params"]:
                    out.append(f"| `{name}` | `{ann}` | {('`' + default + '`') if default else ''} |")
                out.append("")
            if m["stub"]:
                out += [f"**Поля запроса** `{short(rpc.input_type.full_name)}`", ""]
                out += render_fields_table(rpc.input_type, comments)
                out += [f"**Поля ответа** `{short(rpc.output_type.full_name)}`"
                        + (" (приходит потоком сообщений)" if rpc.server_streaming else ""), ""]
                out += render_fields_table(rpc.output_type, comments)
        if not by_service[key]:
            out += ["_Методов клиента нет._", ""]

    out += ["## Сессия и жизненный цикл клиента", "", "| Член | Описание |", "|---|---|"]
    for m in lifecycle:
        doc = LIFECYCLE_NOTES.get(m["name"]) or (m["doc"] or METHOD_NOTES.get(m["name"], "")).split("\n")[0]
        kind = "свойство" if m["property"] else f"`{m['name']}({m['args'].replace('self, ', '').replace('self', '')})`"
        label = f"`{m['name']}`" if m["property"] else kind
        out.append(f"| {cell(label)} | {cell(doc)} |")
    out.append("")

    out += ["## Нейтральные модели", "",
            "`finam_client.assets` - данные брокера без доменных интерпретаций.", ""]
    assets = importlib.import_module("finam_client.assets")
    for name in ("AssetListItem", "AssetInfo", "AssetParams", "Bar"):
        out += render_dataclass(getattr(assets, name))
    out += ["Мапперы из protobuf:", ""]
    out += render_functions(
        "finam_client.assets",
        ["asset_list_item_from_proto", "asset_info_from_proto", "asset_params_from_proto", "bar_from_proto"],
    )

    out += ["## Конфигурация", ""]
    config = importlib.import_module("finam_client.config")
    out += render_dataclass(config.GrpcTuning) + render_dataclass(config.ClientConfig)
    out += render_functions("finam_client.config", ["read_secret_file"])

    out += ["## Ошибки", ""]
    errors = importlib.import_module("finam_client.errors")
    out += ["`FinamError(category, message, retryable=False, broker_code=None)` - исключение по умолчанию.",
            "Потребитель может передать `error_factory(category, message, *, retryable, broker_code)`,",
            "чтобы клиент бросал собственный тип (BF передаёт `BrokerError`).", "",
            "| `ErrorCategory` | Значение |", "|---|---|"]
    for c in errors.ErrorCategory:
        out.append(f"| `{c.name}` | `{c.value}` |")
    out += ["", "`broker_code` - имя gRPC-статуса (`UNAVAILABLE`, `RESOURCE_EXHAUSTED`, `INVALID_ARGUMENT`, ...),",
            "а также `place_timeout` (таймаут заявки: исход неизвестен) и `auction_only`",
            "(отказ из-за аукциона: заявку можно повторить позже).", ""]

    out += ["## Площадки и символы", ""]
    out += render_functions("finam_client.venue", ["to_finam_venue", "from_finam_venue", "finam_board_from_venue"])
    out += render_functions("finam_client.symbols", ["validate_finam_symbol", "split_symbol"])

    out += ["## Хелперы значений (`finam_client.proto_values`)", ""]
    out += render_functions(
        "finam_client.proto_values",
        ["from_proto_decimal", "to_proto_decimal", "optional_proto_decimal", "optional_google_money",
         "from_google_money", "money_currency_code", "sum_money_list", "money_list_by_currency",
         "price_step_from_asset", "lots_from_proto", "decimal_to_json", "timestamp_to_datetime",
         "proto_calendar_date_to_iso", "timeframe_to_finam"],
    )
    out += ["Словарь таймфреймов `TIMEFRAME_MAP`: " + ", ".join(
        f"`{k}`" for k in importlib.import_module("finam_client.proto_values").TIMEFRAME_MAP) + ".", ""]
    return "\n".join(out).rstrip() + "\n"


def used_by_map(services, methods) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for m in methods:
        if not m["stub"] or m["stub"][0] not in services:
            continue
        _mod, svc = services[m["stub"][0]]
        rpc = next((r for r in svc.methods if r.name == m["stub"][1]), None)
        if rpc is None:
            continue
        for desc, role in ((rpc.input_type, "запрос"), (rpc.output_type, "ответ")):
            result.setdefault(desc.full_name, []).append(f"{m['name']} ({role})")
    return result


def generate() -> dict[str, str]:
    comments = ProtoComments()
    services = load_services()
    used_by = used_by_map(services, client_methods())
    return {
        "docs/API.md": build_api(services, comments, used_by),
        "docs/STRUCTURES.md": build_structures(services, comments, used_by),
    }


def main() -> int:
    for rel, text in generate().items():
        (ROOT / rel).write_text(text, encoding="utf-8")
        print(f"wrote {rel} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
