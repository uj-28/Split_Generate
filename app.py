import streamlit as st

import report as R

st.html(R.CSS)  # injected once here (not per page) so switching pages never re-flashes unstyled content

st.navigation([
    st.Page("pages/0_Instructions.py", title="Instructions", icon=":material/menu_book:", default=True),
    st.Page("pages/1_Signal_Splitter.py", title="1 · Signal Splitter", icon=":material/content_cut:"),
    st.Page("pages/2_Backtest_Dashboard.py", title="2 · Backtest Report", icon=":material/monitoring:"),
]).run()
