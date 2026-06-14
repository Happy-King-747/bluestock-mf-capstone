"""
email_report.py
---------------
Bonus B5 — Automated HTML Email Report Generator
Sends weekly mutual fund performance summary via email.

Features:
  - Beautiful HTML email with fund performance table
  - Top 5 funds by Sharpe ratio
  - Weekly NAV change summary
  - SIP inflow highlights
  - Works with Gmail SMTP

Usage:
    pip install schedule
    python scripts/email_report.py --test          # send test email now
    python scripts/email_report.py --schedule      # run weekly scheduler

Setup:
    1. Enable Gmail "App Passwords" in Google Account settings
    2. Set environment variables or edit config below:
       SENDER_EMAIL    = your Gmail address
       SENDER_PASSWORD = your App Password (16 chars)
       RECEIVER_EMAIL  = recipient email address
"""

import os
import smtplib
import schedule
import time
import argparse
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
LOGS      = ROOT / "reports"
LOGS.mkdir(parents=True, exist_ok=True)

# ── Email Config ───────────────────────────────────────────────────────────
# Set these as environment variables or replace directly
SENDER_EMAIL    = os.getenv("BLUESTOCK_EMAIL",    "your_email@gmail.com")
SENDER_PASSWORD = os.getenv("BLUESTOCK_PASSWORD", "your_app_password_here")
RECEIVER_EMAIL  = os.getenv("BLUESTOCK_RECEIVER", "receiver_email@gmail.com")
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "email_report_log.txt"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


