"""
streamlit_dashboard.py
----------------------
Day 5 — Bluestock MF Analytics Dashboard
Bonus B2 — Streamlit alternative to Power BI

Usage:
    streamlit run dashboard/streamlit_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bluestock MF Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme colours ─────────────────────────────────────────────────────────
PRIMARY   = "#1B4F9B"
SECONDARY = "#E8F0FE"
ACCENT    = "#F4B942"
RED       = "#E74C3C"
GREEN     = "#2ECC71"

# ── Load data ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    ROOT = Path(__file__).resolve().parent.parent
    P    = ROOT / "data" / "processed"

    nav  = pd.read_csv(P / "02_nav_history_clean.csv")
    nav["date"] = pd.to_datetime(nav["date"])

    perf = pd.read_csv(P / "07_scheme_performance_clean.csv")

    txn  = pd.read_csv(P / "08_investor_transactions_clean.csv")
    txn["transaction_date"] = pd.to_datetime(txn["transaction_date"])

    sc   = pd.read_csv(P / "fund_scorecard.csv") if (P/"fund_scorecard.csv").exists() else pd.DataFrame()
    ab   = pd.read_csv(P / "alpha_beta.csv")     if (P/"alpha_beta.csv").exists()     else pd.DataFrame()

    return nav, perf, txn, sc, ab

nav, perf, txn, sc, ab = load_data()

# ── Sidebar navigation ────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/color/96/stock-market.png", width=60)
st.sidebar.title("Bluestock MF Analytics")
st.sidebar.markdown("**Data Analytics Internship**")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate to",
    ["🏠 Industry Overview",
     "📊 Fund Performance",
     "👥 Investor Analytics",
     "📈 SIP & Market Trends"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Filters**")

# Global filters
fund_houses = ["All"] + sorted(perf["fund_house"].dropna().unique().tolist())
selected_fh = st.sidebar.selectbox("Fund House", fund_houses)

categories  = ["All"] + sorted(perf["category"].dropna().unique().tolist())
selected_cat = st.sidebar.selectbox("Category", categories)

plans = ["All", "Direct", "Regular"]
selected_plan = st.sidebar.selectbox("Plan", plans)

st.sidebar.markdown("---")
st.sidebar.caption("Revanth A | Bluestock Fintech MJ28")

# Apply global filters to perf
perf_f = perf.copy()
if selected_fh   != "All": perf_f = perf_f[perf_f["fund_house"]==selected_fh]
if selected_cat  != "All": perf_f = perf_f[perf_f["category"]==selected_cat]
if selected_plan != "All": perf_f = perf_f[perf_f["plan"]==selected_plan]

# ══════════════════════════════════════════════════════════════════════════
# PAGE 1 — INDUSTRY OVERVIEW
# ══════════════════════════════════════════════════════════════════════════
if page == "🏠 Industry Overview":
    st.title("🏠 Industry Overview")
    st.markdown("Key industry-level metrics and trends across the Indian mutual fund ecosystem.")

    # ── KPI Cards ─────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    total_aum  = perf["aum_crore"].sum() / 1e5
    total_schm = len(perf)
    sip_vol    = txn[txn["transaction_type"]=="SIP"]["amount_inr"].sum() / 1e7
    unique_inv = txn["investor_id"].nunique()

    k1.metric("💰 Total AUM", f"₹{total_aum:.1f}L Cr",   delta="↑ 18% YoY")
    k2.metric("📋 Schemes",   f"{total_schm}",             delta="40 tracked")
    k3.metric("🔄 SIP Volume", f"₹{sip_vol:.0f} Cr",      delta="↑ 23% YoY")
    k4.metric("👤 Investors",  f"{unique_inv:,}",          delta="Active 2024")

    st.markdown("---")
    col1, col2 = st.columns(2)

    # AUM by fund house bar chart
    with col1:
        st.subheader("AUM by Fund House")
        aum_data = perf.groupby("fund_house")["aum_crore"].sum().reset_index()
        aum_data["aum_lakh_crore"] = (aum_data["aum_crore"] / 1e5).round(2)
        aum_data = aum_data.sort_values("aum_lakh_crore", ascending=True)
        fig = px.bar(aum_data, x="aum_lakh_crore", y="fund_house", orientation="h",
                     color="aum_lakh_crore", color_continuous_scale="Blues",
                     labels={"aum_lakh_crore":"AUM (₹ Lakh Crore)","fund_house":"Fund House"},
                     text="aum_lakh_crore")
        fig.update_traces(texttemplate="₹%{text:.2f}L Cr", textposition="outside")
        fig.update_layout(height=400, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # Category breakdown pie
    with col2:
        st.subheader("AUM by Category")
        cat_aum = perf.groupby("category")["aum_crore"].sum().reset_index()
        fig2 = px.pie(cat_aum, values="aum_crore", names="category",
                      color_discrete_sequence=px.colors.qualitative.Set3,
                      hole=0.4)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    col3, col4 = st.columns(2)

    # NAV trend for top 5 funds
    with col3:
        st.subheader("NAV Trend — Top 5 Funds by AUM")
        top5 = perf.nlargest(5,"aum_crore")["amfi_code"].tolist()
        nav_top5 = nav[nav["amfi_code"].isin(top5)].merge(
            perf[["amfi_code","scheme_name"]], on="amfi_code")
        nav_top5["short_name"] = nav_top5["scheme_name"].str.split("-").str[0].str.strip().str[:20]
        fig3 = px.line(nav_top5, x="date", y="nav", color="short_name",
                       labels={"nav":"NAV (₹)","date":"Date","short_name":"Fund"})
        fig3.update_layout(height=350, legend=dict(font=dict(size=9)))
        st.plotly_chart(fig3, use_container_width=True)

    # Risk grade distribution
    with col4:
        st.subheader("Funds by Risk Grade")
        risk_data = perf["risk_grade"].value_counts().reset_index()
        risk_data.columns = ["risk_grade","count"]
        color_map = {"Low":"#2ECC71","Moderate":"#F39C12",
                     "Moderately High":"#E67E22","High":"#E74C3C","Very High":"#8E44AD"}
        fig4 = px.bar(risk_data, x="risk_grade", y="count",
                      color="risk_grade", color_discrete_map=color_map,
                      labels={"count":"Number of Funds","risk_grade":"Risk Grade"},
                      text="count")
        fig4.update_traces(textposition="outside")
        fig4.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 2 — FUND PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════
elif page == "📊 Fund Performance":
    st.title("📊 Fund Performance")
    st.markdown("Risk-return analysis, scorecard rankings, and NAV trends.")

    # ── KPI row ───────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📈 Avg 3yr CAGR",    f"{perf_f['return_3yr_pct'].mean():.1f}%")
    k2.metric("⚡ Avg Sharpe",       f"{perf_f['sharpe_ratio'].mean():.2f}")
    k3.metric("📉 Avg Max Drawdown", f"{perf_f['max_drawdown_pct'].mean():.1f}%")
    k4.metric("💸 Avg Expense",      f"{perf_f['expense_ratio_pct'].mean():.2f}%")

    st.markdown("---")
    col1, col2 = st.columns([3, 2])

    # Risk vs Return scatter
    with col1:
        st.subheader("Risk vs Return (Bubble = AUM)")
        fig = px.scatter(perf_f.dropna(subset=["std_dev_ann_pct","return_3yr_pct"]),
                         x="std_dev_ann_pct", y="return_3yr_pct",
                         size="aum_crore", color="category",
                         hover_name="scheme_name",
                         hover_data={"sharpe_ratio":True,"expense_ratio_pct":True},
                         labels={"std_dev_ann_pct":"Risk: Std Dev (%)","return_3yr_pct":"3yr CAGR (%)"},
                         size_max=40)
        fig.add_hline(y=perf_f["return_3yr_pct"].mean(), line_dash="dash",
                      line_color="gray", annotation_text="Avg Return")
        fig.add_vline(x=perf_f["std_dev_ann_pct"].mean(), line_dash="dash",
                      line_color="gray", annotation_text="Avg Risk")
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    # Top 10 by Sharpe
    with col2:
        st.subheader("Top 10 by Sharpe Ratio")
        top_sharpe = perf_f.nlargest(10,"sharpe_ratio")[["scheme_name","category","sharpe_ratio","return_3yr_pct"]]
        top_sharpe["scheme_name"] = top_sharpe["scheme_name"].str.split("-").str[0].str.strip().str[:22]
        fig2 = px.bar(top_sharpe.sort_values("sharpe_ratio"), x="sharpe_ratio", y="scheme_name",
                      orientation="h", color="sharpe_ratio",
                      color_continuous_scale="RdYlGn",
                      labels={"sharpe_ratio":"Sharpe Ratio","scheme_name":""},
                      text="sharpe_ratio")
        fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig2.update_layout(height=420, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # Fund Scorecard Table
    st.subheader("📋 Fund Scorecard — Sortable Table")
    display_cols = ["scheme_name","fund_house","category","plan",
                    "return_3yr_pct","sharpe_ratio","max_drawdown_pct",
                    "expense_ratio_pct","aum_crore","morningstar_rating"]
    show_df = perf_f[display_cols].copy()
    show_df.columns = ["Scheme","Fund House","Category","Plan",
                       "3yr CAGR%","Sharpe","Max DD%","Expense%","AUM Cr","⭐ Rating"]
    show_df["3yr CAGR%"] = show_df["3yr CAGR%"].round(2)
    show_df["Sharpe"]    = show_df["Sharpe"].round(3)
    st.dataframe(show_df.sort_values("Sharpe", ascending=False).reset_index(drop=True),
                 use_container_width=True, height=350)

    st.markdown("---")

    # NAV detail drill-through
    st.subheader("🔍 NAV Detail — Select a Fund")
    fund_options = perf_f["scheme_name"].tolist()
    selected_fund = st.selectbox("Choose fund", fund_options)
    if selected_fund:
        code = perf_f[perf_f["scheme_name"]==selected_fund]["amfi_code"].iloc[0]
        fund_nav = nav[nav["amfi_code"]==code].sort_values("date")
        fund_nav["rolling_1yr"] = fund_nav["nav"].pct_change(252) * 100
        fig3 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                             subplot_titles=["NAV (₹)","Rolling 1yr Return (%)"],
                             row_heights=[0.6, 0.4])
        fig3.add_trace(go.Scatter(x=fund_nav["date"], y=fund_nav["nav"],
                                  name="NAV", line=dict(color=PRIMARY, width=2)), row=1, col=1)
        fig3.add_trace(go.Scatter(x=fund_nav["date"], y=fund_nav["rolling_1yr"],
                                  name="1yr Return%", line=dict(color=ACCENT, width=1.5),
                                  fill="tozeroy"), row=2, col=1)
        fig3.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
        fig3.update_layout(height=450, showlegend=True)
        st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 3 — INVESTOR ANALYTICS
# ══════════════════════════════════════════════════════════════════════════
elif page == "👥 Investor Analytics":
    st.title("👥 Investor Analytics")
    st.markdown("Demographics, geographic distribution, and transaction behaviour.")

    # Investor filters
    icol1, icol2, icol3 = st.columns(3)
    states     = ["All"] + sorted(txn["state"].dropna().unique().tolist())
    age_groups = ["All"] + sorted(txn["age_group"].dropna().unique().tolist())
    tiers      = ["All"] + sorted(txn["city_tier"].dropna().unique().tolist())
    sel_state  = icol1.selectbox("State", states, key="inv_state")
    sel_age    = icol2.selectbox("Age Group", age_groups, key="inv_age")
    sel_tier   = icol3.selectbox("City Tier", tiers, key="inv_tier")

    txn_f = txn.copy()
    if sel_state != "All": txn_f = txn_f[txn_f["state"]==sel_state]
    if sel_age   != "All": txn_f = txn_f[txn_f["age_group"]==sel_age]
    if sel_tier  != "All": txn_f = txn_f[txn_f["city_tier"]==sel_tier]

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📦 Transactions",  f"{len(txn_f):,}")
    k2.metric("💰 Total Volume",  f"₹{txn_f['amount_inr'].sum()/1e7:.0f} Cr")
    k3.metric("👤 Investors",     f"{txn_f['investor_id'].nunique():,}")
    k4.metric("📊 Avg Ticket",    f"₹{txn_f['amount_inr'].mean():,.0f}")

    st.markdown("---")
    col1, col2 = st.columns(2)

    # Transaction by state
    with col1:
        st.subheader("SIP Amount by State")
        state_data = txn_f[txn_f["transaction_type"]=="SIP"].groupby("state")["amount_inr"].sum().reset_index()
        state_data["amount_cr"] = (state_data["amount_inr"]/1e7).round(1)
        state_data = state_data.sort_values("amount_cr", ascending=True)
        fig = px.bar(state_data, x="amount_cr", y="state", orientation="h",
                     color="amount_cr", color_continuous_scale="Blues",
                     labels={"amount_cr":"SIP Amount (₹ Cr)","state":"State"},
                     text="amount_cr")
        fig.update_traces(texttemplate="₹%{text} Cr", textposition="outside")
        fig.update_layout(height=380, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # Transaction type donut
    with col2:
        st.subheader("Transaction Type Split")
        type_data = txn_f.groupby("transaction_type")["amount_inr"].sum().reset_index()
        fig2 = px.pie(type_data, values="amount_inr", names="transaction_type",
                      hole=0.45, color_discrete_sequence=[PRIMARY, ACCENT, RED])
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(height=380)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    col3, col4 = st.columns(2)

    # Age group vs avg SIP
    with col3:
        st.subheader("Average SIP Amount by Age Group")
        age_data = txn_f[txn_f["transaction_type"]=="SIP"].groupby("age_group")["amount_inr"].mean().reset_index()
        age_data["amount_inr"] = age_data["amount_inr"].round(0)
        fig3 = px.bar(age_data, x="age_group", y="amount_inr",
                      color="amount_inr", color_continuous_scale="Purples",
                      labels={"amount_inr":"Avg SIP Amount (₹)","age_group":"Age Group"},
                      text="amount_inr")
        fig3.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
        fig3.update_layout(height=350, coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True)

    # Monthly transaction volume
    with col4:
        st.subheader("Monthly Transaction Volume")
        txn_f["month"] = txn_f["transaction_date"].dt.to_period("M").astype(str)
        monthly = txn_f.groupby(["month","transaction_type"])["amount_inr"].sum().reset_index()
        monthly["amount_cr"] = (monthly["amount_inr"]/1e7).round(2)
        fig4 = px.line(monthly, x="month", y="amount_cr", color="transaction_type",
                       labels={"amount_cr":"Amount (₹ Cr)","month":"Month"},
                       markers=True)
        fig4.update_layout(height=350, xaxis_tickangle=-45)
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # Gender + KYC
    col5, col6 = st.columns(2)
    with col5:
        st.subheader("Gender Distribution")
        gender_data = txn_f["gender"].value_counts().reset_index()
        gender_data.columns = ["gender","count"]
        fig5 = px.pie(gender_data, values="count", names="gender",
                      color_discrete_sequence=[PRIMARY,"#E91E63"],
                      hole=0.4)
        fig5.update_layout(height=300)
        st.plotly_chart(fig5, use_container_width=True)

    with col6:
        st.subheader("KYC Status by City Tier")
        kyc_data = txn_f.groupby(["city_tier","kyc_status"]).size().reset_index(name="count")
        fig6 = px.bar(kyc_data, x="city_tier", y="count", color="kyc_status",
                      barmode="group", color_discrete_sequence=[GREEN, RED],
                      labels={"count":"Transactions","city_tier":"City Tier"})
        fig6.update_layout(height=300)
        st.plotly_chart(fig6, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE 4 — SIP & MARKET TRENDS
# ══════════════════════════════════════════════════════════════════════════
elif page == "📈 SIP & Market Trends":
    st.title("📈 SIP & Market Trends")
    st.markdown("SIP inflow trends, category analysis, and market correlation.")

    # KPIs
    sip_txn = txn[txn["transaction_type"]=="SIP"]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💳 Total SIP Txns",    f"{len(sip_txn):,}")
    k2.metric("💰 Total SIP Volume",  f"₹{sip_txn['amount_inr'].sum()/1e7:.0f} Cr")
    k3.metric("📅 Avg Monthly SIP",   f"₹{sip_txn.groupby(sip_txn['transaction_date'].dt.to_period('M'))['amount_inr'].sum().mean()/1e7:.0f} Cr")
    k4.metric("🏦 Top SIP State",     txn[txn["transaction_type"]=="SIP"].groupby("state")["amount_inr"].sum().idxmax())

    st.markdown("---")

    # Monthly SIP trend
    st.subheader("Monthly SIP Inflow Trend")
    sip_monthly = sip_txn.copy()
    sip_monthly["month"] = sip_monthly["transaction_date"].dt.to_period("M").astype(str)
    sip_vol = sip_monthly.groupby("month")["amount_inr"].sum().reset_index()
    sip_vol["amount_cr"] = (sip_vol["amount_inr"]/1e7).round(2)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=sip_vol["month"], y=sip_vol["amount_cr"],
                         name="SIP Inflow (₹ Cr)", marker_color=PRIMARY, opacity=0.8))
    fig.add_trace(go.Scatter(x=sip_vol["month"], y=sip_vol["amount_cr"].rolling(3).mean(),
                             name="3-Month Moving Avg", line=dict(color=ACCENT, width=2.5)))
    fig.update_layout(height=350, xaxis_tickangle=-45, legend=dict(orientation="h"),
                      yaxis_title="SIP Amount (₹ Cr)", xaxis_title="Month")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)

    # SIP by age group trend
    with col1:
        st.subheader("SIP Volume by Age Group Over Time")
        sip_age = sip_txn.copy()
        sip_age["month"] = sip_age["transaction_date"].dt.to_period("M").astype(str)
        age_monthly = sip_age.groupby(["month","age_group"])["amount_inr"].sum().reset_index()
        age_monthly["amount_cr"] = (age_monthly["amount_inr"]/1e7).round(2)
        fig2 = px.area(age_monthly, x="month", y="amount_cr", color="age_group",
                       labels={"amount_cr":"SIP Amount (₹ Cr)","month":"Month"},
                       color_discrete_sequence=px.colors.qualitative.Set2)
        fig2.update_layout(height=380, xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

    # Payment mode trend
    with col2:
        st.subheader("SIP by Payment Mode")
        pay_data = sip_txn.groupby("payment_mode")["amount_inr"].agg(["sum","count"]).reset_index()
        pay_data["sum_cr"] = (pay_data["sum"]/1e7).round(1)
        fig3 = px.bar(pay_data, x="payment_mode", y="sum_cr",
                      color="sum_cr", color_continuous_scale="Teal",
                      labels={"sum_cr":"Total SIP (₹ Cr)","payment_mode":"Payment Mode"},
                      text="sum_cr")
        fig3.update_traces(texttemplate="₹%{text} Cr", textposition="outside")
        fig3.update_layout(height=380, coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")

    # NAV correlation heatmap
    st.subheader("NAV Return Correlation — All Funds")
    top10_codes = perf.nlargest(10,"aum_crore")["amfi_code"].tolist()
    pivot = nav[nav["amfi_code"].isin(top10_codes)].pivot(index="date", columns="amfi_code", values="nav")
    returns = pivot.pct_change().dropna()
    short_names = {c: perf[perf["amfi_code"]==c]["scheme_name"].iloc[0].split("-")[0].strip()[:18]
                   for c in returns.columns if len(perf[perf["amfi_code"]==c]) > 0}
    returns = returns.rename(columns=short_names)
    corr = returns.corr()
    fig4 = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdYlGn",
                     zmin=-1, zmax=1, aspect="auto",
                     labels=dict(color="Correlation"))
    fig4.update_layout(height=450)
    st.plotly_chart(fig4, use_container_width=True)

    # Top funds by city tier
    st.markdown("---")
    st.subheader("SIP Distribution — T30 vs B30 Cities by State")
    tier_state = txn[txn["transaction_type"]=="SIP"].groupby(["state","city_tier"])["amount_inr"].sum().reset_index()
    tier_state["amount_cr"] = (tier_state["amount_inr"]/1e7).round(1)
    fig5 = px.bar(tier_state, x="state", y="amount_cr", color="city_tier",
                  barmode="group", color_discrete_sequence=[PRIMARY, ACCENT],
                  labels={"amount_cr":"SIP Amount (₹ Cr)","state":"State"})
    fig5.update_layout(height=380)
    st.plotly_chart(fig5, use_container_width=True)
