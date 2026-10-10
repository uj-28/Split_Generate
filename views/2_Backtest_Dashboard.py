import io
import pathlib
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import core  # noqa: E402
import report as R  # noqa: E402

st.set_page_config(page_title="Stages 2-3 · Backtest Report", layout="wide", page_icon=":material/monitoring:")
EXAMPLES = {"Long": ROOT.parent / "Algo Test Long.csv", "Short": ROOT.parent / "Algo test  Short.csv"}
COLORS = {"Long": R.LONG, "Short": R.SHORT, "Combined": R.COMB}


@st.cache_data(show_spinner=False)
def load(file_bytes, name, direction):
    return core.load_algotest(core.read_table(io.BytesIO(file_bytes), name), direction)


# ====================== sidebar: Stage 2 import + Stage 3 controls ======================
sb = st.sidebar
sb.markdown("### ② Import AlgoTest results")
sb.caption("Upload the backtest file AlgoTest produced for each signal file (.csv / .xlsx). "
           "Slippage-adjusted exports are fine - the file's own P/L is used as-is.")
files = {d: sb.file_uploader(f"{d} backtest", type=["csv", "xlsx"], key=d) for d in ("Long", "Short")}
# example files exist only on a local copy (they are never committed), so the option is hidden elsewhere
use_ex = all(p.exists() for p in EXAMPLES.values()) and sb.checkbox("Use the bundled example files",
                                                                    value=st.query_params.get("demo") == "1")

# files chosen afresh in this run, or (if nothing new was dropped) the last successful parse
# from this session - so navigating to another page and back doesn't lose an upload.
bt_cache = st.session_state.get("bt_cache", {})
any_upload = any(files.values())
frames, rejected, notes, fnames = {}, [], [], {}
if any_upload or use_ex:
    for d in ("Long", "Short"):
        raw = None
        if files[d]:
            raw = (files[d].getvalue(), files[d].name)
        elif use_ex:
            raw = (EXAMPLES[d].read_bytes(), EXAMPLES[d].name)
        if not raw:
            continue
        try:
            t, rej, warns = load(*raw, d)
        except ValueError as e:
            sb.error(f"{d}: {e}")
            continue
        frames[d] = t
        fnames[d] = raw[1]
        rejected.append(rej.assign(File=d))
        sb.success(f"{d}: {len(t)} trades" + (f" · {len(rej)} rejected" if len(rej) else ""))
        notes += [f"{d}: {w}" for w in warns]
    if frames:
        st.session_state["bt_cache"] = {"frames": frames, "fnames": fnames, "rejected": rejected, "notes": notes}
elif bt_cache:
    frames, fnames, rejected, notes = bt_cache["frames"], bt_cache["fnames"], bt_cache["rejected"], bt_cache["notes"]
    sb.info("Showing the last results from this session - upload new files above to replace them.")
    for d in frames:
        sb.success(f"{d}: {len(frames[d])} trades (cached)")
    if sb.button("Clear cached results"):
        del st.session_state["bt_cache"]
        st.rerun()

HERO = lambda a: st.html(R.wrap(R.hero("STAGES 2-3 OF 3", "Long + Short Backtest Report",
                                       "Built from the AlgoTest trade records you upload. Nothing is estimated: anything that "
                                       "cannot be computed shows n/a.", active=a)))
if not frames:
    HERO(2)
    st.html(R.wrap('<div class="empty"><b>Load your AlgoTest backtest files to build the report</b>'
                   '<div class="steps">① Split your TradingView file on <i>1 Signal Splitter</i><br>'
                   '② Backtest both files on AlgoTest<br>'
                   '③ Upload the Long and Short results in the sidebar &larr;<br>'
                   '④ Read, filter and export the report</div></div>'))
    st.stop()

trades = core.combine(frames.get("Long"), frames.get("Short"))
d0, d1 = trades["Entry DateTime"].dt.date.min(), trades["Entry DateTime"].dt.date.max()

sb.markdown("### ③ Filters")
rng = sb.date_input("Entry date range", (d0, d1), min_value=d0, max_value=d1)
yr = sb.multiselect("Year", sorted(trades["Entry DateTime"].dt.year.unique()))
mo = sb.multiselect("Month", list(range(1, 13)), format_func=lambda m: pd.Timestamp(2000, m, 1).strftime("%B"))
sb.markdown("### Report settings")
cap = sb.number_input("Capital / margin ₹ (optional)", min_value=0.0, step=100000.0, format="%.0f",
                      help="Used only for ROI and '% of capital' figures (simple returns: P&L ÷ capital). The same capital is "
                           "applied to Long, Short and Combined. ₹ P&L never changes with it. Leave 0 = ROI shows n/a.") or None
