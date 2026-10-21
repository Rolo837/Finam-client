#!/usr/bin/env python3
"""Измерение объёма данных потоков Finam: SubscribeQuote и SubscribeBars против опроса Bars. READ-ONLY.

Нужен read-only токен (``--token-file``); скрипт ничего не торгует и не пишет, кроме отчёта.

Что измеряется за ``--duration`` секунд (по умолчанию 300) для каждого инструмента:
  * SubscribeQuote (один поток на все символы): сообщений и байт в минуту, пиковая секунда, интервалы между
    сообщениями, доля сообщений, в которых изменились last / bid / ask, какие поля приходят, есть ли
    начальный снимок;
  * SubscribeBars по каждому таймфрейму из ``--timeframes`` (отдельный поток на пару символ+таймфрейм): то же
    и разбивка на «обновление текущего бара» / «новый бар»;
  * опрос Bars раз в ``--poll-sec`` (по умолчанию 30) за последние бары — число запросов, задержка, байты;
  * «сколько пушей ушло бы в браузер»: для окон слива T = 1, 2, 3, 5, 10, 30 с — число окон, в которых было
    хотя бы одно ИЗМЕНЕНИЕ цены (именно столько строк/мерджей фронтенд получил бы при склейке последнего значения);
  * обрывы потоков и переподключения.

Результат зависит от торговой сессии (вне сессии потоки молчат) — отчёт фиксирует время запуска.

Запуск:  python scripts/probe_finam_streams.py --token-file ../AFB/secrets/finam_ro.token \
             --symbols 'XAU@#WWCP' 'CL@XNYM' --duration 300 --out report.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.protobuf.json_format import MessageToDict

from finam_client import ClientConfig, FinamApiClient, FinamError
from finam_client.grpc_imports import marketdata_service
from finam_client.proto_values import from_proto_decimal, proto_decimal_set, timestamp_to_datetime

DRAIN_WINDOWS_SEC = (1, 2, 3, 5, 10, 30)
QUOTE_PRICE_FIELDS = ("last", "bid", "ask")


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def tf_enum(name: str) -> int:
    return getattr(marketdata_service.TimeFrame, f"TIME_FRAME_{name}")


def dec(value) -> float | None:
    if value is None or not proto_decimal_set(value):
        return None
    return float(from_proto_decimal(value))


class Series:
    """Поток событий одного канала: время прихода, размер, признак изменения цены."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.events: list[tuple[float, int, bool]] = []  # (t_rel, bytes, price_changed)
        self.fields_seen: set[str] = set()
        self.first_sample: dict | None = None
        self.first_is_snapshot: bool | None = None
        self.errors: list[dict] = []
        self.reconnects = 0
        self.extra: dict[str, int] = defaultdict(int)
        self.lock = threading.Lock()

    def add(self, t: float, size: int, changed: bool) -> None:
        with self.lock:
            self.events.append((t, size, changed))

    def summary(self, duration: float) -> dict:
        ev = sorted(self.events)
        n = len(ev)
        minutes = duration / 60.0
        total_bytes = sum(e[1] for e in ev)
        per_second: dict[int, int] = defaultdict(int)
        per_minute: dict[int, int] = defaultdict(int)
        for t, _size, _ch in ev:
            per_second[int(t)] += 1
            per_minute[int(t // 60)] += 1
        gaps = [b[0] - a[0] for a, b in zip(ev, ev[1:])]
        minute_counts = [per_minute.get(i, 0) for i in range(max(1, int(duration // 60)))]
        changed = sum(1 for e in ev if e[2])
        windows = {}
        for w in DRAIN_WINDOWS_SEC:
            buckets = {int(t // w) for t, _s, ch in ev if ch}
            windows[f"T={w}s"] = {
                "pushes_total": len(buckets),
                "pushes_per_min": round(len(buckets) / minutes, 1) if minutes else None,
            }
        return {
            "messages": n,
            "messages_per_min": round(n / minutes, 1) if minutes else None,
            "per_minute_counts": minute_counts,
            "per_minute_min_max": [min(minute_counts), max(minute_counts)] if minute_counts else None,
            "peak_messages_in_one_second": max(per_second.values(), default=0),
            "seconds_with_messages": len(per_second),
            "bytes_total": total_bytes,
            "bytes_per_min": round(total_bytes / minutes) if minutes else None,
            "avg_message_bytes": round(total_bytes / n, 1) if n else None,
            "price_changed_messages": changed,
            "price_changed_share": round(changed / n, 3) if n else None,
            "gap_sec": {
                "median": round(statistics.median(gaps), 3) if gaps else None,
                "p95": round(sorted(gaps)[int(len(gaps) * 0.95) - 1], 3) if len(gaps) >= 20 else None,
                "max": round(max(gaps), 3) if gaps else None,
            },
            "first_message_after_sec": round(ev[0][0], 2) if ev else None,
            "first_message_is_snapshot": self.first_is_snapshot,
            "fields_seen": sorted(self.fields_seen),
            "drain_if_coalesced": windows,
            "reconnects": self.reconnects,
            "errors": self.errors,
            "extra": dict(self.extra),
            "sample": self.first_sample,
        }


def run_stream(open_stream, handler, series: Series, stop: threading.Event, holder: dict, key: str) -> None:
    """Читает блокирующий gRPC-итератор; обрыв — пауза и переподключение (пока не остановили)."""
    attempt = 0
    while not stop.is_set():
        try:
            stream = open_stream()
            holder[key] = stream
            for response in stream:
                if stop.is_set():
                    break
                handler(response)
            if not stop.is_set():
                series.errors.append({"at": round(time.monotonic(), 1), "kind": "stream_ended"})
        except Exception as exc:  # noqa: BLE001 - отмена при остановке тоже приходит исключением
            if stop.is_set():
                break
            series.errors.append({"at": round(time.monotonic(), 1), "kind": type(exc).__name__, "msg": str(exc)[:200]})
        attempt += 1
        series.reconnects += 1
        if stop.wait(min(2.0 * attempt, 15.0)):
            break


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--token-file", required=True)
    ap.add_argument("--symbols", nargs="+", default=["XAU@#WWCP", "CL@XNYM"])
    ap.add_argument("--timeframes", nargs="+", default=["M1", "M5"])
    ap.add_argument("--duration", type=int, default=300, help="секунд измерения")
    ap.add_argument("--poll-sec", type=int, default=30, help="период опроса Bars для сравнения")
    ap.add_argument("--no-poll", action="store_true")
    ap.add_argument("--out", default="streams_probe.json")
    args = ap.parse_args()

    client = FinamApiClient(ClientConfig(secret_file=args.token_file))
    details = client.token_details()
    if not details.readonly:
        print("ОТКАЗ: токен не read-only", file=sys.stderr)
        return 2

    started = datetime.now(timezone.utc)
    t0 = time.monotonic()
    stop = threading.Event()
    holders: dict[str, object] = {}
    threads: list[threading.Thread] = []

    quote_series = {s: Series(f"quote:{s}") for s in args.symbols}
    bars_series = {(s, tf): Series(f"bars:{s}:{tf}") for s in args.symbols for tf in args.timeframes}
    poll_series = {(s, tf): Series(f"poll:{s}:{tf}") for s in args.symbols for tf in args.timeframes}
    poll_latency: dict[tuple[str, str], list[float]] = defaultdict(list)

    # --- SubscribeQuote: один поток на все символы ------------------------------------------------------
    last_quote_values: dict[str, tuple] = {}
    quote_stream_total = Series("quote:stream(all symbols)")

    def on_quote(response) -> None:
        now = time.monotonic() - t0
        size = response.ByteSize()
        if response.error and response.error.ByteSize():
            quote_stream_total.errors.append({"kind": "StreamError", "msg": str(MessageToDict(response.error))[:200]})
        any_changed = False
        for quote in response.quote:
            series = quote_series.get(quote.symbol)
            if series is None:
                continue
            values = tuple(dec(getattr(quote, f)) for f in QUOTE_PRICE_FIELDS)
            changed = last_quote_values.get(quote.symbol) != values
            last_quote_values[quote.symbol] = values
            any_changed = any_changed or changed
            # размер сообщения делим поровну между символами сообщения (обычно в нём один)
            series.add(now, size // max(1, len(response.quote)), changed)
            for field, _v in quote.ListFields():
                series.fields_seen.add(field.name)
            if series.first_sample is None:
                series.first_sample = MessageToDict(quote)
                series.first_is_snapshot = bool(quote.is_data_snapshot)
            if quote.is_data_snapshot:
                series.extra["snapshot_messages"] += 1
        quote_stream_total.add(now, size, any_changed)

    threads.append(threading.Thread(
        target=run_stream,
        args=(lambda: client.subscribe_quote(list(args.symbols)), on_quote, quote_stream_total, stop, holders, "quote"),
        daemon=True,
    ))

    # --- SubscribeBars: по потоку на (символ, таймфрейм) ------------------------------------------------
    for (symbol, tf), series in bars_series.items():
        state: dict = {"last_ts": None, "last_close": None, "last_vol": None}

        def on_bars(response, series=series, state=state) -> None:
            now = time.monotonic() - t0
            size = response.ByteSize()
            changed = False
            for bar in response.bars:
                ts = timestamp_to_datetime(bar.timestamp)
                close, vol = dec(bar.close), dec(bar.volume)
                if state["last_ts"] is not None and ts != state["last_ts"]:
                    series.extra["new_bar_messages"] += 1
                else:
                    series.extra["current_bar_updates"] += 1
                if (ts, close, vol) != (state["last_ts"], state["last_close"], state["last_vol"]):
                    changed = True
                state.update(last_ts=ts, last_close=close, last_vol=vol)
                for field, _v in bar.ListFields():
                    series.fields_seen.add(field.name)
                if bar.is_data_snapshot:
                    series.extra["snapshot_bars"] += 1
            series.extra["bars_per_message_max"] = max(series.extra["bars_per_message_max"], len(response.bars))
            if series.first_sample is None:
                series.first_sample = MessageToDict(response)
                series.first_is_snapshot = any(b.is_data_snapshot for b in response.bars)
            series.add(now, size, changed)

        threads.append(threading.Thread(
            target=run_stream,
            args=(lambda s=symbol, t=tf: client.subscribe_bars(s, tf_enum(t)), on_bars, series, stop, holders, f"bars:{symbol}:{tf}"),
            daemon=True,
        ))

    # --- опрос Bars раз в poll-sec (сравнение) ----------------------------------------------------------
    def poller() -> None:
        while not stop.is_set():
            for (symbol, tf), series in poll_series.items():
                if stop.is_set():
                    return
                started_call = time.monotonic()
                try:
                    end = datetime.now(timezone.utc)
                    response = client.bars(symbol, tf_enum(tf), end - timedelta(minutes=30), end)
                    elapsed = time.monotonic() - started_call
                    poll_latency[(symbol, tf)].append(elapsed)
                    series.add(started_call - t0, response.ByteSize(), True)
                    series.extra["bars_returned_last"] = len(response.bars)
                except FinamError as exc:
                    series.errors.append({"kind": exc.broker_code or "FinamError", "msg": str(exc)[:160]})
            stop.wait(args.poll_sec)

    if not args.no_poll:
        threads.append(threading.Thread(target=poller, daemon=True))

    log(f"старт: символы={args.symbols} таймфреймы={args.timeframes} длительность={args.duration}с, потоков={len(threads)}")
    for thread in threads:
        thread.start()
    try:
        deadline = t0 + args.duration
        while time.monotonic() < deadline:
            time.sleep(15)
            counts = {s: len(se.events) for s, se in quote_series.items()}
            bars_n = {f"{s}:{t}": len(se.events) for (s, t), se in bars_series.items()}
            log(f"{int(time.monotonic() - t0)}с  quote={counts}  bars={bars_n}")
    except KeyboardInterrupt:
        log("прервано, пишу отчёт по набранному")
    duration = time.monotonic() - t0
    stop.set()
    for stream in list(holders.values()):
        try:
            stream.cancel()
        except Exception:  # noqa: BLE001
            pass

    report: dict = {
        "generated_at": started.isoformat(),
        "local_start": datetime.now().astimezone().isoformat(),
        "duration_sec": round(duration, 1),
        "symbols": args.symbols,
        "timeframes": args.timeframes,
        "token_readonly": bool(details.readonly),
        "concurrent_streams": 1 + len(bars_series),
        "quote_stream_all_symbols": quote_stream_total.summary(duration),
        "quote": {s: se.summary(duration) for s, se in quote_series.items()},
        "bars": {f"{s}:{t}": se.summary(duration) for (s, t), se in bars_series.items()},
    }
    if not args.no_poll:
        poll = {}
        for (s, t), se in poll_series.items():
            summary = se.summary(duration)
            lat = poll_latency[(s, t)]
            poll[f"{s}:{t}"] = {
                "requests": summary["messages"],
                "requests_per_min": summary["messages_per_min"],
                "bytes_per_request": summary["avg_message_bytes"],
                "bytes_per_min": summary["bytes_per_min"],
                "latency_sec_median": round(statistics.median(lat), 3) if lat else None,
                "latency_sec_max": round(max(lat), 3) if lat else None,
                "errors": summary["errors"],
            }
        report["poll_bars"] = {"period_sec": args.poll_sec, "series": poll}
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # --- краткая сводка в stdout ------------------------------------------------------------------------
    print(f"\nДлительность {duration:.0f} с, старт {report['local_start']}")
    print(f"{'канал':<28}{'сообщ/мин':>10}{'пик/с':>7}{'байт/мин':>10}{'изменений%':>11}{'T=1c':>7}{'T=3c':>7}{'T=30c':>7}")
    def row(name: str, s: dict) -> None:
        d = s["drain_if_coalesced"]
        share = s["price_changed_share"]
        print(f"{name:<28}{s['messages_per_min']!s:>10}{s['peak_messages_in_one_second']:>7}{s['bytes_per_min']!s:>10}"
              f"{(round(share * 100) if share is not None else '-')!s:>11}"
              f"{d['T=1s']['pushes_per_min']!s:>7}{d['T=3s']['pushes_per_min']!s:>7}{d['T=30s']['pushes_per_min']!s:>7}")
    for sym, s in report["quote"].items():
        row(f"Quote {sym}", s)
    for key, s in report["bars"].items():
        row(f"Bars {key}", s)
    if "poll_bars" in report:
        for key, s in report["poll_bars"]["series"].items():
            print(f"Poll Bars {key:<18} {s['requests_per_min']} зап/мин, {s['bytes_per_request']} байт/зап, "
                  f"задержка медиана {s['latency_sec_median']} с")
    print(f"\nОтчёт: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
