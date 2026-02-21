from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone
from database import db
from auth import get_current_user
from models import UserTaxDeductionCreate, UserTaxDeductionUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# ══════════════════════════════════════
#  TAX CONSTANTS & MAPPINGS
# ══════════════════════════════════════

TAX_SECTION_MAP = {
    "PPF": "80C", "ELSS": "80C", "NPS": "80C", "EPF": "80C",
    "Life Insurance": "80C", "FD": "80C", "Fixed Deposit": "80C", "NSC": "80C",
    "ULIP": "80C", "Sukanya Samriddhi": "80C", "Tax Saver FD": "80C",
    "Health Insurance": "80D",
    "NPS Additional": "80CCD1B",
    "Education Loan": "80E",
}
TAX_LIMITS = {"80C": 150000, "80D": 25000, "80CCD1B": 50000, "80E": 0, "80TTA": 10000}
TAX_SECTION_LABELS = {"80C": "Section 80C", "80D": "Section 80D", "80CCD1B": "Section 80CCD(1B)", "80E": "Section 80E", "80TTA": "Section 80TTA"}
TAX_SECTION_ICONS = {"80C": "shield-lock-outline", "80D": "hospital-box-outline", "80CCD1B": "cash-plus", "80E": "school-outline", "80TTA": "bank-outline"}

TAX_KEYWORD_MAP = {
    "80C": ["ppf", "public provident fund", "provident fund", "pf contribution", "pf deposit", "epf", "employee provident fund", "vpf", "voluntary provident fund", "elss", "tax saver", "tax saving mutual fund", "tax saving fund", "nps tier 1", "national pension", "pension contribution", "lic", "life insurance", "term insurance", "term plan", "endowment", "ulip", "unit linked", "nsc", "national savings certificate", "sukanya samriddhi", "ssy", "tax saver fd", "tax saving fd", "5 year fd", "5-year fd", "five year fd", "tuition fee", "tuition fees", "school fee", "school fees", "college fee", "college fees", "home loan principal", "housing loan principal", "home loan emi principal", "stamp duty", "registration charge", "property registration"],
    "80D": ["health insurance", "medical insurance", "mediclaim", "health policy", "medical premium", "health premium", "health check", "health checkup", "preventive health", "star health", "max bupa", "hdfc ergo health", "care health", "niva bupa", "arogya sanjeevani"],
    "80CCD1B": ["nps additional", "nps extra", "nps 80ccd", "nps tier i additional", "additional nps", "nps over 80c"],
    "80E": ["education loan", "student loan", "education loan interest", "study loan", "edu loan"],
    "80G": ["donation", "charity", "charitable", "pm cares", "pm relief fund", "ngo", "temple donation", "religious donation", "national defence fund", "children fund", "red cross"],
    "80GG": ["rent paid", "house rent", "rental payment"],
    "80TTA": ["savings interest", "savings account interest", "sb interest", "interest on savings"],
    "24b": ["home loan interest", "housing loan interest", "home loan emi interest", "mortgage interest"],
}

TAX_CATEGORY_DETECT = {
    "PPF": {"section": "80C", "name": "Public Provident Fund (PPF)"},
    "EPF": {"section": "80C", "name": "Employee Provident Fund (EPF)"},
    "NPS": {"section": "80C", "name": "National Pension System (NPS)"},
    "ELSS": {"section": "80C", "name": "ELSS Mutual Funds"},
    "Fixed Deposit": {"section": "80C", "name": "Tax Saver Fixed Deposit"},
    "ULIP": {"section": "80C", "name": "ULIP"},
    "Sovereign Gold Bond": {"section": "80C", "name": "Sovereign Gold Bond"},
    "Insurance": {"section": "80D", "name": "Health Insurance Premium"},
    "Education": {"section": "80C", "name": "Children's Tuition Fees"},
    "Donations": {"section": "80G", "name": "Charitable Donations"},
    "EMI": {"section": "80C", "name": "Home Loan Principal"},
    "Loan Repayment": {"section": "80C", "name": "Loan Repayment"},
}

TAX_SECTION_LIMITS = {"80C": 150000, "80D": 25000, "80CCD1B": 50000, "80E": 0, "80G": 0, "80GG": 60000, "80TTA": 10000, "24b": 200000}
TAX_SECTION_NAMES = {"80C": "Section 80C", "80D": "Section 80D", "80CCD1B": "Section 80CCD(1B)", "80E": "Section 80E", "80G": "Section 80G", "80GG": "Section 80GG", "80TTA": "Section 80TTA", "24b": "Section 24(b)"}


