"""
recommender.py
--------------
Day 6 — Simple Fund Recommender System
Input  : risk appetite (Low / Moderate / High)
Output : top 3 funds by Sharpe ratio within matching risk_grade

Usage:
    python scripts/recommender.py
    python scripts/recommender.py --risk Low
    python scripts/recommender.py --risk Moderate
    python scripts/recommender.py --risk High
"""

import argparse
from pathlib import Path
import pandas as pd

ROOT      = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

# Risk grade mapping
RISK_MAP = {
    "Low":      ["Low"],
    "Moderate": ["Moderate", "Moderately High"],
    "High":     ["High", "Very High"],
}

SEP = "=" * 65


def load_data() -> pd.DataFrame:
    path = PROCESSED / "07_scheme_performance_clean.csv"
    if not path.exists():
        raise FileNotFoundError(f"Performance file not found: {path}")
    return pd.read_csv(path)


def recommend(perf: pd.DataFrame, risk_appetite: str) -> pd.DataFrame:
    """Return top 3 funds for the given risk appetite."""
    if risk_appetite not in RISK_MAP:
        raise ValueError(f"Invalid risk appetite. Choose from: {list(RISK_MAP.keys())}")

    grades    = RISK_MAP[risk_appetite]
    filtered  = perf[perf["risk_grade"].isin(grades)].copy()

    if filtered.empty:
        print(f"  ⚠  No funds found for risk grade: {grades}")
        return pd.DataFrame()

    top3 = filtered.nlargest(3, "sharpe_ratio")[
        ["scheme_name", "fund_house", "category", "plan",
         "sharpe_ratio", "return_3yr_pct", "expense_ratio_pct",
         "risk_grade", "morningstar_rating"]
    ].reset_index(drop=True)

    top3.index = top3.index + 1   # rank 1, 2, 3
    return top3


def print_recommendation(risk_appetite: str, top3: pd.DataFrame) -> None:
    print(f"\n{SEP}")
    print(f"  FUND RECOMMENDATIONS — Risk Appetite: {risk_appetite.upper()}")
    print(SEP)

    if top3.empty:
        print("  No recommendations available.")
        return

    for rank, row in top3.iterrows():
        stars = "⭐" * int(row["morningstar_rating"]) if pd.notna(row["morningstar_rating"]) else ""
        print(f"\n  Rank #{rank} {stars}")
        print(f"  Fund     : {row['scheme_name']}")
        print(f"  House    : {row['fund_house']}")
        print(f"  Category : {row['category']}  |  Plan: {row['plan']}")
        print(f"  Sharpe   : {row['sharpe_ratio']:.3f}  |  3yr CAGR: {row['return_3yr_pct']:.2f}%")
        print(f"  Expense  : {row['expense_ratio_pct']:.2f}%  |  Risk Grade: {row['risk_grade']}")

    print(f"\n{SEP}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bluestock MF Fund Recommender")
    parser.add_argument("--risk", type=str, default=None,
                        choices=["Low", "Moderate", "High"],
                        help="Risk appetite: Low, Moderate, or High")
    args = parser.parse_args()

    print(SEP)
    print("  BLUESTOCK MF — Fund Recommender System")
    print(SEP)

    perf = load_data()
    print(f"  Loaded {len(perf)} fund schemes")

    if args.risk:
        # Single recommendation
        top3 = recommend(perf, args.risk)
        print_recommendation(args.risk, top3)
    else:
        # Show all 3 risk levels
        print("\n  No risk appetite specified — showing all 3 levels.\n")
        for appetite in ["Low", "Moderate", "High"]:
            top3 = recommend(perf, appetite)
            print_recommendation(appetite, top3)

        # Interactive mode
        print("\n  Enter your risk appetite to get personalised recommendations.")
        print("  Options: Low | Moderate | High | quit\n")
        while True:
            user_input = input("  Your risk appetite: ").strip().title()
            if user_input.lower() in ("quit", "exit", "q"):
                print("\n  Thank you for using Bluestock Fund Recommender!\n")
                break
            if user_input in RISK_MAP:
                top3 = recommend(perf, user_input)
                print_recommendation(user_input, top3)
            else:
                print("  ⚠  Invalid input. Please enter: Low, Moderate, or High")


if __name__ == "__main__":
    main()
