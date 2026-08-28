"""
Daily Gold & Silver Price Tracker
----------------------------------
1. Fetches live gold (XAU) and silver (XAG) prices in USD and INR from the
   free gold-api.com endpoint (no API key required).
2. Converts troy-ounce prices to price-per-gram and price-per-10-grams
   (the units commonly used in India).
3. Sends a formatted HTML email with today's rates to a list of recipients.
4. Appends today's snapshot to data/history.csv (acts as a simple database).
5. Writes docs/prices.json, which the GitHub Pages static site reads to
   display the latest prices.

All secrets (Gmail credentials, recipient list) are read from environment
variables so nothing sensitive is hardcoded. In GitHub Actions these come
from repository Secrets.
"""

import os
import sys
import json
import csv
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GOLD_API_BASE = "https://api.gold-api.com/price"
TROY_OUNCE_IN_GRAMS = 31.1034768

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_CSV = os.path.join(REPO_ROOT, "data", "history.csv")
PRICES_JSON = os.path.join(REPO_ROOT, "docs", "prices.json")
# GitHub Pages only serves the docs/ folder, so the site needs its own copy
# of the history file to fetch client-side for the trend chart.
DOCS_HISTORY_CSV = os.path.join(REPO_ROOT, "docs", "history.csv")

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
EMAIL_RECIPIENTS = os.environ.get("EMAIL_RECIPIENTS", "")


# ---------------------------------------------------------------------------
# Step 1: Fetch prices
# ---------------------------------------------------------------------------
def fetch_price(symbol: str, currency: str) -> float:
    """Fetch the current price (per troy ounce) for a symbol in a currency."""
    url = f"{GOLD_API_BASE}/{symbol}/{currency}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()
    return float(data["price"])


def fetch_all_prices() -> dict:
    """Fetch gold and silver prices in USD and INR, per ounce/gram/10g."""
    prices = {}
    for symbol_key, symbol in (("gold", "XAU"), ("silver", "XAG")):
        prices[symbol_key] = {}
        for currency in ("USD", "INR"):
            price_per_oz = fetch_price(symbol, currency)
            price_per_gram = price_per_oz / TROY_OUNCE_IN_GRAMS
            prices[symbol_key][currency] = {
                "per_oz": round(price_per_oz, 2),
                "per_gram": round(price_per_gram, 2),
                "per_10g": round(price_per_gram * 10, 2),
            }
    return prices


# ---------------------------------------------------------------------------
# Step 2: Build & send email
# ---------------------------------------------------------------------------
def build_email_html(prices: dict, date_str: str) -> str:
    def metal_block(name, symbol_key, emoji):
        p = prices[symbol_key]
        return f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #eee;">
            <strong>{emoji} {name}</strong>
          </td>
          <td style="padding:12px 16px;border-bottom:1px solid #eee;">
            ${p['USD']['per_oz']} / oz<br>
            ₹{p['INR']['per_10g']} / 10g
          </td>
        </tr>
        """

    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#222;">
        <h2>Gold & Silver Prices — {date_str}</h2>
        <table style="border-collapse:collapse;width:100%;max-width:480px;">
          <thead>
            <tr style="background:#f5f5f5;text-align:left;">
              <th style="padding:12px 16px;">Metal</th>
              <th style="padding:12px 16px;">Price</th>
            </tr>
          </thead>
          <tbody>
            {metal_block("Gold", "gold", "🥇")}
            {metal_block("Silver", "silver", "🥈")}
          </tbody>
        </table>
        <p style="color:#888;font-size:12px;margin-top:16px;">
          Source: gold-api.com · Sent automatically by GitHub Actions
        </p>
      </body>
    </html>
    """


def send_email(html_body: str, date_str: str) -> None:
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("GMAIL_USER / GMAIL_APP_PASSWORD not set — skipping email.")
        return

    recipients = [r.strip() for r in EMAIL_RECIPIENTS.split(",") if r.strip()]
    if not recipients:
        print("No recipients configured — skipping email.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Gold & Silver Prices – {date_str}"
    msg["From"] = GMAIL_USER
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(context=context)
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        print(f"Email sent to {len(recipients)} recipient(s).")
    except Exception as exc:
        # Don't crash the whole run just because email failed — the site
        # update below should still happen.
        print(f"Failed to send email: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Step 3: Update history.csv and prices.json
# ---------------------------------------------------------------------------
def append_history(prices: dict, date_str: str) -> None:
    os.makedirs(os.path.dirname(HISTORY_CSV), exist_ok=True)
    file_exists = os.path.isfile(HISTORY_CSV)

    with open(HISTORY_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "date",
                "gold_usd_oz", "gold_inr_10g",
                "silver_usd_oz", "silver_inr_10g",
            ])
        writer.writerow([
            date_str,
            prices["gold"]["USD"]["per_oz"], prices["gold"]["INR"]["per_10g"],
            prices["silver"]["USD"]["per_oz"], prices["silver"]["INR"]["per_10g"],
        ])


def copy_history_to_docs() -> None:
    """Mirror history.csv into docs/ so the static site can fetch it."""
    if not os.path.isfile(HISTORY_CSV):
        return
    os.makedirs(os.path.dirname(DOCS_HISTORY_CSV), exist_ok=True)
    with open(HISTORY_CSV, "r") as src, open(DOCS_HISTORY_CSV, "w") as dst:
        dst.write(src.read())


def write_prices_json(prices: dict, date_str: str, timestamp: str) -> None:
    os.makedirs(os.path.dirname(PRICES_JSON), exist_ok=True)
    payload = {
        "date": date_str,
        "updated_at": timestamp,
        "gold": prices["gold"],
        "silver": prices["silver"],
    }
    with open(PRICES_JSON, "w") as f:
        json.dump(payload, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%d %b %Y")
    timestamp = now.isoformat()

    try:
        prices = fetch_all_prices()
    except Exception as exc:
        print(f"Failed to fetch prices: {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(prices, indent=2))

    html_body = build_email_html(prices, date_str)
    send_email(html_body, date_str)

    append_history(prices, date_str)
    copy_history_to_docs()
    write_prices_json(prices, date_str, timestamp)
    print("Done.")


if __name__ == "__main__":
    main()
