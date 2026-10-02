# TradingView → AlgoTest → Combined Backtest Report

A Streamlit app that replaces the manual Excel work around an AlgoTest backtest:

1. **Split** a TradingView strategy export into `Long Signals` and `Short Signals` files for AlgoTest.
2. **Combine** the two AlgoTest result files into one professional Long + Short + Combined report.

The app opens on an **Instructions** page with the full guide; this README is the short version.

---

## Run the app

Requires Python 3.10+ (developed on 3.14).

```bash
# 1. open a terminal in this folder
cd algotest_trade_visualizer-main

# 2. (optional) create a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. install dependencies
pip install -r requirements.txt

# 4. start the app
python -m streamlit run app.py
```

The browser opens at <http://localhost:8501>. Stop with `Ctrl+C`.

> If `streamlit run app.py` says "streamlit is not recognized", use `python -m streamlit run app.py` (as above) —
> Python's `Scripts` folder is simply not on your PATH.
> Different port: `python -m streamlit run app.py --server.port 8502`.

## Workflow

| Step | Where | What you do |
|---|---|---|
| 1 | TradingView | Export the strategy trade list (Long and Short rows together). |
| 2 | **1 · Signal Splitter** | Upload it, check the counts, download **Long Signals** and **Short Signals**. |
| 3 | AlgoTest | Backtest the Long file and the Short file separately; download both results. |
| 4 | **2 · Backtest Report** | Upload the Long and Short results (sidebar), filter, read, export. |

For a PDF of the report use the browser's Print (`Ctrl+P`, "Background graphics" on).

## Pages

- **Instructions** – complete guide: workflow, accepted files, every formula, troubleshooting.
- **1 · Signal Splitter** – splits on the `Type` column (`Entry/Exit long|short`), keeps row order and values, reconciles
  counts (Long + Short + unclassified = source), lists unclassified rows, exports `.xlsx` / `.csv`.
- **2 · Backtest Report** – KPI cards, Long / Short / Combined comparison, cumulative P&L and drawdown charts,
  regime split, monthly heatmap, yearly and rolling-return tables, risk summary, filterable trade ledger,
  Excel / CSV exports. Accepts slippage-adjusted AlgoTest files (the file's own `P/L` is used as-is) and merged
  reports that use `Trade #` instead of `Index`.

## Calculation rules (summary)

- One trade = one AlgoTest trade row; P&L = its `P/L`. Leg rows are only cross-checked, never added again.
- Direction = the file (Long / Short) the trade was uploaded in.
- Win rate = wins ÷ all trades. Profit factor = gross profit ÷ |gross loss| (n/a with no losses).
- Equity = cumulative P&L by exit time from 0. Max drawdown = largest drop below the running peak (closed trades only).
- Combined metrics are always recomputed from the combined trade records, never averaged.
- Percent returns need a capital you enter; otherwise they show n/a. Nothing is estimated.

## Project layout

```
app.py                      navigation (entry point)
core.py                     all logic: splitting, AlgoTest import, metrics
report.py                   HTML/CSS building blocks for the report look
pages/0_Instructions.py     user guide
pages/1_Signal_Splitter.py  stage 1
pages/2_Backtest_Dashboard.py  stages 2-3
tests/test_core.py          automated tests
.streamlit/config.toml      light theme, upload limit
legacy_clktrd_app.py        the original .clktrd viewer (not in the menu)
```

## Tests

```bash
python -m pytest tests -q
```

Tests use the example CSVs one folder above this one (`Long+Short Row file.csv`, `Long Example.csv`,
`Short Example.csv`, `Algo Test Long.csv`, `Algo test  Short.csv`) and independent recalculations.
They skip nothing silently: if those files are missing, the tests fail.

## Limits

- Drawdown is closed-trade based; AlgoTest trade files do not contain intraday equity.
- Results include only the costs/slippage already inside the AlgoTest files.
- Backtested results are hypothetical and do not guarantee future performance.

## Legacy viewer

The original `.clktrd` analyzer was kept as `legacy_clktrd_app.py`. Run it on its own with
`python -m streamlit run legacy_clktrd_app.py`.
