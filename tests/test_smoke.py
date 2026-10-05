"""Self-contained checks (no private data): synthetic TradingView + AlgoTest files run through
the whole pipeline, and every page of the app renders without an exception. Runs on GitHub CI."""
import io
import pathlib
import sys

import openpyxl
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import core  # noqa: E402


def tradingview(n=40):
    """n trades alternating long/short, exported the TradingView way (exit row, then entry row)."""
    rows, t0 = [], pd.Timestamp("2024-01-01 09:30")
    for i in range(1, n + 1):
        side = "long" if i % 2 else "short"
        e = t0 + pd.Timedelta(days=i)
        pnl = (-1) ** i * 10.5 * i
        for kind, ts in (("Exit", e + pd.Timedelta(hours=2)), ("Entry", e)):
            rows.append({"Trade number": i, "Type": f"{kind} {side}", "Date and time": f"{ts:%Y-%m-%d %H:%M}",
                         "Signal": "entry" if kind == "Entry" else "exit", "Price": 20000 + i, "Size (qty)": 1,
                         "Net PnL NONE": pnl})
    return pd.DataFrame(rows)


def algotest(n, pnl, start="2024-01-01"):
    """AlgoTest layout: a parent row (Type blank, holds P/L) followed by one leg row per trade."""
    rows, d = [], pd.Timestamp(start)
    for i in range(1, n + 1):
        day = d + pd.Timedelta(days=i)
        base = {"Entry Date": f"{day:%Y-%m-%d}", "Entry Time": " 10:00:00", "Exit Date": f"{day:%Y-%m-%d}",
                "Exit Time": " 14:30:00"}
        p = pnl(i)
        rows.append({"Index": str(i), **base, "Type": None, "Strike": None, "B/S": None, "Qty": None,
                     "Entry Price": None, "Exit Price": None, "Vix": 13.5, "P/L": p})
        rows.append({"Index": f"{i}.1", **base, "Type": "PE", "Strike": 22000, "B/S": "Sell", "Qty": 65,
                     "Entry Price": 100.0, "Exit Price": 100 - p / 65, "Vix": None, "P/L": p})
    return pd.DataFrame(rows)


def test_splitter_end_to_end():
    src = tradingview(40)
    r = core.split_signals(src)
    assert r.reconciled and (len(r.long), len(r.short), len(r.unclassified)) == (40, 40, 0) and not r.warnings
    assert set(r.long.Type.str.split().str[1]) == {"long"} and set(r.short.Type.str.split().str[1]) == {"short"}
    assert openpyxl.load_workbook(io.BytesIO(core.to_xlsx(r.long))).active.max_row == 41


def test_report_end_to_end_with_capital():
    L, _, _ = core.load_algotest(algotest(30, lambda i: 100.0 if i % 3 else -150.0), "Long")
    S, _, _ = core.load_algotest(algotest(20, lambda i: -80.0 if i % 4 == 0 else 60.0, "2024-03-01"), "Short")
    C = core.combine(L, S)
    m = core.metrics(C)
    assert m["Total Trades"] == 50 and m["Net P&L"] == pytest.approx(L["P/L"].sum() + S["P/L"].sum())
    assert core.capital_metrics(m, 100000)["ROI %"] == pytest.approx(m["Net P&L"] / 1000)
    tables = core.report_tables({"Combined": C, "Long": L, "Short": S}, 100000, pd.Timestamp("2024-03-15"), (1,), C)
    wb = openpyxl.load_workbook(io.BytesIO(core.report_workbook([("Capital", "100000")], tables)))
    assert {"Report Info", "Summary", "Yearly", "Trades"} <= set(wb.sheetnames)
    assert wb["Trades"].max_row - 4 == 50


@pytest.mark.parametrize("page", ["app.py", "views/0_Instructions.py", "views/1_Signal_Splitter.py",
                                  "views/2_Backtest_Dashboard.py"])
def test_every_page_renders(page):
    at = AppTest.from_file(str(ROOT / page), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