mid = d0 + (d1 - d0) / 2
split = pd.Timestamp(sb.date_input("Regime split date", mid, min_value=d0, max_value=d1))
roll_m = sb.multiselect("Rolling windows (months)", [1, 2, 3, 6, 12, 24], default=[1, 3, 6, 12])

v = trades
if len(rng) == 2:
    dd_ = v["Entry DateTime"].dt.date
    v = v[(dd_ >= rng[0]) & (dd_ <= rng[1])]
if yr:
    v = v[v["Entry DateTime"].dt.year.isin(yr)]
if mo:
    v = v[v["Entry DateTime"].dt.month.isin(mo)]
if v.empty:
    st.warning("No trades match the current filters.")
    st.stop()

SER = {"Combined": v}
for d in ("Long", "Short"):
    if d in frames and (v.Direction == d).any():
        SER[d] = v[v.Direction == d]
M = {k: core.metrics(s) for k, s in SER.items()}
CM = {k: core.capital_metrics(m, cap) for k, m in M.items()}
names = list(SER)
mc = M["Combined"]

# ====================== metric specs (single source for every table) ======================
tone = lambda k: (lambda m: R.sgn(m[k]))
SPECS = [
    ("Net P&L", lambda m: R.inr(m["Net P&L"]) + R.pct_of(m["Net P&L"], cap), tone("Net P&L")),
    ("Trades", lambda m: str(m["Total Trades"]), ""),
    ("Win rate", lambda m: R.num(m["Win Rate %"], 2, "%"), ""),
    ("Wins / losses / breakeven", lambda m: f'{m["Winning Trades"]} / {m["Losing Trades"]} / {m["Breakeven Trades"]}', ""),
    ("Profit factor", lambda m: R.num(m["Profit Factor"]), "hl"),
    ("Avg P&L / trade", lambda m: R.inr(m["Avg P&L / Trade"]) + R.pct_of(m["Avg P&L / Trade"], cap), tone("Avg P&L / Trade")),
    ("Avg monthly P&L", lambda m: R.inr(m["Avg Monthly P&L"]) + R.pct_of(m["Avg Monthly P&L"], cap), tone("Avg Monthly P&L")),
    ("Annualised P&L", lambda m: R.inr(m["Annualised P&L"]) + R.pct_of(m["Annualised P&L"], cap), tone("Annualised P&L")),
    ("Avg winning trade", lambda m: R.inr(m["Avg Win"]), "good"),
    ("Avg losing trade", lambda m: R.inr(m["Avg Loss"]), "bad"),
    ("Largest win", lambda m: R.inr(m["Largest Win"]), "good"),
    ("Largest loss", lambda m: R.inr(m["Largest Loss"]), "bad"),
    ("Gross profit", lambda m: R.inr(m["Gross Profit"]), "good"),
    ("Gross loss", lambda m: R.inr(m["Gross Loss"]), "bad"),
    ("Maximum drawdown", lambda m: R.inr(m["Max Drawdown"]) + R.pct_of(m["Max Drawdown"], cap), "bad"),
    ("Drawdown window", lambda m: f'{R.dt(m["DD From"])} – {R.dt(m["DD To"])}' if m["DD From"] is not None else "n/a", ""),
    ("Return / MDD (annualised)", lambda m: R.num(m["Return / MDD"]), "hl"),
    ("Avg trade duration", lambda m: R.dur(m["Avg Duration (min)"]), ""),
    ("Longest win / loss streak", lambda m: f'{m["Max Win Streak"]} / {m["Max Loss Streak"]}', ""),
]
if cap:
    roi = lambda k: (lambda m: R.num(core.capital_metrics(m, cap)[k], 2, "%"))
    SPECS[1:1] = [("ROI on capital", roi("ROI %"), "hl"), ("Annualised ROI (simple)", roi("Annualised ROI %"), "hl"),
                  ("Avg monthly ROI", roi("Avg Monthly ROI %"), "hl"), ("Max drawdown % of capital", roi("Max DD % of Capital"), "bad")]


def spec_rows(ms):
    rows = []
    for label, f, t in SPECS:
        rows.append([label] + [(f(m), t(m) if callable(t) else t) for m in ms])
    return rows