def get_fy_for_date(date_str: str) -> str:
    if not date_str or len(date_str) < 10:
        return ""
    try:
        year = int(date_str[:4])
        month = int(date_str[5:7])
        if month >= 4:
            return f"{year}-{(year + 1) % 100:02d}"
        else:
            return f"{year - 1}-{year % 100:02d}"
    except (ValueError, IndexError):
        return ""


def detect_tax_deduction(category: str, description: str, notes: str, txn_type: str) -> dict | None:
    search_text = f"{description} {notes or ''}".lower().strip()
    if search_text:
        for section, keywords in TAX_KEYWORD_MAP.items():
            for kw in keywords:
                if kw in search_text:
                    name = _get_deduction_name(section, kw, description)
                    return {"section": section, "name": name, "detected_from": "description"}
    if category in TAX_CATEGORY_DETECT:
        match = TAX_CATEGORY_DETECT[category]
        if category == "Insurance" and txn_type == "investment":
            return {"section": "80C", "name": "Life Insurance Premium", "detected_from": "category"}
        return {**match, "detected_from": "category"}
    return None


def _get_deduction_name(section: str, matched_keyword: str, description: str) -> str:
    name_map = {
        "80C": {"ppf": "Public Provident Fund (PPF)", "public provident fund": "Public Provident Fund (PPF)", "provident fund": "Provident Fund", "pf contribution": "PF Contribution", "pf deposit": "PF Deposit", "epf": "Employee Provident Fund (EPF)", "employee provident fund": "Employee Provident Fund (EPF)", "vpf": "Voluntary Provident Fund (VPF)", "voluntary provident fund": "Voluntary Provident Fund (VPF)", "elss": "ELSS Mutual Funds", "tax saver": "Tax Saver Investment", "tax saving": "Tax Saving Investment", "nps": "National Pension System", "national pension": "National Pension System", "lic": "Life Insurance (LIC)", "life insurance": "Life Insurance Premium", "term insurance": "Term Insurance Premium", "term plan": "Term Insurance Premium", "ulip": "ULIP", "unit linked": "ULIP", "nsc": "National Savings Certificate", "national savings certificate": "National Savings Certificate", "sukanya samriddhi": "Sukanya Samriddhi Yojana", "ssy": "Sukanya Samriddhi Yojana", "tax saver fd": "Tax Saver FD", "tax saving fd": "Tax Saver FD", "tuition fee": "Tuition Fees", "school fee": "School Fees", "college fee": "College Fees", "home loan principal": "Home Loan Principal", "housing loan principal": "Home Loan Principal", "stamp duty": "Stamp Duty & Registration"},
        "80D": {"health insurance": "Health Insurance Premium", "medical insurance": "Medical Insurance Premium", "mediclaim": "Mediclaim Premium", "health check": "Preventive Health Check-up", "health checkup": "Preventive Health Check-up", "preventive health": "Preventive Health Check-up"},
        "80CCD1B": {"nps additional": "NPS Additional Contribution", "additional nps": "NPS Additional Contribution"},
        "80E": {"education loan": "Education Loan Interest", "student loan": "Education Loan Interest", "study loan": "Education Loan Interest"},
        "80G": {"donation": "Charitable Donation", "charity": "Charitable Donation", "pm cares": "PM CARES Fund", "ngo": "NGO Donation"},
        "80GG": {"rent paid": "Rent (No HRA)", "house rent": "House Rent (No HRA)"},
        "80TTA": {"savings interest": "Savings Account Interest", "sb interest": "Savings Account Interest"},
        "24b": {"home loan interest": "Home Loan Interest", "housing loan interest": "Home Loan Interest", "mortgage interest": "Home Loan Interest"},
    }
    section_names = name_map.get(section, {})
    for kw, name in section_names.items():
        if kw in matched_keyword:
            return name
    return description[:50] if description else TAX_SECTION_NAMES.get(section, section)


