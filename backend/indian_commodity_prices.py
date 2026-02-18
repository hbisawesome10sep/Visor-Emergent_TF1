"""
Fetches live Indian gold & silver prices from goodreturns.in.
Falls back to COMEX conversion if scraping fails.
"""
import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-IN,en;q=0.9",
}
TIMEOUT = 12


def _parse_inr(text: str) -> float:
    """Parse ₹1,54,200 or similar formats to float."""
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    return float(cleaned) if cleaned else 0.0


def fetch_indian_gold_price() -> dict:
    """Fetch live 24K gold price per 10 grams from goodreturns.in."""
    try:
        r = requests.get("https://www.goodreturns.in/gold-rates/", headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "lxml")

        # Look for the header ticker: "22k Gold₹ 14,135/gm"
        # and the main price: "₹15,420" for 24K per gram
        text = soup.get_text(" ", strip=True)

        # Method 1: Extract from "24K Gold /g ₹15,420" pattern
        m = re.search(r"24K\s*Gold\s*/g\s*₹\s*([\d,]+)", text)
        if m:
            price_per_gram = _parse_inr(m.group(1))
            if price_per_gram > 1000:
                price_10g = price_per_gram * 10
                # Get yesterday's price for change calculation
                change = 0.0
                m2 = re.search(r"10\s*₹\s*([\d,]+)\s*₹\s*([\d,]+)", text)
                if m2:
                    today_10g = _parse_inr(m2.group(1))
                    yesterday_10g = _parse_inr(m2.group(2))
                    if today_10g > 0 and yesterday_10g > 0:
                        change = today_10g - yesterday_10g
                        price_10g = today_10g

                logger.info(f"Gold from goodreturns: ₹{price_10g:,.0f}/10g (change: {change:+.0f})")
                return {
                    "price": price_10g,
                    "change": change,
                    "change_percent": round(change / (price_10g - change) * 100, 2) if (price_10g - change) > 0 else 0,
                    "source": "goodreturns.in",
                }

        # Method 2: Look for table with "10 | ₹1,54,200" pattern
        tables = soup.find_all("table")
        for table in tables:
            for row in table.find_all("tr"):
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) >= 2 and cells[0] == "10":
                    price_10g = _parse_inr(cells[1])
                    change = 0.0
                    if len(cells) >= 3:
                        yesterday = _parse_inr(cells[2])
                        if yesterday > 0:
                            change = price_10g - yesterday
                    if price_10g > 10000:
                        logger.info(f"Gold from goodreturns table: ₹{price_10g:,.0f}/10g")
                        return {
                            "price": price_10g,
                            "change": change,
                            "change_percent": round(change / (price_10g - change) * 100, 2) if (price_10g - change) > 0 else 0,
                            "source": "goodreturns.in",
                        }

    except Exception as e:
        logger.warning(f"Gold scrape failed: {e}")

    return {}


def fetch_indian_silver_price() -> dict:
    """Fetch live silver price per 1 kg from goodreturns.in."""
    try:
        r = requests.get("https://www.goodreturns.in/silver-rates/", headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.get_text(" ", strip=True)

        # Method 1: Header ticker "Silver₹ 2,55,000/kg"
        m = re.search(r"Silver\s*₹\s*([\d,]+)\s*/kg", text)
        if m:
            price_kg = _parse_inr(m.group(1))
            if price_kg > 10000:
                logger.info(f"Silver from goodreturns header: ₹{price_kg:,.0f}/kg")
                return {
                    "price": price_kg,
                    "change": 0.0,
                    "change_percent": 0.0,
                    "source": "goodreturns.in",
                }

        # Method 2: Table with "1 Kg" or "1Kg" row
        tables = soup.find_all("table")
        for table in tables:
            for row in table.find_all("tr"):
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) >= 2:
                    label = cells[0].lower().replace(" ", "")
                    if "1kg" in label or label == "1":
                        price_kg = _parse_inr(cells[1])
                        change = 0.0
                        if len(cells) >= 3:
                            yesterday = _parse_inr(cells[2])
                            if yesterday > 0:
                                change = price_kg - yesterday
                        if price_kg > 10000:
                            logger.info(f"Silver from goodreturns table: ₹{price_kg:,.0f}/kg")
                            return {
                                "price": price_kg,
                                "change": change,
                                "change_percent": round(change / (price_kg - change) * 100, 2) if (price_kg - change) > 0 else 0,
                                "source": "goodreturns.in",
                            }

    except Exception as e:
        logger.warning(f"Silver scrape failed: {e}")

    return {}