# ── Data Helpers ───────────────────────────────────────────────────────────
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load performance, NAV, and scorecard data."""
    perf = pd.read_csv(PROCESSED / "07_scheme_performance_clean.csv")
    nav  = pd.read_csv(PROCESSED / "02_nav_history_clean.csv")
    nav["date"] = pd.to_datetime(nav["date"])

    sc_path = PROCESSED / "fund_scorecard.csv"
    sc = pd.read_csv(sc_path) if sc_path.exists() else pd.DataFrame()

    return perf, nav, sc


def get_weekly_nav_change(nav: pd.DataFrame, perf: pd.DataFrame) -> pd.DataFrame:
    """Compute NAV change over last 7 days for top 10 funds."""
    latest_date  = nav["date"].max()
    week_ago     = latest_date - pd.Timedelta(days=7)

    results = []
    top10 = perf.nlargest(10, "aum_crore")["amfi_code"].tolist()

    for code in top10:
        grp = nav[nav["amfi_code"] == code].sort_values("date")
        latest_nav = grp[grp["date"] == latest_date]["nav"].values
        week_nav   = grp[grp["date"] >= week_ago]["nav"].values

        if len(latest_nav) == 0 or len(week_nav) == 0:
            continue

        change_pct = ((latest_nav[0] - week_nav[0]) / week_nav[0]) * 100
        meta = perf[perf["amfi_code"] == code]
        results.append({
            "scheme_name": meta["scheme_name"].iloc[0].split("-")[0].strip()[:35] if len(meta) else str(code),
            "category":    meta["category"].iloc[0] if len(meta) else "",
            "latest_nav":  round(latest_nav[0], 4),
            "week_change_pct": round(change_pct, 2),
        })

    return pd.DataFrame(results).sort_values("week_change_pct", ascending=False)


# ── HTML Builder ───────────────────────────────────────────────────────────
def build_html_report(perf: pd.DataFrame, nav: pd.DataFrame, sc: pd.DataFrame) -> str:
    """Build beautiful HTML email content."""
    today       = datetime.now().strftime("%d %B %Y")
    week_change = get_weekly_nav_change(nav, perf)
    top5_sharpe = perf[~perf["category"].isin(["Liquid","Gilt"])].nlargest(5, "sharpe_ratio")
    total_aum   = perf["aum_crore"].sum()
    avg_return  = perf["return_3yr_pct"].mean()
    avg_sharpe  = perf[~perf["category"].isin(["Liquid","Gilt"])]["sharpe_ratio"].mean()

    # ── Fund Performance Table ─────────────────────────────────────────────
    def fund_rows(df: pd.DataFrame) -> str:
        rows = ""
        for i, (_, row) in enumerate(df.iterrows()):
            bg    = "#F8F9FF" if i % 2 == 0 else "#FFFFFF"
            chg   = row.get("week_change_pct", 0)
            color = "#2ECC71" if chg >= 0 else "#E74C3C"
            arrow = "▲" if chg >= 0 else "▼"
            rows += f"""
            <tr style="background:{bg};">
                <td style="padding:10px 14px;font-weight:500;color:#1B3A6B;">{row.get('scheme_name','')[:35]}</td>
                <td style="padding:10px 14px;color:#64748B;">{row.get('category','')}</td>
                <td style="padding:10px 14px;text-align:right;">₹{row.get('latest_nav',0):.2f}</td>
                <td style="padding:10px 14px;text-align:right;color:{color};font-weight:600;">{arrow} {abs(chg):.2f}%</td>
            </tr>"""
        return rows

    def sharpe_rows(df: pd.DataFrame) -> str:
        rows = ""
        for i, (_, row) in enumerate(df.iterrows()):
            bg    = "#F8F9FF" if i % 2 == 0 else "#FFFFFF"
            stars = "⭐" * int(row.get("morningstar_rating", 3))
            rows += f"""
            <tr style="background:{bg};">
                <td style="padding:10px 14px;font-weight:500;color:#1B3A6B;">{str(row.get('scheme_name',''))[:35]}</td>
                <td style="padding:10px 14px;color:#64748B;">{row.get('category','')}</td>
                <td style="padding:10px 14px;text-align:right;font-weight:600;color:#1B3A6B;">{row.get('sharpe_ratio',0):.3f}</td>
                <td style="padding:10px 14px;text-align:right;color:#2ECC71;">{row.get('return_3yr_pct',0):.1f}%</td>
                <td style="padding:10px 14px;text-align:center;">{stars}</td>
            </tr>"""
        return rows

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#F0F4FF;font-family:Segoe UI,Arial,sans-serif;">

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:30px 20px 0;">
        <table width="620" style="background:#1B3A6B;border-radius:12px 12px 0 0;">
          <tr>
            <td style="padding:32px 40px;">
              <div style="font-size:11px;color:#C8DEFF;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">
                Weekly Performance Report
              </div>
              <div style="font-size:28px;font-weight:700;color:#FFFFFF;margin-bottom:4px;">
                Bluestock MF Analytics
              </div>
              <div style="font-size:14px;color:#C8DEFF;">
                Week ending {today}
              </div>
            </td>
            <td style="padding:32px 40px;text-align:right;">
              <div style="font-size:36px;">📈</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <!-- KPI Cards -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:0 20px;">
        <table width="620" style="background:#FFFFFF;">
          <tr>
            <td style="padding:24px 40px 20px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="33%" style="text-align:center;padding:16px;background:#F4F7FF;border-radius:8px;margin:4px;">
                    <div style="font-size:22px;font-weight:700;color:#1B3A6B;">₹{total_aum/1e5:.1f}L Cr</div>
                    <div style="font-size:11px;color:#64748B;margin-top:4px;">Total AUM Tracked</div>
                  </td>
                  <td width="4px"></td>
                  <td width="33%" style="text-align:center;padding:16px;background:#F4F7FF;border-radius:8px;">
                    <div style="font-size:22px;font-weight:700;color:#2ECC71;">{avg_return:.1f}%</div>
                    <div style="font-size:11px;color:#64748B;margin-top:4px;">Avg 3yr CAGR</div>
                  </td>
                  <td width="4px"></td>
                  <td width="33%" style="text-align:center;padding:16px;background:#F4F7FF;border-radius:8px;">
                    <div style="font-size:22px;font-weight:700;color:#F4B942;">{avg_sharpe:.2f}</div>
                    <div style="font-size:11px;color:#64748B;margin-top:4px;">Avg Sharpe Ratio</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <!-- Weekly NAV Change -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:0 20px;">
        <table width="620" style="background:#FFFFFF;">
          <tr>
            <td style="padding:0 40px 24px;">
              <div style="font-size:16px;font-weight:700;color:#1B3A6B;margin-bottom:14px;padding-top:20px;
                          border-top:2px solid #E8EEFF;">
                📊 Weekly NAV Movement — Top 10 Funds by AUM
              </div>
              <table width="100%" style="border-collapse:collapse;">
                <tr style="background:#1B3A6B;">
                  <th style="padding:10px 14px;text-align:left;color:#FFFFFF;font-size:12px;font-weight:600;">Fund</th>
                  <th style="padding:10px 14px;text-align:left;color:#FFFFFF;font-size:12px;font-weight:600;">Category</th>
                  <th style="padding:10px 14px;text-align:right;color:#FFFFFF;font-size:12px;font-weight:600;">Latest NAV</th>
                  <th style="padding:10px 14px;text-align:right;color:#FFFFFF;font-size:12px;font-weight:600;">7-Day Change</th>
                </tr>
                {fund_rows(week_change)}
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <!-- Top 5 by Sharpe -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:0 20px;">
        <table width="620" style="background:#FFFFFF;">
          <tr>
            <td style="padding:0 40px 24px;">
              <div style="font-size:16px;font-weight:700;color:#1B3A6B;margin-bottom:14px;padding-top:20px;
                          border-top:2px solid #E8EEFF;">
                🏆 Top 5 Funds by Sharpe Ratio (Rf = 6.5%)
              </div>
              <table width="100%" style="border-collapse:collapse;">
                <tr style="background:#1B3A6B;">
                  <th style="padding:10px 14px;text-align:left;color:#FFFFFF;font-size:12px;">Fund</th>
                  <th style="padding:10px 14px;text-align:left;color:#FFFFFF;font-size:12px;">Category</th>
                  <th style="padding:10px 14px;text-align:right;color:#FFFFFF;font-size:12px;">Sharpe</th>
                  <th style="padding:10px 14px;text-align:right;color:#FFFFFF;font-size:12px;">3yr CAGR</th>
                  <th style="padding:10px 14px;text-align:center;color:#FFFFFF;font-size:12px;">Rating</th>
                </tr>
                {sharpe_rows(top5_sharpe)}
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <!-- Footer -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:0 20px 30px;">
        <table width="620" style="background:#1B3A6B;border-radius:0 0 12px 12px;">
          <tr>
            <td style="padding:24px 40px;text-align:center;">
              <div style="color:#C8DEFF;font-size:12px;line-height:1.8;">
                <strong style="color:#FFFFFF;">Bluestock MF Analytics</strong> — Automated Weekly Report<br>
                Generated on {today} | Data source: AMFI / mfapi.in<br>
                <span style="color:#8899CC;">This is an automated report. Do not reply to this email.</span>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""
    return html


# ── Email Sender ───────────────────────────────────────────────────────────
def send_email(html_content: str) -> bool:
    """Send HTML email via Gmail SMTP."""
    today = datetime.now().strftime("%d %B %Y")
    msg   = MIMEMultipart("alternative")
    msg["Subject"] = f"Bluestock MF Weekly Report — {today}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        log.info(f"✔ Email sent to {RECEIVER_EMAIL}")
        return True
    except smtplib.SMTPAuthenticationError:
        log.error("✘ Authentication failed — check email and App Password")
        log.error("  Gmail: Account → Security → 2-Step Verification → App Passwords")
        return False
    except Exception as e:
        log.error(f"✘ Failed to send email: {e}")
        return False


def save_html_preview(html_content: str) -> None:
    """Save HTML to file so you can preview it in browser."""
    path = LOGS / "weekly_report_preview.html"
    path.write_text(html_content, encoding="utf-8")
    log.info(f"✔ HTML preview saved → {path}")
    log.info(f"  Open in browser: file:///{path}")


def run_weekly_report() -> None:
    """Main job: generate and send weekly report."""
    log.info("=" * 55)
    log.info(f"Generating weekly report — {datetime.now()}")
    log.info("=" * 55)

    try:
        perf, nav, sc = load_data()
        html          = build_html_report(perf, nav, sc)
        save_html_preview(html)
        send_email(html)
    except Exception as e:
        log.error(f"Report generation failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Bluestock MF Email Report")
    parser.add_argument("--test",     action="store_true", help="Send test email now")
    parser.add_argument("--preview",  action="store_true", help="Save HTML preview only (no email)")
    parser.add_argument("--schedule", action="store_true", help="Run weekly scheduler (every Monday 8AM)")
    args = parser.parse_args()

    log.info("Bluestock MF — Automated Email Report (Bonus B5)")

    if args.preview:
        perf, nav, sc = load_data()
        html = build_html_report(perf, nav, sc)
        save_html_preview(html)
        log.info("Preview saved — open reports/weekly_report_preview.html in browser")

    elif args.test:
        log.info("Sending test email now...")
        run_weekly_report()

    elif args.schedule:
        log.info("Scheduler started — sends every Monday at 08:00")
        log.info("Press Ctrl+C to stop\n")
        schedule.every().monday.at("08:00").do(run_weekly_report)
        # Run once immediately
        run_weekly_report()
        while True:
            schedule.run_pending()
            time.sleep(60)

    else:
        # Default: just save preview
        log.info("No flag specified — saving HTML preview")
        log.info("Use --test to send email, --schedule for weekly auto-send")
        perf, nav, sc = load_data()
        html = build_html_report(perf, nav, sc)
        save_html_preview(html)


if __name__ == "__main__":
    main()