async def process_auto_tax_deduction(user_id: str, txn_id: str, category: str, description: str,
                                      notes: str, txn_type: str, amount: float, date_str: str):
    detection = detect_tax_deduction(category, description, notes, txn_type)
    if not detection:
        return None
    fy = get_fy_for_date(date_str)
    if not fy:
        return None
    section = detection["section"]
    limit = TAX_SECTION_LIMITS.get(section, 0)
    doc = {
        "id": str(uuid4()), "user_id": user_id, "transaction_id": txn_id,
        "section": section, "section_label": TAX_SECTION_NAMES.get(section, section),
        "name": detection["name"], "amount": round(amount, 2), "limit": limit, "fy": fy,
        "detected_from": detection["detected_from"], "source_category": category,
        "source_description": description, "source_date": date_str,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.auto_tax_deductions.insert_one(doc)
    del doc["_id"]
    return doc


async def remove_auto_tax_deduction(user_id: str, txn_id: str):
    await db.auto_tax_deductions.delete_many({"user_id": user_id, "transaction_id": txn_id})


async def update_auto_tax_deduction(user_id: str, txn_id: str, category: str, description: str,
                                     notes: str, txn_type: str, amount: float, date_str: str):
    await remove_auto_tax_deduction(user_id, txn_id)
    return await process_auto_tax_deduction(user_id, txn_id, category, description, notes, txn_type, amount, date_str)


# ══════════════════════════════════════
#  TAX ENDPOINTS
# ══════════════════════════════════════

@router.get("/tax-summary")
async def get_tax_summary(user=Depends(get_current_user)):
    txns = await db.transactions.find({"user_id": user["id"], "type": "investment"}, {"_id": 0}).to_list(1000)
    holdings_list = []
    async for doc in db.holdings.find({"user_id": user["id"]}):
        doc["id"] = str(doc.pop("_id"))
        holdings_list.append(doc)

    sections: dict = {}
    for sec_id, limit in TAX_LIMITS.items():
        sections[sec_id] = {"section": sec_id, "label": TAX_SECTION_LABELS.get(sec_id, sec_id), "icon": TAX_SECTION_ICONS.get(sec_id, "file-document-outline"), "limit": limit, "used": 0, "items": []}

    for t in txns:
        cat = t.get("category", "")
        sec = TAX_SECTION_MAP.get(cat)
        if sec and sec in sections:
            amt = t.get("amount", 0)
            sections[sec]["used"] += amt
            sections[sec]["items"].append({"name": cat, "amount": amt, "source": "transaction"})

    for h in holdings_list:
        cat = h.get("category", "")
        sec = TAX_SECTION_MAP.get(cat)
        if sec and sec in sections:
            amt = h.get("quantity", 0) * h.get("buy_price", 0)
            sections[sec]["used"] += amt
            sections[sec]["items"].append({"name": h.get("name", cat), "amount": amt, "source": "holding"})

    for sec_id in sections:
        sections[sec_id]["used"] = round(sections[sec_id]["used"], 2)
        limit = sections[sec_id]["limit"]
        pct = (sections[sec_id]["used"] / limit * 100) if limit > 0 else 0
        sections[sec_id]["percentage"] = round(min(pct, 100), 1)
        remaining = max(limit - sections[sec_id]["used"], 0) if limit > 0 else 0
        sections[sec_id]["remaining"] = round(remaining, 2)

    total_deductions = sum(min(s["used"], s["limit"]) if s["limit"] > 0 else s["used"] for s in sections.values())
    active = [s for s in sections.values() if s["used"] > 0 or s["section"] in ("80C", "80D")]

    return {
        "sections": active,
        "total_deductions": round(total_deductions, 2),
        "tax_saved_30_slab": round(total_deductions * 0.30, 2),
        "tax_saved_20_slab": round(total_deductions * 0.20, 2),
        "fy": "2025-26",
    }


@router.get("/capital-gains")
async def get_capital_gains(user=Depends(get_current_user)):
    txns = await db.transactions.find({"user_id": user["id"], "type": "investment"}, {"_id": 0}).to_list(1000)
    buys = {}
    sells = []
    for t in txns:
        key = t.get("description", t.get("category", "Unknown"))
        buy_sell = t.get("buy_sell", "buy")
        if buy_sell == "sell":
            sells.append({"date": t.get("date", ""), "amount": t.get("amount", 0), "units": t.get("units", 0), "price_per_unit": t.get("price_per_unit", 0), "category": t.get("category", ""), "description": t.get("description", ""), "key": key})
        else:
            if key not in buys:
                buys[key] = []
            buys[key].append({"date": t.get("date", ""), "amount": t.get("amount", 0), "units": t.get("units", t.get("amount", 0)), "price_per_unit": t.get("price_per_unit", 1)})

    gains = []
    total_stcg = 0
    total_ltcg = 0

    for sell in sells:
        key = sell["key"]
        sell_date = datetime.strptime(sell["date"], "%Y-%m-%d") if sell["date"] else datetime.now(timezone.utc)
        sell_amount = sell["amount"]
        sell_units = sell["units"] or 1
        cost_basis = 0
        is_long_term = False
        holding_days = 0

        if key in buys and buys[key]:
            buy_entry = buys[key][0]
            buy_date = datetime.strptime(buy_entry["date"], "%Y-%m-%d") if buy_entry["date"] else sell_date
            holding_days = (sell_date - buy_date).days
            is_equity = sell["category"] in ("Stocks", "Stock", "Mutual Funds", "ETF", "ELSS", "SIP")
            ltcg_threshold = 365 if is_equity else 730
            is_long_term = holding_days >= ltcg_threshold
            if sell_units > 0 and buy_entry.get("price_per_unit", 0) > 0:
                cost_basis = sell_units * buy_entry["price_per_unit"]
            else:
                cost_basis = buy_entry.get("amount", sell_amount)

        gain = sell_amount - cost_basis
        gain_pct = (gain / cost_basis * 100) if cost_basis > 0 else 0
        is_equity = sell["category"] in ("Stocks", "Stock", "Mutual Funds", "ETF", "ELSS", "SIP")

        if is_long_term:
            taxable_gain = max(gain, 0)
            tax_rate = 0.125
            total_ltcg += taxable_gain
        else:
            taxable_gain = max(gain, 0)
            tax_rate = 0.20 if is_equity else 0.30
            total_stcg += taxable_gain

        gains.append({"description": sell["description"] or sell["category"], "category": sell["category"], "sell_date": sell["date"], "sell_amount": round(sell_amount, 2), "cost_basis": round(cost_basis, 2), "gain_loss": round(gain, 2), "gain_loss_pct": round(gain_pct, 2), "holding_days": holding_days, "is_long_term": is_long_term, "tax_rate": tax_rate, "tax_liability": round(taxable_gain * tax_rate, 2)})

    ltcg_exemption = 125000
    ltcg_taxable = max(total_ltcg - ltcg_exemption, 0)
    ltcg_tax = ltcg_taxable * 0.125 if ltcg_taxable > 0 else 0
    stcg_tax = total_stcg * 0.20

    return {
        "gains": gains,
        "summary": {"total_stcg": round(total_stcg, 2), "total_ltcg": round(total_ltcg, 2), "ltcg_exemption": ltcg_exemption, "ltcg_taxable": round(ltcg_taxable, 2), "estimated_stcg_tax": round(stcg_tax, 2), "estimated_ltcg_tax": round(ltcg_tax, 2), "total_estimated_tax": round(stcg_tax + ltcg_tax, 2)},
        "notes": ["STCG on equity: 20% (holding < 1 year)", "LTCG on equity: 12.5% above ₹1.25L exemption (holding ≥ 1 year)", "Debt funds: 12.5% LTCG (≥2 years), slab rate STCG"],
        "fy": "2025-26",
    }


# ══════════════════════════════════════
#  USER TAX DEDUCTIONS
# ══════════════════════════════════════

@router.get("/user-tax-deductions")
async def get_user_tax_deductions(user=Depends(get_current_user)):
    deductions = await db.user_tax_deductions.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    return {"deductions": deductions}

@router.post("/user-tax-deductions")
async def add_user_tax_deduction(data: UserTaxDeductionCreate, user=Depends(get_current_user)):
    existing = await db.user_tax_deductions.find_one({"user_id": user["id"], "deduction_id": data.deduction_id})
    if existing:
        raise HTTPException(status_code=400, detail="Deduction already added")
    deduction = {"id": str(uuid4()), "user_id": user["id"], "deduction_id": data.deduction_id, "section": data.section, "name": data.name, "limit": data.limit, "invested_amount": data.invested_amount, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.user_tax_deductions.insert_one(deduction)
    del deduction["_id"]
    return deduction

@router.put("/user-tax-deductions/{deduction_id}")
async def update_user_tax_deduction(deduction_id: str, data: UserTaxDeductionUpdate, user=Depends(get_current_user)):
    result = await db.user_tax_deductions.update_one({"user_id": user["id"], "id": deduction_id}, {"$set": {"invested_amount": data.invested_amount}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Deduction not found")
    updated = await db.user_tax_deductions.find_one({"user_id": user["id"], "id": deduction_id}, {"_id": 0})
    return updated

@router.delete("/user-tax-deductions/{deduction_id}")
async def delete_user_tax_deduction(deduction_id: str, user=Depends(get_current_user)):
    result = await db.user_tax_deductions.delete_one({"user_id": user["id"], "id": deduction_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Deduction not found")
    return {"status": "deleted"}


# ══════════════════════════════════════
#  AUTO-DETECTED TAX DEDUCTIONS
# ══════════════════════════════════════

@router.get("/auto-tax-deductions")
async def get_auto_tax_deductions(user=Depends(get_current_user), fy: str = "2025-26"):
    deductions = await db.auto_tax_deductions.find({"user_id": user["id"], "fy": fy}, {"_id": 0}).to_list(500)
    sections = {}
    for d in deductions:
        sid = d["section"]
        if sid not in sections:
            sections[sid] = {"section": sid, "section_label": d.get("section_label", TAX_SECTION_NAMES.get(sid, sid)), "limit": d.get("limit", TAX_SECTION_LIMITS.get(sid, 0)), "total_amount": 0, "transactions": []}
        sections[sid]["total_amount"] = round(sections[sid]["total_amount"] + d["amount"], 2)
        sections[sid]["transactions"].append({"id": d["id"], "transaction_id": d["transaction_id"], "name": d["name"], "amount": d["amount"], "detected_from": d.get("detected_from", ""), "source_category": d.get("source_category", ""), "source_description": d.get("source_description", ""), "source_date": d.get("source_date", "")})
    return {"fy": fy, "sections": list(sections.values()), "total_detected": round(sum(s["total_amount"] for s in sections.values()), 2), "count": len(deductions)}

@router.delete("/auto-tax-deductions/{deduction_id}")
async def dismiss_auto_tax_deduction(deduction_id: str, user=Depends(get_current_user)):
    result = await db.auto_tax_deductions.delete_one({"user_id": user["id"], "id": deduction_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Auto deduction not found")
    return {"status": "dismissed"}

@router.put("/auto-tax-deductions/{deduction_id}")
async def update_auto_tax_deduction_amount(deduction_id: str, data: UserTaxDeductionUpdate, user=Depends(get_current_user)):
    result = await db.auto_tax_deductions.update_one({"user_id": user["id"], "id": deduction_id}, {"$set": {"amount": data.invested_amount}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Auto deduction not found")
    updated = await db.auto_tax_deductions.find_one({"user_id": user["id"], "id": deduction_id}, {"_id": 0})
    return updated


# ══════════════════════════════════════
#  TAX CALCULATOR
# ══════════════════════════════════════

def calculate_old_regime_tax(taxable_income: float) -> dict:
    slabs = [(250000, 0), (500000, 0.05), (1000000, 0.20), (float('inf'), 0.30)]
    tax = 0
    prev = 0
    breakdown = []
    for limit, rate in slabs:
        if taxable_income <= prev:
            break
        slab_income = min(taxable_income, limit) - prev
        slab_tax = slab_income * rate
        tax += slab_tax
        if slab_income > 0:
            breakdown.append({"range": f"₹{prev:,.0f} - ₹{limit:,.0f}" if limit != float('inf') else f"Above ₹{prev:,.0f}", "rate": f"{int(rate*100)}%", "income": round(slab_income, 2), "tax": round(slab_tax, 2)})
        prev = limit
    rebate = min(tax, 12500) if taxable_income <= 500000 else 0
    return {"tax": round(tax, 2), "rebate": round(rebate, 2), "tax_after_rebate": round(max(tax - rebate, 0), 2), "breakdown": breakdown}

def calculate_new_regime_tax(taxable_income: float) -> dict:
    slabs = [(400000, 0), (800000, 0.05), (1200000, 0.10), (1600000, 0.15), (2000000, 0.20), (2400000, 0.25), (float('inf'), 0.30)]
    tax = 0
    prev = 0
    breakdown = []
    for limit, rate in slabs:
        if taxable_income <= prev:
            break
        slab_income = min(taxable_income, limit) - prev
        slab_tax = slab_income * rate
        tax += slab_tax
        if slab_income > 0:
            breakdown.append({"range": f"₹{prev:,.0f} - ₹{limit:,.0f}" if limit != float('inf') else f"Above ₹{prev:,.0f}", "rate": f"{int(rate*100)}%", "income": round(slab_income, 2), "tax": round(slab_tax, 2)})
        prev = limit
    rebate = min(tax, 60000) if taxable_income <= 1200000 else 0
    return {"tax": round(tax, 2), "rebate": round(rebate, 2), "tax_after_rebate": round(max(tax - rebate, 0), 2), "breakdown": breakdown}

def calculate_surcharge(income: float, tax: float, regime: str) -> float:
    if income <= 5000000: return 0
    elif income <= 10000000: return tax * 0.10
    elif income <= 20000000: return tax * 0.15
    elif income <= 50000000: return tax * 0.25
    else: return tax * (0.25 if regime == "new" else 0.37)


@router.get("/tax-calculator")
async def income_tax_calculator(user=Depends(get_current_user), fy: str = "2025-26"):
    fy_parts = fy.split("-")
    fy_start_year = int(fy_parts[0])
    fy_start = f"{fy_start_year}-04-01"
    fy_end = f"{fy_start_year + 1}-03-31"
    ay = f"{fy_start_year + 1}-{int(fy_parts[1]) + 1:02d}"

    all_txns = await db.transactions.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    fy_txns = [t for t in all_txns if t.get("date", "") and fy_start <= t["date"] <= fy_end]

    salary_income = sum(t.get("amount", 0) for t in fy_txns if t.get("type") == "income" and t.get("category", "").lower() in ("salary", "wages", "bonus", "income"))
    other_income = sum(t.get("amount", 0) for t in fy_txns if t.get("type") == "income" and t.get("category", "").lower() not in ("salary", "wages", "bonus", "income"))
    if salary_income == 0:
        salary_income = sum(t.get("amount", 0) for t in fy_txns if t.get("type") == "income")
        other_income = 0
    gross_income = salary_income + other_income

    cap_gains = await get_capital_gains(user)
    total_stcg = cap_gains["summary"]["total_stcg"]
    total_ltcg = cap_gains["summary"]["total_ltcg"]
    ltcg_exemption = cap_gains["summary"]["ltcg_exemption"]
    ltcg_taxable = cap_gains["summary"]["ltcg_taxable"]
    stcg_tax = cap_gains["summary"]["estimated_stcg_tax"]
    ltcg_tax = cap_gains["summary"]["estimated_ltcg_tax"]
    total_cg_tax = stcg_tax + ltcg_tax

    tax_summary = await get_tax_summary(user)
    system_deductions = tax_summary["total_deductions"]

    user_deductions_data = await db.user_tax_deductions.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    auto_deductions_data = await db.auto_tax_deductions.find({"user_id": user["id"], "fy": fy}, {"_id": 0}).to_list(500)

    deductions_by_section = {}
    for sec in tax_summary.get("sections", []):
        if sec["used"] > 0:
            sid = sec["section"]
            if sid not in deductions_by_section:
                deductions_by_section[sid] = {"section": sid, "label": sec["label"], "limit": sec["limit"], "amount": 0, "source": "transactions"}
            deductions_by_section[sid]["amount"] += sec["used"]
    for d in user_deductions_data:
        sid = d.get("section", "")
        if sid not in deductions_by_section:
            deductions_by_section[sid] = {"section": sid, "label": f"Section {sid}", "limit": d.get("limit", 0), "amount": 0, "source": "user_added"}
        deductions_by_section[sid]["amount"] += d.get("invested_amount", 0)
    for d in auto_deductions_data:
        sid = d.get("section", "")
        if sid not in deductions_by_section:
            deductions_by_section[sid] = {"section": sid, "label": d.get("section_label", TAX_SECTION_NAMES.get(sid, f"Section {sid}")), "limit": d.get("limit", TAX_SECTION_LIMITS.get(sid, 0)), "amount": 0, "source": "auto_detected"}
        deductions_by_section[sid]["amount"] += d.get("amount", 0)

    total_old_deductions = 0
    deductions_list = []
    for sid, info in deductions_by_section.items():
        capped = min(info["amount"], info["limit"]) if info["limit"] and info["limit"] > 0 else info["amount"]
        total_old_deductions += capped
        deductions_list.append({"section": sid, "label": info["label"], "amount": round(info["amount"], 2), "limit": info["limit"], "capped_amount": round(capped, 2)})

    old_std_deduction = 50000 if salary_income > 0 else 0
    new_std_deduction = 75000 if salary_income > 0 else 0

    old_total_deductions = old_std_deduction + total_old_deductions
    old_taxable_income = max(gross_income - old_total_deductions, 0)
    old_tax_calc = calculate_old_regime_tax(old_taxable_income)
    old_surcharge = calculate_surcharge(old_taxable_income, old_tax_calc["tax_after_rebate"], "old")
    old_cess = (old_tax_calc["tax_after_rebate"] + old_surcharge) * 0.04
    old_total_tax_on_income = old_tax_calc["tax_after_rebate"] + old_surcharge + old_cess
    old_total_tax = old_total_tax_on_income + total_cg_tax

    new_nps_deduction = sum(d.get("invested_amount", 0) for d in user_deductions_data if d.get("section", "") in ("80CCD1B", "80CCD(1B)"))
    new_total_deductions = new_std_deduction + new_nps_deduction
    new_taxable_income = max(gross_income - new_total_deductions, 0)
    new_tax_calc = calculate_new_regime_tax(new_taxable_income)
    new_surcharge = calculate_surcharge(new_taxable_income, new_tax_calc["tax_after_rebate"], "new")
    new_cess = (new_tax_calc["tax_after_rebate"] + new_surcharge) * 0.04
    new_total_tax_on_income = new_tax_calc["tax_after_rebate"] + new_surcharge + new_cess
    new_total_tax = new_total_tax_on_income + total_cg_tax

    savings = abs(old_total_tax - new_total_tax)
    better_regime = "old" if old_total_tax < new_total_tax else "new" if new_total_tax < old_total_tax else "equal"

    return {
        "fy": fy, "ay": ay,
        "income": {"salary": round(salary_income, 2), "other": round(other_income, 2), "gross_total": round(gross_income, 2)},
        "capital_gains": {"stcg": round(total_stcg, 2), "ltcg": round(total_ltcg, 2), "ltcg_exemption": ltcg_exemption, "ltcg_taxable": round(ltcg_taxable, 2), "stcg_tax": round(stcg_tax, 2), "ltcg_tax": round(ltcg_tax, 2), "total_cg_tax": round(total_cg_tax, 2)},
        "deductions": deductions_list,
        "old_regime": {"standard_deduction": old_std_deduction, "chapter_via_deductions": round(total_old_deductions, 2), "total_deductions": round(old_total_deductions, 2), "taxable_income": round(old_taxable_income, 2), "tax_on_income": round(old_tax_calc["tax"], 2), "rebate_87a": round(old_tax_calc["rebate"], 2), "tax_after_rebate": round(old_tax_calc["tax_after_rebate"], 2), "surcharge": round(old_surcharge, 2), "cess": round(old_cess, 2), "total_tax_on_income": round(old_total_tax_on_income, 2), "capital_gains_tax": round(total_cg_tax, 2), "total_tax": round(old_total_tax, 2), "slab_breakdown": old_tax_calc["breakdown"]},
        "new_regime": {"standard_deduction": new_std_deduction, "nps_deduction": round(new_nps_deduction, 2), "total_deductions": round(new_total_deductions, 2), "taxable_income": round(new_taxable_income, 2), "tax_on_income": round(new_tax_calc["tax"], 2), "rebate_87a": round(new_tax_calc["rebate"], 2), "tax_after_rebate": round(new_tax_calc["tax_after_rebate"], 2), "surcharge": round(new_surcharge, 2), "cess": round(new_cess, 2), "total_tax_on_income": round(new_total_tax_on_income, 2), "capital_gains_tax": round(total_cg_tax, 2), "total_tax": round(new_total_tax, 2), "slab_breakdown": new_tax_calc["breakdown"]},
        "comparison": {"better_regime": better_regime, "savings": round(savings, 2), "old_effective_rate": round((old_total_tax / gross_income * 100), 2) if gross_income > 0 else 0, "new_effective_rate": round((new_total_tax / gross_income * 100), 2) if gross_income > 0 else 0},
        "notes": ["Capital Gains Tax is the same under both regimes", "STCG on equity: 20% | LTCG on equity: 12.5% (above ₹1.25L)", "Old Regime allows Chapter VI-A deductions (80C, 80D, etc.)", "New Regime: Standard deduction ₹75,000 + limited NPS deduction", "4% Health & Education Cess on all tax + surcharge", "Rebate u/s 87A: Old ≤₹5L (₹12,500) | New ≤₹12L (₹60,000)"],
    }
