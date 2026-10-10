"""Run: python -m pytest tests -q. Uses your example CSVs one folder up; they are never committed,
so on GitHub (CI) these tests are skipped and tests/test_smoke.py covers the app with synthetic data."""
import csv
import io
import pathlib
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import core  # noqa: E402

D = pathlib.Path(__file__).resolve().parents[2]
rd = lambda n: core.read_table(D / n, n)
pytestmark = pytest.mark.skipif(not (D / "Long+Short Row file.csv").exists(),
                                reason="example CSVs are local-only (not in the repo)")


# ---------- signal splitter ----------
def test_split_matches_manual_examples():
    r = core.split_signals(rd("Long+Short Row file.csv"))
    assert r.reconciled and len(r.unclassified) == 0 and not r.warnings
    assert (len(r.long), len(r.short), r.total) == (1264, 1198, 2462)
    for got, name in ((r.long, "Long Example.csv"), (r.short, "Short Example.csv")):
        pd.testing.assert_frame_equal(got.reset_index(drop=True), rd(name))  # values, order, dates


def test_split_keeps_each_row_once_and_values_unchanged():
    src = rd("Long+Short Row file.csv")
    r = core.split_signals(src, out_fmt=None)
    both = pd.concat([r.long, r.short]).sort_index()
    pd.testing.assert_frame_equal(both, src)


def test_unclassified_and_missing_column_and_empty_side():
    src = rd("Long+Short Row file.csv").head(4)  # long trades only
    src.loc[0, "Type"] = "Weird"
    r = core.split_signals(src)
    assert len(r.unclassified) == 1 and len(r.short) == 0 and r.reconciled
    assert r.warnings  # trade 1 now lacks its exit
    with pytest.raises(ValueError, match="Missing required"):
        core.split_signals(src.drop(columns="Price"))
    with pytest.raises(ValueError, match="unsupported"):
        core.read_table(io.BytesIO(b""), "x.txt")


# ---------- backtest import / analytics ----------
def independent(path):
    """Plain-csv recomputation of parent-row P/L (no pandas, no core)."""
    pl = []
    for row in csv.DictReader(open(D / path, encoding="utf-8-sig")):
        if row["Type"] == "":
            pl.append(float(row["P/L"]))
    return pl


def load(name, d):
    t, rej, w = core.load_algotest(rd(name), d)
    assert rej.empty and not w
    return t


def test_trades_match_independent_calc():
    lt, st_ = load("Algo Test Long.csv", "Long"), load("Algo test  Short.csv", "Short")
    for t, f in ((lt, "Algo Test Long.csv"), (st_, "Algo test  Short.csv")):
        ref = independent(f)
        m = core.metrics(t)
        assert m["Total Trades"] == len(ref)
        assert m["Net P&L"] == pytest.approx(sum(ref))
        assert m["Gross Profit"] == pytest.approx(sum(x for x in ref if x > 0))
        assert m["Gross Loss"] == pytest.approx(sum(x for x in ref if x < 0))
        assert m["Win Rate %"] == pytest.approx(sum(x > 0 for x in ref) / len(ref) * 100)
        # drawdown by brute force (file order == chronological, all intraday)
        cum = peak = dd = 0
        for x in ref:
            cum += x
            peak = max(peak, cum)
            dd = max(dd, peak - cum)
        assert m["Max Drawdown"] == pytest.approx(dd)
    assert core.metrics(lt)["Net P&L"] == pytest.approx(-47399.34)
    assert core.metrics(st_)["Net P&L"] == pytest.approx(18190.25)


def test_combined_uses_trade_records_not_averages():
    lt, st_ = load("Algo Test Long.csv", "Long"), load("Algo test  Short.csv", "Short")
    c = core.combine(lt, st_)
    mc, ml, ms = core.metrics(c), core.metrics(lt), core.metrics(st_)
    assert mc["Total Trades"] == ml["Total Trades"] + ms["Total Trades"] == 510
    assert mc["Net P&L"] == pytest.approx(ml["Net P&L"] + ms["Net P&L"])
    wins = ml["Winning Trades"] + ms["Winning Trades"]
    assert mc["Win Rate %"] == pytest.approx(wins / 510 * 100)
    assert mc["Avg P&L / Trade"] == pytest.approx(mc["Net P&L"] / 510)
    assert c["Entry DateTime"].is_monotonic_increasing
    assert set(c.Direction) == {"Long", "Short"} and not c.duplicated(["Direction", "Entry DateTime"]).any()
    assert core.period_pnl(c, "M")["Net P&L"].sum() == pytest.approx(mc["Net P&L"])
    assert core.period_pnl(c, "Y")["Trades"].sum() == 510


