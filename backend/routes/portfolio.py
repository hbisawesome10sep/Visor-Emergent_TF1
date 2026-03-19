from fastapi import APIRouter, Depends
from database import db
from auth import get_current_user
from routes.holdings import _fetch_live_prices
from datetime import datetime, timezone
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

_yf_executor = ThreadPoolExecutor(max_workers=2)

CATEGORY_RETURNS = {
    # Equity-linked (Nifty-tracked estimate)
    "Stocks": "nifty", "Stock": "nifty",
    "SIP": "nifty", "Mutual Funds": "nifty", "Mutual Fund": "nifty",
    "ETFs": "nifty", "ETF": "nifty", "ELSS": "nifty",
    # Gold / Silver
    "Gold": "gold", "Sovereign Gold Bond": "gold",
    "Silver": "silver",
    # Fixed-return instruments
    "PPF": 0.071, "EPF": 0.0815, "NPS": 0.10,
    "FD": 0.07, "Fixed Deposit": 0.07,
    "Bonds": 0.075, "ULIP": 0.08, "Real Estate": 0.08, "Crypto": 0.0,
}


def _compute_portfolio_values(transactions: list, market_data: dict) -> dict:
    """Compute estimated current value for each investment category."""
    from datetime import date as dt_date
    today = dt_date.today()
    categories = {}
    for txn in transactions:
        cat = txn["category"]
        if cat not in categories:
            categories[cat] = {"invested": 0, "current_value": 0, "transactions": 0}
        amount = txn["amount"]
        categories[cat]["invested"] += amount
        categories[cat]["transactions"] += 1
        try:
            parts = txn["date"].split("-")
            txn_date = dt_date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            txn_date = today
        days_held = max((today - txn_date).days, 0)
        return_type = CATEGORY_RETURNS.get(cat, 0.0)
        if return_type == "nifty":
            nifty_now = market_data.get("nifty_50", {}).get("price", 0)
            nifty_prev = market_data.get("nifty_50", {}).get("prev_close", nifty_now)
            if nifty_now and nifty_prev:
                daily_return = (nifty_now / nifty_prev - 1) if nifty_prev else 0
                estimated_return = daily_return * days_held * 0.6
                categories[cat]["current_value"] += amount * (1 + estimated_return)
            else:
                categories[cat]["current_value"] += amount
        elif return_type == "gold":
            gold_now = market_data.get("gold_10g", {}).get("price", 0)
            gold_prev = market_data.get("gold_10g", {}).get("prev_close", gold_now)
            if gold_now and gold_prev:
                daily_return = (gold_now / gold_prev - 1) if gold_prev else 0
                estimated_return = daily_return * days_held * 0.5
                categories[cat]["current_value"] += amount * (1 + estimated_return)
            else:
                categories[cat]["current_value"] += amount
        elif return_type == "silver":
            silver_now = market_data.get("silver_1kg", {}).get("price", 0)
            silver_prev = market_data.get("silver_1kg", {}).get("prev_close", silver_now)
            if silver_now and silver_prev:
                daily_return = (silver_now / silver_prev - 1) if silver_prev else 0
                estimated_return = daily_return * days_held * 0.5
                categories[cat]["current_value"] += amount * (1 + estimated_return)
            else:
                categories[cat]["current_value"] += amount
        elif isinstance(return_type, (int, float)):
            annual_rate = return_type
            pro_rated = annual_rate * (days_held / 365)
            categories[cat]["current_value"] += amount * (1 + pro_rated)
        else:
            categories[cat]["current_value"] += amount
    for cat in categories:
        categories[cat]["invested"] = round(categories[cat]["invested"], 2)
        categories[cat]["current_value"] = round(categories[cat]["current_value"], 2)
        inv = categories[cat]["invested"]
        cur = categories[cat]["current_value"]
        categories[cat]["gain_loss"] = round(cur - inv, 2)
        categories[cat]["gain_loss_pct"] = round(((cur - inv) / inv * 100), 2) if inv else 0
    return categories


