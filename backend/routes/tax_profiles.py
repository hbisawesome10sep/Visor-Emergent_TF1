"""
Non-Salaried Tax Profiles — Phase 3b
Freelancer (Section 44ADA), Business Owner (Section 44AD), 
Investor/F&O (Speculative Income), Rental Income (House Property)
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
from database import db
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tax")


# ══════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════

# Section 44ADA - Eligible Professions (ICAI, ICSI, etc.)
ELIGIBLE_44ADA_PROFESSIONS = [
    "chartered_accountant",
    "company_secretary",
    "cost_accountant",
    "doctor",
    "lawyer",
    "architect",
    "engineer",
    "interior_decorator",
    "film_artist",
    "authorized_representative",
    "consultant",
    "freelance_developer",
    "freelance_designer",
    "freelance_writer",
    "other_professional",
]

# Section 44AD - Eligible Businesses
ELIGIBLE_44AD_BUSINESSES = [
    "retail_trade",
    "wholesale_trade",
    "manufacturing",
    "contractor",
    "commission_agent",
    "transport_operator",
    "restaurant",
    "other_business",
]

# Presumptive rates
RATE_44ADA = 0.50  # 50% of gross receipts deemed profit for professionals
RATE_44AD_CASH = 0.08  # 8% for cash/cheque receipts
RATE_44AD_DIGITAL = 0.06  # 6% for digital receipts

# F&O / Speculative income thresholds
FO_TURNOVER_LIMIT = 10000000  # ₹1 Crore - beyond this, audit required

# House Property
STANDARD_DEDUCTION_HP = 0.30  # 30% standard deduction on rental income
MUNICIPAL_TAX_DEDUCTION = True  # Municipal taxes paid are deductible


# ══════════════════════════════════════
#  PYDANTIC MODELS
# ══════════════════════════════════════

class FreelancerProfile(BaseModel):
    profession: str
    gross_receipts: float
    expenses_claimed: Optional[float] = None  # Optional: if user wants to claim actual expenses
    use_presumptive: bool = True
    bank_account_for_receipts: Optional[str] = None
    gst_registered: bool = False
    gst_number: Optional[str] = None
    fy: str = "2025-26"


class BusinessProfile(BaseModel):
    business_type: str
    business_name: Optional[str] = None
    gross_turnover: float
    digital_receipts_pct: float = 60.0  # % received via digital modes
    expenses_claimed: Optional[float] = None
    use_presumptive: bool = True
    gst_registered: bool = False
    gst_number: Optional[str] = None
    fy: str = "2025-26"


class InvestorProfile(BaseModel):
    has_equity_delivery: bool = False
    equity_delivery_turnover: float = 0
    equity_delivery_profit: float = 0
    
    has_intraday: bool = False
    intraday_turnover: float = 0
    intraday_profit: float = 0
    
    has_futures: bool = False
    futures_turnover: float = 0
    futures_profit: float = 0
    
    has_options: bool = False
    options_turnover: float = 0
    options_profit: float = 0
    
    has_crypto: bool = False
    crypto_profit: float = 0
    
    demat_broker: Optional[str] = None
    fy: str = "2025-26"


class RentalProperty(BaseModel):
    property_name: str
    property_type: str = "residential"  # residential, commercial
    gross_annual_rent: float
    municipal_taxes_paid: float = 0
    home_loan_interest: float = 0  # Section 24(b)
    is_self_occupied: bool = False
    fy: str = "2025-26"


class RentalProfile(BaseModel):
    properties: List[RentalProperty]
    fy: str = "2025-26"


# ══════════════════════════════════════
#  FREELANCER (SECTION 44ADA)
# ══════════════════════════════════════

def compute_44ada_income(profile: dict) -> dict:
    """
    Section 44ADA - Presumptive Taxation for Professionals
    - Applicable if gross receipts ≤ ₹75L (₹50L if < 5% digital)
    - 50% of gross receipts deemed as profit
    - No need to maintain books of accounts
    - Can claim lower profit if books maintained and audited
    """
    gross = profile.get("gross_receipts", 0)
    use_presumptive = profile.get("use_presumptive", True)
    expenses_claimed = profile.get("expenses_claimed")
    
    # Check eligibility
    presumptive_limit = 7500000  # ₹75L for FY 2024-25 onwards
    is_eligible = gross <= presumptive_limit
    
    if use_presumptive and is_eligible:
        deemed_profit = gross * RATE_44ADA
        deemed_expenses = gross - deemed_profit
        actual_expenses = None
        method = "presumptive_44ada"
    else:
        # Actual income/expenses method
        actual_expenses = expenses_claimed if expenses_claimed else gross * 0.30  # Assume 30% if not provided
        deemed_profit = gross - actual_expenses
        deemed_expenses = actual_expenses
        method = "actual"
    
    return {
        "gross_receipts": round(gross, 2),
        "method": method,
        "presumptive_rate": RATE_44ADA if method == "presumptive_44ada" else None,
        "deemed_expenses": round(deemed_expenses, 2),
        "taxable_income": round(deemed_profit, 2),
        "eligible_for_44ada": is_eligible,
        "presumptive_limit": presumptive_limit,
        "audit_required": gross > presumptive_limit or (not use_presumptive and deemed_profit < gross * RATE_44ADA),
        "advance_tax_applicable": deemed_profit > 0,
        "itr_form": "ITR-4 (Sugam)",
        "notes": [
            "50% of gross receipts treated as taxable income under 44ADA",
            "No books of accounts required if opting for presumptive",
            "Advance tax due in full by March 15 (single installment allowed)",
            "GST registration required if turnover > ₹20L (₹10L for special states)",
        ],
    }


@router.get("/freelancer-profile")
async def get_freelancer_profile(user=Depends(get_current_user), fy: str = "2025-26"):
    """Get freelancer profile for the user."""
    profile = await db.freelancer_profiles.find_one(
        {"user_id": user["id"], "fy": fy},
        {"_id": 0}
    )
    if profile:
        profile["computation"] = compute_44ada_income(profile)
    return {"profile": profile}


@router.post("/freelancer-profile")
async def save_freelancer_profile(data: FreelancerProfile, user=Depends(get_current_user)):
    """Save freelancer profile (Section 44ADA)."""
    doc = {
        "user_id": user["id"],
        "fy": data.fy,
        "profession": data.profession,
        "gross_receipts": data.gross_receipts,
        "expenses_claimed": data.expenses_claimed,
        "use_presumptive": data.use_presumptive,
        "bank_account_for_receipts": data.bank_account_for_receipts,
        "gst_registered": data.gst_registered,
        "gst_number": data.gst_number,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.freelancer_profiles.update_one(
        {"user_id": user["id"], "fy": data.fy},
        {"$set": doc},
        upsert=True,
    )
    
    doc["computation"] = compute_44ada_income(doc)
    return {"status": "saved", "profile": doc}


# ══════════════════════════════════════
#  BUSINESS OWNER (SECTION 44AD)
# ══════════════════════════════════════

def compute_44ad_income(profile: dict) -> dict:
    """
    Section 44AD - Presumptive Taxation for Business
    - Applicable if turnover ≤ ₹3 Crore (₹2 Cr if < 5% digital)
    - 6% of digital receipts + 8% of cash receipts deemed as profit
    - No need to maintain books of accounts
    """
    turnover = profile.get("gross_turnover", 0)
    digital_pct = profile.get("digital_receipts_pct", 60) / 100
    use_presumptive = profile.get("use_presumptive", True)
    expenses_claimed = profile.get("expenses_claimed")
    
    # Check eligibility
    presumptive_limit = 30000000  # ₹3 Crore for FY 2024-25 onwards (if > 5% digital)
    is_eligible = turnover <= presumptive_limit
    
    digital_amount = turnover * digital_pct
    cash_amount = turnover * (1 - digital_pct)
    
    if use_presumptive and is_eligible:
        digital_profit = digital_amount * RATE_44AD_DIGITAL
        cash_profit = cash_amount * RATE_44AD_CASH
        deemed_profit = digital_profit + cash_profit
        blended_rate = deemed_profit / turnover if turnover > 0 else 0
        method = "presumptive_44ad"
    else:
        actual_expenses = expenses_claimed if expenses_claimed else turnover * 0.70  # Assume 70% if not provided
        deemed_profit = turnover - actual_expenses
        blended_rate = None
        method = "actual"
    
    return {
        "gross_turnover": round(turnover, 2),
        "digital_receipts": round(digital_amount, 2),
        "cash_receipts": round(cash_amount, 2),
        "digital_pct": round(digital_pct * 100, 1),
        "method": method,
        "digital_rate": RATE_44AD_DIGITAL if method == "presumptive_44ad" else None,
        "cash_rate": RATE_44AD_CASH if method == "presumptive_44ad" else None,
        "blended_rate": round(blended_rate * 100, 2) if blended_rate else None,
        "taxable_income": round(deemed_profit, 2),
        "eligible_for_44ad": is_eligible,
        "presumptive_limit": presumptive_limit,
        "audit_required": turnover > presumptive_limit or (not use_presumptive and deemed_profit < turnover * RATE_44AD_DIGITAL),
        "advance_tax_applicable": deemed_profit > 0,
        "itr_form": "ITR-4 (Sugam)",
        "notes": [
            f"Digital receipts: 6% deemed profit = ₹{digital_amount * RATE_44AD_DIGITAL:,.0f}",
            f"Cash receipts: 8% deemed profit = ₹{cash_amount * RATE_44AD_CASH:,.0f}",
            "No books required if opting for presumptive scheme",
            "Advance tax due in full by March 15",
        ],
    }


@router.get("/business-profile")
async def get_business_profile(user=Depends(get_current_user), fy: str = "2025-26"):
    """Get business owner profile for the user."""
    profile = await db.business_profiles.find_one(
        {"user_id": user["id"], "fy": fy},
        {"_id": 0}
    )
    if profile:
        profile["computation"] = compute_44ad_income(profile)
    return {"profile": profile}


@router.post("/business-profile")
async def save_business_profile(data: BusinessProfile, user=Depends(get_current_user)):
    """Save business owner profile (Section 44AD)."""
    doc = {
        "user_id": user["id"],
        "fy": data.fy,
        "business_type": data.business_type,
        "business_name": data.business_name,
        "gross_turnover": data.gross_turnover,
        "digital_receipts_pct": data.digital_receipts_pct,
        "expenses_claimed": data.expenses_claimed,
        "use_presumptive": data.use_presumptive,
        "gst_registered": data.gst_registered,
        "gst_number": data.gst_number,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.business_profiles.update_one(
        {"user_id": user["id"], "fy": data.fy},
        {"$set": doc},
        upsert=True,
    )
    
    doc["computation"] = compute_44ad_income(doc)
    return {"status": "saved", "profile": doc}


# ══════════════════════════════════════
#  INVESTOR / F&O PROFILE
# ══════════════════════════════════════

def compute_investor_income(profile: dict) -> dict:
    """
    Compute investor income from various sources:
    - Equity Delivery: STCG (20%) / LTCG (12.5% above ₹1.25L)
    - Intraday: Speculative Business Income (taxed at slab)
    - F&O: Non-speculative Business Income (taxed at slab)
    - Crypto: 30% flat + 1% TDS
    """
    # Equity Delivery (Capital Gains)
    equity_profit = profile.get("equity_delivery_profit", 0)
    equity_turnover = profile.get("equity_delivery_turnover", 0)
    
    # Intraday (Speculative)
    intraday_profit = profile.get("intraday_profit", 0)
    intraday_turnover = profile.get("intraday_turnover", 0)
    
    # F&O (Non-Speculative Business)
    futures_profit = profile.get("futures_profit", 0)
    futures_turnover = profile.get("futures_turnover", 0)
    options_profit = profile.get("options_profit", 0)
    options_turnover = profile.get("options_turnover", 0)
    fo_total_profit = futures_profit + options_profit
    fo_total_turnover = futures_turnover + options_turnover
    
    # Crypto (VDA)
    crypto_profit = profile.get("crypto_profit", 0)
    crypto_tax = crypto_profit * 0.30 if crypto_profit > 0 else 0
    
    # Audit requirement check
    fo_audit_required = fo_total_turnover > FO_TURNOVER_LIMIT
    
    # ITR form determination
    if fo_total_profit != 0 or intraday_profit != 0:
        itr_form = "ITR-3"
    elif equity_profit != 0 or crypto_profit != 0:
        itr_form = "ITR-2"
    else:
        itr_form = "ITR-1/ITR-2"
    
    return {
        "equity_delivery": {
            "turnover": round(equity_turnover, 2),
            "profit_loss": round(equity_profit, 2),
            "tax_type": "Capital Gains (STCG 20% / LTCG 12.5%)",
            "ltcg_exemption": 125000,
        },
        "intraday": {
            "turnover": round(intraday_turnover, 2),
            "profit_loss": round(intraday_profit, 2),
            "tax_type": "Speculative Business Income (Slab Rate)",
            "loss_setoff": "Only against speculative income (4 years)",
        },
        "futures_options": {
            "futures_turnover": round(futures_turnover, 2),
            "futures_profit": round(futures_profit, 2),
            "options_turnover": round(options_turnover, 2),
            "options_profit": round(options_profit, 2),
            "total_turnover": round(fo_total_turnover, 2),
            "total_profit_loss": round(fo_total_profit, 2),
            "tax_type": "Non-Speculative Business Income (Slab Rate)",
            "audit_required": fo_audit_required,
            "audit_limit": FO_TURNOVER_LIMIT,
            "loss_setoff": "Against any income except salary (8 years)",
        },
        "crypto": {
            "profit_loss": round(crypto_profit, 2),
            "tax_rate": "30% flat",
            "estimated_tax": round(crypto_tax, 2),
            "tds_rate": "1% on transfers",
            "loss_setoff": "Not allowed",
        },
        "total_taxable": {
            "capital_gains": round(equity_profit, 2),
            "speculative_income": round(intraday_profit, 2),
            "business_income_fo": round(fo_total_profit, 2),
            "crypto_income": round(crypto_profit, 2),
        },
        "itr_form": itr_form,
        "advance_tax_required": (fo_total_profit + intraday_profit) > 10000,
        "notes": [
            "F&O profit/loss is business income, not capital gains",
            "Intraday is speculative — losses only offset speculative gains",
            "Crypto losses cannot be set off against any other income",
            "Audit required if F&O turnover > ₹1 Crore",
        ],
    }


@router.get("/investor-profile")
async def get_investor_profile(user=Depends(get_current_user), fy: str = "2025-26"):
    """Get investor/trader profile for the user."""
    profile = await db.investor_profiles.find_one(
        {"user_id": user["id"], "fy": fy},
        {"_id": 0}
    )
    if profile:
        profile["computation"] = compute_investor_income(profile)
    return {"profile": profile}


@router.post("/investor-profile")
async def save_investor_profile(data: InvestorProfile, user=Depends(get_current_user)):
    """Save investor/trader profile."""
    doc = {
        "user_id": user["id"],
        "fy": data.fy,
        "has_equity_delivery": data.has_equity_delivery,
        "equity_delivery_turnover": data.equity_delivery_turnover,
        "equity_delivery_profit": data.equity_delivery_profit,
        "has_intraday": data.has_intraday,
        "intraday_turnover": data.intraday_turnover,
        "intraday_profit": data.intraday_profit,
        "has_futures": data.has_futures,
        "futures_turnover": data.futures_turnover,
        "futures_profit": data.futures_profit,
        "has_options": data.has_options,
        "options_turnover": data.options_turnover,
        "options_profit": data.options_profit,
        "has_crypto": data.has_crypto,
        "crypto_profit": data.crypto_profit,
        "demat_broker": data.demat_broker,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.investor_profiles.update_one(
        {"user_id": user["id"], "fy": data.fy},
        {"$set": doc},
        upsert=True,
    )
    
    doc["computation"] = compute_investor_income(doc)
    return {"status": "saved", "profile": doc}


# ══════════════════════════════════════
#  RENTAL INCOME (HOUSE PROPERTY)
# ══════════════════════════════════════

def compute_rental_income(properties: List[dict]) -> dict:
    """
    Compute income from house property:
    - Gross Annual Value (GAV) = Higher of Actual Rent or Expected Rent
    - Less: Municipal Taxes
    - Net Annual Value (NAV) = GAV - Municipal Taxes
    - Less: Standard Deduction (30% of NAV)
    - Less: Home Loan Interest (Section 24b, max ₹2L for self-occupied, no limit for let-out)
    - = Income from House Property
    """
    total_gross_rent = 0
    total_municipal = 0
    total_standard_ded = 0
    total_interest = 0
    total_taxable = 0
    
    property_details = []
    
    for p in properties:
        gross_rent = p.get("gross_annual_rent", 0)
        municipal = p.get("municipal_taxes_paid", 0)
        interest = p.get("home_loan_interest", 0)
        is_self_occupied = p.get("is_self_occupied", False)
        
        if is_self_occupied:
            # Self-occupied: GAV = 0, only interest deduction (max ₹2L)
            nav = 0
            standard_ded = 0
            interest_allowed = min(interest, 200000)
            taxable = -interest_allowed  # Loss from self-occupied
        else:
            # Let-out property
            nav = gross_rent - municipal
            standard_ded = nav * STANDARD_DEDUCTION_HP
            interest_allowed = interest  # No limit for let-out
            taxable = nav - standard_ded - interest_allowed
        
        property_details.append({
            "property_name": p.get("property_name", "Property"),
            "property_type": p.get("property_type", "residential"),
            "is_self_occupied": is_self_occupied,
            "gross_annual_rent": round(gross_rent, 2),
            "municipal_taxes": round(municipal, 2),
            "net_annual_value": round(nav, 2),
            "standard_deduction_30pct": round(standard_ded, 2),
            "home_loan_interest_24b": round(interest_allowed, 2),
            "taxable_income": round(taxable, 2),
        })
        
        total_gross_rent += gross_rent
        total_municipal += municipal
        total_standard_ded += standard_ded
        total_interest += interest_allowed
        total_taxable += taxable
    
    # Loss from house property can be set off against other income (max ₹2L per year)
    setoff_limit = 200000
    can_setoff = min(abs(total_taxable), setoff_limit) if total_taxable < 0 else 0
    
    return {
        "properties": property_details,
        "summary": {
            "total_properties": len(properties),
            "total_gross_rent": round(total_gross_rent, 2),
            "total_municipal_taxes": round(total_municipal, 2),
            "total_standard_deduction": round(total_standard_ded, 2),
            "total_loan_interest": round(total_interest, 2),
            "total_taxable_income": round(total_taxable, 2),
            "loss_setoff_allowed": round(can_setoff, 2) if total_taxable < 0 else 0,
            "carry_forward_loss": round(abs(total_taxable) - can_setoff, 2) if total_taxable < 0 else 0,
        },
        "itr_form": "ITR-2" if len(properties) > 0 else "ITR-1",
        "notes": [
            "30% standard deduction is mandatory (no actual expense claims)",
            "Self-occupied: Interest deduction max ₹2L under Section 24(b)",
            "Let-out: No limit on interest deduction",
            "House property loss can offset other income up to ₹2L/year",
            "Excess loss can be carried forward for 8 years",
        ],
    }


@router.get("/rental-profile")
async def get_rental_profile(user=Depends(get_current_user), fy: str = "2025-26"):
    """Get rental income profile for the user."""
    profile = await db.rental_profiles.find_one(
        {"user_id": user["id"], "fy": fy},
        {"_id": 0}
    )
    if profile and profile.get("properties"):
        profile["computation"] = compute_rental_income(profile["properties"])
    return {"profile": profile}


@router.post("/rental-profile")
async def save_rental_profile(data: RentalProfile, user=Depends(get_current_user)):
    """Save rental income profile."""
    properties = [p.dict() for p in data.properties]
    
    doc = {
        "user_id": user["id"],
        "fy": data.fy,
        "properties": properties,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.rental_profiles.update_one(
        {"user_id": user["id"], "fy": data.fy},
        {"$set": doc},
        upsert=True,
    )
    
    doc["computation"] = compute_rental_income(properties)
    return {"status": "saved", "profile": doc}


@router.post("/rental-profile/add-property")
async def add_rental_property(property_data: RentalProperty, user=Depends(get_current_user)):
    """Add a rental property to the profile."""
    fy = property_data.fy
    
    # Get existing profile
    profile = await db.rental_profiles.find_one(
        {"user_id": user["id"], "fy": fy},
        {"_id": 0}
    )
    
    properties = profile.get("properties", []) if profile else []
    properties.append(property_data.dict())
    
    doc = {
        "user_id": user["id"],
        "fy": fy,
        "properties": properties,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.rental_profiles.update_one(
        {"user_id": user["id"], "fy": fy},
        {"$set": doc},
        upsert=True,
    )
    
    doc["computation"] = compute_rental_income(properties)
    return {"status": "added", "profile": doc}


# ══════════════════════════════════════
#  CONSOLIDATED TAX COMPUTATION
# ══════════════════════════════════════

@router.get("/consolidated-income")
async def get_consolidated_income(user=Depends(get_current_user), fy: str = "2025-26"):
    """
    Get consolidated income from all sources for tax computation.
    Combines: Salary, Freelancer, Business, Investor, Rental
    """
    user_id = user["id"]
    
    # Fetch all profiles
    salary_profile = await db.salary_profiles.find_one({"user_id": user_id, "fy": fy}, {"_id": 0})
    freelancer_profile = await db.freelancer_profiles.find_one({"user_id": user_id, "fy": fy}, {"_id": 0})
    business_profile = await db.business_profiles.find_one({"user_id": user_id, "fy": fy}, {"_id": 0})
    investor_profile = await db.investor_profiles.find_one({"user_id": user_id, "fy": fy}, {"_id": 0})
    rental_profile = await db.rental_profiles.find_one({"user_id": user_id, "fy": fy}, {"_id": 0})
    income_profile = await db.tax_income_profiles.find_one({"user_id": user_id}, {"_id": 0})
    
    income_sources = {}
    total_income = 0
    
    # Salary Income
    if salary_profile:
        gross_salary = salary_profile.get("gross_annual", 0)
        standard_ded = min(75000, gross_salary)  # FY 2024-25 onwards
        net_salary = gross_salary - standard_ded
        income_sources["salary"] = {
            "gross": round(gross_salary, 2),
            "standard_deduction": round(standard_ded, 2),
            "taxable": round(net_salary, 2),
        }
        total_income += net_salary
    
    # Freelancer Income (44ADA)
    if freelancer_profile:
        computation = compute_44ada_income(freelancer_profile)
        income_sources["freelancer"] = {
            "gross_receipts": computation["gross_receipts"],
            "taxable": computation["taxable_income"],
            "method": computation["method"],
            "itr_form": computation["itr_form"],
        }
        total_income += computation["taxable_income"]
    
    # Business Income (44AD)
    if business_profile:
        computation = compute_44ad_income(business_profile)
        income_sources["business"] = {
            "gross_turnover": computation["gross_turnover"],
            "taxable": computation["taxable_income"],
            "method": computation["method"],
            "itr_form": computation["itr_form"],
        }
        total_income += computation["taxable_income"]
    
    # Investor Income
    if investor_profile:
        computation = compute_investor_income(investor_profile)
        investor_taxable = (
            computation["total_taxable"]["speculative_income"] +
            computation["total_taxable"]["business_income_fo"]
        )
        income_sources["investor"] = {
            "capital_gains": computation["total_taxable"]["capital_gains"],
            "speculative_income": computation["total_taxable"]["speculative_income"],
            "fo_income": computation["total_taxable"]["business_income_fo"],
            "crypto_income": computation["total_taxable"]["crypto_income"],
            "taxable_as_business": round(investor_taxable, 2),
            "itr_form": computation["itr_form"],
        }
        total_income += investor_taxable
    
    # Rental Income
    if rental_profile and rental_profile.get("properties"):
        computation = compute_rental_income(rental_profile["properties"])
        rental_taxable = computation["summary"]["total_taxable_income"]
        income_sources["rental"] = {
            "total_rent": computation["summary"]["total_gross_rent"],
            "taxable": round(rental_taxable, 2),
            "properties_count": computation["summary"]["total_properties"],
            "itr_form": computation["itr_form"],
        }
        total_income += rental_taxable
    
    # Determine ITR form based on income sources
    if "investor" in income_sources and income_sources["investor"].get("fo_income", 0) != 0:
        itr_form = "ITR-3"
    elif "business" in income_sources or "freelancer" in income_sources:
        itr_form = "ITR-4 (Sugam)"
    elif "rental" in income_sources or "investor" in income_sources:
        itr_form = "ITR-2"
    else:
        itr_form = "ITR-1 (Sahaj)"
    
    return {
        "fy": fy,
        "income_types": income_profile.get("income_types", []) if income_profile else [],
        "income_sources": income_sources,
        "total_taxable_income": round(total_income, 2),
        "recommended_itr_form": itr_form,
        "profiles_available": {
            "salary": salary_profile is not None,
            "freelancer": freelancer_profile is not None,
            "business": business_profile is not None,
            "investor": investor_profile is not None,
            "rental": rental_profile is not None,
        },
    }


# ══════════════════════════════════════
#  HELPER ENDPOINTS
# ══════════════════════════════════════

@router.get("/professions-list")
async def get_professions_list():
    """Get list of eligible professions for Section 44ADA."""
    return {
        "professions": [
            {"id": p, "label": p.replace("_", " ").title()}
            for p in ELIGIBLE_44ADA_PROFESSIONS
        ]
    }


@router.get("/business-types-list")
async def get_business_types_list():
    """Get list of eligible business types for Section 44AD."""
    return {
        "business_types": [
            {"id": b, "label": b.replace("_", " ").title()}
            for b in ELIGIBLE_44AD_BUSINESSES
        ]
    }
