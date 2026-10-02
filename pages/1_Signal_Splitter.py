import pathlib
import sys

import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import core  # noqa: E402
import report as R  # noqa: E402

st.set_page_config(page_title="Stage 1 · Signal Splitter", layout="wide", page_icon="✂️")
st.html(R.wrap(R.hero("STAGE 1 OF 3", "TradingView Signal Splitter",
                      "Upload your TradingView strategy export. The app separates Long and Short signals, checks that no row is "
                      "lost, and gives you two files ready to upload to AlgoTest.", active=1)))

# ---------- input ----------
left, right = st.columns([3, 2], gap="large")
with left:
    with st.container(border=True):
        st.markdown("**1 · Upload TradingView report**")
        up = st.file_uploader("TradingView strategy report", type=["csv", "xlsx"], label_visibility="collapsed")
        fmt_label = st.radio("Date format in the output files", list(core.DATE_FMTS), horizontal=False,
                             help="Only 'Date and time' is re-formatted; every other value is copied unchanged.")
with right:
    st.html(R.wrap(
        '<div class="card"><h4>What you get</h4><div class="feat">'
        '<div><b>Long Signals</b>All Entry long / Exit long rows</div>'
        '<div><b>Short Signals</b>All Entry short / Exit short rows</div>'
        '<div><b>Reconciliation</b>Long + Short + unclassified = source rows</div>'
        '<div><b>Validation report</b>Any row it cannot classify is listed, never dropped</div></div></div>'))

if not up:
    st.html(R.wrap('<div class="banner next">⬆️ <span>Upload your TradingView export above to begin. '
                   'Accepted: <b>.csv</b> or <b>.xlsx</b> with columns <i>Trade number, Type, Date and time, Price</i>.</span></div>'))
    st.stop()

try:
    with st.spinner("Reading and classifying signals…"):
        src = core.read_table(up, up.name)
        res = core.split_signals(src, core.DATE_FMTS[fmt_label])
except ValueError as e:
    st.html(R.wrap(f'<div class="banner bad">⛔ <span><b>Cannot process this file.</b> {e}</span></div>'))
    st.stop()

# ---------- results ----------
st.html(R.wrap(R.h2("✓", "Result") + R.kpis([
    ("Source rows", f"{res.total:,}", up.name, ""),
    ("Long signals", f"{len(res.long):,}", "Entry + exit rows", ""),
    ("Short signals", f"{len(res.short):,}", "Entry + exit rows", ""),
    ("Unclassified", f"{len(res.unclassified):,}", "Needs your attention" if len(res.unclassified) else "None - all rows placed",
     "neg" if len(res.unclassified) else "pos")])
    + (f'<div class="banner ok">✅ <span><b>Counts reconcile:</b> {len(res.long):,} Long + {len(res.short):,} Short + '
       f'{len(res.unclassified):,} unclassified = {res.total:,} source rows. No row lost or duplicated.</span></div>'
       if res.reconciled else
       '<div class="banner bad">⛔ <span><b>Counts do not reconcile.</b> Do not use these files.</span></div>')
    + "".join(f'<div class="warn">⚠️ {w}</div>' for w in res.warnings)))

cols = st.columns(2, gap="large")
for col, name, df, color in zip(cols, ("Long", "Short"), (res.long, res.short), (R.LONG, R.SHORT)):
    with col, st.container(border=True):
        st.html(R.wrap(f'<div class="dl-head"><h4><i style="background:{color}"></i>{name} Signals</h4>'
                       f'<span>{len(df):,} rows · {len(df) // 2:,} trades</span></div>'))
        if df.empty:
            st.info(f"No {name} signals found - nothing to download.")
            continue
        st.dataframe(df, height=290, hide_index=True)
        b1, b2 = st.columns([3, 1.4])
        b1.download_button(f"⬇️  Download {name} Signals.xlsx", core.to_xlsx(df), f"{name} Signals.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key=f"x{name}", type="primary", width="stretch")
        b2.download_button("CSV", core.to_csv(df), f"{name} Signals.csv", "text/csv", key=f"c{name}", width="stretch")

if len(res.unclassified):
    with st.container(border=True):
        st.markdown(f"**⚠️ {len(res.unclassified)} unclassified rows** - not placed in either file")
        st.dataframe(res.unclassified, hide_index=True, height=220)
        st.download_button("⬇️ Validation report (CSV)", core.to_csv(res.unclassified),
                           f"{up.name.rsplit('.', 1)[0]} - unclassified.csv", "text/csv")

st.html(R.wrap('<div class="banner next">➡️ <span><b>Next:</b> backtest both files on AlgoTest, download the two results, '
               'then open <b>2 · Backtest Report</b> in the left menu.</span></div>'))
