"""
Tax Advanced Features — Phase 3
Capital Gains Engine, Deduction Gap Analysis, TDS Mismatch Detection, Tax Calendar Reminders
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from database import db
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tax")


# ══════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════

# Grandfathering date for LTCG (Budget 2018)
GRANDFATHERING_DATE = "2018-01-31"

# FMV on Jan 31, 2018 for major indices (approximate)
GRANDFATHERING_FMV = {
    "NIFTY50": 11027.70,
    "SENSEX": 35965.02,
}

# LTCG exemption limit
LTCG_EXEMPTION_EQUITY = 125000  # ₹1.25L for FY 2024-25 onwards

# Tax rates
STCG_EQUITY_RATE = 0.20  # 20% for listed equity
LTCG_EQUITY_RATE = 0.125  # 12.5% for listed equity above exemption
STCG_DEBT_RATE = 0.30  # As per slab (assuming 30%)
LTCG_DEBT_RATE = 0.125  # 12.5% for debt funds (no indexation post Apr 2023)

# Deduction sections with limits and recommended products
DEDUCTION_RECOMMENDATIONS = {
    "80C": {
        "limit": 150000,
        "products": [
            {"name": "ELSS Mutual Funds", "priority": 1, "lock_in": "3 years", "returns": "Market-linked (10-15%)", "tax_benefit": "Exempt-Exempt-Exempt"},
            {"name": "PPF", "priority": 2, "lock_in": "15 years", "returns": "7.1% (Govt)", "tax_benefit": "Exempt-Exempt-Exempt"},
            {"name": "NPS Tier 1", "priority": 3, "lock_in": "Till 60", "returns": "8-10%", "tax_benefit": "Taxable at 60% withdrawal"},
            {"name": "Tax Saver FD", "priority": 4, "lock_in": "5 years", "returns": "6-7%", "tax_benefit": "Interest taxable"},
            {"name": "Sukanya Samriddhi", "priority": 5, "lock_in": "21 years", "returns": "8.2% (Govt)", "tax_benefit": "Exempt-Exempt-Exempt", "eligibility": "Girl child < 10 years"},
        ],
    },
    "80CCD1B": {
        "limit": 50000,
        "products": [
            {"name": "NPS Additional Contribution", "priority": 1, "lock_in": "Till 60", "returns": "8-10%", "tax_benefit": "Extra ₹50K over 80C"},
        ],
    },
    "80D": {
        "limit": 25000,  # Self & family (50K if senior citizen)
        "products": [
            {"name": "Health Insurance Premium", "priority": 1, "lock_in": "1 year", "returns": "Risk cover", "tax_benefit": "Premium deductible"},
            {"name": "Preventive Health Checkup", "priority": 2, "lock_in": "None", "returns": "N/A", "tax_benefit": "Up to ₹5,000"},
        ],
    },
    "80E": {
        "limit": 0,  # No limit - full interest deductible
        "products": [
            {"name": "Education Loan Interest", "priority": 1, "lock_in": "8 years max", "returns": "N/A", "tax_benefit": "Full interest deductible"},
        ],
    },
    "80G": {
        "limit": 0,  # Varies by donation type
        "products": [
            {"name": "PM CARES Fund", "priority": 1, "lock_in": "None", "returns": "N/A", "tax_benefit": "100% deduction"},
            {"name": "Registered NGOs", "priority": 2, "lock_in": "None", "returns": "N/A", "tax_benefit": "50% deduction"},
        ],
    },
    "24b": {
        "limit": 200000,  # Self-occupied property
        "products": [
            {"name": "Home Loan Interest", "priority": 1, "lock_in": "Loan tenure", "returns": "Property appreciation", "tax_benefit": "Up to ₹2L for self-occupied"},
        ],
    },
    "80TTA": {
        "limit": 10000,
        "products": [
            {"name": "Savings Account Interest", "priority": 1, "lock_in": "None", "returns": "3-4%", "tax_benefit": "Up to ₹10K exempt"},
        ],
    },
}

# Tax Calendar - Important dates
TAX_CALENDAR = [
    {"month": 4, "day": 1, "event": "New Financial Year Begins", "action": "Review tax planning for new FY"},
    {"month": 6, "day": 15, "event": "Advance Tax Q1 Due", "action": "Pay 15% of estimated tax", "applicable_to": ["business", "freelancer", "investor"]},
    {"month": 7, "day": 31, "event": "ITR Filing Deadline (Non-Audit)", "action": "File ITR before deadline", "applicable_to": ["salaried"]},
    {"month": 9, "day": 15, "event": "Advance Tax Q2 Due", "action": "Pay 45% of estimated tax (cumulative)", "applicable_to": ["business", "freelancer", "investor"]},
    {"month": 10, "day": 31, "event": "ITR Filing Deadline (Audit Cases)", "action": "File ITR for audit cases", "applicable_to": ["business"]},
    {"month": 12, "day": 15, "event": "Advance Tax Q3 Due", "action": "Pay 75% of estimated tax (cumulative)", "applicable_to": ["business", "freelancer", "investor"]},
    {"month": 12, "day": 31, "event": "Last Date for Tax Saving Investments", "action": "Complete 80C investments before year-end rush"},
    {"month": 1, "day": 15, "event": "Form 16 Interim Check", "action": "Verify TDS deducted with employer"},
    {"month": 3, "day": 15, "event": "Advance Tax Q4 Due", "action": "Pay 100% of estimated tax", "applicable_to": ["business", "freelancer", "investor"]},
    {"month": 3, "day": 31, "event": "Financial Year Ends", "action": "Ensure all tax-saving proofs submitted to employer"},
]


# ══════════════════════════════════════
#  CAPITAL GAINS ENGINE
# ══════════════════════════════════════

def calculate_grandfathered_cost(
    buy_price: float,
    buy_date: str,
    fmv_jan_2018: float = None,
    highest_price_jan_2018: float = None,
) -> float:
    """
    Calculate cost of acquisition with grandfathering for LTCG.
    For equity acquired before Feb 1, 2018:
    Cost = Higher of (Actual Cost, Lower of (FMV on Jan 31 2018, Highest price on Jan 31 2018))
    """
    if buy_date >= GRANDFATHERING_DATE:
        return buy_price
    
    if fmv_jan_2018 is None:
        fmv_jan_2018 = buy_price * 1.5  # Assume 50% appreciation if FMV not provided
    
    if highest_price_jan_2018 is None:
        highest_price_jan_2018 = fmv_jan_2018
    
    deemed_cost = min(fmv_jan_2018, highest_price_jan_2018)
    return max(buy_price, deemed_cost)


def classify_holding_period(buy_date: str, sell_date: str, asset_type: str) -> dict:
    """Classify holding as STCG or LTCG based on asset type and holding period."""
    try:
        buy = datetime.strptime(buy_date, "%Y-%m-%d")
        sell = datetime.strptime(sell_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return {"is_long_term": False, "holding_days": 0, "threshold_days": 365}
    
    holding_days = (sell - buy).days
    
    # Threshold varies by asset type
    if asset_type.lower() in ("stocks", "stock", "equity", "mutual funds", "mf", "etf", "elss"):
        threshold = 365  # 1 year for listed equity
    elif asset_type.lower() in ("debt", "debt fund", "liquid fund", "fd", "bonds"):
        threshold = 365  # Changed to 1 year post Budget 2023 (no LTCG benefit for debt)
    elif asset_type.lower() in ("property", "real estate", "land", "house"):
        threshold = 730  # 2 years for property
    elif asset_type.lower() in ("gold", "sovereign gold bond", "sgb", "jewelry"):
        threshold = 730  # 2 years for gold
    else:
        threshold = 365  # Default 1 year
    
    return {
        "is_long_term": holding_days >= threshold,
        "holding_days": holding_days,
        "threshold_days": threshold,
        "asset_type": asset_type,
    }


def calculate_capital_gains_tax(
    gains: List[Dict],
    apply_grandfathering: bool = True,
) -> Dict:
    """
    Calculate capital gains tax with grandfathering and proper categorization.
    """
    total_stcg_equity = 0
    total_ltcg_equity = 0
    total_stcg_other = 0
    total_ltcg_other = 0
    
    processed_gains = []
    
    for g in gains:
        sell_amount = g.get("sell_amount", 0)
        buy_price = g.get("buy_price", g.get("cost_basis", 0))
        buy_date = g.get("buy_date", "")
        sell_date = g.get("sell_date", "")
        asset_type = g.get("asset_type", g.get("category", "equity"))
        fmv_jan_2018 = g.get("fmv_jan_2018")
        
        # Classify holding period
        classification = classify_holding_period(buy_date, sell_date, asset_type)
        is_long_term = classification["is_long_term"]
        is_equity = asset_type.lower() in ("stocks", "stock", "equity", "mutual funds", "mf", "etf", "elss")
        
        # Apply grandfathering if applicable
        if apply_grandfathering and is_long_term and is_equity and buy_date < GRANDFATHERING_DATE:
            adjusted_cost = calculate_grandfathered_cost(buy_price, buy_date, fmv_jan_2018)
        else:
            adjusted_cost = buy_price
        
        gain_loss = sell_amount - adjusted_cost
        
        # Categorize
        if is_equity:
            if is_long_term:
                total_ltcg_equity += max(0, gain_loss)
            else:
                total_stcg_equity += max(0, gain_loss)
            tax_rate = LTCG_EQUITY_RATE if is_long_term else STCG_EQUITY_RATE
        else:
            if is_long_term:
                total_ltcg_other += max(0, gain_loss)
            else:
                total_stcg_other += max(0, gain_loss)
            tax_rate = LTCG_DEBT_RATE if is_long_term else STCG_DEBT_RATE
        
        processed_gains.append({
            "description": g.get("description", g.get("name", "Investment")),
            "asset_type": asset_type,
            "buy_date": buy_date,
            "sell_date": sell_date,
            "original_cost": round(buy_price, 2),
            "adjusted_cost": round(adjusted_cost, 2),
            "grandfathering_applied": adjusted_cost != buy_price,
            "sell_amount": round(sell_amount, 2),
            "gain_loss": round(gain_loss, 2),
            "is_long_term": is_long_term,
            "holding_days": classification["holding_days"],
            "tax_rate": tax_rate,
            "estimated_tax": round(max(0, gain_loss) * tax_rate, 2),
        })
    
    # Calculate taxes
    ltcg_equity_taxable = max(0, total_ltcg_equity - LTCG_EXEMPTION_EQUITY)
    ltcg_equity_tax = ltcg_equity_taxable * LTCG_EQUITY_RATE
    stcg_equity_tax = total_stcg_equity * STCG_EQUITY_RATE
    ltcg_other_tax = total_ltcg_other * LTCG_DEBT_RATE
    stcg_other_tax = total_stcg_other * STCG_DEBT_RATE
    
    total_tax = ltcg_equity_tax + stcg_equity_tax + ltcg_other_tax + stcg_other_tax
    
    return {
        "gains": processed_gains,
        "summary": {
            "stcg_equity": round(total_stcg_equity, 2),
            "ltcg_equity": round(total_ltcg_equity, 2),
            "ltcg_equity_exemption": LTCG_EXEMPTION_EQUITY,
            "ltcg_equity_taxable": round(ltcg_equity_taxable, 2),
            "stcg_other": round(total_stcg_other, 2),
            "ltcg_other": round(total_ltcg_other, 2),
        },
        "tax_breakdown": {
            "stcg_equity_tax": round(stcg_equity_tax, 2),
            "ltcg_equity_tax": round(ltcg_equity_tax, 2),
            "stcg_other_tax": round(stcg_other_tax, 2),
            "ltcg_other_tax": round(ltcg_other_tax, 2),
            "total_cg_tax": round(total_tax, 2),
        },
        "notes": [
            f"LTCG on equity: 12.5% above ₹{LTCG_EXEMPTION_EQUITY:,} exemption",
            "STCG on equity: 20%",
            "Grandfathering applied for equity acquired before Feb 1, 2018",
            "Debt fund gains taxed as per slab (no LTCG benefit post Apr 2023)",
        ],
    }


@router.get("/capital-gains-v2")
async def get_capital_gains_v2(user=Depends(get_current_user), fy: str = "2025-26"):
    """
    Enhanced Capital Gains API with grandfathering support.
    """
    user_id = user["id"]
    fy_parts = fy.split("-")
    fy_start = f"{int(fy_parts[0])}-04-01"
    fy_end = f"{int(fy_parts[0]) + 1}-03-31"
    
    # Get all holdings with sell transactions
    txns = await db.transactions.find(
        {"user_id": user_id, "type": "investment"},
        {"_id": 0}
    ).to_list(5000)
    
    holdings = await db.holdings.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(200)
    
    # Build buy records by description/name
    buys = {}
    sells = []
    
    for t in txns:
        key = t.get("description", t.get("category", "Unknown"))
        buy_sell = t.get("buy_sell", "buy")
        
        if buy_sell == "sell" and fy_start <= t.get("date", "") <= fy_end:
            sells.append({
                "description": key,
                "sell_date": t.get("date", ""),
                "sell_amount": t.get("amount", 0),
                "asset_type": t.get("category", "equity"),
                "units": t.get("units", 0),
            })
        elif buy_sell == "buy":
            if key not in buys:
                buys[key] = []
            buys[key].append({
                "buy_date": t.get("date", ""),
                "buy_price": t.get("amount", 0),
                "units": t.get("units", t.get("amount", 0)),
                "price_per_unit": t.get("price_per_unit", 1),
            })
    
    # Match sells with buys (FIFO)
    gains_data = []
    for sell in sells:
        key = sell["description"]
        if key in buys and buys[key]:
            buy = buys[key][0]  # FIFO - first buy
            gains_data.append({
                "description": sell["description"],
                "asset_type": sell["asset_type"],
                "buy_date": buy["buy_date"],
                "buy_price": buy["buy_price"],
                "sell_date": sell["sell_date"],
                "sell_amount": sell["sell_amount"],
            })
    
    # Calculate gains with grandfathering
    result = calculate_capital_gains_tax(gains_data)
    result["fy"] = fy
    
    return result


# ══════════════════════════════════════
#  DEDUCTION GAP ANALYSIS
# ══════════════════════════════════════

@router.get("/deduction-gap")
async def get_deduction_gap_analysis(user=Depends(get_current_user), fy: str = "2025-26"):
    """
    Analyze deduction gaps and provide product recommendations.
    """
    user_id = user["id"]
    
    # Get current deductions
    auto_deds = await db.auto_tax_deductions.find(
        {"user_id": user_id, "fy": fy},
        {"_id": 0}
    ).to_list(500)
    
    user_deds = await db.user_tax_deductions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    salary_profile = await db.salary_profiles.find_one({"user_id": user_id}, {"_id": 0})
    
    # Aggregate by section
    section_totals = {}
    for d in auto_deds:
        section = d.get("section", "")
        if section not in section_totals:
            section_totals[section] = 0
        section_totals[section] += d.get("amount", 0)
    
    for d in user_deds:
        section = d.get("section", "")
        if section not in section_totals:
            section_totals[section] = 0
        section_totals[section] += d.get("invested_amount", 0)
    
    # Add EPF from salary profile
    if salary_profile:
        epf_annual = salary_profile.get("employee_pf_monthly", 0) * 12
        if epf_annual > 0:
            section_totals["80C"] = section_totals.get("80C", 0) + epf_annual
    
    # Calculate gaps and recommendations
    gaps = []
    total_gap = 0
    potential_savings = 0
    
    for section, config in DEDUCTION_RECOMMENDATIONS.items():
        limit = config["limit"]
        used = section_totals.get(section, 0)
        remaining = max(0, limit - used) if limit > 0 else 0
        utilization = (used / limit * 100) if limit > 0 else 100
        
        if remaining > 0 or (limit == 0 and used == 0):
            # Has gap - provide recommendations
            gap_entry = {
                "section": section,
                "limit": limit,
                "used": round(used, 2),
                "remaining": round(remaining, 2),
                "utilization_pct": round(min(100, utilization), 1),
                "status": "optimized" if utilization >= 90 else "good" if utilization >= 50 else "under_utilized",
                "potential_tax_savings_30": round(remaining * 0.30, 2),
                "potential_tax_savings_20": round(remaining * 0.20, 2),
                "recommendations": [],
            }
            
            # Add product recommendations
            for product in config["products"]:
                rec = {
                    "product": product["name"],
                    "priority": product["priority"],
                    "lock_in": product["lock_in"],
                    "expected_returns": product["returns"],
                    "tax_benefit": product["tax_benefit"],
                }
                if "eligibility" in product:
                    rec["eligibility"] = product["eligibility"]
                gap_entry["recommendations"].append(rec)
            
            gaps.append(gap_entry)
            total_gap += remaining
            potential_savings += remaining * 0.30  # Assuming 30% slab
    
    # Sort by priority (under_utilized first, then by remaining amount)
    gaps.sort(key=lambda x: (0 if x["status"] == "under_utilized" else 1, -x["remaining"]))
    
    # Top 3 actionable recommendations
    top_actions = []
    for gap in gaps:
        if gap["remaining"] > 0 and gap["recommendations"]:
            top_rec = gap["recommendations"][0]
            top_actions.append({
                "section": gap["section"],
                "action": f"Invest ₹{gap['remaining']:,.0f} in {top_rec['product']}",
                "tax_savings": f"Save ₹{gap['remaining'] * 0.30:,.0f} (30% slab)",
                "product": top_rec["product"],
            })
        if len(top_actions) >= 3:
            break
    
    return {
        "fy": fy,
        "gaps": gaps,
        "summary": {
            "total_gap": round(total_gap, 2),
            "potential_tax_savings": round(potential_savings, 2),
            "sections_analyzed": len(gaps),
            "sections_under_utilized": sum(1 for g in gaps if g["status"] == "under_utilized"),
        },
        "top_actions": top_actions,
    }


# ══════════════════════════════════════
#  TDS MISMATCH DETECTION
# ══════════════════════════════════════

@router.get("/tds-mismatch")
async def get_tds_mismatch(user=Depends(get_current_user), fy: str = "2025-26"):
    """
    Compare TDS from various sources and detect mismatches.
    Sources: Salary profile (employer TDS), Form 26AS (uploaded), Transactions
    """
    user_id = user["id"]
    fy_parts = fy.split("-")
    fy_start = f"{int(fy_parts[0])}-04-01"
    fy_end = f"{int(fy_parts[0]) + 1}-03-31"
    
    tds_sources = []
    
    # 1. TDS from Salary Profile
    salary_profile = await db.salary_profiles.find_one({"user_id": user_id}, {"_id": 0})
    if salary_profile:
        monthly_tds = salary_profile.get("tds_monthly", 0)
        # Calculate months in FY based on profile update date
        months = 12  # Assume full year for now
        employer_tds = monthly_tds * months
        if employer_tds > 0:
            tds_sources.append({
                "source": "Salary Profile",
                "source_type": "employer",
                "deductor": salary_profile.get("employer_name", "Employer"),
                "expected_tds": round(employer_tds, 2),
                "reported_tds": None,  # Will be filled from Form 26AS
                "mismatch": None,
                "status": "pending_verification",
            })
    
    # 2. TDS from uploaded Form 26AS / AIS
    tax_docs = await db.tax_documents.find(
        {"user_id": user_id, "document_type": {"$in": ["form26as", "ais"]}},
        {"_id": 0}
    ).to_list(10)
    
    form26as_tds = []
    for doc in tax_docs:
        parsed = doc.get("parsed_data", {})
        tds_details = parsed.get("tds_details", [])
        for tds in tds_details:
            form26as_tds.append({
                "deductor": tds.get("deductor_name", "Unknown"),
                "tan": tds.get("deductor_tan", ""),
                "tds": tds.get("tds_deducted", 0),
                "section": tds.get("section", ""),
            })
    
    # 3. TDS from transactions (bank statements)
    txns = await db.transactions.find(
        {
            "user_id": user_id,
            "date": {"$gte": fy_start, "$lte": fy_end},
            "category": {"$in": ["TDS", "Tax Deducted", "Income Tax"]},
        },
        {"_id": 0}
    ).to_list(100)
    
    txn_tds = sum(t.get("amount", 0) for t in txns)
    
    # Match and detect mismatches
    mismatches = []
    total_expected = 0
    total_reported = 0
    
    for source in tds_sources:
        if source["source_type"] == "employer":
            # Try to match with Form 26AS
            employer_name = source["deductor"].lower()
            matched = False
            for f26 in form26as_tds:
                if employer_name in f26["deductor"].lower() or f26["deductor"].lower() in employer_name:
                    source["reported_tds"] = f26["tds"]
                    source["tan"] = f26["tan"]
                    diff = abs(source["expected_tds"] - f26["tds"])
                    source["mismatch"] = round(diff, 2)
                    source["mismatch_pct"] = round(diff / source["expected_tds"] * 100, 1) if source["expected_tds"] > 0 else 0
                    source["status"] = "matched" if diff < 1000 else "mismatch_minor" if diff < 5000 else "mismatch_major"
                    matched = True
                    total_reported += f26["tds"]
                    break
            
            if not matched:
                source["status"] = "not_found_in_26as"
            
            total_expected += source["expected_tds"]
    
    # Add Form 26AS entries not matched
    for f26 in form26as_tds:
        already_matched = any(
            s.get("tan") == f26["tan"] or f26["deductor"].lower() in s.get("deductor", "").lower()
            for s in tds_sources
        )
        if not already_matched:
            tds_sources.append({
                "source": "Form 26AS",
                "source_type": "form26as",
                "deductor": f26["deductor"],
                "tan": f26["tan"],
                "expected_tds": None,
                "reported_tds": f26["tds"],
                "mismatch": None,
                "status": "additional_in_26as",
            })
            total_reported += f26["tds"]
    
    # Summary
    overall_diff = abs(total_expected - total_reported)
    
    return {
        "fy": fy,
        "tds_sources": tds_sources,
        "summary": {
            "total_expected_tds": round(total_expected, 2),
            "total_reported_tds": round(total_reported, 2),
            "overall_difference": round(overall_diff, 2),
            "tds_from_transactions": round(txn_tds, 2),
            "status": "all_matched" if overall_diff < 1000 else "minor_mismatch" if overall_diff < 10000 else "major_mismatch",
        },
        "recommendations": [
            "Upload Form 26AS to verify all TDS credits" if not tax_docs else None,
            "Contact employer if TDS mismatch > ₹5,000" if any(s.get("status") == "mismatch_major" for s in tds_sources) else None,
            "Check Form 16 Part A for accurate TDS breakup" if total_expected > 0 else None,
        ],
    }


# ══════════════════════════════════════
#  TAX CALENDAR & REMINDERS
# ══════════════════════════════════════

@router.get("/calendar")
async def get_tax_calendar(user=Depends(get_current_user), fy: str = "2025-26"):
    """
    Get personalized tax calendar with reminders.
    """
    user_id = user["id"]
    
    # Get user's income profile to personalize calendar
    income_profile = await db.tax_income_profiles.find_one({"user_id": user_id}, {"_id": 0})
    income_types = income_profile.get("income_types", ["salaried"]) if income_profile else ["salaried"]
    
    # Get current date
    now = datetime.now(timezone.utc)
    fy_parts = fy.split("-")
    fy_start_year = int(fy_parts[0])
    
    calendar_events = []
    
    for event in TAX_CALENDAR:
        # Determine event date
        month = event["month"]
        day = event["day"]
        
        # Calculate year based on FY
        if month >= 4:
            event_year = fy_start_year
        else:
            event_year = fy_start_year + 1
        
        try:
            event_date = datetime(event_year, month, day, tzinfo=timezone.utc)
        except ValueError:
            continue
        
        # Check if applicable to user's income type
        applicable_to = event.get("applicable_to")
        is_applicable = True
        if applicable_to:
            is_applicable = any(it in applicable_to for it in income_types)
        
        # Determine status
        if event_date < now:
            status = "completed" if (now - event_date).days < 30 else "past"
        elif (event_date - now).days <= 7:
            status = "urgent"
        elif (event_date - now).days <= 30:
            status = "upcoming"
        else:
            status = "future"
        
        calendar_events.append({
            "date": event_date.strftime("%Y-%m-%d"),
            "month": event_date.strftime("%B"),
            "day": day,
            "event": event["event"],
            "action": event["action"],
            "is_applicable": is_applicable,
            "status": status,
            "days_until": (event_date - now).days if event_date > now else 0,
        })
    
    # Sort by date
    calendar_events.sort(key=lambda x: x["date"])
    
    # Upcoming urgent items
    urgent_items = [e for e in calendar_events if e["status"] in ("urgent", "upcoming") and e["is_applicable"]]
    
    return {
        "fy": fy,
        "income_types": income_types,
        "events": calendar_events,
        "urgent_count": len([e for e in calendar_events if e["status"] == "urgent"]),
        "upcoming_count": len([e for e in calendar_events if e["status"] == "upcoming"]),
        "next_deadline": urgent_items[0] if urgent_items else None,
    }


@router.get("/reminders")
async def get_tax_reminders(user=Depends(get_current_user), fy: str = "2025-26"):
    """
    Get proactive tax reminders based on user's data.
    """
    user_id = user["id"]
    now = datetime.now(timezone.utc)
    current_month = now.month
    
    reminders = []
    
    # Get user data
    income_profile = await db.tax_income_profiles.find_one({"user_id": user_id}, {"_id": 0})
    salary_profile = await db.salary_profiles.find_one({"user_id": user_id}, {"_id": 0})
    auto_deds = await db.auto_tax_deductions.find({"user_id": user_id, "fy": fy}, {"_id": 0}).to_list(500)
    
    total_80c = sum(d.get("amount", 0) for d in auto_deds if d.get("section") == "80C")
    
    # Add EPF from salary
    if salary_profile:
        total_80c += salary_profile.get("employee_pf_monthly", 0) * 12
    
    remaining_80c = max(0, 150000 - total_80c)
    
    # 80C Investment Reminder (Oct-March is critical period)
    if current_month >= 10 or current_month <= 3:
        if remaining_80c > 50000:
            urgency = "high" if current_month >= 1 else "medium"
            reminders.append({
                "id": "80c_investment",
                "type": "action",
                "urgency": urgency,
                "title": "Complete 80C Investments",
                "message": f"₹{remaining_80c:,.0f} remaining in 80C limit. Consider ELSS SIP or PPF before March 31.",
                "potential_savings": round(remaining_80c * 0.30, 0),
                "action_text": "View Recommendations",
                "action_route": "/tax/deduction-gap",
            })
    
    # Form 16 Reminder (June-July)
    if current_month in (6, 7):
        reminders.append({
            "id": "form16_collection",
            "type": "reminder",
            "urgency": "medium",
            "title": "Collect Form 16",
            "message": "Request Form 16 from your employer. ITR filing deadline is July 31.",
            "action_text": "Upload Form 16",
            "action_route": "/tax/upload/form16",
        })
    
    # ITR Filing Reminder (July)
    if current_month == 7:
        reminders.append({
            "id": "itr_filing",
            "type": "deadline",
            "urgency": "high",
            "title": "ITR Filing Deadline Approaching",
            "message": "File your Income Tax Return before July 31 to avoid penalties.",
            "action_text": "Review Tax Summary",
            "action_route": "/tax",
        })
    
    # Advance Tax Reminder (for business/freelancers)
    income_types = income_profile.get("income_types", ["salaried"]) if income_profile else ["salaried"]
    if any(t in income_types for t in ["business", "freelancer", "investor"]):
        advance_tax_months = {6: "Q1 (15%)", 9: "Q2 (45%)", 12: "Q3 (75%)", 3: "Q4 (100%)"}
        if current_month in advance_tax_months:
            reminders.append({
                "id": f"advance_tax_q{list(advance_tax_months.keys()).index(current_month) + 1}",
                "type": "deadline",
                "urgency": "high",
                "title": f"Advance Tax Due - {advance_tax_months[current_month]}",
                "message": f"Pay advance tax by the 15th to avoid interest under Section 234C.",
                "action_text": "Calculate Tax",
                "action_route": "/tax",
            })
    
    # TDS Verification Reminder (Jan)
    if current_month == 1:
        reminders.append({
            "id": "tds_verification",
            "type": "reminder",
            "urgency": "low",
            "title": "Verify TDS with Employer",
            "message": "Check your salary slips and verify TDS deducted matches your investment proofs submitted.",
            "action_text": "Check TDS",
            "action_route": "/tax/tds-mismatch",
        })
    
    # Sort by urgency
    urgency_order = {"high": 0, "medium": 1, "low": 2}
    reminders.sort(key=lambda x: urgency_order.get(x["urgency"], 3))
    
    return {
        "fy": fy,
        "reminders": reminders,
        "count": len(reminders),
        "high_priority": len([r for r in reminders if r["urgency"] == "high"]),
    }
