from fastapi import APIRouter, Depends
from database import db
from auth import get_current_user
from config import GOLDAPI_KEY, REFRESH_TIMES_IST, TROY_OZ_TO_GRAMS, GOLD_DOMESTIC_PREMIUM, SILVER_DOMESTIC_PREMIUM
from datetime import datetime, timezone, timedelta
import asyncio
import logging
import requests
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

_yf_executor = ThreadPoolExecutor(max_workers=2)


def _fetch_goldapi_prices() -> dict:
    """Fetch gold & silver spot prices in INR from GoldAPI.io (most accurate)."""
    result = {}
    if not GOLDAPI_KEY:
        return result
    headers = {"x-access-token": GOLDAPI_KEY, "Content-Type": "application/json"}

    try:
        r = requests.get("https://www.goldapi.io/api/XAU/INR", headers=headers, timeout=10)
        if r.status_code == 200:
            d = r.json()
            gram_24k = d.get("price_gram_24k", 0)
            prev_gram = d.get("prev_close_price", 0) / TROY_OZ_TO_GRAMS if d.get("prev_close_price") else 0
            if gram_24k > 0:
                price_10g = round(gram_24k * 10 * GOLD_DOMESTIC_PREMIUM, 0)
                prev_10g = round(prev_gram * 10 * GOLD_DOMESTIC_PREMIUM, 0) if prev_gram > 0 else price_10g
                change = round(price_10g - prev_10g, 0)
                change_pct = round(change / prev_10g * 100, 2) if prev_10g > 0 else 0
                result["gold"] = {
                    "price": price_10g, "change": change, "change_percent": change_pct,
                    "prev_close": prev_10g, "source": "goldapi.io"
                }
                logger.info(f"GoldAPI: Gold 10g = ₹{price_10g:,.0f}")
    except Exception as e:
        logger.warning(f"GoldAPI gold fetch failed: {e}")

    try:
        r = requests.get("https://www.goldapi.io/api/XAG/INR", headers=headers, timeout=10)
        if r.status_code == 200:
            d = r.json()
            price_oz = d.get("price", 0)
            prev_oz = d.get("prev_close_price", 0)
            if price_oz > 0:
                price_per_gram = price_oz / TROY_OZ_TO_GRAMS
                price_kg = round(price_per_gram * 1000 * SILVER_DOMESTIC_PREMIUM, 0)
                prev_per_gram = prev_oz / TROY_OZ_TO_GRAMS if prev_oz > 0 else 0
                prev_kg = round(prev_per_gram * 1000 * SILVER_DOMESTIC_PREMIUM, 0) if prev_per_gram > 0 else price_kg
                change = round(price_kg - prev_kg, 0)
                change_pct = round(change / prev_kg * 100, 2) if prev_kg > 0 else 0
                result["silver"] = {
                    "price": price_kg, "change": change, "change_percent": change_pct,
                    "prev_close": prev_kg, "source": "goldapi.io"
                }
                logger.info(f"GoldAPI: Silver 1Kg = ₹{price_kg:,.0f}")
    except Exception as e:
        logger.warning(f"GoldAPI silver fetch failed: {e}")

    return result


def _fetch_yfinance_data() -> list:
    """Synchronous yfinance fetch — runs in thread executor. Uses GoldAPI for gold/silver when available."""
    results = []
    goldapi_data = _fetch_goldapi_prices()

    try:
        tickers = yf.Tickers("^NSEI ^BSESN ^NSEBANK GC=F SI=F INR=X")
        usd_inr = 87.0
        try:
            fx = tickers.tickers["INR=X"].fast_info
            usd_inr = float(fx.last_price) if fx.last_price else 87.0
        except Exception:
            pass

        configs = [
            {"key": "nifty_50", "name": "Nifty 50", "yf": "^NSEI", "type": "index"},
            {"key": "sensex", "name": "SENSEX", "yf": "^BSESN", "type": "index"},
            {"key": "nifty_bank", "name": "Nifty Bank", "yf": "^NSEBANK", "type": "index"},
            {"key": "gold_10g", "name": "Gold (10g)", "yf": "GC=F", "type": "gold"},
            {"key": "silver_1kg", "name": "Silver (1Kg)", "yf": "SI=F", "type": "silver"},
        ]

        for cfg in configs:
            try:
                if cfg["type"] == "gold" and "gold" in goldapi_data:
                    gd = goldapi_data["gold"]
                    results.append({"key": cfg["key"], "name": cfg["name"], "price": gd["price"],
                                    "change": gd["change"], "change_percent": gd["change_percent"],
                                    "prev_close": gd["prev_close"]})
                    continue
                if cfg["type"] == "silver" and "silver" in goldapi_data:
                    sd = goldapi_data["silver"]
                    results.append({"key": cfg["key"], "name": cfg["name"], "price": sd["price"],
                                    "change": sd["change"], "change_percent": sd["change_percent"],
                                    "prev_close": sd["prev_close"]})
                    continue

                t = tickers.tickers[cfg["yf"]]
                info = t.fast_info
                last = float(info.last_price) if info.last_price else 0
                prev = float(info.previous_close) if info.previous_close else 0

                if cfg["type"] == "gold":
                    price_per_gram = (last / TROY_OZ_TO_GRAMS) * usd_inr * GOLD_DOMESTIC_PREMIUM
                    price = round(price_per_gram * 10, 0)
                    prev_price_per_gram = (prev / TROY_OZ_TO_GRAMS) * usd_inr * GOLD_DOMESTIC_PREMIUM
                    prev_price = round(prev_price_per_gram * 10, 0)
                    change = round(price - prev_price, 0)
                    change_pct = round((change / prev_price * 100), 2) if prev_price else 0
                    results.append({"key": cfg["key"], "name": cfg["name"], "price": price, "change": change, "change_percent": change_pct, "prev_close": prev_price})
                elif cfg["type"] == "silver":
                    price_per_kg = (last * (1000 / TROY_OZ_TO_GRAMS)) * usd_inr * SILVER_DOMESTIC_PREMIUM
                    price = round(price_per_kg, 0)
                    prev_per_kg = (prev * (1000 / TROY_OZ_TO_GRAMS)) * usd_inr * SILVER_DOMESTIC_PREMIUM
                    prev_price = round(prev_per_kg, 0)
                    change = round(price - prev_price, 0)
                    change_pct = round((change / prev_price * 100), 2) if prev_price else 0
                    results.append({"key": cfg["key"], "name": cfg["name"], "price": price, "change": change, "change_percent": change_pct, "prev_close": prev_price})
                else:
                    price = round(last, 2)
                    change = round(last - prev, 2)
                    change_pct = round((change / prev * 100), 2) if prev else 0
                    results.append({"key": cfg["key"], "name": cfg["name"], "price": price, "change": change, "change_percent": change_pct, "prev_close": round(prev, 2)})
            except Exception as e:
                logger.error(f"yfinance fetch error for {cfg['key']}: {e}")
    except Exception as e:
        logger.error(f"yfinance batch fetch error: {e}")
    return results


