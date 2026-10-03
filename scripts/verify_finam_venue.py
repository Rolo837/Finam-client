#!/usr/bin/env python3
"""Stage 0 check: how Finam's catalog lines up with ours. READ-ONLY.

Uses a read-only token (``--token-file``) and the AFB catalog opened read-only.
It never places orders and never writes to the catalog. Output is one JSON report.

What it establishes:
  * the token is read-only (TokenDetails);
  * AllAssets without filters: size, time, distribution by type / mic / archived;
  * for every active catalog listing: do ``from_finam_venue(GetAsset.mic, .board)``
    + ticker give exactly the listing's ``(mic, board, ticker)``;
  * observed ``(finam mic, finam board)`` per catalog ``(mic, board, market)`` --
    the data for the venue translation table;
  * which non-trading / index / commodity instruments have bars, and at which timeframes;
  * what GetAsset says about archived instruments;
  * Bars: the longest interval Finam accepts per timeframe;
  * SubscribeBars: does a stream open and deliver.

Run:  python scripts/verify_finam_venue.py --token-file ../AFB/secrets/finam_ro.token \
          --catalog-db ../AFB/db/catalog.db --out report.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.protobuf.json_format import MessageToDict

from finam_client import ClientConfig, FinamApiClient, FinamError
from finam_client.assets import asset_info_from_proto, asset_list_item_from_proto
from finam_client.grpc_imports import marketdata_service
from finam_client.venue import from_finam_venue, to_finam_venue

TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H2", "H4", "H8", "D", "W", "MN", "QR"]
WINDOW_DAYS = [3650, 1825, 730, 365, 180, 90, 30, 14, 7, 3, 1]


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


THROTTLE = {"rate_limited_retries": 0, "calls": 0}


def install_throttle(client: FinamApiClient, per_min: int = 150) -> None:
    """Finam rate-limits to ~200 req/min per token (RESOURCE_EXHAUSTED). Keep under it
    and retry with backoff when it still trips. Applied only inside this script."""
    lock = threading.Lock()
    interval = 60.0 / per_min
    state = {"next": 0.0}
    original = client._call

    def throttled(*args, **kwargs):
        for attempt in range(8):
            with lock:
                now = time.monotonic()
                wait = max(0.0, state["next"] - now)
                state["next"] = max(now, state["next"]) + interval
            if wait:
                time.sleep(wait)
            THROTTLE["calls"] += 1
            try:
                return original(*args, **kwargs)
            except FinamError as exc:
                if exc.broker_code == "RESOURCE_EXHAUSTED" and attempt < 7:
                    THROTTLE["rate_limited_retries"] += 1
                    time.sleep(5 * (attempt + 1))
                    continue
                raise

    client._call = throttled  # type: ignore[method-assign]


def tf_enum(name: str) -> int:
    return getattr(marketdata_service.TimeFrame, f"TIME_FRAME_{name}")


def load_listings(path: Path) -> list[dict]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT instrument_key, mic, board, market, ticker, instrument_type "
            "FROM listing WHERE lifecycle = 'active'"
        ).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def step_token(client: FinamApiClient) -> dict:
    details = client.token_details()
    return {
        "readonly": bool(details.readonly),
        "account_ids": list(details.account_ids),
        "md_permissions": [MessageToDict(p) for p in details.md_permissions],
    }


def step_all_assets(client: FinamApiClient) -> tuple[list, dict]:
    stats: dict = {}
    t0 = time.monotonic()
    pages = 0
    items = []
    cursor = 0
    while True:
        resp = client.all_assets(cursor=cursor, only_active=False)
        pages += 1
        items.extend(asset_list_item_from_proto(a) for a in resp.assets)
        nxt = int(resp.next_cursor)
        if nxt == 0 or nxt == cursor:
            break
        cursor = nxt
    stats["all_assets_unfiltered"] = {
        "rows": len(items),
        "pages": pages,
        "seconds": round(time.monotonic() - t0, 2),
        "by_type": Counter(i.type for i in items).most_common(),
        "by_mic": Counter(i.mic for i in items).most_common(),
        "archived": sum(1 for i in items if i.is_archived),
        "duplicate_symbols": len(items) - len({i.symbol for i in items}),
    }
    t0 = time.monotonic()
    active = sum(1 for _ in client.iter_all_assets(only_active=True))
    stats["all_assets_only_active_rows"] = active
    stats["all_assets_only_active_seconds"] = round(time.monotonic() - t0, 2)
    t0 = time.monotonic()
    stats["assets_rpc_rows"] = len(client.assets().assets)
    stats["assets_rpc_seconds"] = round(time.monotonic() - t0, 2)
    return items, stats


def get_asset_safe(client: FinamApiClient, symbol: str, account_id: str) -> dict:
    try:
        info = asset_info_from_proto(client.get_asset(symbol, account_id), symbol=symbol)
        return {"ok": True, "info": info}
    except FinamError as exc:
        return {"ok": False, "error": f"{exc.broker_code}: {exc.message}"}
    except Exception as exc:  # noqa: BLE001 - report, keep going
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def step_match(client, listings, items, account_id) -> dict:
    by_ticker: dict[str, list] = defaultdict(list)
    for it in items:
        by_ticker[it.ticker].append(it)

    jobs: list[tuple[dict, str]] = []
    no_candidate: list[dict] = []
    for lst in listings:
        want_mics = {to_finam_venue(lst["mic"], lst["board"]).mic, lst["mic"], "MISX", "RTSX"}
        cands = [c for c in by_ticker.get(lst["ticker"], []) if c.mic in want_mics]
        if not cands:
            no_candidate.append({"key": lst["instrument_key"], "other_mics": sorted({c.mic for c in by_ticker.get(lst["ticker"], [])})})
        for c in cands:
            jobs.append((lst, c.symbol))
    log(f"match: {len(listings)} listings, {len(jobs)} GetAsset calls, {len(no_candidate)} without candidate")

    def run(job):
        lst, symbol = job
        return lst, symbol, get_asset_safe(client, symbol, account_id)

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n, res in enumerate(pool.map(run, jobs), 1):
            results.append(res)
            if n % 200 == 0:
                log(f"  GetAsset {n}/{len(jobs)}")

    per_listing: dict[str, list] = defaultdict(list)
    errors = []
    observed: dict[str, Counter] = defaultdict(Counter)
    for lst, symbol, res in results:
        if not res["ok"]:
            errors.append({"key": lst["instrument_key"], "symbol": symbol, "error": res["error"]})
            continue
        info = res["info"]
        back = from_finam_venue(info.mic, info.board)
        match = (back.mic, back.board, info.ticker) == (lst["mic"], lst["board"], lst["ticker"])
        per_listing[lst["instrument_key"]].append(
            {"symbol": symbol, "finam": [info.mic, info.board], "back": [back.mic, back.board], "match": match, "type": info.type}
        )
        observed[f"{lst['mic']}|{lst['board']}|{lst['market']}"][f"{info.mic}|{info.board}|{info.type}"] += 1

    # Matching rules, in order:
    #   strict    - from_finam_venue(finam mic, board) + ticker == catalog (mic, board, ticker)
    #   empty     - Finam board is empty (foreign venues, indices, archived, some CETS):
    #               compare (mic, ticker) only
    #   tiebreak  - still several: keep the one on the mic that to_finam_venue() predicts
    matched, unmatched, ambiguous = [], [], []
    rules = Counter()
    for lst in listings:
        cands = per_listing.get(lst["instrument_key"], [])
        rule = "strict"
        hits = [c for c in cands if c["match"]]
        if not hits:
            hits = [c for c in cands if c["finam"][1] == "" and c["back"][0] == lst["mic"]]
            rule = "empty_board"
        if len(hits) > 1:
            want = to_finam_venue(lst["mic"], lst["board"]).mic
            preferred = [c for c in hits if c["finam"][0] == want]
            if len(preferred) == 1:
                hits, rule = preferred, rule + "+mic_tiebreak"
        if len(hits) == 1:
            matched.append(lst["instrument_key"])
            rules[rule] += 1
        elif len(hits) > 1:
            ambiguous.append({"key": lst["instrument_key"], "symbols": [h["symbol"] for h in hits]})
        elif cands:
            unmatched.append({"key": lst["instrument_key"], "candidates": cands})
    return {
        "listings": len(listings),
        "matched_exactly_one": len(matched),
        "match_rules": dict(rules),
        "ambiguous": ambiguous,
        "unmatched": unmatched,
        "no_candidate": no_candidate,
        "get_asset_errors": errors,
        "observed_venues": {k: v.most_common() for k, v in observed.items()},
        "matched_keys_sample": matched[:5],
    }


def bars_probe(client, symbol: str, tf: str, days: int) -> dict:
    end = datetime.now(timezone.utc)
    try:
        resp = client.bars(symbol, tf_enum(tf), end - timedelta(days=days), end)
        n = len(resp.bars)
        out = {"ok": True, "count": n}
        if n:
            out["first"] = resp.bars[0].timestamp.ToDatetime().isoformat()
            out["last"] = resp.bars[-1].timestamp.ToDatetime().isoformat()
        return out
    except FinamError as exc:
        return {"ok": False, "error": f"{exc.broker_code}: {exc.message}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def step_bar_limits(client, symbol: str) -> dict:
    out = {}
    for tf in TIMEFRAMES:
        tried = []
        best = None
        for days in WINDOW_DAYS:
            res = bars_probe(client, symbol, tf, days)
            tried.append({"days": days, **res})
            if res["ok"]:
                best = {"days": days, "count": res["count"]}
                break
        out[tf] = {"largest_ok": best, "attempts": tried}
        log(f"  bars {symbol} {tf}: {best}")
    return out


def step_instruments_bars(client, items, account_id) -> dict:
    """Types other than plain stocks/futures: details + whether bars exist."""
    by_type: dict[str, list] = defaultdict(list)
    for it in items:
        if not it.is_archived:
            by_type[it.type].append(it)
    keywords = ("BRENT", "GOLD", "OIL", "НЕФТ", "ЗОЛОТ", "BR", "XAU")
    out: dict = {"types": {}, "commodity_name_hits": []}
    for typ, lst in sorted(by_type.items()):
        sample = lst[:3]
        rows = []
        for it in sample:
            asset = get_asset_safe(client, it.symbol, account_id)
            row = {"symbol": it.symbol, "name": it.name}
            if asset["ok"]:
                row.update(mic=asset["info"].mic, board=asset["info"].board)
            else:
                row["asset_error"] = asset["error"]
            row["bars_D"] = bars_probe(client, it.symbol, "D", 30)
            row["bars_H1"] = bars_probe(client, it.symbol, "H1", 7)
            rows.append(row)
        out["types"][typ] = {"count": len(lst), "samples": rows}
    for it in items:
        name = f"{it.ticker} {it.name}".upper()
        if not it.is_archived and any(k in name for k in keywords) and "INDEX" in it.type.upper() or (
            "ИНДЕКС" in it.name.upper() and any(k in name for k in keywords)
        ):
            out["commodity_name_hits"].append({"symbol": it.symbol, "type": it.type, "name": it.name})
    out["commodity_name_hits"] = out["commodity_name_hits"][:40]
    return out


def step_archived(client, items, account_id) -> dict:
    archived = [i for i in items if i.is_archived]
    rows = []
    for it in archived[:8]:
        asset = get_asset_safe(client, it.symbol, account_id)
        rows.append(
            {
                "symbol": it.symbol,
                "name": it.name,
                "get_asset": {"ok": True, "mic": asset["info"].mic, "board": asset["info"].board}
                if asset["ok"]
                else {"ok": False, "error": asset["error"]},
                "bars_D_30d": bars_probe(client, it.symbol, "D", 30),
            }
        )
    return {"archived_total": len(archived), "samples": rows}


def step_stream(client, symbol: str, seconds: float) -> dict:
    events: list[str] = []
    error: list[str] = []
    started = threading.Event()

    def consume():
        try:
            stream = client.subscribe_bars(symbol, tf_enum("M1"))
            started.set()
            for ev in stream:
                events.append(datetime.now().isoformat())
                if len(events) >= 3:
                    break
        except Exception as exc:  # noqa: BLE001
            error.append(f"{type(exc).__name__}: {exc}")

    th = threading.Thread(target=consume, daemon=True)
    th.start()
    th.join(timeout=seconds)
    alive = th.is_alive()
    return {"symbol": symbol, "opened": started.is_set(), "events": len(events), "still_waiting": alive, "error": error}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token-file", required=True)
    ap.add_argument("--catalog-db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-types", action="store_true")
    ap.add_argument("--skip-bars", action="store_true")
    ap.add_argument("--skip-stream", action="store_true")
    ap.add_argument("--stream-seconds", type=float, default=15.0)
    args = ap.parse_args()

    client = FinamApiClient(ClientConfig(secret_file=args.token_file))
    install_throttle(client)
    report: dict = {"generated_at": datetime.now(timezone.utc).isoformat()}
    try:
        report["token"] = step_token(client)
        log(f"token: {report['token']}")
        if not report["token"]["readonly"] or not report["token"]["account_ids"]:
            report["abort"] = "token is not read-only or has no accounts"
            Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2))
            log("ABORT: token is not read-only")
            return 2
        account_id = report["token"]["account_ids"][0]

        log("AllAssets ...")
        items, report["assets"] = step_all_assets(client)
        log(f"AllAssets: {report['assets']['all_assets_unfiltered']['rows']} rows")

        listings = load_listings(Path(args.catalog_db))
        report["match"] = step_match(client, listings, items, account_id)
        log(f"matched exactly one: {report['match']['matched_exactly_one']}/{report['match']['listings']}")

        report["archived"] = step_archived(client, items, account_id)
        if not args.skip_types:
            report["instrument_types"] = step_instruments_bars(client, items, account_id)
        if not args.skip_bars:
            report["bar_limits"] = {"SBER@MISX": step_bar_limits(client, "SBER@MISX")}
        if not args.skip_stream:
            report["stream"] = step_stream(client, "SBER@MISX", args.stream_seconds)
        report["throttle"] = dict(THROTTLE)
    finally:
        client.close()
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        log(f"report -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