@router.get("/portfolio-overview")
async def get_portfolio_overview(user=Depends(get_current_user)):
    """Portfolio overview based ONLY on real holdings (not transaction estimates)."""
    holdings_cursor = db.holdings.find({"user_id": user["id"]})
    holdings_list = []
    async for doc in holdings_cursor:
        doc["id"] = str(doc.pop("_id"))
        holdings_list.append(doc)

    if not holdings_list:
        return {
            "total_invested": 0,
            "total_current_value": 0,
            "total_gain_loss": 0,
            "total_gain_loss_pct": 0,
            "categories": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    loop = asyncio.get_running_loop()
    tickers = list(set(h["ticker"] for h in holdings_list if h.get("ticker")))
    prices = await loop.run_in_executor(_yf_executor, _fetch_live_prices, tickers) if tickers else {}

    categories = {}
    for h in holdings_list:
        cat = h.get("category", "Stock")
        invested = h.get("invested_value", 0) or (h["quantity"] * h["buy_price"])
        stored_current = h.get("current_value", 0)

        if h.get("ticker") and h["ticker"] in prices and prices[h["ticker"]]["price"] > 0:
            current_value = h["quantity"] * prices[h["ticker"]]["price"]
        elif stored_current > 0:
            current_value = stored_current
        else:
            current_value = invested

        if cat not in categories:
            categories[cat] = {"invested": 0, "current_value": 0, "gain_loss": 0, "gain_loss_pct": 0, "transactions": 0}
        categories[cat]["invested"] = round(categories[cat]["invested"] + invested, 2)
        categories[cat]["current_value"] = round(categories[cat]["current_value"] + current_value, 2)
        categories[cat]["transactions"] += 1

    for cat_key in categories:
        inv = categories[cat_key]["invested"]
        cur = categories[cat_key]["current_value"]
        categories[cat_key]["gain_loss"] = round(cur - inv, 2)
        categories[cat_key]["gain_loss_pct"] = round((cur - inv) / inv * 100, 2) if inv else 0

    total_invested = sum(c["invested"] for c in categories.values())
    total_current = sum(c["current_value"] for c in categories.values())
    total_gain = round(total_current - total_invested, 2)
    total_gain_pct = round((total_gain / total_invested * 100), 2) if total_invested else 0
    breakdown = []
    for cat, data in sorted(categories.items(), key=lambda x: x[1]["invested"], reverse=True):
        breakdown.append({
            "category": cat,
            "invested": data["invested"],
            "current_value": data["current_value"],
            "gain_loss": data["gain_loss"],
            "gain_loss_pct": data["gain_loss_pct"],
            "transactions": data["transactions"],
        })
    return {
        "total_invested": total_invested,
        "total_current_value": round(total_current, 2),
        "total_gain_loss": total_gain,
        "total_gain_loss_pct": total_gain_pct,
        "categories": breakdown,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/portfolio-rebalancing")
async def get_portfolio_rebalancing(user=Depends(get_current_user)):
    """Get portfolio rebalancing suggestions based on risk profile."""
    risk = await db.risk_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    risk_profile = risk.get("profile", "Moderate") if risk else "Moderate"

    # Target allocation per risk profile
    targets = {
        "Conservative": {"Equity": 20, "Debt": 50, "Gold": 15, "Cash": 15},
        "Moderate": {"Equity": 40, "Debt": 30, "Gold": 15, "Cash": 15},
        "Aggressive": {"Equity": 60, "Debt": 20, "Gold": 10, "Cash": 10},
        "Very Aggressive": {"Equity": 75, "Debt": 10, "Gold": 5, "Cash": 10},
    }
    target = targets.get(risk_profile, targets["Moderate"])

    # Get current allocation from portfolio
    portfolio = await get_portfolio_overview(user=user)
    total = portfolio["total_current_value"] or 1
    equity_cats = {"Stock", "Stocks", "Mutual Fund", "Mutual Funds", "SIP", "ETFs", "ELSS", "NPS"}
    debt_cats = {"FD", "Fixed Deposit", "PPF", "EPF", "Bonds", "ULIP"}
    gold_cats = {"Gold", "Sovereign Gold Bond", "Silver"}

    current = {"Equity": 0, "Debt": 0, "Gold": 0, "Cash": 0}
    for cat in portfolio.get("categories", []):
        name = cat["category"]
        val = cat["current_value"]
        if name in equity_cats:
            current["Equity"] += val
        elif name in debt_cats:
            current["Debt"] += val
        elif name in gold_cats:
            current["Gold"] += val
        else:
            current["Cash"] += val

    suggestions = []
    for asset_class, target_pct in target.items():
        current_val = current.get(asset_class, 0)
        current_pct = round((current_val / total) * 100, 1) if total > 0 else 0
        diff = round(target_pct - current_pct, 1)
        if abs(diff) > 2:
            action = "increase" if diff > 0 else "decrease"
            suggestions.append({
                "asset_class": asset_class,
                "current_pct": current_pct,
                "target_pct": target_pct,
                "diff": diff,
                "action": action,
                "amount": round(abs(diff / 100) * total, 2),
            })

    return {
        "risk_profile": risk_profile,
        "target_allocation": target,
        "current_allocation": {k: round((v / total) * 100, 1) if total > 0 else 0 for k, v in current.items()},
        "suggestions": suggestions,
        "total_portfolio_value": round(total, 2),
    }

