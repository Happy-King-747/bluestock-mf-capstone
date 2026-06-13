"""
compute_metrics.py
------------------
D4 — Performance Metrics Computation (Bluestock MF Analytics)
Computes: CAGR, Sharpe, Sortino, Alpha, Beta, Max Drawdown, VaR, CVaR
Outputs : fund_scorecard.csv, alpha_beta.csv, var_cvar_report.csv

Usage:
    python scripts/compute_metrics.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

# ── Constants ──────────────────────────────────────────────────────────────
RF_ANNUAL = 0.065          # RBI repo rate proxy: 6.5%
RF_DAILY  = RF_ANNUAL / 252
TRADING_DAYS = 252

SEP = "=" * 65


def section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load NAV history and scheme performance data."""
    nav  = pd.read_csv(PROCESSED / "02_nav_history_clean.csv")
    nav["date"] = pd.to_datetime(nav["date"])
    nav  = nav[nav["date"].dt.dayofweek < 5]  # weekdays only
    nav  = nav.sort_values(["amfi_code", "date"]).reset_index(drop=True)
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    nav  = nav.dropna(subset=["daily_return"])

    perf = pd.read_csv(PROCESSED / "07_scheme_performance_clean.csv")
    return nav, perf


def compute_cagr(nav: pd.DataFrame, perf: pd.DataFrame) -> pd.DataFrame:
    """Compute 1yr and 3yr CAGR for all funds."""
    section("CAGR Computation")
    today = nav["date"].max()
    results = []

    for code, grp in nav.groupby("amfi_code"):
        grp = grp.sort_values("date")
        meta = perf[perf["amfi_code"] == code]

        def cagr(years: float) -> float:
            start = today - pd.DateOffset(years=years)
            sub   = grp[grp["date"] >= start]
            if len(sub) < 10:
                return np.nan
            n = (sub.iloc[-1]["date"] - sub.iloc[0]["date"]).days / 365.25
            if n <= 0 or sub.iloc[0]["nav"] <= 0:
                return np.nan
            return ((sub.iloc[-1]["nav"] / sub.iloc[0]["nav"]) ** (1/n) - 1) * 100

        results.append({
            "amfi_code":   code,
            "scheme_name": meta["scheme_name"].iloc[0] if len(meta) else str(code),
            "fund_house":  meta["fund_house"].iloc[0]  if len(meta) else "",
            "category":    meta["category"].iloc[0]    if len(meta) else "",
            "cagr_1yr":    round(cagr(1), 2),
            "cagr_3yr":    round(cagr(3), 2),
        })

    df = pd.DataFrame(results)
    print(f"  CAGR computed for {len(df)} funds")
    print(f"\n  Top 5 by 3yr CAGR:")
    print(df.nlargest(5, "cagr_3yr")[["scheme_name","cagr_1yr","cagr_3yr"]].to_string(index=False))
    return df


def compute_sharpe_sortino(nav: pd.DataFrame, perf: pd.DataFrame) -> pd.DataFrame:
    """Compute Sharpe and Sortino ratios for all funds."""
    section("Sharpe & Sortino Ratios  (Rf = 6.5%)")
    results = []

    for code, grp in nav.groupby("amfi_code"):
        r = grp["daily_return"].dropna()
        if len(r) < 50:
            continue
        excess   = r - RF_DAILY
        sharpe   = (excess.mean() / r.std()) * np.sqrt(TRADING_DAYS)
        downside = r[r < 0]
        sortino  = (excess.mean() / downside.std()) * np.sqrt(TRADING_DAYS) if len(downside) >= 5 else np.nan
        meta = perf[perf["amfi_code"] == code]
        results.append({
            "amfi_code":      code,
            "sharpe_ratio":   round(sharpe,  4),
            "sortino_ratio":  round(sortino, 4) if not np.isnan(sortino) else np.nan,
        })

    df = pd.DataFrame(results)
    print(f"  Sharpe/Sortino computed for {len(df)} funds")
    return df


