import io
import pathlib
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import core  # noqa: E402
import hub  # noqa: E402
import report as R  # noqa: E402

st.set_page_config(page_title="Strategy Analytics Hub", layout="wide", page_icon=":material/hub:")
st.html(hub.CSS)


def chart(fig, title, h=360):
    fig.update_layout(title=dict(text=title, x=0, font=dict(size=14, color=hub.TEXT)), height=h, **hub.PLOTLY_DARK)
    st.plotly_chart(fig, width="stretch")


def gfmt(x):
    """1.0 -> '1', 1.1 -> '1.1' (Index/Strike arrive as floats because a leg sub-index like '1.1'
    forces the whole column to float on read)."""
    return f"{x:g}" if isinstance(x, float) and not pd.isna(x) else ("" if pd.isna(x) else str(x))


# ====================== header ======================
st.html(hub.wrap(hub.hero(
    "Strategy Analytics Hub",
    "Combine multiple AlgoTest or StockMock trade reports into a single, account-level performance dashboard. "
    "Upload as many files as you like - Long and Short AlgoTest exports (either column layout), and StockMock "
    "basket workbooks - they are merged chronologically into one trade log and one set of KPIs.")))

with st.expander("Which files can I upload?"):
    st.html(hub.wrap(hub.table(["Format", "What it looks like", "What you get"], [
        ["AlgoTest (standard)", "Index, Entry Date, Entry Time, Type, Strike, B/S, Qty, Entry/Exit Price, P/L",
         "One row per trade, with strike/option type/position"],
        ["AlgoTest (detailed)", "Entry-Date, Instrument-Kind, StrikePrice, Position, ExitDate, ExpiryDate, Remarks …",
         "Same, plus expiry date and the exit remark"],
        ["StockMock (.xlsx)", "A basket workbook with a 'Basket Strategies' sheet and one '# S-n - Result' sheet per strategy",
         "One row per expiry cycle, from every enabled (Run=True) strategy, matched exactly against StockMock's own "
         "Overall Profit / Win% figures. No per-leg strike/price or entry time is available at this level, so those "
         "columns are blank and Duration is left out rather than guessed"],
        ["A previous report from this app", "Any 'Download full report (Excel)' this app has given you before (Backtest "
         "Report or an earlier Strategy Hub export)", "Its 'Trades' sheet is re-imported directly, so you can merge an "
         "older report back in alongside new files"],
    ])))

up = st.file_uploader("Drop trade report files here, or browse", type=["csv", "xlsx"], accept_multiple_files=True)
cache = st.session_state.get("hub_cache")

# ====================== per-file parsing (new upload), or the last successful run from this session ======================
if up:
    frames, chips, errors, notes, margins = [], [], [], [], []
    for f in up:
        try:
            raw = f.getvalue()
            t, rej, warn, kind = core.detect_and_load(raw, f.name)
            t = t.rename(columns={"Direction": "Source"})
            t["Source"] = f.name
        except Exception as e:  # one bad file must never take down the whole page
            chips.append(hub.chip(f.name, "", 0, err=True))
            errors.append(f"{f.name}: {e}")
            continue
        frames.append(t)
        chips.append(hub.chip(f.name, kind, len(t)))
        if kind == "StockMock":
            mg = core.extract_stockmock_margin(raw)
            if mg:
                margins.append((f.name, mg))
        if len(rej):
            notes.append(f"{f.name}: {len(rej)} row(s) rejected - {'; '.join(rej['Reason'].unique()[:3])}")
        notes += [f"{f.name}: {w}" for w in warn]
    names = [f.name for f in up]
    if frames:  # keep the last successful parse in memory - switching pages or closing the uploader won't lose it
        st.session_state["hub_cache"] = {"frames": frames, "chips": chips, "errors": errors, "notes": notes,
                                         "names": names, "margins": margins}
    cache = st.session_state.get("hub_cache") if frames else None
