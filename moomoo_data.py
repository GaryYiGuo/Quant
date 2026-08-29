"""Fetch market data through the locally running Moomoo OpenD gateway.

OpenD, rather than this script, handles sign-in and account access.  Do not put
your Moomoo password or trading password in this file.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable


def _sdk():
    """Load the SDK only when the program runs, with an actionable error."""
    try:
        from moomoo import AuType, KLType, OpenQuoteContext, RET_OK, SubType
    except ImportError as exc:
        raise RuntimeError(
            "The Moomoo SDK is not installed. Run: python -m pip install -r "
            "requirements-moomoo.txt"
        ) from exc
    return AuType, KLType, OpenQuoteContext, RET_OK, SubType


def _write_csv(frame, output: str | None) -> None:
    if output:
        path = Path(output).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(f"Saved {len(frame)} rows to {path}")
    else:
        print(frame.to_string(index=False))


def get_quotes(codes: Iterable[str], host: str, port: int):
    """Return the most recent subscribed quote for each Moomoo-format symbol."""
    _, _, OpenQuoteContext, RET_OK, SubType = _sdk()
    codes = list(codes)
    quote_ctx = OpenQuoteContext(host=host, port=port)
    try:
        result, detail = quote_ctx.subscribe(codes, [SubType.QUOTE], subscribe_push=False)
        if result != RET_OK:
            raise RuntimeError(f"Quote subscription failed: {detail}")
        result, data = quote_ctx.get_stock_quote(codes)
        if result != RET_OK:
            raise RuntimeError(f"Could not fetch quotes: {data}")
        return data
    finally:
        quote_ctx.close()


def get_history(
    code: str,
    start: str | None,
    end: str | None,
    interval: str,
    host: str,
    port: int,
    extended_hours: bool,
):
    """Return all historical candles in the requested date range."""
    AuType, KLType, OpenQuoteContext, RET_OK, _ = _sdk()
    interval_map = {
        "1m": KLType.K_1M,
        "5m": KLType.K_5M,
        "15m": KLType.K_15M,
        "30m": KLType.K_30M,
        "60m": KLType.K_60M,
        "day": KLType.K_DAY,
        "week": KLType.K_WEEK,
        "month": KLType.K_MON,
    }
    quote_ctx = OpenQuoteContext(host=host, port=port)
    pages = []
    page_key = None
    try:
        while True:
            result, data, page_key = quote_ctx.request_history_kline(
                code,
                start=start,
                end=end,
                ktype=interval_map[interval],
                autype=AuType.QFQ,
                max_count=1000,
                page_req_key=page_key,
                extended_time=extended_hours,
            )
            if result != RET_OK:
                raise RuntimeError(f"Could not fetch history: {data}")
            pages.append(data)
            if page_key is None:
                break
    finally:
        quote_ctx.close()

    # pandas is installed as a dependency of the official SDK.
    import pandas as pd

    return pd.concat(pages, ignore_index=True) if pages else pd.DataFrame()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Moomoo stock data via OpenD.")
    parser.add_argument("--host", default=os.getenv("MOOMOO_OPEND_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MOOMOO_OPEND_PORT", "11111")))
    subparsers = parser.add_subparsers(dest="command", required=True)

    quote_parser = subparsers.add_parser("quote", help="Get latest quotes.")
    quote_parser.add_argument("codes", nargs="+", help="Symbols, e.g. US.AAPL HK.00700")
    quote_parser.add_argument("--output", help="Optional CSV output path.")

    history_parser = subparsers.add_parser("history", help="Get historical candlesticks.")
    history_parser.add_argument("code", help="Symbol, e.g. US.AAPL")
    history_parser.add_argument("--start", help="Start date/time, e.g. 2026-01-01")
    history_parser.add_argument("--end", help="End date/time, e.g. 2026-08-01")
    history_parser.add_argument(
        "--interval", choices=["1m", "5m", "15m", "30m", "60m", "day", "week", "month"], default="day"
    )
    history_parser.add_argument("--extended-hours", action="store_true", help="Include US pre-/after-hours where supported.")
    history_parser.add_argument("--output", help="Optional CSV output path.")

    args = parser.parse_args()
    try:
        if args.command == "quote":
            _write_csv(get_quotes(args.codes, args.host, args.port), args.output)
        else:
            _write_csv(
                get_history(args.code, args.start, args.end, args.interval, args.host, args.port, args.extended_hours),
                args.output,
            )
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