def compute_alpha_beta(nav: pd.DataFrame, perf: pd.DataFrame) -> pd.DataFrame:
    """OLS regression of fund returns vs index proxy."""
    section("Alpha & Beta  (OLS vs Index ETF proxy)")
    index_codes = perf[perf["category"].isin(["Index","Index/ETF"])]["amfi_code"].tolist()
    if not index_codes:
        print("  ⚠  No index funds found — skipping Alpha/Beta")
        return pd.DataFrame()

    mkt = nav[nav["amfi_code"].isin(index_codes)].groupby("date")["daily_return"].mean()
    results = []

    for code, grp in nav.groupby("amfi_code"):
        if code in index_codes:
            continue
        fund_r = grp.set_index("date")["daily_return"]
        common = fund_r.index.intersection(mkt.index)
        if len(common) < 100:
            continue
        y = fund_r.loc[common].values
        x = mkt.loc[common].values
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < 100:
            continue
        slope, intercept, r_val, p_val, _ = stats.linregress(x[mask], y[mask])
        meta = perf[perf["amfi_code"] == code]
        results.append({
            "amfi_code":     code,
            "scheme_name":   meta["scheme_name"].iloc[0] if len(meta) else str(code),
            "fund_house":    meta["fund_house"].iloc[0]  if len(meta) else "",
            "category":      meta["category"].iloc[0]    if len(meta) else "",
            "beta_computed": round(slope, 4),
            "alpha_ann_pct": round(intercept * TRADING_DAYS * 100, 4),
            "r_squared":     round(r_val**2, 4),
            "p_value":       round(p_val, 6),
            "n_obs":         int(mask.sum()),
        })

    df = pd.DataFrame(results)
    if len(df):
        print(f"  Alpha/Beta computed for {len(df)} funds")
        print(f"\n  Top 5 by Alpha:")
        print(df.nlargest(5,"alpha_ann_pct")[["scheme_name","alpha_ann_pct","beta_computed"]].to_string(index=False))
    return df


def compute_max_drawdown(nav: pd.DataFrame, perf: pd.DataFrame) -> pd.DataFrame:
    """Maximum peak-to-trough drawdown per fund."""
    section("Maximum Drawdown")
    results = []

    for code, grp in nav.groupby("amfi_code"):
        grp = grp.sort_values("date").reset_index(drop=True)
        running_max = grp["nav"].cummax()
        drawdown    = (grp["nav"] / running_max) - 1
        max_dd      = drawdown.min()
        worst_idx   = drawdown.idxmin()
        peak_idx    = grp["nav"][:worst_idx+1].idxmax()
        meta = perf[perf["amfi_code"] == code]
        results.append({
            "amfi_code":        code,
            "scheme_name":      meta["scheme_name"].iloc[0] if len(meta) else str(code),
            "category":         meta["category"].iloc[0]    if len(meta) else "",
            "max_drawdown_pct": round(max_dd * 100, 2),
            "peak_date":        grp.loc[peak_idx, "date"].strftime("%Y-%m-%d"),
            "trough_date":      grp.loc[worst_idx,"date"].strftime("%Y-%m-%d"),
            "duration_days":    int((grp.loc[worst_idx,"date"] - grp.loc[peak_idx,"date"]).days),
        })

    df = pd.DataFrame(results).sort_values("max_drawdown_pct")
    print(f"  Max Drawdown computed for {len(df)} funds")
    return df


def compute_var_cvar(nav: pd.DataFrame, perf: pd.DataFrame) -> pd.DataFrame:
    """Historical VaR (95% & 99%) and CVaR for all funds."""
    section("VaR & CVaR  (Historical simulation)")
    results = []

    for code, grp in nav.groupby("amfi_code"):
        r = grp["daily_return"].dropna()
        if len(r) < 50:
            continue
        var_95  = np.percentile(r, 5)
        cvar_95 = r[r <= var_95].mean()
        var_99  = np.percentile(r, 1)
        cvar_99 = r[r <= var_99].mean()
        meta = perf[perf["amfi_code"] == code]
        results.append({
            "amfi_code":         code,
            "scheme_name":       meta["scheme_name"].iloc[0] if len(meta) else str(code),
            "category":          meta["category"].iloc[0]    if len(meta) else "",
            "risk_grade":        meta["risk_grade"].iloc[0]  if len(meta) else "",
            "var_95_daily_pct":  round(var_95  * 100, 4),
            "cvar_95_daily_pct": round(cvar_95 * 100, 4),
            "var_99_daily_pct":  round(var_99  * 100, 4),
            "cvar_99_daily_pct": round(cvar_99 * 100, 4),
            "var_95_annual_pct": round(var_95  * np.sqrt(TRADING_DAYS) * 100, 4),
            "n_observations":    len(r),
        })

    df = pd.DataFrame(results).sort_values("var_95_daily_pct")
    df.to_csv(PROCESSED / "var_cvar_report.csv", index=False)
    print(f"  VaR/CVaR computed for {len(df)} funds")
    print(f"  ✔  Saved → data/processed/var_cvar_report.csv")
    return df