elif cache:
    frames, chips, errors, notes = cache["frames"], cache["chips"], cache["errors"], cache["notes"]
    margins, names = cache.get("margins", []), cache["names"]
    b1, b2 = st.columns([5, 1])
    b1.html(hub.wrap(f'<div class="notice-ok">Showing the last report generated in this session '
                     f'({", ".join(names)}) - drop new files above to replace it.</div>'))
    if b2.button("Clear", width="stretch"):
        del st.session_state["hub_cache"]
        st.rerun()
else:
    frames, chips, errors, notes, margins, names = [], [], [], [], [], []

if not frames:
    st.html(hub.wrap('<div class="empty"><b>Upload your trade reports to build the dashboard</b>'
                     '<div class="steps">① Export your results from AlgoTest or StockMock<br>'
                     '② Drop one or more files above - Long, Short, multiple strategies, mixed sources, all fine<br>'
                     '③ Set your capital and charges<br>'
                     '④ Get one merged equity curve, KPI set and trade log</div></div>'))
    st.stop()

# ====================== capital / charges (margin detected from StockMock files, if any) ======================
sm_margin = sum(v for _, v in margins) if margins else None
c1, c2, c3 = st.columns([1.3, 1, 1.7])
use_margin = c1.checkbox(f"Use StockMock's own margin ({R.inr(sm_margin)})" if sm_margin else "Use StockMock's own margin",
                         value=bool(sm_margin), disabled=not sm_margin,
                         help="StockMock prints its own basket margin in the file (Basket Strategies sheet) - "
                             "tick to use that as capital instead of the figure typed below." if sm_margin else
                             "No StockMock file with a readable margin is in this upload.")
manual_capital = c2.number_input("Initial Capital (₹)", min_value=0.0, step=10000.0, format="%.0f", key="hub_capital",
                                 value=(cache or {}).get("capital", 200000.0), disabled=use_margin and bool(sm_margin),
                                 help="Ignored while 'Use StockMock's own margin' is ticked." if sm_margin else None)
capital = sm_margin if (use_margin and sm_margin) else manual_capital
charges = c3.number_input("Total Charges (₹)", min_value=0.0, step=100.0, format="%.0f", key="hub_charges",
                          value=(cache or {}).get("charges", 0.0),
                          help="Spread evenly across every merged trade (the source files carry no per-trade charge).")
if cache is not None:
    cache["capital"], cache["charges"] = manual_capital, charges

st.html(hub.wrap('<div class="filebar">' + "".join(chips) + "</div>"
                 + "".join(f'<div class="notice-bad">{e}</div>' for e in errors)
                 + "".join(f'<div class="notice-warn">{n}</div>' for n in notes)))

m = core.hub_merge(frames, capital, charges)
mm = core.hub_metrics(m, capital)
eq = core.hub_equity(m, capital)
mat, yearly = core.hub_monthly_matrix(m, capital)
daily = core.daily_pnl(m)

# ====================== section visibility ======================
st.html(hub.wrap(hub.h2("Report sections")))
t1, t2, t3, t4, t5 = st.columns(5)
show_kpi = t1.checkbox("KPIs", True)
show_charts = t2.checkbox("Charts", True)
show_matrix = t3.checkbox("Monthly / Yearly", True)
show_daily = t4.checkbox("Day-wise", True)
show_log = t5.checkbox("Trade log", True)

