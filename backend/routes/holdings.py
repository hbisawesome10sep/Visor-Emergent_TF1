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


@router.delete("/holdings/clear-all")
async def clear_all_holdings(user=Depends(get_current_user)):
    """Delete all holdings for the current user."""
    result = await db.holdings.delete_many({"user_id": user["id"]})
    return {"message": f"Deleted {result.deleted_count} holding(s)", "deleted": result.deleted_count}


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


@router.get("/holdings/live")
async def get_holdings_live(user=Depends(get_current_user)):
    return await get_holdings(user=user)


@router.put("/holdings/{holding_id}")
async def update_holding(holding_id: str, holding: HoldingCreate, user=Depends(get_current_user)):
    existing = await db.holdings.find_one({"_id": ObjectId(holding_id), "user_id": user["id"]})
    if not existing:
        raise HTTPException(404, "Holding not found")
    update_data = {
        "name": holding.name, "ticker": holding.ticker, "isin": holding.isin,
        "category": holding.category, "quantity": holding.quantity,
        "buy_price": holding.buy_price, "buy_date": holding.buy_date,
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


@router.post("/holdings/refresh-prices")
async def refresh_holdings_prices(user=Depends(get_current_user)):
    """Fetch live prices for all holdings (stocks via yfinance, MFs via mfapi.in) and update DB."""
    import asyncio
    from services.holdings_price_updater import fetch_stock_prices, fetch_mf_prices

    holdings = []
    cursor = db.holdings.find({"user_id": user["id"]})
    async for doc in cursor:
        mongo_id = doc["_id"]
        doc["id"] = doc.get("id") or str(mongo_id)
        doc["_mongo_id"] = mongo_id  # Keep for DB update
        doc.pop("_id", None)
        holdings.append(doc)

    if not holdings:
        return {"message": "No holdings to update", "updated": 0}

    stocks = [h for h in holdings if h.get("category") == "Stock"]
    mfs = [h for h in holdings if h.get("category") == "Mutual Fund"]

    loop = asyncio.get_running_loop()
    stock_prices, mf_navs = {}, {}

    if stocks:
        stock_prices = await loop.run_in_executor(_yf_executor, fetch_stock_prices, stocks)
    if mfs:
        mf_navs = await loop.run_in_executor(_yf_executor, fetch_mf_prices, mfs)

    updated = 0
    now = datetime.now(timezone.utc).isoformat()

    for h in holdings:
        hid = h["id"]
        qty = h.get("quantity", 0)
        invested = h.get("invested_value", 0) or (qty * h.get("buy_price", 0))
        new_price = None

        if hid in stock_prices:
            new_price = stock_prices[hid]["price"]
        elif hid in mf_navs:
            new_price = mf_navs[hid]

        if new_price and new_price > 0:
            current_value = round(qty * new_price, 2)
            gain_loss = round(current_value - invested, 2)
            gain_loss_pct = round((gain_loss / invested) * 100, 2) if invested else 0

            await db.holdings.update_one(
                {"_id": h["_mongo_id"]},
                {"$set": {
                    "current_price": round(new_price, 4),
                    "current_value": current_value,
                    "gain_loss": gain_loss,
                    "gain_loss_pct": gain_loss_pct,
                    "price_updated_at": now,
                }},
            )
            updated += 1

    return {
        "message": f"Updated prices for {updated} of {len(holdings)} holdings",
        "updated": updated,
        "total": len(holdings),
        "stocks_updated": len(stock_prices),
        "mfs_updated": len(mf_navs),
    }


@router.post("/holdings/upload-cas")
async def upload_cas(
    file: UploadFile = File(...),
    password: str = Form(default=""),
    user=Depends(get_current_user),
):
    """Parse CAMS/NSDL eCAS PDF and import MF holdings. Also detects SIP funds."""
    content = await file.read()
    pdf_stream = io.BytesIO(content)

    try:
        with pdfplumber.open(pdf_stream, password=password if password else None) as pdf:
            text = ""
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        raise HTTPException(400, "Could not open PDF. Please check the password and try again.")

    holdings, detected_sip_names = _parse_cas_text(text)

    if not holdings:
        raise HTTPException(422, "No mutual fund holdings found in this PDF. Please ensure it is a valid CAMS/NSDL eCAS statement.")

    imported_count = 0
    for h in holdings:
        existing = await db.holdings.find_one({
            "user_id": user["id"],
            "isin": h["isin"],
        })
        if existing:
            await db.holdings.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "name": h["name"],
                    "quantity": h["quantity"],
                    "buy_price": h.get("nav", existing.get("buy_price", 0)),
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
                "ticker": "",
                "category": "Mutual Fund",
                "quantity": h["quantity"],
                "buy_price": h.get("nav", 0),
                "buy_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "invested_value": h.get("invested_value", 0),
                "current_value": h.get("current_value", 0),
                "source": "eCAS",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        imported_count += 1

    # Save SIP suggestions (upsert by user+name)
    saved_sip_suggestions = []
    for name in detected_sip_names:
        isin = next((h["isin"] for h in holdings if h["name"] == name), "")
        existing_sug = await db.sip_suggestions.find_one({
            "user_id": user["id"],
            "fund_name": name,
            "status": "pending",
        })
        if not existing_sug:
            result = await db.sip_suggestions.insert_one({
                "user_id": user["id"],
                "fund_name": name,
                "isin": isin,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            saved_sip_suggestions.append({
                "id": str(result.inserted_id),
                "fund_name": name,
                "isin": isin,
                "status": "pending",
            })
        else:
            saved_sip_suggestions.append({
                "id": str(existing_sug["_id"]),
                "fund_name": existing_sug["fund_name"],
                "isin": existing_sug.get("isin", ""),
                "status": "pending",
            })

    return {
        "imported": imported_count,
        "message": f"Successfully imported {imported_count} mutual fund holding{'s' if imported_count != 1 else ''} from your eCAS statement.",
        "detected_sips": saved_sip_suggestions,
        "sip_count": len(saved_sip_suggestions),
    }


# ── SIP Suggestions endpoints ──────────────────────────────────────────────

@router.get("/sip-suggestions")
async def get_sip_suggestions(user=Depends(get_current_user)):
    """Get all pending SIP suggestions detected from eCAS uploads."""
    suggestions = []
    cursor = db.sip_suggestions.find({"user_id": user["id"], "status": "pending"})
    async for doc in cursor:
        suggestions.append({
            "id": str(doc.pop("_id")),
            "fund_name": doc["fund_name"],
            "isin": doc.get("isin", ""),
            "status": doc["status"],
            "created_at": doc.get("created_at", ""),
        })
    return {"suggestions": suggestions}


@router.delete("/sip-suggestions/{suggestion_id}")
async def dismiss_sip_suggestion(suggestion_id: str, user=Depends(get_current_user)):
    """Decline/dismiss a SIP suggestion."""
    result = await db.sip_suggestions.delete_one({
        "_id": ObjectId(suggestion_id),
        "user_id": user["id"],
    })
    if result.deleted_count == 0:
        raise HTTPException(404, "Suggestion not found")
    return {"message": "Suggestion dismissed"}


@router.post("/sip-suggestions/{suggestion_id}/approve")
async def approve_sip_suggestion(suggestion_id: str, user=Depends(get_current_user)):
    """Mark a SIP suggestion as approved (frontend opens Add SIP modal)."""
    await db.sip_suggestions.update_one(
        {"_id": ObjectId(suggestion_id), "user_id": user["id"]},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"message": "Suggestion approved"}


def _parse_cas_text(text: str) -> tuple:
    """
    Parse CAMS/NSDL eCAS PDF text.
    Returns (holdings_list, sip_fund_names_list)

    eCAS format:
    Account Details section:
      AMC Name : HDFC Mutual Fund
      Scheme Name : HDFC Flexi Cap Fund - Direct Plan - Growth Option Scheme Code : 02T
      ISIN : INF179K01UT0 UCC : MFHDFC0019 RTA : CAMS

    Transaction section (per fund):
      HDFC Mutual Fund
      02T - HDFC Flexi Cap Fund - Direct Plan - Growth Option
      ISIN : INF179K01UT0 UCC : MFHDFC0019
      Opening Balance 7.166
      29-12-2025 999.95 2251.607 2251.607 .444 .05 0 0    <- Date Amount NAV NAV Units Stamp 0 0
      Closing Balance 7.61

      SIP entry example:
      SIP Purchase-BSE -
      Instalment No - 3/999 -
      29-12-2025 1699.92 126.2 126.2 13.47 .08 0 0
    """
    # Clean: strip non-ASCII chars that come from mixed-encoding Devanagari PDFs
    raw_lines = text.split("\n")
    lines = []
    for raw in raw_lines:
        clean = re.sub(r"[^\x20-\x7E]", "", raw).strip()
        if clean:
            lines.append(clean)

    # ── Phase 1: Build fund name map from AMC Name / Scheme Name / ISIN blocks ──
    funds_by_isin = {}  # isin -> cleaned scheme name
    i = 0
    while i < len(lines):
        if lines[i].startswith("AMC Name :"):
            scheme_name = None
            isin = None
            for j in range(i + 1, min(i + 12, len(lines))):
                if lines[j].startswith("Scheme Name :"):
                    sn = lines[j].replace("Scheme Name :", "").strip()
                    # Remove "Scheme Code : XXXX" suffix
                    sn = re.sub(r"\s*Scheme Code\s*:\s*\S+\s*$", "", sn).strip()
                    # Remove trailing plan codes like "- Direct Plan" duplication
                    scheme_name = sn if sn else None
                elif "ISIN :" in lines[j]:
                    m = re.search(r"(INF[A-Z0-9]{9,10})", lines[j])
                    if m:
                        isin = m.group(1)
                        break
            if scheme_name and isin and isin not in funds_by_isin:
                funds_by_isin[isin] = scheme_name
        i += 1

    # ── Phase 2: Extract transactions — closing balances, NAV, SIP detection, invested amounts ──
    holdings_data = {}   # isin -> {quantity, nav, is_sip, opening_units, total_purchase_amount, first_nav}
    sip_isins = set()
    current_isin = None
    last_nav = 0.0
    pending_sip = False   # True when we've seen a SIP keyword before the date line
    pending_purchase = False  # True when we've seen a purchase keyword before the date line

    SIP_KEYWORDS = [
        "sip purchase", "systematic investment", "sys. investment",
        "purchase - systematic", "sip instalment", "sip - purchase",
        "sip purchase-bse", "sip purchase-nse",
    ]
    PURCHASE_KEYWORDS = [
        "purchase", "systematic investment", "sys. investment",
        "switch in", "fresh purchase", "new purchase", "additional purchase",
    ]
    REDEMPTION_KEYWORDS = [
        "redemption", "switch out", "switch-out", "withdrawal",
    ]
    DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}\s")

    i = 0
    while i < len(lines):
        line = lines[i]
        line_lower = line.lower()

        # ISIN line in transaction section: "ISIN : INF... UCC : ..."
        if "ISIN :" in line and "UCC" in line:
            m = re.search(r"(INF[A-Z0-9]{9,10})", line)
            if m:
                current_isin = m.group(1)
                last_nav = 0.0
                pending_sip = False
                pending_purchase = False
                if current_isin not in holdings_data:
                    holdings_data[current_isin] = {
                        "quantity": 0.0, "nav": 0.0, "is_sip": False,
                        "opening_units": 0.0, "total_purchase_amount": 0.0, "first_nav": 0.0,
                    }

        if current_isin:
            # Detect SIP transaction type keywords (may appear 1-2 lines before the date line)
            if any(kw in line_lower for kw in SIP_KEYWORDS):
                pending_sip = True
                pending_purchase = True  # SIP is a type of purchase

            # Detect general purchase keywords (broader than SIP)
            elif any(kw in line_lower for kw in PURCHASE_KEYWORDS):
                pending_purchase = True

            # Detect redemption keywords — cancel any pending purchase flag
            if any(kw in line_lower for kw in REDEMPTION_KEYWORDS):
                pending_purchase = False

            # Opening Balance line: "Opening Balance X.XXX"
            ob_m = re.match(r"^Opening Balance\s+([\d.]+)", line)
            if ob_m:
                holdings_data[current_isin]["opening_units"] = float(ob_m.group(1))

            # Transaction date line: DD-MM-YYYY amount NAV NAV units stamp 0 0
            if DATE_RE.match(line):
                after_date = line[10:]
                nums = re.findall(r"[\d]+(?:\.[\d]+)?", after_date)
                # Find two consecutive equal values (NAV repeated) - robust across formats
                found_nav = False
                for k in range(len(nums) - 1):
                    try:
                        v1, v2 = float(nums[k]), float(nums[k + 1])
                        if v1 == v2 and v1 > 0.5:  # NAV is always > 0.5, appears twice
                            last_nav = v1
                            found_nav = True
                            break
                    except ValueError:
                        continue
                # Fallback: use 3rd number if repeated-NAV not found
                if not found_nav and len(nums) >= 3:
                    try:
                        fallback = float(nums[2])
                        if fallback > 0.5:
                            last_nav = fallback
                    except ValueError:
                        pass

                # Record first NAV for this fund (used to estimate opening balance cost)
                if last_nav > 0 and holdings_data[current_isin]["first_nav"] == 0:
                    holdings_data[current_isin]["first_nav"] = last_nav

                # Sum purchase amounts: first number after date is the transaction amount
                if pending_purchase and nums:
                    try:
                        txn_amount = float(nums[0])
                        if txn_amount > 0:
                            holdings_data[current_isin]["total_purchase_amount"] += txn_amount
                    except ValueError:
                        pass

                if pending_sip:
                    sip_isins.add(current_isin)
                    holdings_data[current_isin]["is_sip"] = True
                    pending_sip = False
                pending_purchase = False

            # Closing Balance line
            cb_m = re.match(r"^Closing Balance\s+([\d.]+)", line)
            if cb_m:
                qty = float(cb_m.group(1))
                holdings_data[current_isin]["quantity"] = qty
                if last_nav > 0:
                    holdings_data[current_isin]["nav"] = last_nav
                current_isin = None  # reset after capturing

        i += 1

    # ── Merge Phase 1 (names) + Phase 2 (quantities + invested amounts) ──
    result_holdings = []
    for isin, data in holdings_data.items():
        if data["quantity"] <= 0:
            continue
        name = funds_by_isin.get(isin, f"Mutual Fund ({isin})")
        nav = data["nav"]
        qty = data["quantity"]
        current_value = round(qty * nav, 2) if nav > 0 else 0.0

        # Calculate invested_value from parsed transaction amounts
        total_purchase = data["total_purchase_amount"]
        opening_units = data["opening_units"]
        first_nav = data["first_nav"] or nav

        # Estimate cost of opening balance units using earliest available NAV
        opening_cost = round(opening_units * first_nav, 2) if opening_units > 0 and first_nav > 0 else 0.0
        invested_value = round(total_purchase + opening_cost, 2)

        # Fallback: if no transactions were detected but we have units, use NAV as estimate
        if invested_value <= 0 and qty > 0 and nav > 0:
            invested_value = current_value

        result_holdings.append({
            "name": name,
            "isin": isin,
            "quantity": qty,
            "nav": nav,
            "current_value": current_value,
            "invested_value": invested_value,
            "category": "Mutual Fund",
            "is_sip": data["is_sip"],
        })

    detected_sip_names = [h["name"] for h in result_holdings if h["is_sip"]]

    logger.info(f"eCAS parse: {len(result_holdings)} holdings, {len(detected_sip_names)} SIPs detected")
    return result_holdings, detected_sip_names