def build_scorecard(cagr_df, sharpe_df, ab_df, dd_df, perf) -> pd.DataFrame:
    """Build composite fund scorecard (0–100)."""
    section("Fund Scorecard  (0–100 composite)")
    sc = cagr_df[["amfi_code","scheme_name","fund_house","category","cagr_3yr"]].copy()
    sc = sc.merge(sharpe_df[["amfi_code","sharpe_ratio","sortino_ratio"]], on="amfi_code", how="left")
    sc = sc.merge(dd_df[["amfi_code","max_drawdown_pct"]], on="amfi_code", how="left")
    sc = sc.merge(perf[["amfi_code","expense_ratio_pct"]], on="amfi_code", how="left")
    if len(ab_df):
        sc = sc.merge(ab_df[["amfi_code","alpha_ann_pct","beta_computed"]], on="amfi_code", how="left")
    else:
        sc["alpha_ann_pct"] = np.nan
        sc["beta_computed"] = np.nan

    def rank_score(series: pd.Series, ascending: bool = False) -> pd.Series:
        ranked = series.rank(ascending=ascending, na_option="bottom")
        return ((ranked - 1) / (len(ranked) - 1) * 100).round(2)

    sc["score_return"]  = rank_score(sc["cagr_3yr"],          ascending=False)
    sc["score_sharpe"]  = rank_score(sc["sharpe_ratio"],       ascending=False)
    sc["score_alpha"]   = rank_score(sc["alpha_ann_pct"],      ascending=False)
    sc["score_expense"] = rank_score(sc["expense_ratio_pct"],  ascending=True)
    sc["score_dd"]      = rank_score(sc["max_drawdown_pct"],   ascending=False)

    sc["composite_score"] = (
        0.30 * sc["score_return"]  +
        0.25 * sc["score_sharpe"]  +
        0.20 * sc["score_alpha"]   +
        0.15 * sc["score_expense"] +
        0.10 * sc["score_dd"]
    ).round(2)

    sc["rank"] = sc["composite_score"].rank(ascending=False).astype(int)
    sc = sc.sort_values("composite_score", ascending=False).reset_index(drop=True)
    sc.to_csv(PROCESSED / "fund_scorecard.csv", index=False)
    print(f"  Scorecard built for {len(sc)} funds")
    print(f"  ✔  Saved → data/processed/fund_scorecard.csv")
    print(f"\n  Top 10 Funds:")
    print(sc[["rank","scheme_name","category","composite_score","cagr_3yr","sharpe_ratio"]].head(10).to_string(index=False))
    return sc


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    print(SEP)
    print("  BLUESTOCK MF ANALYTICS — Compute Metrics (D4)")
    print(SEP)

    nav, perf = load_data()
    print(f"  NAV records loaded : {len(nav):,}")
    print(f"  Schemes            : {nav['amfi_code'].nunique()}")

    cagr_df   = compute_cagr(nav, perf)
    sharpe_df = compute_sharpe_sortino(nav, perf)
    ab_df     = compute_alpha_beta(nav, perf)
    dd_df     = compute_max_drawdown(nav, perf)
    var_df    = compute_var_cvar(nav, perf)
    sc        = build_scorecard(cagr_df, sharpe_df, ab_df, dd_df, perf)

    if len(ab_df):
        ab_df.to_csv(PROCESSED / "alpha_beta.csv", index=False)
        print(f"\n  ✔  Saved → data/processed/alpha_beta.csv")

    cagr_df.to_csv(PROCESSED / "cagr_comparison.csv", index=False)
    dd_df.to_csv(PROCESSED / "max_drawdown.csv", index=False)

    section("ALL METRICS COMPLETE")
    print(f"  fund_scorecard.csv   ✔")
    print(f"  alpha_beta.csv       ✔")
    print(f"  var_cvar_report.csv  ✔")
    print(f"  cagr_comparison.csv  ✔")
    print(f"  max_drawdown.csv     ✔\n")


if __name__ == "__main__":
    main()