# ====================== KPI row ======================
if show_kpi:
    roi = f'Return: {mm["ROI %"]:.2f}% on {R.inr(capital)}' if mm["ROI %"] is not None else f'Capital: {R.inr(capital)}'
    dd_sub = f'{mm["Max Drawdown % of Capital"]:.2f}% of Initial Capital' if mm["Max Drawdown % of Capital"] is not None else "Peak to trough"
    st.html(hub.wrap(hub.kpis([
        ("Net P&L", R.inr(mm["Net P&L"]), roi, R.sgn(mm["Net P&L"]), hub.POS if mm["Net P&L"] >= 0 else hub.NEG),
        ("Win Rate", R.num(mm["Win Rate %"], 1, "%"), f'Wins: {mm["Winning Trades"]} | Losses: {mm["Losing Trades"]}', "", hub.ACCENT),
        ("Profit Factor", R.num(mm["Profit Factor"]), f'Gross: {R.inr(mm["Gross Profit"])}', "", hub.ACCENT2),
        ("Max Drawdown", R.inr(-mm["Max Drawdown"]) if mm["Max Drawdown"] else "n/a", dd_sub, "neg", hub.NEG),
        ("Avg Trade P&L", R.inr(mm["Avg P&L / Trade"]), f'Total Trades: {mm["Total Trades"]:,}',
         R.sgn(mm["Avg P&L / Trade"]), hub.ACCENT),
    ])))

# ====================== charts ======================
if show_charts:
    st.html(hub.wrap(hub.h2("Combined Cumulative Equity Curve")))
    with st.container(border=True):
        f = go.Figure(go.Scatter(x=eq["Exit DateTime"], y=eq["Equity"], mode="lines", line=dict(color=hub.ACCENT, width=2.6, shape="spline", smoothing=0.3),
                                 fill="tozeroy", fillcolor="rgba(76,141,255,.14)", hovertemplate="%{x|%d %b %Y}<br>₹%{y:,.0f}<extra></extra>"))
        f.update_xaxes(rangeslider=dict(visible=True, thickness=0.06, bgcolor=hub.PANEL2, bordercolor=hub.BORDER, borderwidth=1))
        chart(f, "Combined Cumulative Equity Curve (₹)", 460)
    with st.container(border=True):
        f = go.Figure(go.Scatter(x=eq["Exit DateTime"], y=-eq["Drawdown %"], mode="lines", line=dict(color=hub.NEG, width=1.8, shape="spline", smoothing=0.3),
                                 fill="tozeroy", fillcolor="rgba(251,91,91,.16)", hovertemplate="%{x|%d %b %Y}<br>%{y:.2f}%<extra></extra>"))
        f.update_yaxes(ticksuffix="%")
        chart(f, "Underwater Drawdown Curve (%)", 320)

    a, b = st.columns(2)
    with a, st.container(border=True):
        f = go.Figure(go.Bar(x=yearly["Year"].astype(str), y=yearly["Net P&L"],
                             marker_color=[hub.POS if x > 0 else hub.NEG for x in yearly["Net P&L"]]))
        chart(f, "Yearly Returns Breakdown (₹)", 340)
    with b, st.container(border=True):
        f = go.Figure(go.Pie(labels=["Winning", "Losing", "Breakeven"], hole=.6, sort=False,
                             values=[mm["Winning Trades"], mm["Losing Trades"], mm["Breakeven Trades"]],
                             marker_colors=[hub.POS, hub.NEG, hub.MUTED2], textfont=dict(color=hub.TEXT)))
        chart(f, "Winning vs Losing Trades", 340)
    st.html(hub.wrap('<p class="cap">Equity starts at Initial Capital and adds each trade\'s Net P&L in exit-time order. '
                     'The underwater curve is the standard drawdown %: current equity below its own running peak. '
                     '"% of Initial Capital" in the KPI card above uses a fixed denominator instead, for a quick capital-at-risk read.</p>'))

# ====================== monthly/yearly matrix ======================
if show_matrix:
    st.html(hub.wrap(hub.h2("Monthly & Yearly Returns Performance Matrix") + hub.heatmap(mat, yearly)
                     + '<p class="cap">₹ net P&L by exit month. Return % is each year\'s net P&L ÷ Initial Capital (not '
                       'annualised, not compounded). This is the same exit-date basis used for the day-wise table below, '
                       'and matches a StockMock file\'s own day-level Overall Profit / Win% exactly.</p>'))

