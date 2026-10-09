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


def chart(fig, title, h=320):
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
         "One row per expiry cycle, from every enabled (Run=True) strategy. No per-leg strike/price or entry "
         "time is available at this level, so those columns are blank and Duration is left out rather than guessed"],
    ])))

up = st.file_uploader("Drop trade report files here, or browse", type=["csv", "xlsx"], accept_multiple_files=True)
c1, c2 = st.columns(2)
capital = c1.number_input("Initial Capital (₹)", min_value=0.0, value=200000.0, step=10000.0, format="%.0f")
charges = c2.number_input("Total Charges (₹)", min_value=0.0, value=0.0, step=100.0, format="%.0f",
                          help="Spread evenly across every merged trade (the source files carry no per-trade charge).")

if not up:
    st.html(hub.wrap('<div class="empty"><b>Upload your trade reports to build the dashboard</b>'
                     '<div class="steps">① Export your results from AlgoTest or StockMock<br>'
                     '② Drop one or more files above - Long, Short, multiple strategies, mixed sources, all fine<br>'
                     '③ Set your capital and charges<br>'
                     '④ Get one merged equity curve, KPI set and trade log</div></div>'))
    st.stop()

# ====================== per-file parsing ======================
frames, chips, errors, notes = [], [], [], []
for f in up:
    try:
        t, rej, warn, kind = core.detect_and_load(f.getvalue(), f.name)
    except ValueError as e:
        chips.append(hub.chip(f.name, "", 0, err=True))
        errors.append(f"{f.name}: {e}")
        continue
    t = t.rename(columns={"Direction": "Source"})
    t["Source"] = f.name
    frames.append(t)
    chips.append(hub.chip(f.name, kind, len(t)))
    if len(rej):
        notes.append(f"{f.name}: {len(rej)} row(s) rejected - {'; '.join(rej['Reason'].unique()[:3])}")
    notes += [f"{f.name}: {w}" for w in warn]

st.html(hub.wrap('<div class="filebar">' + "".join(chips) + "</div>"
                 + "".join(f'<div class="bad">{e}</div>' for e in errors)
                 + "".join(f'<div class="warn">{n}</div>' for n in notes)))

if not frames:
    st.stop()

m = core.hub_merge(frames, capital, charges)
mm = core.hub_metrics(m, capital)
eq = core.hub_equity(m, capital)
mat, yearly = core.hub_monthly_matrix(m, capital)

# ====================== KPI row ======================
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
st.html(hub.wrap(hub.h2("Combined Cumulative Equity Curve")))
a, b = st.columns(2)
with a:
    f = go.Figure(go.Scatter(x=eq["Exit DateTime"], y=eq["Equity"], mode="lines", line=dict(color=hub.ACCENT, width=2.2),
                             fill="tozeroy", fillcolor="rgba(76,141,255,.10)"))
    chart(f, "Combined Cumulative Equity Curve (₹)", 330)
with b:
    f = go.Figure(go.Bar(x=yearly["Year"].astype(str), y=yearly["Net P&L"],
                         marker_color=[hub.POS if x > 0 else hub.NEG for x in yearly["Net P&L"]]))
    chart(f, "Yearly Returns Breakdown (₹)", 330)

a, b = st.columns(2)
with a:
    f = go.Figure(go.Scatter(x=eq["Exit DateTime"], y=-eq["Drawdown %"], mode="lines", line=dict(color=hub.NEG, width=1.6),
                             fill="tozeroy", fillcolor="rgba(251,91,91,.14)"))
    f.update_yaxes(ticksuffix="%")
    chart(f, "Underwater Drawdown Curve (%)", 300)
with b:
    f = go.Figure(go.Pie(labels=["Winning", "Losing", "Breakeven"], hole=.6, sort=False,
                         values=[mm["Winning Trades"], mm["Losing Trades"], mm["Breakeven Trades"]],
                         marker_colors=[hub.POS, hub.NEG, hub.MUTED2], textfont=dict(color=hub.TEXT)))
    chart(f, "Winning vs Losing Trades", 300)
st.html(hub.wrap('<p class="cap">Equity starts at Initial Capital and adds each trade\'s Net P&L in exit-time order. '
                 'The underwater curve is the standard drawdown %: current equity below its own running peak. '
                 '"% of Initial Capital" in the KPI card above uses a fixed denominator instead, for a quick capital-at-risk read.</p>'))

# ====================== monthly/yearly matrix ======================
st.html(hub.wrap(hub.h2("Monthly & Yearly Returns Performance Matrix") + hub.heatmap(mat, yearly)
                 + '<p class="cap">₹ net P&L by exit month. Return % is each year\'s net P&L ÷ Initial Capital (not annualised, not compounded).</p>'))

# ====================== master trade log ======================
st.html(hub.wrap(hub.h2("Combined Master Trade Log")))
disp = m.copy()
disp["Strike/Type"] = disp["Strike"].map(gfmt) + disp.get("Type", "").fillna("").radd(" ")
disp["Strike/Type"] = disp["Strike/Type"].str.strip().replace("", "—")
disp["Index"] = disp["Index"].map(gfmt)
for c in ("Entry Price", "Exit Price", "B/S", "Expiry", "Remarks"):
    if c not in disp:
        disp[c] = None
cols = ["Index", "Source", "Entry DateTime", "Strike/Type", "Expiry", "B/S", "Entry Price", "Exit Price",
       "Exit DateTime", "Gross P/L", "Charges", "Net P/L", "Return %", "Remarks"]
disp = disp[cols].rename(columns={"B/S": "Position", "Net P/L": "Net P/L (₹)"})

q = st.text_input("Search the trade log (any column)")
sources = ["All"] + sorted(m["Source"].unique().tolist())
tabs = st.tabs(["All", "Winning", "Losing"] + ([f"By file" ] if len(sources) > 2 else []))
views = [disp, disp[m["Net P/L"] > 0], disp[m["Net P/L"] < 0]]
for tab, name, s in zip(tabs, ["All", "Winning", "Losing"], views):
    with tab:
        if q:
            s = s[s.astype(str).apply(lambda c: c.str.contains(q, case=False, regex=False)).any(axis=1)]
        st.caption(f"{len(s):,} trades" + (f" (showing first 200)" if len(s) > 200 else ""))
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

# ====================== full Excel report ======================
info = [
    ("Files merged", ", ".join(f.name for f in up)),
    ("Initial capital", R.inr(capital)),
    ("Total charges", R.inr(charges) + " (spread evenly across every trade)"),
    ("Trade definition", "AlgoTest: one parent trade row (P/L = file P/L). StockMock: one expiry cycle per enabled strategy."),
    ("Net P/L", "Gross P/L (file) minus this trade's share of Total Charges"),
    ("Return %", "Net P/L ÷ Initial Capital × 100, per trade and per year"),
    ("Generated", pd.Timestamp.now().strftime("%d %b %Y %H:%M")),
]
tables = core.report_tables({"Combined": m}, capital, None, (1, 3, 6, 12), m)
xlsx = core.report_workbook(info, tables, title="Strategy Hub Report")
x2.download_button("Download full report (Excel)", xlsx, "Strategy Hub Report.xlsx", type="primary")
