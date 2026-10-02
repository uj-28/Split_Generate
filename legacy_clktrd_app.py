# app.py
import json
import pandas as pd
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="AlgoTest Trade Analyzer", layout="wide")

st.title("📊 AlgoTest Trade Analyzer")
st.caption("Analyze .clktrd files | P&L | Duration | Holding Periods")

# ==============================
# FILE UPLOAD
# ==============================
uploaded_file = st.file_uploader("Upload AlgoTest .clktrd file", type=["clktrd"])

capital = st.number_input(
    "Enter total capital deployed (₹)",
    min_value=0.0,
    value=1000000.0,
    step=10000.0,
)

if uploaded_file is not None:
    # ==============================
    # LOAD FILE
    # ==============================
    data = json.load(uploaded_file)
    df = pd.DataFrame(data["data"]["trades"])

    df["TradedTime"] = pd.to_datetime(df["TradedTime"])
    df = df.sort_values("TradedTime").reset_index(drop=True)

    # ==============================
    # CASHFLOW
    # ==============================
    df["Cashflow"] = -df["Position"] * df["TradedPrice"] * df["Quantity"]
    df["CumPnL"] = df["Cashflow"].cumsum()

    # ==============================
    # STRATEGY DURATION
    # ==============================
    start_date = df["TradedTime"].min()
    end_date = df["TradedTime"].max()

    total_days = (end_date - start_date).days
    total_months = round(total_days / 30.44, 2)
    total_years = round(total_days / 365, 2)

    total_pnl = df["Cashflow"].sum()
    return_pct = (total_pnl / capital * 100) if capital > 0 else 0

    # ==============================
    # METRIC CARDS
    # ==============================
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total P&L", f"₹{total_pnl:,.0f}")
    col2.metric("Return %", f"{return_pct:.2f}%")
    col3.metric("Trading Duration", f"{total_months} months")
    col4.metric("Date Range", f"{start_date.date()} → {end_date.date()}")

    # ==============================
    # EQUITY CURVE
    # ==============================
    st.subheader("📈 Equity Curve")
    st.line_chart(df.set_index("TradedTime")["CumPnL"])

    # ==============================
    # OPTION HOLDING
    # ==============================
    st.subheader("⏱ Option Holding Period")
    option_df = df[df["Strike"].notna()].copy()

    if not option_df.empty:
        option_holding = (
            option_df.groupby(["Ticker", "Strike", "Expiry"])
            .agg(
                EntryTime=("TradedTime", "min"),
                ExitTime=("TradedTime", "max"),
            )
            .reset_index()
        )

        option_holding["HoldingDays"] = (
            option_holding["ExitTime"] - option_holding["EntryTime"]
        ).dt.days
        option_holding["HoldingMonths"] = round(option_holding["HoldingDays"] / 30.44, 2)

        st.dataframe(option_holding, use_container_width=True)
    else:
        st.info("No option trades found")

    # ==============================
    # CASH HOLDING (FIFO)
    # ==============================
    st.subheader("⏱ Cash / Underlying Holding Period")
    cash_df = df[df["Strike"].isna()].copy()

    cash_positions = []
    open_positions = []

    for _, row in cash_df.iterrows():
        if row["Position"] == 1:
            open_positions.append(row.copy())
        else:
            qty_to_close = row["Quantity"]

            while qty_to_close > 0 and open_positions:
                entry = open_positions.pop(0)
                matched_qty = min(qty_to_close, entry["Quantity"])

                cash_positions.append(
                    {
                        "Ticker": row["Ticker"],
                        "EntryTime": entry["TradedTime"],
                        "ExitTime": row["TradedTime"],
                        "Quantity": matched_qty,
                        "HoldingDays": (row["TradedTime"] - entry["TradedTime"]).days,
                    }
                )

                qty_to_close -= matched_qty

    if cash_positions:
        cash_holding_df = pd.DataFrame(cash_positions)
        cash_holding_df["HoldingMonths"] = round(
            cash_holding_df["HoldingDays"] / 30.44, 2
        )
        st.dataframe(cash_holding_df, use_container_width=True)
    else:
        st.info("No cash / underlying positions found")

    # ==============================
    # ALL TRADES
    # ==============================
    # ==============================
    # OWS MONTHLY NET OPTION P&L (SELL + BUY MERGED)
    # ==============================
    st.subheader("🌀 Option Wheel – Monthly Net Option P&L")

    ows_df = df.copy()

    # Keep only option trades (ignore cash / underlying)
    opt_df = ows_df[ows_df["Strike"].notna()].copy()

    # Month
    opt_df["Month"] = opt_df["TradedTime"].dt.to_period("M").astype(str)

    # Unified P&L per execution
    opt_df["PnL"] = -opt_df["Position"] * opt_df["TradedPrice"] * opt_df["Quantity"]

    # Group SELL + BUY into ONE net result
    monthly_net = (
        opt_df.groupby([
            "Month",
            "Ticker",
            "Strike",
            "Expiry",
        ])
        .agg(
            Contracts=("Quantity", "sum"),
            Net_Profit_Loss=("PnL", "sum")
        )
        .reset_index()
        .sort_values(["Month", "Ticker", "Strike"])
    )

    # Option type fixed for Wheel view
    monthly_net.insert(3, "OptionType", "PE")

    monthly_net.rename(
        columns={"Net_Profit_Loss": "Profit / Loss (₹)"},
        inplace=True,
    )

    st.dataframe(monthly_net, use_container_width=True)

    # ==============================
    # MONTH-WISE TOTAL OPTION PROFIT
    # ==============================
    st.subheader("💰 Month-wise Total Option Profit (Net)")

    month_total = (
        monthly_net.groupby("Month")["Profit / Loss (₹)"]
        .sum()
        .reset_index()
    )

    st.dataframe(month_total, use_container_width=True)
    st.line_chart(month_total.set_index("Month")["Profit / Loss (₹)"])