def chart(fig, title, h=320):
    fig.update_layout(title=dict(text=title, x=0, font=dict(size=14, color="#14324f")), height=h, template="plotly_white",
                      margin=dict(l=10, r=10, t=48, b=10), font=dict(family="Arial", size=12),
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right"), plot_bgcolor="#fff", paper_bgcolor="#fff")
    st.plotly_chart(fig, width="stretch")


# ====================== report ======================
HERO(3)
st.html(R.wrap(
    '<div class="meta">'
    f'<div><b>Horizon:</b> {R.dt(v["Entry DateTime"].min())} – {R.dt(v["Exit DateTime"].max())}</div>'
    f'<div><b>Trades analysed:</b> {len(v):,} of {len(trades):,} loaded</div>'
    f'<div><b>Files:</b> ' + " · ".join(f'{d}: {len(frames[d])} trades' for d in frames) + '</div>'
    + f'<div><b>Capital / margin:</b> {R.inr(cap) + " (applied to Long, Short and Combined)" if cap else "not entered - ROI shows n/a"}</div>'
    '<div><b>Basis:</b> one trade = one AlgoTest trade row; P&amp;L = file P/L; direction = file it came from</div></div>'
    + "".join(f'<div class="warn">{n}</div>' for n in notes)
    + ("" if len(v) == len(trades) else f'<div class="ok">Filters active - every figure below covers the {len(v):,} filtered trades.</div>')))

rej_all = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
if len(rej_all):
    with st.expander(f"{len(rej_all)} rejected rows (not in any figure) - view / download"):
        st.dataframe(rej_all, hide_index=True)
        st.download_button("Validation report (CSV)", core.to_csv(rej_all), "rejected trades.csv", "text/csv")
if len(frames) == 2:
    both = set(frames["Long"]["Entry DateTime"]) & set(frames["Short"]["Entry DateTime"])
    if both:
        st.warning(f"{len(both)} entry timestamp(s) appear in both files (kept - check they are not duplicates).")

st.html(R.wrap(R.h2("", "Report sections")))
SECTION_ITEMS = [
    ("kpi", "1 · KPI cards & summary"),
    ("cards", "2 · Strategy cards"),
    ("dash_table", "2 · Metrics table"),
    ("equity", "2 · Equity curve chart"),
    ("dd", "2 · Drawdown chart"),
    ("regime", "3 · Regime table"),
    ("dd_table", "4 · Metrics table"),
    ("dd_heatmap", "4 · Monthly heatmap"),
    ("dd_yearly", "4 · Yearly table"),
    ("dd_rolling", "4 · Rolling table"),
    ("dd_yearlychart", "4 · Yearly chart"),
    ("dd_rollingchart", "4 · Rolling chart"),
    ("dd_takeaway", "4 · Takeaway note"),
    ("risk", "5 · Risk & Capital table"),
    ("dist_pnl", "6 · P&L distribution chart"),
    ("dist_activity", "6 · Monthly activity chart"),
    ("dist_winloss", "6 · Win/loss chart"),
    ("ledger", "7 · Trade ledger tables"),
    ("conclusion", "8 · Conclusion"),
]
with st.expander("Customize report sections - hide any table or chart you don't need", expanded=False):
    sel = st.multiselect("Visible", [lab for _, lab in SECTION_ITEMS], default=[lab for _, lab in SECTION_ITEMS],
                         label_visibility="collapsed")
show = {key: lab in sel for key, lab in SECTION_ITEMS}

# 1 -------------------------------------------------------------------------------------
if show["kpi"]:
    dd_txt = f' ({R.dt(mc["DD From"])} – {R.dt(mc["DD To"])})' if mc["DD From"] is not None else ""
    summary = (f'Across <b>{mc["Total Trades"]:,}</b> trades ({R.dt(v["Entry DateTime"].min())} – {R.dt(v["Exit DateTime"].max())}) the strategy '
               f'returned <b>{R.inr(mc["Net P&L"])}</b> with a <b>{R.num(mc["Win Rate %"], 2, "%")}</b> win rate and a profit factor of '
               f'<b>{R.num(mc["Profit Factor"])}</b>. The maximum closed-trade drawdown was <b>{R.inr(mc["Max Drawdown"])}</b>{dd_txt}.')
    if len(names) == 3:
        summary += (f' Long contributed {R.inr(M["Long"]["Net P&L"])} over {M["Long"]["Total Trades"]} trades and Short '
                    f'{R.inr(M["Short"]["Net P&L"])} over {M["Short"]["Total Trades"]} trades.')
    st.html(R.wrap(R.h2(1, "Executive Summary") + R.kpis([
        ("Net P&L", R.inr(mc["Net P&L"]), f'{mc["Total Trades"]:,} trades' + (f' · ROI {CM["Combined"]["ROI %"]:.2f}%' if cap else ""),
         "pos" if mc["Net P&L"] > 0 else "neg" if mc["Net P&L"] < 0 else ""),
        ("Win rate", R.num(mc["Win Rate %"], 2, "%"), f'{mc["Winning Trades"]} wins · {mc["Losing Trades"]} losses · {mc["Breakeven Trades"]} BE', ""),
        ("Profit factor", R.num(mc["Profit Factor"]), "Gross profit ÷ |gross loss|", ""),
        ("Max drawdown", R.inr(mc["Max Drawdown"]), "Peak-to-trough, closed trades"
         + (f' · {CM["Combined"]["Max DD % of Capital"]:.2f}% of capital' if cap else ""), "neg")]) + f"<p>{summary}</p>"))

# 2 -------------------------------------------------------------------------------------
if show["cards"] or show["dash_table"] or show["equity"] or show["dd"]:
    st.html(R.wrap(R.h2(2, "Comparative Performance Dashboard")))
if show["cards"]:
    cards = [(n, COLORS[n], [("Net P&L", R.inr(M[n]["Net P&L"])), ("Win rate", R.num(M[n]["Win Rate %"], 1, "%")),
                             ("Profit factor", R.num(M[n]["Profit Factor"])), ("Avg / trade", R.inr(M[n]["Avg P&L / Trade"])),
                             ("Max drawdown", R.inr(M[n]["Max Drawdown"])), ("Worst trade", R.inr(M[n]["Largest Loss"]))])
             for n in names]
    st.html(R.wrap(R.cards(cards)))
if show["dash_table"]:
    st.html(R.wrap(R.table(["Metric"] + names, spec_rows([M[n] for n in names]))
                   + '<p class="cap">Every figure is computed from that column\'s own trade records - Combined is never an average of Long and Short. '
                     'Win rate = wins ÷ all trades; profit factor = gross profit ÷ |gross loss| (n/a when there is no loss).</p>'))
if show["equity"] or show["dd"]:
    EQ = {n: core.equity(s) for n, s in SER.items()}
if show["equity"]:
    fig = go.Figure()
    for n in names:
        fig.add_scatter(x=EQ[n]["Exit DateTime"], y=EQ[n]["Cum P&L"], name=n, mode="lines",
                        line=dict(color=COLORS[n], width=3 if n == "Combined" else 1.7))
    chart(fig, "Cumulative realised P&L (₹) - restarts at 0 on the first filtered trade", 360)
if show["dd"]:
    fig = go.Figure()
    for n in names:
        fig.add_scatter(x=EQ[n]["Exit DateTime"], y=-EQ[n]["Drawdown"], name=n, mode="lines", fill="tozeroy" if n == "Combined" else None,
                        line=dict(color=COLORS[n] if n != "Combined" else R.NEG, width=1.4))
    chart(fig, "Underwater curve - drawdown below running peak (₹)", 260)
    st.caption("Drawdown = running peak of cumulative realised P&L (floored at 0) − current cumulative P&L, trades ordered by exit time. "
               "Closed-trade basis: no intraday mark-to-market.")

# 3 -------------------------------------------------------------------------------------
if show["regime"]:
    reg = []
    for n in names:
        post = SER[n][SER[n]["Exit DateTime"] >= split]
        for tag, s in (("full period", SER[n]), (f"from {R.dt(split)}", post)):
            if s.empty:
                continue
            m = core.metrics(s)
            reg.append([f'{n}<span class="tag">{tag}</span>', (R.inr(m["Net P&L"]), R.sgn(m["Net P&L"])), str(m["Total Trades"]),
                        R.num(m["Win Rate %"], 2, "%"), R.num(m["Profit Factor"]), R.inr(m["Avg P&L / Trade"]),
                        (R.inr(m["Max Drawdown"]), "bad"), (R.num(m["Return / MDD"]), "hl")]
                       + ([(R.num(core.capital_metrics(m, cap)["ROI %"], 2, "%"), "hl")] if cap else []))
    st.html(R.wrap(R.h2(3, f"Regime Analysis - split at {R.dt(split)}")
                   + "<p>The horizon is split at the date chosen in the sidebar to check whether the edge persists in the later period. "
                     "A strategy that keeps its numbers after the split is more credible than one whose edge sits entirely before it.</p>"
                   + R.table(["Series / period", "Net P&L", "Trades", "Win rate", "Profit factor", "Avg / trade", "Max DD", "Return / MDD"]
                             + (["ROI"] if cap else []), reg)))

# 4 -------------------------------------------------------------------------------------
dd_any = any(show[k] for k in ("dd_table", "dd_heatmap", "dd_yearly", "dd_rolling", "dd_yearlychart", "dd_rollingchart", "dd_takeaway"))
if dd_any:
    st.html(R.wrap(R.h2(4, "Strategy Deep-Dive")))
    for tab, n in zip(st.tabs(names), names):
        with tab:
            s, m = SER[n], M[n]
            mat, yearly = core.monthly_matrix(s)
            roll = core.rolling_returns(s, tuple(roll_m)).astype({"Months": int, "Windows": int})
            if show["dd_table"]:
                st.html(R.wrap(f"<h3>4.{names.index(n) + 1}.1 Performance metrics</h3>" + R.table(["Metric", n], spec_rows([m]))))
            if show["dd_heatmap"]:
                st.html(R.wrap("<h3>Monthly net P&amp;L (by exit month)</h3>" + R.heatmap(mat, yearly, m["Max Drawdown"], cap)))
            if show["dd_yearly"]:
                yrows = [[str(int(r["Year"])), (R.inr(r["Net P&L"]), R.sgn(r["Net P&L"])), str(int(r["Trades"])),
                          R.num(r["Win Rate %"], 2, "%"), R.num(r["Profit Factor"]), R.inr(r["Avg P&L / Trade"]),
                          (R.inr(r["Max Drawdown"]) + R.pct_of(r["Max Drawdown"], cap), "bad"),
                          (R.num(r["Net P&L"] / cap * 100, 2, "%") if cap else "n/a", "hl")] for _, r in yearly.iterrows()]
                st.html(R.wrap("<h3>Yearly breakdown</h3>"
                               + R.table(["Year", "Net P&L", "Trades", "Win rate", "Profit factor", "Avg / trade", "Max DD", "ROI"], yrows)))
            rrows = [[("1 Month" if int(r.Months) == 1 else f"{int(r.Months)} Months" if r.Months < 12 else f"{int(r.Months) // 12} Year" + ("s" if r.Months > 12 else "")),
                      str(int(r.Windows)), (R.inr(r.Worst) + R.pct_of(r.Worst, cap), R.sgn(r.Worst)),
                      (R.inr(r.Median) + R.pct_of(r.Median, cap), R.sgn(r.Median)),
                      (R.inr(r.Average) + R.pct_of(r.Average, cap), R.sgn(r.Average)), (R.inr(r.Best) + R.pct_of(r.Best, cap), "good"),
                      (R.num(r["Positive %"], 1, "%"), "good" if r["Positive %"] == 100 else "hl" if r["Positive %"] >= 90 else "")]
                     for _, r in roll.iterrows()]
            if show["dd_rolling"]:
                st.html(R.wrap("<h3>Rolling return validation</h3><p>Each window is a real calendar period anchored on every trade, "
                               "counted only where the full period fits inside the data.</p>"
                               + (R.table(["Holding period", "Windows", "Worst", "Median", "Average", "Best", "Positive"], rrows)
                                  if rrows else "<p>The sample is shorter than every selected window.</p>")))
            if show["dd_yearlychart"] or show["dd_rollingchart"]:
                a, b = st.columns(2)
                if show["dd_yearlychart"]:
                    with a:
                        f = go.Figure(go.Bar(x=yearly["Year"].astype(str), y=yearly["Net P&L"],
                                             marker_color=[R.POS if x > 0 else R.NEG for x in yearly["Net P&L"]]))
                        chart(f, "Net P&L by calendar year (₹)", 300)
                if show["dd_rollingchart"] and len(roll):
                    with b:
                        lbl = roll.Months.astype(str) + "m"
                        f = go.Figure()
                        for col, c in (("Worst", R.NEG), ("Average", R.NAVY), ("Best", R.POS)):
                            f.add_bar(x=lbl, y=roll[col], name=col, marker_color=c)
                        chart(f, "Rolling windows - worst / average / best (₹)", 300)
            if show["dd_takeaway"] and len(roll):
                clean = roll[(roll["Positive %"] == 100) & (roll.Windows >= 5)]
                if len(clean):
                    c = clean.iloc[0]
                    take = (f'Every {int(c.Months)}-month window in this sample closed positive ({int(c.Windows)} overlapping windows). '
                            f'The worst {int(roll.iloc[0].Months)}-month window lost {R.inr(-roll.iloc[0].Worst) if roll.iloc[0].Worst < 0 else "nothing"}.')
                else:
                    b = roll.loc[roll["Positive %"].idxmax()]
                    take = (f'No holding period tested was uniformly positive; the best is {int(b.Months)}-month at {b["Positive %"]:.1f}% '
                            f'of windows in profit, worst case {R.inr(b.Worst)}.')
                st.html(R.wrap(f'<div class="callout"><b>Holding-period takeaway:</b> {take}</div>'))

# 5 -------------------------------------------------------------------------------------
if show["risk"]:
    risk = [[n, (R.inr(M[n]["Max Drawdown"]) + R.pct_of(M[n]["Max Drawdown"], cap), "bad"), (R.inr(M[n]["Largest Loss"]), "bad"),
             str(M[n]["Max Loss Streak"]), (R.inr(M[n]["Annualised P&L"]), R.sgn(M[n]["Annualised P&L"])), (R.num(M[n]["Return / MDD"]), "hl")]
            + ([(R.num(CM[n]["Annualised ROI %"], 2, "%"), "hl")] if cap else [])
            for n in names]
    st.html(R.wrap(R.h2(5, "Risk & Capital Efficiency")
                   + R.table(["Series", "Max drawdown", "Worst trade", "Longest losing run", "Annualised P&L", "Return / MDD"]
                             + (["Annualised ROI"] if cap else []), risk)
                   + ('' if cap else '<p class="cap">Enter capital / margin in the sidebar to add % of capital and ROI figures. '
                                     'No capital is assumed.</p>')))

# 6 -------------------------------------------------------------------------------------
dist_any = show["dist_pnl"] or show["dist_activity"] or show["dist_winloss"]
if dist_any:
    st.html(R.wrap(R.h2(6, "Trade Distribution & Activity")))
    a, b, c = st.columns([2, 2, 1.4])
    if show["dist_pnl"]:
        with a:
            f = go.Figure()
            for n in names[1:] or names:
                f.add_histogram(x=SER[n]["P/L"], name=n, marker_color=COLORS[n], opacity=.8, nbinsx=40)
            f.update_layout(barmode="overlay")
            chart(f, "Trade P&L distribution (₹)", 320)
    if show["dist_activity"]:
        with b:
            act = v.groupby([v["Entry DateTime"].dt.to_period("M").astype(str), "Direction"]).size().unstack(fill_value=0)
            f = go.Figure()
            for d in act.columns:
                f.add_bar(x=act.index, y=act[d], name=d, marker_color=COLORS[d])
            f.update_layout(barmode="stack")
            chart(f, "Monthly trade activity (by entry)", 320)
    if show["dist_winloss"]:
        with c:
            f = go.Figure(go.Pie(labels=["Winning", "Losing", "Breakeven"], hole=.55, sort=False,
                                 values=[mc["Winning Trades"], mc["Losing Trades"], mc["Breakeven Trades"]],
                                 marker_colors=[R.POS, R.NEG, "#9AA5B1"]))
            chart(f, "Win vs loss", 320)

# 7 -------------------------------------------------------------------------------------
lead = ["Trade #", "Direction", "Entry DateTime", "Exit DateTime", "Duration (min)", "P/L"]
cols = lead + [c for c in v.columns if c not in lead + ["Entry Date", "Entry Time", "Exit Date", "Exit Time"]]
if show["ledger"]:
    st.html(R.wrap(R.h2(7, "Trade Ledger & Exports")))
    q = st.text_input("Search (any column)")
    tabs = ["All", "Long", "Short", "Winning", "Losing"]
    subsets = [v, v[v.Direction == "Long"], v[v.Direction == "Short"], v[v["P/L"] > 0], v[v["P/L"] < 0]]
    for tab, name, s in zip(st.tabs(tabs), tabs, subsets):
        with tab:
            s = s[cols].copy()
            if "Index" in s:
                s["Index"] = s["Index"].map(lambda x: f"{x:g}" if isinstance(x, float) else str(x))
            if q:
                s = s[s.astype(str).apply(lambda c: c.str.contains(q, case=False, regex=False)).any(axis=1)]
            st.caption(f"{len(s):,} trades")
            st.dataframe(s.style.map(lambda x: f"color: {R.POS if x > 0 else R.NEG if x < 0 else 'inherit'}; font-weight:600", subset=["P/L"])
                         .format({"P/L": "{:,.2f}", "Duration (min)": "{:.0f}"}), hide_index=True, height=380,
                         column_config={"Entry DateTime": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm"),
                                        "Exit DateTime": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm")})
            x1, x2 = st.columns([1, 6])
            x1.download_button("Excel", core.to_xlsx(s), f"{name} trades.xlsx", key=f"x{name}")
            x2.download_button("CSV", core.to_csv(s), f"{name} trades.csv", "text/csv", key=f"c{name}")

# full report export - always available, even if the on-screen ledger above is hidden
ledger = v[cols].copy()
if "Index" in ledger:
    ledger["Index"] = ledger["Index"].map(lambda x: f"{x:g}" if isinstance(x, float) else str(x))
info = [
    ("Horizon", f'{R.dt(v["Entry DateTime"].min())} – {R.dt(v["Exit DateTime"].max())}'),
    ("Trades analysed", f"{len(v):,} of {len(trades):,} loaded"),
    ("Files", " · ".join(f"{d}: {fnames[d]} ({len(frames[d])} trades)" for d in frames)),
    ("Entry date filter", f"{rng[0]:%d %b %Y} – {rng[1]:%d %b %Y}" if len(rng) == 2 else "none"),
    ("Year filter", ", ".join(map(str, yr)) or "all years"),
    ("Month filter", ", ".join(pd.Timestamp(2000, m_, 1).strftime("%B") for m_ in mo) or "all months"),
    ("Capital / margin", f"₹{cap:,.0f} - applied to Long, Short and Combined" if cap else "Not entered - ROI figures not calculated"),
    ("Regime split date", f"{split:%d %b %Y}"),
    ("Rolling windows (months)", ", ".join(map(str, roll_m)) or "none"),
    ("Trade definition", "One AlgoTest trade row; P&L = the file's P/L (including any slippage the backtest applied)"),
    ("Direction", "The file the trade was uploaded in (Long or Short)"),
    ("Win rate", "Winning trades ÷ all trades"),
    ("Profit factor", "Gross profit ÷ |gross loss|; n/a when there is no loss"),
    ("Max drawdown", "Largest drop of cumulative realised P&L below its running peak (closed trades, ordered by exit time)"),
    ("ROI", "Simple return: P&L ÷ capital × 100 (annualised ROI = annualised P&L ÷ capital)"),
    ("Generated", pd.Timestamp.now().strftime("%d %b %Y %H:%M")),
]
report_xlsx = core.report_workbook(info, core.report_tables(SER, cap, split, tuple(roll_m), ledger, rej_all if len(rej_all) else None))
st.download_button("Download full report (Excel)", report_xlsx, "Backtest Report.xlsx", type="primary", key="xfull",
                   help="Every section of this report as formatted Excel tables, with your filters and capital applied.")
sb.download_button("Download full report (Excel)", report_xlsx, "Backtest Report.xlsx", type="primary", key="xfull_sb")

# 8 -------------------------------------------------------------------------------------
if show["conclusion"]:
    st.html(R.wrap(R.h2(8, "Conclusion")
                   + f"<p>The combined book produced {R.inr(mc['Net P&L'])} over {mc['Total Trades']:,} trades at a "
                     f"{R.num(mc['Win Rate %'], 2, '%')} win rate and {R.num(mc['Profit Factor'])} profit factor, with a worst closed-trade "
                     f"drawdown of {R.inr(mc['Max Drawdown'])}. "
                   + (f"Long and Short contributed {R.inr(M['Long']['Net P&L'])} and {R.inr(M['Short']['Net P&L'])} respectively. " if len(names) == 3 else "")
                   + "</p><p class=\"cap\">Backtested results are hypothetical and do not guarantee future performance. Figures use the P/L in the "
                     "AlgoTest files (including whatever slippage the backtest applied) and exclude any costs not in those files. "
                     "Save as PDF with your browser's Print (Ctrl+P, background graphics on).</p>"))