def test_small_known_case_and_edges():
    t = pd.DataFrame({"P/L": [100.0, -50, -80, 30, 0],
                      "Entry DateTime": pd.date_range("2024-01-01 10:00", periods=5, freq="D"),
                      "Duration (min)": [10, 20, 30, 40, 50]})
    t["Exit DateTime"] = t["Entry DateTime"] + pd.Timedelta(minutes=5)
    m = core.metrics(t)
    assert (m["Winning Trades"], m["Losing Trades"], m["Breakeven Trades"]) == (2, 2, 1)
    assert m["Max Drawdown"] == 130  # peak 100 -> trough -30
    assert m["Profit Factor"] == pytest.approx(130 / 130)
    assert m["Avg Loss"] == -65 and m["Largest Loss"] == -80 and m["Avg Duration (min)"] == 30
    # all-winners / empty -> unavailable, not guessed
    w = core.metrics(t[t["P/L"] > 0])
    assert w["Profit Factor"] is None and w["Avg Loss"] is None
    e = core.metrics(t.iloc[0:0])
    assert e["Total Trades"] == 0 and e["Win Rate %"] is None and e["Net P&L"] is None
    # drawdown from a losing start is measured from the 0 baseline
    assert core.equity(t[t["P/L"] < 0])["Drawdown"].max() == 130


def test_validation_and_bad_rows():
    raw = rd("Algo Test Long.csv")
    with pytest.raises(ValueError, match="missing column"):
        core.load_algotest(raw.drop(columns="P/L"), "Long")
    # reordered columns + optional leg/Vix columns absent still load
    t, rej, _ = core.load_algotest(raw[["P/L", "Exit Time", "Exit Date", "Entry Time", "Entry Date", "Index"]]
                                   [raw.Type.isna()], "Long")
    assert len(t) == 238 and rej.empty
    # bad date, bad P/L and an exact duplicate are reported, not dropped silently
    bad = pd.concat([raw.head(2), raw.head(2).iloc[:2]], ignore_index=True)  # parent+leg twice
    bad = pd.concat([bad, raw.iloc[[2]]], ignore_index=True)
    bad.loc[4, "Entry Date"] = "not-a-date"
    t, rej, w = core.load_algotest(bad, "Long")
    assert len(t) == 1 and set(rej.Reason) == {"duplicate trade", "invalid entry date/time"} and w


# ---------- report analytics / tolerant loader ----------
def test_monthly_yearly_rolling_consistent():
    t = core.combine(load("Algo Test Long.csv", "Long"), load("Algo test  Short.csv", "Short"))
    mat, yearly = core.monthly_matrix(t)
    net = core.metrics(t)["Net P&L"]
    assert mat.sum().sum() == pytest.approx(net) and yearly["Net P&L"].sum() == pytest.approx(net)
    assert yearly["Trades"].sum() == 510
    r = core.rolling_returns(t, (1, 3))
    assert (r["Worst"] <= r["Average"]).all() and (r["Average"] <= r["Best"]).all()
    # monthly rows (one per month, +10) -> every 3-month window sums 30, 12m window only fits once
    m = pd.DataFrame({"P/L": [10.0] * 13, "Entry DateTime": pd.date_range("2024-01-01", periods=13, freq="MS")})
    m["Exit DateTime"] = m["Entry DateTime"]
    m["Duration (min)"] = 0
    r = core.rolling_returns(m, (3, 12, 24)).set_index("Months")
    assert r.loc[3, "Windows"] == 10 and r.loc[3, "Worst"] == r.loc[3, "Best"] == 30
    assert r.loc[12, "Windows"] == 1 and 24 not in r.index


def test_tolerant_loader_merged_report_and_case():
    raw = pd.read_csv(D / "Algo Test Long.csv", encoding="utf-8-sig")
    raw.columns = [c.lower() for c in raw.columns]  # 'entry date', 'p/l' ...
    t, rej, _ = core.load_algotest(raw, "Long")
    assert len(t) == 238 and rej.empty
    merged = pd.DataFrame({"Trade #": [1, 2], "Entry Date": ["2022-01-03"] * 2, "Entry Time": ["09:30:00", "12:15:00"],
                           "Exit Date": ["2022-01-03"] * 2, "Exit Time": ["15:10:00", "13:20:00"],
                           "Entry Price Spot": [1.0, 2.0], "Exit Price Spot": [2.0, 1.0], "P/L": [3526.25, -783.25]})
    t, rej, _ = core.load_algotest(merged, "Long")
    assert len(t) == 2 and core.metrics(t)["Net P&L"] == pytest.approx(2743.0)


# ---------- capital / ROI and the formatted Excel report ----------
def _series():
    lt, st_ = load("Algo Test Long.csv", "Long"), load("Algo test  Short.csv", "Short")
    return {"Combined": core.combine(lt, st_), "Long": lt, "Short": st_}


