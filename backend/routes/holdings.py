from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from database import db
from auth import get_current_user
from models import HoldingCreate
from bson import ObjectId
from datetime import datetime, timezone
import logging
import pdfplumber
import re
import io
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

_yf_executor = ThreadPoolExecutor(max_workers=2)


def _fetch_live_prices(tickers: list) -> dict:
    """Fetch live prices for a list of tickers via yfinance."""
    result = {}
    if not tickers:
        return result
    try:
        batch = yf.Tickers(" ".join(tickers))
        for t_str in tickers:
            try:
                info = batch.tickers[t_str].fast_info
                price = float(info.last_price) if info.last_price else 0
                prev = float(info.previous_close) if info.previous_close else 0
                result[t_str] = {"price": price, "prev_close": prev}
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Batch price fetch error: {e}")
    return result


def _search_ticker(name: str, category: str) -> str:
    """Try to find a Yahoo Finance ticker for a given name."""
    try:
        suffix = ".NS"
        clean = re.sub(r'[^a-zA-Z0-9 ]', '', name).strip()
        search = yf.Ticker(clean.split()[0].upper() + suffix)
        if search.fast_info.last_price:
            return clean.split()[0].upper() + suffix
    except Exception:
        pass
    return ""


@router.post("/holdings")
async def add_holding(holding: HoldingCreate, user=Depends(get_current_user)):
    doc = {
        "user_id": user["id"],
        "name": holding.name,
        "ticker": holding.ticker,
        "isin": holding.isin,
        "category": holding.category,
        "quantity": holding.quantity,
        "buy_price": holding.buy_price,
        "buy_date": holding.buy_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "manual",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.holdings.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


@router.get("/holdings")
async def get_holdings(user=Depends(get_current_user)):
    holdings = []
    cursor = db.holdings.find({"user_id": user["id"]})
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        holdings.append(doc)

    tickers = list(set(h["ticker"] for h in holdings if h.get("ticker")))
    prices = {}
    if tickers:
        import asyncio
        loop = asyncio.get_running_loop()
        prices = await loop.run_in_executor(_yf_executor, _fetch_live_prices, tickers)

    for h in holdings:
        invested = h.get("invested_value", 0) or (h["quantity"] * h["buy_price"])
        stored_current = h.get("current_value", 0)
        if stored_current > 0:
            current_value = stored_current
        elif h.get("ticker") and h["ticker"] in prices:
            current_value = h["quantity"] * prices[h["ticker"]]["price"]
        else:
            current_value = invested
        h["invested_value"] = round(invested, 2)
        h["current_value"] = round(current_value, 2)
        h["gain_loss"] = round(current_value - invested, 2)
        h["gain_loss_pct"] = round((current_value - invested) / invested * 100, 2) if invested else 0

    total_invested = sum(h["invested_value"] for h in holdings)
    total_current = sum(h["current_value"] for h in holdings)
    total_gain = total_current - total_invested
    total_gain_pct = (total_gain / total_invested * 100) if total_invested else 0

    return {
        "holdings": holdings,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2),
            "total_gain_loss": round(total_gain, 2),
            "total_gain_loss_pct": round(total_gain_pct, 2),
            "holding_count": len(holdings),
        },
    }


@router.put("/holdings/{holding_id}")
async def update_holding(holding_id: str, holding: HoldingCreate, user=Depends(get_current_user)):
    existing = await db.holdings.find_one({"_id": ObjectId(holding_id), "user_id": user["id"]})
    if not existing:
        raise HTTPException(404, "Holding not found")

    update_data = {
        "name": holding.name,
        "ticker": holding.ticker,
        "isin": holding.isin,
        "category": holding.category,
        "quantity": holding.quantity,
        "buy_price": holding.buy_price,
        "buy_date": holding.buy_date,
    }
    await db.holdings.update_one({"_id": ObjectId(holding_id)}, {"$set": update_data})
    updated = await db.holdings.find_one({"_id": ObjectId(holding_id)})
    updated["id"] = str(updated.pop("_id"))
    return updated


@router.delete("/holdings/{holding_id}")
async def delete_holding(holding_id: str, user=Depends(get_current_user)):
    result = await db.holdings.delete_one({"_id": ObjectId(holding_id), "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Holding not found")
    return {"message": "Holding deleted"}


@router.post("/holdings/upload-cas")
async def upload_cas(
    file: UploadFile = File(...),
    password: str = Form(default=""),
    user=Depends(get_current_user),
):
    """Parse CAMS/Karvy eCAS PDF and import holdings."""
    content = await file.read()
    pdf_stream = io.BytesIO(content)

    try:
        with pdfplumber.open(pdf_stream, password=password if password else None) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        raise HTTPException(400, "Could not parse PDF. Check password if encrypted.")

    holdings = _parse_cas_text(text)
    if not holdings:
        return {"imported": 0, "message": "No holdings found in PDF"}

    imported_count = 0
    for h in holdings:
        existing = await db.holdings.find_one({
            "user_id": user["id"],
            "isin": h["isin"],
            "name": h["name"],
        })
        if existing:
            await db.holdings.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "quantity": h["quantity"],
                    "invested_value": h.get("invested_value", 0),
                    "current_value": h.get("current_value", 0),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
        else:
            await db.holdings.insert_one({
                "user_id": user["id"],
                "name": h["name"],
                "isin": h["isin"],
                "ticker": h.get("ticker", ""),
                "category": h.get("category", "Mutual Fund"),
                "quantity": h["quantity"],
                "buy_price": h.get("nav", 0),
                "buy_date": h.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                "invested_value": h.get("invested_value", 0),
                "current_value": h.get("current_value", 0),
                "source": "eCAS",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        imported_count += 1

    return {"imported": imported_count, "message": f"Imported {imported_count} holdings from eCAS"}


def _parse_cas_text(text: str) -> list:
    """Parse eCAS PDF text to extract mutual fund holdings."""
    holdings = []
    lines = text.split("\n")

    current_fund = None
    isin_pattern = re.compile(r"INF[A-Z0-9]{9}")
    units_pattern = re.compile(r"(\d+[\d,]*\.?\d*)\s*Units")
    nav_pattern = re.compile(r"NAV[:\s]*₹?\s*([\d,]+\.?\d*)")
    value_pattern = re.compile(r"(?:Market\s*)?Value[:\s]*₹?\s*([\d,]+\.?\d*)")
    cost_pattern = re.compile(r"(?:Cost|Invested)[:\s]*₹?\s*([\d,]+\.?\d*)")

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        isin_match = isin_pattern.search(line)
        if isin_match:
            if current_fund and current_fund.get("quantity", 0) > 0:
                holdings.append(current_fund)
            current_fund = {
                "isin": isin_match.group(),
                "name": line[:line.find(isin_match.group())].strip() or f"Fund {isin_match.group()}",
                "quantity": 0,
                "nav": 0,
                "invested_value": 0,
                "current_value": 0,
                "category": "Mutual Fund",
            }

        if current_fund:
            units_match = units_pattern.search(line)
            if units_match:
                current_fund["quantity"] = float(units_match.group(1).replace(",", ""))

            nav_match = nav_pattern.search(line)
            if nav_match:
                current_fund["nav"] = float(nav_match.group(1).replace(",", ""))

            value_match = value_pattern.search(line)
            if value_match:
                current_fund["current_value"] = float(value_match.group(1).replace(",", ""))

            cost_match = cost_pattern.search(line)
            if cost_match:
                current_fund["invested_value"] = float(cost_match.group(1).replace(",", ""))

    if current_fund and current_fund.get("quantity", 0) > 0:
        holdings.append(current_fund)

    return holdings
