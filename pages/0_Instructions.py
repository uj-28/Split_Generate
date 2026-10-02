import pathlib
import sys

import streamlit as st

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import report as R  # noqa: E402

st.set_page_config(page_title="Instructions", layout="wide", page_icon=":material/menu_book:")

def steps(items):
    return "<ol style='font-size:13px;line-height:1.8;margin:6px 0 10px 18px'>" + "".join(f"<li>{i}</li>" for i in items) + "</ol>"


def ul(items):
    return "<ul style='font-size:13px;line-height:1.8;margin:6px 0 10px 18px'>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


st.html(R.wrap(
    R.hero("USER GUIDE", "How to use this app",
           "Turn a TradingView strategy export into AlgoTest-ready Long and Short files, then turn the two AlgoTest results "
           "into one professional Long + Short + Combined performance report.")

    + R.h2("A", "What this app gives you")
    + R.table(["Page", "You upload", "You get"], [
        ["1 · Signal Splitter", "TradingView strategy export (.csv / .xlsx)",
         "<b>Long Signals</b> and <b>Short Signals</b> files (.xlsx or .csv) ready for AlgoTest, signal counts, a preview, "
         "and a list of any rows it could not classify"],
        ["2 · Backtest Report", "The two result files AlgoTest gave you (Long and Short)",
         "KPI cards, Long / Short / Combined comparison, cumulative P&amp;L and drawdown charts, regime split, monthly heatmap, "
         "yearly and rolling-return tables, risk summary, filterable trade ledger, Excel / CSV exports"]])

    + R.h2("B", "The workflow in 6 steps")
    + steps([
        "<b>TradingView:</b> run your strategy and export the trade list. Keep it as it is (Long and Short rows together).",
        "<b>Page 1 · Signal Splitter:</b> upload that file. Check the counts: Long + Short + unclassified must equal the source total "
        "(a green tick confirms it).",
        "Download <b>Long Signals</b> and <b>Short Signals</b>.",
        "<b>AlgoTest:</b> backtest the Long file and the Short file separately, then download each result.",
        "<b>Page 2 · Backtest Report:</b> upload the Long result in the <i>Long backtest</i> box and the Short result in the "
        "<i>Short backtest</i> box (sidebar).",
        "Read the report, use the filters, and export what you need. For a PDF, press <b>Ctrl+P</b> in your browser and tick "
        "&ldquo;Background graphics&rdquo;."])

    + R.h2("C", "Page 1 · Signal Splitter - details")
    + ul([
        "<b>Required columns:</b> Trade number, Type, Date and time, Price. A missing column stops the process with a clear message.",
        "<b>How direction is found:</b> from the <code>Type</code> text: <i>Entry long</i> / <i>Exit long</i> go to Long; "
        "<i>Entry short</i> / <i>Exit short</i> go to Short. An exit therefore always stays with its own entry's direction.",
        "<b>Nothing is lost or edited:</b> every row appears in exactly one place (Long, Short or Unclassified). Original row order "
        "and all values are kept. Only <i>Date and time</i> is reformatted, and you choose the format "
        "(DD-MM-YYYY HH:MM like your manual files, or the original YYYY-MM-DD HH:MM).",
        "<b>Unclassified rows</b> (a Type that is not Entry/Exit long/short) are listed with a reason and a downloadable report; "
        "they are not placed in either file.",
        "<b>Warnings</b> appear if a trade number is not exactly one entry plus one exit, or a date cannot be read.",
        "If there are no Long (or no Short) signals you get a message instead of an empty download."])
    + R.h2("D", "Page 2 · Backtest Report - details")
    + "<h3>Accepted files</h3>"
    + ul([
        "AlgoTest exports (.csv / .xlsx) with columns Index, Entry Date, Entry Time, Exit Date, Exit Time, P/L "
        "(Type, Strike, B/S, Qty, prices and Vix are optional). Column order does not matter and header case is ignored.",
        "Also accepted: merged trade reports with <i>Trade #</i> instead of <i>Index</i> and no leg rows (one row = one trade).",
        "<b>Slippage:</b> files exported with slippage are fine - the report uses the P/L inside the file exactly as given.",
        "You can upload only Long or only Short; the report adapts."])
    + "<h3>How trades are read</h3>"
    + ul([
        "One trade = one AlgoTest trade row (the row holding P/L and Vix). Leg rows are used for display and cross-checked, "
        "never added again, so P&amp;L is not double-counted.",
        "Direction = the box you uploaded the file into (Long or Short).",
        "Rows with invalid dates / P&amp;L, exit before entry, or exact duplicates are <b>rejected and listed</b> (with a download), "
        "never silently dropped."])
    + "<h3>Sidebar controls</h3>"
    + ul([
        "<b>Filters:</b> entry date range, year, month - the whole report (cards, tables, charts) updates together.",
        "<b>Capital / margin (optional):</b> enables ROI % figures. If left at 0, ROI shows n/a - no capital is assumed.",
        "<b>Regime split date:</b> compares the full period with the period from that date onward.",
        "<b>Rolling windows:</b> choose the holding periods (months) to test.",
        "<b>Full report data (Excel):</b> summary, yearly, monthly, rolling and trades in one workbook."])
    + "<h3>Report sections</h3>"
    + R.table(["#", "Section", "What it shows"], [
        ["1", "Executive Summary", "Net P&amp;L, win rate, profit factor, max drawdown + a plain-language summary"],
        ["2", "Comparative Dashboard", "Long / Short / Combined cards and a full metrics table; cumulative P&amp;L and drawdown charts"],
        ["3", "Regime Analysis", "Full period vs. period after the split date"],
        ["4", "Strategy Deep-Dive", "Per series: all metrics, monthly heatmap, yearly table, rolling returns, charts"],
        ["5", "Risk &amp; Capital Efficiency", "Drawdown, worst trade, losing streak, return / max drawdown"],
        ["6", "Distribution &amp; Activity", "P&amp;L histogram, trades per month, win / loss split"],
        ["7", "Trade Ledger &amp; Exports", "All / Long / Short / Winning / Losing tables with search and Excel / CSV export"],
        ["8", "Conclusion", "Factual summary and disclaimer"]])

    + R.h2("E", "How every number is calculated")
    + R.table(["Metric", "Definition"], [
        ["Trade P&amp;L", "The <code>P/L</code> of the AlgoTest trade row (rupees, as exported)"],
        ["Net P&amp;L", "Sum of trade P&amp;L"],
        ["Win / loss / breakeven", "P&amp;L &gt; 0 / &lt; 0 / = 0"],
        ["Win rate", "Winning trades ÷ <b>all</b> trades (breakeven trades count in the denominator)"],
        ["Gross profit / loss", "Sum of winning trades / sum of losing trades"],
        ["Profit factor", "Gross profit ÷ |gross loss|; <i>n/a</i> when there is no losing trade"],
        ["Avg P&amp;L per trade", "Net P&amp;L ÷ number of trades"],
        ["Equity curve", "Cumulative P&amp;L of trades ordered by <b>exit time</b>, starting from 0 at the first filtered trade"],
        ["Max drawdown", "Largest drop of the equity curve below its running peak (peak floored at 0). Closed-trade basis - no intraday mark-to-market"],
        ["Annualised P&amp;L", "Net P&amp;L ÷ elapsed years (minimum 0.25 year)"],
        ["Avg monthly P&amp;L", "Annualised P&amp;L ÷ 12"],
        ["Return / MDD", "Annualised P&amp;L ÷ max drawdown"],
        ["Monthly / yearly P&amp;L", "Trades grouped by exit date"],
        ["Rolling windows", "For each trade, the P&amp;L of trades exited in the next N calendar months; only windows that fit entirely in the data"],
        ["Combined metrics", "Always recomputed from the combined trade records - never by averaging Long and Short"],
        ["% returns", "Only when you enter capital; otherwise n/a"]])

    + R.h2("F", "Troubleshooting")
    + R.table(["Problem", "What to check"], [
        ["&ldquo;Missing required column(s)&rdquo;", "The file is not the expected type. Splitter needs the TradingView columns; the report needs AlgoTest columns (see C and D)"],
        ["File not accepted", "Use .csv or .xlsx only. Re-export if the file is corrupt or empty"],
        ["Counts do not reconcile on page 1", "Do not use the files; send the source file for review"],
        ["Fewer trades than expected", "Open &ldquo;rejected rows&rdquo; at the top of the report - each has a reason"],
        ["Report shows n/a", "That metric cannot be computed from the data (e.g. profit factor with no losses, ROI without capital)"],
        ["No trades after filtering", "Widen the date range or clear the year / month filters"]])

    + R.h2("G", "Limits to be aware of")
    + ul([
        "Drawdown uses closed trades only; open-trade swings inside a trade are not visible in AlgoTest trade files.",
        "Results are only as good as the AlgoTest files; costs or slippage not in those files are not added.",
        "Long and Short are separated by the file they came from, not by reading option type.",
        "Backtested results are hypothetical and do not guarantee future performance."])
    + R.h2("H", "Run the app")
    + "<p>In a terminal: <code>cd algotest_trade_visualizer-main</code>, <code>pip install -r requirements.txt</code>, "
      "then <code>python -m streamlit run app.py</code>. Tests: <code>python -m pytest tests -q</code>.</p>", "guide"))