def test_capital_changes_roi_but_never_pnl():
    m = core.metrics(_series()["Combined"])
    assert all(v is None for v in core.capital_metrics(m, None).values())
    assert all(v is None for v in core.capital_metrics(m, 0).values())
    a, b = core.capital_metrics(m, 500000), core.capital_metrics(m, 1000000)
    assert a["ROI %"] == pytest.approx(m["Net P&L"] / 500000 * 100)
    assert a["Annualised ROI %"] == pytest.approx(m["Annualised P&L"] / 500000 * 100)
    assert a["Avg Monthly ROI %"] == pytest.approx(m["Avg Monthly P&L"] / 500000 * 100)
    assert a["Max DD % of Capital"] == pytest.approx(m["Max Drawdown"] / 500000 * 100)
    assert b["ROI %"] == pytest.approx(a["ROI %"] / 2)                      # double capital -> half ROI
    assert core.metrics(_series()["Combined"])["Net P&L"] == m["Net P&L"]    # P&L untouched


def _wb(cap):
    import io as _io
    import openpyxl
    S = _series()
    trades = S["Combined"]
    tables = core.report_tables(S, cap, pd.Timestamp("2025-09-26"), (1, 3), trades)
    return tables, openpyxl.load_workbook(_io.BytesIO(core.report_workbook([("Capital", str(cap))], tables)))


def test_excel_report_complete_and_formatted():
    tables, wb = _wb(500000)
    for sh in ("Report Info", "Summary", "Yearly", "Monthly Combined", "Monthly Long", "Monthly Short",
               "Regime", "Rolling", "Risk", "Trades"):
        assert sh in wb.sheetnames, sh
    ws = wb["Summary"]
    hdr = [c.value for c in ws[4]]
    assert hdr == ["Metric", "Combined", "Long", "Short"]
    assert ws["A4"].fill.fgColor.rgb.endswith("1F4E79") and ws["A4"].font.b    # navy bold header
    rows = {ws[f"A{r}"].value: r for r in range(5, ws.max_row + 1)}
    m = core.metrics(_series()["Combined"])
    assert ws[f"B{rows['Net P&L']}"].value == pytest.approx(m["Net P&L"])
    assert ws[f"B{rows['Net P&L']}"].number_format.startswith('"₹"#,##0.00')
    assert ws[f"B{rows['ROI on capital %']}"].value == pytest.approx(m["Net P&L"] / 500000 * 100)
    assert ws[f"B{rows['Win rate %']}"].number_format.startswith('0.00"%"')
    assert len(ws.tables) == 1                                                  # real Excel table (sort / filter)
    mon = wb["Monthly Combined"]
    assert [c.value for c in mon[4]][:13] == ["Year"] + core.MONTHS and mon.conditional_formatting
    assert mon.cell(mon.max_row, 1).value == "All years"
    tr = wb["Trades"]
    assert tr.max_row - 4 == 510
    pl_col = [c.value for c in tr[4]].index("P/L") + 1
    assert tr.cell(5, pl_col).number_format.startswith('"₹"')
    dt_col = [c.value for c in tr[4]].index("Entry DateTime") + 1
    assert tr.cell(5, dt_col).number_format == "dd-mmm-yyyy hh:mm"
    # monthly sheet total equals net P&L; yearly ROI follows the capital
    assert sum(r[0] for r in wb["Yearly"].iter_rows(min_row=5, min_col=3, max_col=3, values_only=True)
               if r[0] is not None) == pytest.approx(m["Net P&L"] + core.metrics(_series()["Long"])["Net P&L"]
                                                     + core.metrics(_series()["Short"])["Net P&L"])


def test_excel_without_capital_has_no_fake_roi():
    tables, wb = _wb(None)
    labels = [wb["Summary"][f"A{r}"].value for r in range(5, wb["Summary"].max_row + 1)]
    assert not any("ROI" in str(x) or "capital" in str(x) for x in labels)
    assert "ROI %" not in tables["Yearly"][0].columns and "Annualised ROI %" not in tables["Risk"][0].columns


def test_excel_sheet_order_and_year_format():
    _, wb = _wb(500000)
    assert wb.sheetnames[:3] == ["Report Info", "Summary", "Yearly"] and wb.sheetnames[-1] == "Trades"
    y = wb["Yearly"]
    yc = [c.value for c in y[4]].index("Year") + 1
    assert y.cell(5, yc).number_format == "0"          # 2024, not 2,024


def test_backtest_report_section_toggles_never_crash():
    """Each of the 19 table/chart toggles (Instructions > Page 2 details) must be independently
    removable, and clearing all of them must still render - with the Excel export always kept -
    without an exception. Needs real example files to drive the sidebar's own data loading, so
    this lives here (skipped like the rest of this file when they're absent), not in test_smoke."""
    from streamlit.testing.v1 import AppTest
    root = pathlib.Path(__file__).resolve().parents[1]
    at = AppTest.from_file(str(root / "views/2_Backtest_Dashboard.py"), default_timeout=60).run()
    example_cb = next(c for c in at.sidebar.checkbox if "bundled example" in c.label)
    at = example_cb.set_value(True).run()
    assert not at.exception
    ms = at.multiselect[0]
    assert len(ms.options) == 19
    at = at.multiselect[0].set_value(ms.options[:-1]).run()  # drop the last item
    assert not at.exception
    at = at.multiselect[0].set_value([]).run()  # clear everything
    assert not at.exception  # the Excel-building code at the bottom of the page still ran fine
