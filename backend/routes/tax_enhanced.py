"""
Tax Enhanced Routes — Phase 0 + Phase 1
Income Profile (P0), Salary Profile Wizard (1.2), HRA Auto-Calc (1.3),
80C Limit Tracker (1.4), Enhanced Section Mapping with confidence (1.1)
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timezone
from database import db
from auth import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# ══════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════

METRO_CITIES = {"mumbai", "delhi", "new delhi", "kolkata", "chennai"}

PROFESSIONAL_TAX_BY_STATE = {
    "maharashtra": 2400,
    "karnataka": 2400,
    "west bengal": 2400,
    "andhra pradesh": 2400,
    "telangana": 2400,
    "gujarat": 2400,
    "kerala": 2400,
    "odisha": 2400,
    "assam": 2400,
    "bihar": 2500,
    "jharkhand": 2500,
    "tamil nadu": 1200,
    "madhya pradesh": 2400,
    "sikkim": 2400,
    "chhattisgarh": 2400,
    "nagaland": 2400,
    "manipur": 2400,
    "meghalaya": 2400,
    "tripura": 2400,
    # Delhi, UP, Punjab, Haryana, Rajasthan, HP → no professional tax (default 0)
}

LIMIT_80C = 150000
LIMIT_NPS_EXTRA = 50000

# Confidence-weighted keyword rules: (keywords_set, section, friendly_name, confidence)
CONFIDENCE_RULES = [
    ({"ppf", "public provident fund"}, "80C", "Public Provident Fund (PPF)", 0.95),
    ({"elss", "tax saver fund", "tax saving mutual fund", "tax saving fund"}, "80C", "ELSS / Tax Saver MF", 0.95),
    ({"sukanya samriddhi", "ssy"}, "80C", "Sukanya Samriddhi Yojana", 0.95),
    ({"lic premium", "lic payment", "life insurance", "term insurance", "term plan", "jeevan"}, "80C", "Life Insurance (LIC/Term)", 0.90),
    ({"epf", "employee provident fund", "pf contribution", "pf deposit", "provident fund"}, "80C", "EPF (Employee)", 0.90),
    ({"nsc", "national savings certificate"}, "80C", "NSC", 0.90),
    ({"tuition fee", "tuition fees", "school fee", "college fee"}, "80C", "Tuition Fees", 0.90),
    ({"home loan principal", "housing loan principal"}, "80C", "Home Loan Principal", 0.90),
    ({"tax saver fd", "tax saving fd", "5 year fd"}, "80C", "Tax Saver FD", 0.88),
    ({"nps tier 1", "national pension system", "national pension scheme"}, "80CCD1B", "NPS Contribution", 0.90),
    ({"hdfc ergo health", "star health", "niva bupa", "max bupa", "care health", "arogya sanjeevani"}, "80D", "Health Insurance Premium", 0.95),
    ({"health insurance", "mediclaim", "medical insurance", "health premium", "medical premium"}, "80D", "Health Insurance Premium", 0.85),
    ({"preventive health", "health checkup", "apollo diagnostics", "dr lal", "thyrocare"}, "80D", "Preventive Health Checkup", 0.85),
    ({"home loan interest", "housing loan interest", "mortgage interest"}, "24b", "Home Loan Interest", 0.90),
    ({"education loan interest", "student loan interest", "edu loan"}, "80E", "Education Loan Interest", 0.90),
    ({"pm cares", "pm relief", "cry india", "helpAge", "akshaya patra", "goonj"}, "80G", "Charitable Donation", 0.85),
    ({"donation", "charity"}, "80G", "Charitable Donation", 0.70),
    ({"home loan", "housing loan", "home emi"}, "80C", "Home Loan (Principal Component)", 0.60),
    ({"nps"}, "80CCD1B", "NPS Additional Contribution", 0.72),
    ({"insurance"}, "80D", "Insurance Premium (verify: health/life?)", 0.55),
    ({"rent paid", "house rent", "monthly rent"}, "HRA", "Rent Paid", 0.70),
]


def detect_city_type(city: str) -> str:
    return "metro" if city.lower().strip() in METRO_CITIES else "non_metro"


def get_professional_tax_for_state(state: str) -> float:
    return float(PROFESSIONAL_TAX_BY_STATE.get(state.lower().strip(), 0))


def compute_confidence_match(description: str, notes: str = "") -> Optional[tuple]:
    """Returns (section, name, confidence) or None."""
    text = f"{description} {notes or ''}".lower()
    best = None
    best_conf = 0.0
    for keywords, section, name, confidence in CONFIDENCE_RULES:
        for kw in keywords:
            if kw in text and confidence > best_conf:
                best_conf = confidence
                best = (section, name, confidence)
    return best


def categorize_80c_instrument(name: str) -> str:
    n = name.lower()
    if "elss" in n or "tax saver" in n or "tax saving" in n: return "ELSS / Tax Saver MF"
    if "ppf" in n or "public provident" in n: return "PPF"
    if "epf" in n or "provident fund" in n or "pf contribution" in n: return "EPF (Employee)"
    if "lic" in n or "life insurance" in n or "term" in n: return "Life Insurance (LIC/Term)"
    if "nsc" in n or "national savings cert" in n: return "NSC"
    if "sukanya" in n or "ssy" in n: return "Sukanya Samriddhi"
    if "home loan principal" in n or "housing loan principal" in n: return "Home Loan Principal"
    if "tuition" in n or "school fee" in n or "college fee" in n: return "Tuition Fees"
    if "tax saver fd" in n or "tax saving fd" in n: return "Tax Saver FD"
    if "ulip" in n: return "ULIP"
    return name[:40]


def compute_hra(profile: dict) -> dict:
    """HRA Exemption = min(actual HRA, city% of basic, rent - 10% basic)."""
    annual_basic = profile.get("monthly_basic", 0) * 12
    annual_hra = profile.get("monthly_hra", 0) * 12
    annual_rent = profile.get("monthly_rent", 0) * 12
    city_type = profile.get("city_type", "non_metro")

    if not profile.get("is_rent_paid") or annual_rent == 0:
        return {
            "applicable": False,
            "hra_exemption": 0,
            "taxable_hra": round(annual_hra, 2),
            "message": "Not applicable — no rent paid" if annual_hra > 0 else "Set rent details to compute HRA",
        }

    c1 = annual_hra
    c2 = annual_basic * (0.50 if city_type == "metro" else 0.40)
    c3 = max(0, annual_rent - (0.10 * annual_basic))

    exemption = min(c1, c2, c3)
    conditions = [c1, c2, c3]
    condition_names = [
        "Actual HRA Received",
        f"{'50' if city_type == 'metro' else '40'}% of Basic ({city_type.replace('_', '-').title()})",
        "Rent Paid − 10% of Basic",
    ]
    limiting_idx = conditions.index(exemption)
    pan_required = annual_rent > 100000

    return {
        "applicable": True,
        "annual_basic": round(annual_basic, 2),
        "annual_hra_received": round(annual_hra, 2),
        "annual_rent_paid": round(annual_rent, 2),
        "city_type": city_type,
        "condition_1_actual_hra": round(c1, 2),
        "condition_2_city_pct": round(c2, 2),
        "condition_3_rent_minus_basic": round(c3, 2),
        "hra_exemption": round(exemption, 2),
        "taxable_hra": round(max(0, annual_hra - exemption), 2),
        "limiting_condition": condition_names[limiting_idx],
        "landlord_pan_required": pan_required,
        "warning": "Landlord PAN mandatory — annual rent exceeds ₹1,00,000" if pan_required else None,
        "monthly_benefit": round(exemption / 12, 2),
        "tax_saved_30_slab": round(exemption * 0.30, 2),
        "tax_saved_20_slab": round(exemption * 0.20, 2),
    }


# ══════════════════════════════════════
#  PHASE 0: INCOME PROFILE
# ══════════════════════════════════════

class IncomeProfileCreate(BaseModel):
    income_types: List[str]
    primary_income_type: str = "salaried"
    fy: str = "2025-26"


@router.get("/tax/income-profile")
async def get_income_profile(user=Depends(get_current_user)):
    profile = await db.tax_income_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    return {"profile": profile}


@router.post("/tax/income-profile")
async def save_income_profile(data: IncomeProfileCreate, user=Depends(get_current_user)):
    doc = {
        "user_id": user["id"],
        "income_types": data.income_types,
        "primary_income_type": data.primary_income_type,
        "fy": data.fy,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tax_income_profiles.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
    return {"profile": doc}


@router.delete("/tax/income-profile")
async def delete_income_profile(user=Depends(get_current_user)):
    await db.tax_income_profiles.delete_one({"user_id": user["id"]})
    return {"status": "deleted"}


# ══════════════════════════════════════
#  PHASE 1.2: SALARY PROFILE
# ══════════════════════════════════════

class SalaryProfileCreate(BaseModel):
    fy: str = "2025-26"
    employer_name: str = ""
    employment_type: str = "salaried"
    monthly_basic: float = 0
    monthly_hra: float = 0
    monthly_special_allowance: float = 0
    monthly_lta: float = 0
    monthly_other_allowances: float = 0
    annual_bonus: float = 0
    employee_pf_monthly: float = 0
    professional_tax_annual: float = 0
    tds_monthly: float = 0
    residence_city: str = ""
    state: str = ""
    city_type: Optional[str] = None
    is_rent_paid: bool = False
    monthly_rent: float = 0
    landlord_pan_available: bool = False


@router.get("/tax/salary-profile")
async def get_salary_profile(user=Depends(get_current_user)):
    profile = await db.salary_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if profile:
        profile["hra_data"] = compute_hra(profile)
    return {"profile": profile}


@router.post("/tax/salary-profile")
async def save_salary_profile(data: SalaryProfileCreate, user=Depends(get_current_user)):
    city_type = data.city_type or detect_city_type(data.residence_city)
    gross_monthly = (
        data.monthly_basic + data.monthly_hra + data.monthly_special_allowance +
        data.monthly_lta + data.monthly_other_allowances
    )
    # Auto-suggest EPF at 12% of basic if not provided
    epf = data.employee_pf_monthly
    if epf == 0 and data.monthly_basic > 0:
        epf = round(min(data.monthly_basic * 0.12, 1800), 2)  # capped at ₹1800/month (EPFO ceiling)

    prof_tax = data.professional_tax_annual
    if prof_tax == 0 and data.state:
        prof_tax = get_professional_tax_for_state(data.state)

    doc = {
        "user_id": user["id"],
        "fy": data.fy,
        "employer_name": data.employer_name,
        "employment_type": data.employment_type,
        "monthly_basic": data.monthly_basic,
        "monthly_hra": data.monthly_hra,
        "monthly_special_allowance": data.monthly_special_allowance,
        "monthly_lta": data.monthly_lta,
        "monthly_other_allowances": data.monthly_other_allowances,
        "gross_monthly": round(gross_monthly, 2),
        "gross_annual": round(gross_monthly * 12 + data.annual_bonus, 2),
        "annual_bonus": data.annual_bonus,
        "employee_pf_monthly": epf,
        "professional_tax_annual": prof_tax,
        "tds_monthly": data.tds_monthly,
        "residence_city": data.residence_city,
        "state": data.state,
        "city_type": city_type,
        "is_rent_paid": data.is_rent_paid,
        "monthly_rent": data.monthly_rent if data.is_rent_paid else 0,
        "landlord_pan_available": data.landlord_pan_available,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.salary_profiles.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
    doc["hra_data"] = compute_hra(doc)
    return {"profile": doc}


@router.delete("/tax/salary-profile")
async def delete_salary_profile(user=Depends(get_current_user)):
    await db.salary_profiles.delete_one({"user_id": user["id"]})
    return {"status": "deleted"}


@router.get("/tax/state-prof-tax")
async def get_state_professional_tax(state: str = ""):
    """Returns professional tax for a given state (for UI auto-fill)."""
    amount = get_professional_tax_for_state(state)
    return {"state": state, "professional_tax_annual": amount}


# ══════════════════════════════════════
#  PHASE 1.3: HRA CALCULATION
# ══════════════════════════════════════

@router.get("/tax/hra-calculation")
async def get_hra_calculation(user=Depends(get_current_user)):
    profile = await db.salary_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        return {"hra_data": None, "message": "Set up your salary profile to compute HRA exemption"}
    return {"hra_data": compute_hra(profile)}


# ══════════════════════════════════════
#  PHASE 1.4: 80C LIMIT TRACKER
# ══════════════════════════════════════

@router.get("/tax/80c-summary")
async def get_80c_summary(user=Depends(get_current_user), fy: str = "2025-26"):
    user_id = user["id"]

    # Gather all auto-detected 80C deductions for this FY
    auto_deds = await db.auto_tax_deductions.find(
        {"user_id": user_id, "fy": fy, "section": {"$in": ["80C", "80CCD1B", "80CCD(1B)"]}},
        {"_id": 0}
    ).to_list(300)

    # Gather manually added 80C deductions
    user_deds = await db.user_tax_deductions.find(
        {"user_id": user_id, "section": {"$in": ["80C", "80CCD1B", "80CCD(1B)"]}},
        {"_id": 0}
    ).to_list(100)

    # Salary profile for EPF
    salary_profile = await db.salary_profiles.find_one({"user_id": user_id}, {"_id": 0})

    instruments_80c: dict = {}
    instruments_nps: dict = {}

    def add_to(bucket: dict, key: str, amount: float, source: str):
        if key not in bucket:
            bucket[key] = {"name": key, "amount": 0, "source": source}
        bucket[key]["amount"] += amount

    for d in auto_deds:
        section = d.get("section", "80C")
        bucket = instruments_nps if section in ("80CCD1B", "80CCD(1B)") else instruments_80c
        key = categorize_80c_instrument(d.get("name", "Investment"))
        add_to(bucket, key, d.get("amount", 0), d.get("detected_from", "auto"))

    for d in user_deds:
        section = d.get("section", "80C")
        bucket = instruments_nps if section in ("80CCD1B", "80CCD(1B)") else instruments_80c
        key = d.get("name", "Manual Entry")
        add_to(bucket, key, d.get("invested_amount", 0), "manual")

    # Add EPF from salary profile if not already counted from transactions
    if salary_profile and salary_profile.get("employee_pf_monthly", 0) > 0:
        epf_annual = salary_profile["employee_pf_monthly"] * 12
        has_epf = any(
            "epf" in k.lower() or "provident fund" in k.lower()
            for k in instruments_80c
        )
        if not has_epf:
            add_to(instruments_80c, "EPF (Employee)", round(epf_annual, 2), "salary_profile")

    total_80c = round(sum(v["amount"] for v in instruments_80c.values()), 2)
    total_nps = round(sum(v["amount"] for v in instruments_nps.values()), 2)
    remaining_80c = round(max(0, LIMIT_80C - total_80c), 2)
    over_limit = round(max(0, total_80c - LIMIT_80C), 2)
    util_pct = round(min(100, (total_80c / LIMIT_80C * 100)), 1) if LIMIT_80C else 0

    if remaining_80c <= 10000:
        status, rec = "optimized", "80C fully optimized! Great tax planning."
    elif remaining_80c > 75000:
        status = "under_utilized"
        rec = f"₹{remaining_80c:,.0f} remaining in 80C — consider ELSS SIP for market-linked returns with 3-year lock-in."
    else:
        status = "good"
        rec = f"₹{remaining_80c:,.0f} more to fully optimize 80C. A quick ELSS top-up will do."

    instruments_list = sorted(
        [{"name": k, **v} for k, v in instruments_80c.items()], key=lambda x: -x["amount"]
    )
    nps_list = sorted(
        [{"name": k, **v} for k, v in instruments_nps.items()], key=lambda x: -x["amount"]
    )

    return {
        "fy": fy,
        "instruments_80c": instruments_list,
        "total_80c": total_80c,
        "limit_80c": LIMIT_80C,
        "remaining_80c": remaining_80c,
        "over_limit_80c": over_limit,
        "utilization_percentage": util_pct,
        "status": status,
        "recommendation": rec,
        "nps_80ccd_1b": nps_list,
        "total_nps": total_nps,
        "nps_limit": LIMIT_NPS_EXTRA,
        "nps_remaining": round(max(0, LIMIT_NPS_EXTRA - total_nps), 2),
        "nps_utilization_pct": round(min(100, (total_nps / LIMIT_NPS_EXTRA * 100)), 1) if LIMIT_NPS_EXTRA else 0,
    }


# ══════════════════════════════════════
#  PHASE 1.1: REMAP TRANSACTIONS — ENHANCED CONFIDENCE MAPPING
# ══════════════════════════════════════

@router.post("/tax/remap-transactions")
async def remap_with_confidence(user=Depends(get_current_user), fy: str = "2025-26"):
    """Re-runs enhanced section mapping with confidence scores on all transactions for the FY."""
    from routes.tax import TAX_SECTION_NAMES, TAX_SECTION_LIMITS

    user_id = user["id"]
    fy_start = f"{int(fy.split('-')[0])}-04-01"
    fy_end = f"{int(fy.split('-')[0]) + 1}-03-31"

    # Remove only transaction-sourced auto-deductions (keep holdings/loans/sip entries)
    await db.auto_tax_deductions.delete_many({
        "user_id": user_id, "fy": fy,
        "detected_from": {"$in": ["description", "category"]},
    })

    txns = await db.transactions.find(
        {"user_id": user_id, "date": {"$gte": fy_start, "$lte": fy_end}},
        {"_id": 0}
    ).to_list(5000)

    new_docs = []
    for t in txns:
        result = compute_confidence_match(t.get("description", ""), t.get("notes", ""))
        if not result:
            continue
        section, name, confidence = result
        doc = {
            "id": str(uuid4()),
            "user_id": user_id,
            "transaction_id": t.get("id", ""),
            "section": section,
            "section_label": TAX_SECTION_NAMES.get(section, f"Section {section}"),
            "name": name,
            "amount": round(t.get("amount", 0), 2),
            "limit": TAX_SECTION_LIMITS.get(section, 0),
            "fy": fy,
            "detected_from": "description",
            "confidence": confidence,
            "source_category": t.get("category", ""),
            "source_description": t.get("description", ""),
            "source_date": t.get("date", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        new_docs.append(doc)

    if new_docs:
        await db.auto_tax_deductions.insert_many(new_docs)
        for d in new_docs:
            d.pop("_id", None)

    high = sum(1 for d in new_docs if d.get("confidence", 0) >= 0.80)
    review = sum(1 for d in new_docs if d.get("confidence", 0) < 0.70)
    return {
        "status": "remapped",
        "fy": fy,
        "total_found": len(new_docs),
        "high_confidence": high,
        "needs_review": review,
    }