async def refresh_all_market_data():
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(_yf_executor, _fetch_yfinance_data)
    now = datetime.now(timezone.utc).isoformat()
    for item in results:
        if item.get("price"):
            item["last_updated"] = now
            await db.market_data.update_one({"key": item["key"]}, {"$set": item}, upsert=True)
            logger.info(f"Market LIVE: {item['name']} = {item['price']}")
    return results


async def market_data_scheduler():
    last_refresh = None
    while True:
        utc_now = datetime.now(timezone.utc)
        ist_now = utc_now + timedelta(hours=5, minutes=30)
        ist_hhmm = ist_now.strftime("%H:%M")
        if ist_hhmm in REFRESH_TIMES_IST and last_refresh != ist_hhmm:
            logger.info(f"Scheduled market refresh at IST {ist_hhmm}")
            last_refresh = ist_hhmm
            await refresh_all_market_data()
        await asyncio.sleep(30)


async def seed_market_data():
    """Seed with live data from yfinance, or use accurate fallback values."""
    await db.market_data.delete_many({})
    logger.info("Fetching live market data for seed...")
    results = await refresh_all_market_data()
    if not results or len(results) < 5:
        logger.warning("Live fetch incomplete, using accurate fallback seed data")
        now = datetime.now(timezone.utc).isoformat()
        fallback = [
            {"key": "nifty_50", "name": "Nifty 50", "price": 25734.20, "change": 51.75, "change_percent": 0.20, "prev_close": 25682.45, "last_updated": now},
            {"key": "sensex", "name": "SENSEX", "price": 83389.45, "change": 112.39, "change_percent": 0.13, "prev_close": 83277.06, "last_updated": now},
            {"key": "nifty_bank", "name": "Nifty Bank", "price": 61126.95, "change": 133.10, "change_percent": 0.22, "prev_close": 60993.85, "last_updated": now},
            {"key": "gold_10g", "name": "Gold (10g)", "price": 154910.0, "change": -1530.0, "change_percent": -0.98, "prev_close": 156440.0, "last_updated": now},
            {"key": "silver_1kg", "name": "Silver (1Kg)", "price": 260000.0, "change": -8000.0, "change_percent": -2.99, "prev_close": 268000.0, "last_updated": now},
        ]
        for s in fallback:
            await db.market_data.update_one({"key": s["key"]}, {"$set": s}, upsert=True)
    logger.info("Market data seeded successfully")


@router.get("/market-data")
async def get_market_data(force: bool = False):
    """Return market data, refreshing from yfinance if stale (>2 min) or forced."""
    data = await db.market_data.find({}, {"_id": 0}).to_list(10)

    is_stale = True
    if data and not force:
        last_updated = data[0].get("last_updated", "")
        if last_updated:
            try:
                from dateutil.parser import parse as parse_date
                updated_dt = parse_date(last_updated)
                if updated_dt.tzinfo is None:
                    updated_dt = updated_dt.replace(tzinfo=timezone.utc)
                age_seconds = (datetime.now(timezone.utc) - updated_dt).total_seconds()
                is_stale = age_seconds > 120
            except Exception:
                pass

    if is_stale or force:
        logger.info("Market data stale or force refresh, fetching live prices...")
        fresh = await refresh_all_market_data()
        if fresh:
            data = await db.market_data.find({}, {"_id": 0}).to_list(10)

    return data


@router.post("/market-data/refresh")
async def trigger_market_refresh(user=Depends(get_current_user)):
    asyncio.create_task(refresh_all_market_data())
    return {"message": "Market data refresh triggered"}