# ====================== day-wise breakdown ======================
if show_daily and len(daily):
    st.html(hub.wrap(hub.h2("Day-wise Breakdown")))
    st.html(hub.wrap('<p class="cap">Every trading day, all together - sums every trade (across every uploaded strategy/file) '
                     'that exited that day, the same basis StockMock itself uses for its day-level Win% and Max Profit/Loss '
                     'figures. Use the filters only if you want to narrow it down.</p>'))
    dd = pd.to_datetime(daily["Date"])
    f1, f2, f3 = st.columns([1, 1, 2])
    years_av = sorted(dd.dt.year.unique(), reverse=True)
    dy = f1.multiselect("Year", years_av, key="hub_day_year")
    months_av = sorted(dd.dt.month.unique())
    dm = f2.multiselect("Month", months_av, format_func=lambda n: pd.Timestamp(2000, n, 1).strftime("%B"), key="hub_day_month")
    dq = f3.text_input("Search", key="hub_day_q", placeholder="e.g. a date, or part of it")

    sel = daily.copy()
    if dy:
        sel = sel[dd.dt.year.isin(dy)]
    if dm:
        sel = sel[dd.dt.month.isin(dm)]

    # --- day-wise monthly breakdown - every calendar day's ₹ value shown directly, same table
    #     style as the Monthly & Yearly matrix above (no hidden-behind-hover colour boxes) ---
    hdd = pd.to_datetime(sel["Date"])
    grid = sel.assign(YM=hdd.dt.to_period("M").astype(str), Day=hdd.dt.day).pivot_table(
        index="YM", columns="Day", values="Net P&L", aggfunc="sum").reindex(columns=range(1, 32)).sort_index()
    if len(grid):
        st.html(hub.wrap(hub.day_table(grid)
                         + '<p class="cap">One row per month, one column per calendar day - every cell shows that day\'s '
                           'net P&amp;L directly. Directly comparable to the Monthly &amp; Yearly matrix above, just at day resolution.</p>'))

    # --- daily P&L bar chart, smooth zoom/pan via a range slider ---
    if len(sel):
        bar = go.Figure(go.Bar(x=pd.to_datetime(sel["Date"]), y=sel["Net P&L"],
                               marker_color=[hub.POS if v > 0 else hub.NEG if v < 0 else hub.MUTED2 for v in sel["Net P&L"]],
                               hovertemplate="%{x|%d %b %Y}<br>₹%{y:,.0f}<extra></extra>"))
        bar.update_xaxes(rangeslider=dict(visible=True, thickness=0.08, bgcolor=hub.PANEL2, bordercolor=hub.BORDER, borderwidth=1),
                         rangeselector=dict(
            buttons=[dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"), dict(step="all", label="All")],
            bgcolor=hub.PANEL2, activecolor=hub.ACCENT, font=dict(color=hub.TEXT, size=11)))
        with st.container(border=True):
            chart(bar, "Daily Net P&L (₹) - drag the range below to zoom", 380)

    # --- the full day-by-day table, every day at once, no selection required ---
    disp_daily = sel.sort_values("Date", ascending=False).copy()
    disp_daily["Date"] = pd.to_datetime(disp_daily["Date"]).dt.strftime("%a, %d %b %Y")
    disp_daily = disp_daily.rename(columns={"Net P&L": "Net P&L (₹)"})
    if dq:
        disp_daily = disp_daily[disp_daily["Date"].str.contains(dq, case=False, regex=False)]
    st.caption(f"{len(disp_daily):,} trading day(s)" + (f" of {len(daily):,} total" if len(disp_daily) != len(daily) else ""))
    st.dataframe(disp_daily.style.map(lambda x: f"color:{hub.POS}" if isinstance(x, (int, float)) and x > 0
                                      else f"color:{hub.NEG}" if isinstance(x, (int, float)) and x < 0 else "",
                                      subset=["Net P&L (₹)"]).format({"Net P&L (₹)": "{:,.2f}"}),
                 hide_index=True, height=420, width="stretch")

# ====================== master trade log ======================
if show_log:
    st.html(hub.wrap(hub.h2("Combined Master Trade Log")))
    disp = m.copy()
    for c in ("Strike", "Type", "Entry Price", "Exit Price", "B/S", "Expiry", "Remarks"):
        if c not in disp:
            disp[c] = None
    disp["Strike/Type"] = (disp["Strike"].map(gfmt) + " " + disp["Type"].fillna("")).str.strip().replace("", "—")
    disp["Index"] = disp["Index"].map(gfmt)
    cols = ["Index", "Source", "Entry DateTime", "Strike/Type", "Expiry", "B/S", "Entry Price", "Exit Price",
           "Exit DateTime", "Gross P/L", "Charges", "Net P/L", "Return %", "Remarks"]
    disp = disp[cols].rename(columns={"B/S": "Position", "Net P/L": "Net P/L (₹)"})

    q = st.text_input("Search the trade log (any column)")
    sources = ["All"] + sorted(m["Source"].unique().tolist())
    tabs = st.tabs(["All", "Winning", "Losing"] + (["By file"] if len(sources) > 2 else []))
    views = [disp, disp[m["Net P/L"] > 0], disp[m["Net P/L"] < 0]]
    for tab, name, s in zip(tabs, ["All", "Winning", "Losing"], views):
        with tab:
            if q:
                s = s[s.astype(str).apply(lambda c: c.str.contains(q, case=False, regex=False)).any(axis=1)]
            st.caption(f"{len(s):,} trades" + (" (showing first 200)" if len(s) > 200 else ""))
            st.dataframe(s.head(200).style.map(lambda x: f"color:{hub.POS}" if isinstance(x, (int, float)) and x > 0
                                               else f"color:{hub.NEG}" if isinstance(x, (int, float)) and x < 0 else "",
                                               subset=[c for c in ("Gross P/L", "Net P/L (₹)", "Return %") if c in s])
                         .format({"Gross P/L": "{:,.2f}", "Charges": "{:,.2f}", "Net P/L (₹)": "{:,.2f}", "Return %": "{:,.2f}%"}),
                         hide_index=True, height=420,
                         column_config={"Entry DateTime": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm"),
                                        "Exit DateTime": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm")})
    if len(sources) > 2:
        with tabs[-1]:
            for src in sources[1:]:
                s = disp[m["Source"] == src]
                st.markdown(f"**{src}** · {len(s):,} trades")
                st.dataframe(s.head(100), hide_index=True, height=240)

    x1, x2 = st.columns([1, 6])
    x1.download_button("Download CSV", core.to_csv(disp), "strategy hub trades.csv", "text/csv")
else:
    x2 = st

# ====================== full Excel report ======================
info = [
    ("Files merged", ", ".join(names)),
    ("Initial capital", R.inr(capital) + (" (StockMock's own margin)" if use_margin and sm_margin else "")),
    ("Total charges", R.inr(charges) + " (spread evenly across every trade)"),
    ("Trade definition", "AlgoTest: one parent trade row (P/L = file P/L). StockMock: one expiry cycle per enabled strategy."),
    ("Net P/L", "Gross P/L (file) minus this trade's share of Total Charges"),
    ("Return %", "Net P/L ÷ Initial Capital × 100, per trade and per year"),
    ("Generated", pd.Timestamp.now().strftime("%d %b %Y %H:%M")),
]
tables = core.report_tables({"Combined": m}, capital, None, (1, 3, 6, 12), m)
xlsx = core.report_workbook(info, tables, title="Strategy Hub Report")
x2.download_button("Download full report (Excel)", xlsx, "Strategy Hub Report.xlsx", type="primary")
