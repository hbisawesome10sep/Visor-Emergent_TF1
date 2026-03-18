"""
Phase 3: EMI & SIP Analytics
  - Principal vs Interest split analysis
  - Prepayment calculator
  - SIP analytics dashboard
  - Wealth projector
  - Goal-SIP mapping
"""

from fastapi import APIRouter, Depends, Body, HTTPException
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from database import db
from auth import get_current_user
from routes.loans import calculate_emi, generate_emi_schedule
import math
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# ─── EMI: Principal vs Interest Overview ────────────────────────
@router.get("/emi-analytics/overview")
async def emi_analytics_overview(user=Depends(get_current_user)):
    """
    Returns aggregated principal vs interest breakdown across all loans,
    per-loan split, and a monthly amortization timeline.
    """
    user_id = user["id"]
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)

    if not loans:
        return {
            "total_principal_paid": 0,
            "total_interest_paid": 0,
            "total_outstanding": 0,
            "total_emi_per_month": 0,
            "interest_to_principal_ratio": 0,
            "loans": [],
            "monthly_timeline": [],
        }

    all_loans = []
    grand_principal_paid = 0
    grand_interest_paid = 0
    grand_outstanding = 0
    grand_monthly_emi = 0
    timeline_map = {}  # month_str -> {principal, interest}

    for loan in loans:
        emi = loan.get("emi_amount") or calculate_emi(
            loan["principal_amount"], loan["interest_rate"], loan["tenure_months"]
        )
        schedule = generate_emi_schedule(
            loan["principal_amount"], loan["interest_rate"],
            loan["tenure_months"], loan["start_date"], emi
        )

        paid = [s for s in schedule if s["status"] == "paid"]
        p_paid = sum(s["principal"] for s in paid)
        i_paid = sum(s["interest"] for s in paid)
        outstanding = loan["principal_amount"] - p_paid
        total_interest_lifetime = sum(s["interest"] for s in schedule)
        total_paid_lifetime = sum(s["emi"] for s in schedule)

        grand_principal_paid += p_paid
        grand_interest_paid += i_paid
        grand_outstanding += outstanding
        grand_monthly_emi += emi

        # Build per-month timeline
        for entry in schedule:
            month_key = entry["date"][:7]  # YYYY-MM
            if month_key not in timeline_map:
                timeline_map[month_key] = {"month": month_key, "principal": 0, "interest": 0}
            timeline_map[month_key]["principal"] += entry["principal"]
            timeline_map[month_key]["interest"] += entry["interest"]

        all_loans.append({
            "id": loan["id"],
            "name": loan["name"],
            "loan_type": loan.get("loan_type", "Personal"),
            "lender": loan.get("lender", ""),
            "principal_amount": loan["principal_amount"],
            "interest_rate": loan["interest_rate"],
            "tenure_months": loan["tenure_months"],
            "emi_amount": emi,
            "principal_paid": round(p_paid, 2),
            "interest_paid": round(i_paid, 2),
            "outstanding": round(max(0, outstanding), 2),
            "total_interest_lifetime": round(total_interest_lifetime, 2),
            "total_cost": round(total_paid_lifetime, 2),
            "progress_pct": round(len(paid) / max(1, loan["tenure_months"]) * 100, 1),
            "remaining_emis": loan["tenure_months"] - len(paid),
        })

    timeline = sorted(timeline_map.values(), key=lambda x: x["month"])
    for t in timeline:
        t["principal"] = round(t["principal"], 2)
        t["interest"] = round(t["interest"], 2)

    ratio = round(grand_interest_paid / max(1, grand_principal_paid), 2)

    return {
        "total_principal_paid": round(grand_principal_paid, 2),
        "total_interest_paid": round(grand_interest_paid, 2),
        "total_outstanding": round(grand_outstanding, 2),
        "total_emi_per_month": round(grand_monthly_emi, 2),
        "interest_to_principal_ratio": ratio,
        "loans": all_loans,
        "monthly_timeline": timeline[-24:],  # Last 24 months
    }


# ─── EMI: Prepayment Calculator ────────────────────────────────
@router.post("/emi-analytics/prepayment")
async def emi_prepayment_calculator(body=Body(...), user=Depends(get_current_user)):
    """
    Calculate savings from making a prepayment on a loan.
    Body: { loan_id, prepayment_amount, reduce_type: "tenure" | "emi" }
    """
    user_id = user["id"]
    loan_id = body.get("loan_id", "")
    prepayment_amount = float(body.get("prepayment_amount", 0))
    reduce_type = body.get("reduce_type", "tenure")  # "tenure" or "emi"

    loan = await db.loans.find_one({"id": loan_id, "user_id": user_id}, {"_id": 0})
    if not loan:
        raise HTTPException(404, "Loan not found")

    principal = loan["principal_amount"]
    rate = loan["interest_rate"]
    tenure = loan["tenure_months"]
    emi = loan.get("emi_amount") or calculate_emi(principal, rate, tenure)

    # Current schedule (without prepayment)
    schedule_original = generate_emi_schedule(principal, rate, tenure, loan["start_date"], emi)
    paid_count = len([s for s in schedule_original if s["status"] == "paid"])
    original_total_interest = sum(s["interest"] for s in schedule_original)
    original_total_paid = sum(s["emi"] for s in schedule_original)
    current_outstanding = principal - sum(s["principal"] for s in schedule_original if s["status"] == "paid")

    if prepayment_amount >= current_outstanding:
        return {
            "loan_name": loan["name"],
            "original_tenure_months": tenure,
            "original_emi": emi,
            "original_total_interest": round(original_total_interest, 2),
            "original_total_paid": round(original_total_paid, 2),
            "new_tenure_months": paid_count,
            "new_emi": 0,
            "new_total_interest": round(sum(s["interest"] for s in schedule_original if s["status"] == "paid"), 2),
            "new_total_paid": round(sum(s["emi"] for s in schedule_original if s["status"] == "paid") + current_outstanding, 2),
            "interest_saved": round(original_total_interest - sum(s["interest"] for s in schedule_original if s["status"] == "paid"), 2),
            "tenure_saved_months": tenure - paid_count,
            "message": "Full prepayment clears the loan entirely!",
        }

    new_outstanding = current_outstanding - prepayment_amount
    remaining_tenure = tenure - paid_count

    if reduce_type == "tenure":
        # Keep same EMI, reduce tenure
        new_emi = emi
        if rate == 0:
            new_tenure = math.ceil(new_outstanding / new_emi)
        else:
            monthly_rate = rate / 12 / 100
            if new_emi <= new_outstanding * monthly_rate:
                new_tenure = remaining_tenure
            else:
                new_tenure = math.ceil(
                    -math.log(1 - (new_outstanding * monthly_rate / new_emi)) /
                    math.log(1 + monthly_rate)
                )
    else:
        # Keep same tenure, reduce EMI
        new_tenure = remaining_tenure
        new_emi = calculate_emi(new_outstanding, rate, new_tenure)

    # Calculate new schedule
    new_schedule = generate_emi_schedule(
        new_outstanding, rate, new_tenure,
        datetime.now().strftime("%Y-%m-%d"), new_emi
    )
    already_paid_interest = sum(s["interest"] for s in schedule_original if s["status"] == "paid")
    new_total_interest = already_paid_interest + sum(s["interest"] for s in new_schedule)
    new_total_paid = sum(s["emi"] for s in schedule_original if s["status"] == "paid") + prepayment_amount + sum(s["emi"] for s in new_schedule)

    interest_saved = original_total_interest - new_total_interest
    tenure_saved = tenure - (paid_count + new_tenure)

    return {
        "loan_name": loan["name"],
        "original_tenure_months": tenure,
        "original_emi": round(emi, 2),
        "original_total_interest": round(original_total_interest, 2),
        "original_total_paid": round(original_total_paid, 2),
        "new_tenure_months": paid_count + new_tenure,
        "new_emi": round(new_emi, 2),
        "new_total_interest": round(new_total_interest, 2),
        "new_total_paid": round(new_total_paid, 2),
        "interest_saved": round(max(0, interest_saved), 2),
        "tenure_saved_months": max(0, tenure_saved),
        "reduce_type": reduce_type,
        "prepayment_amount": prepayment_amount,
    }


# ─── SIP: Analytics Dashboard ──────────────────────────────────
@router.get("/sip-analytics/dashboard")
async def sip_analytics_dashboard(user=Depends(get_current_user)):
    """
    Comprehensive SIP analytics: performance, category allocation,
    growth projection, and discipline metrics.
    """
    user_id = user["id"]

    recurring = await db.recurring_transactions.find({"user_id": user_id}).to_list(200)
    holdings = await db.holdings.find({"user_id": user_id}, {"_id": 0}).to_list(500)

    active_sips = [r for r in recurring if r.get("is_active", True)]
    total_monthly = sum(
        r["amount"] * (1 if r.get("frequency") == "monthly" else
                       1/3 if r.get("frequency") == "quarterly" else
                       1/12 if r.get("frequency") == "yearly" else 1)
        for r in active_sips
    )

    # Category-wise allocation
    cat_map = {}
    for sip in active_sips:
        cat = sip.get("category", "SIP")
        cat_map.setdefault(cat, {"count": 0, "monthly_amount": 0})
        cat_map[cat]["count"] += 1
        freq = sip.get("frequency", "monthly")
        monthly = sip["amount"] * (1 if freq == "monthly" else 1/3 if freq == "quarterly" else 1/12 if freq == "yearly" else 1)
        cat_map[cat]["monthly_amount"] += monthly

    category_allocation = [
        {"category": k, "count": v["count"], "monthly_amount": round(v["monthly_amount"], 2)}
        for k, v in cat_map.items()
    ]

    # Total invested via SIPs
    total_sip_invested = sum(r.get("total_invested", 0) for r in recurring)
    total_executions = sum(r.get("execution_count", 0) for r in recurring)

    # SIP-linked holdings value
    sip_names = set(r.get("name", "").lower() for r in recurring)
    sip_holdings_value = sum(
        h.get("current_value", h.get("invested_value", 0))
        for h in holdings
        if any(sn in h.get("name", "").lower() for sn in sip_names if sn)
    )

    # Discipline score (how many SIPs are active and running)
    total_sips = len(recurring)
    active_count = len(active_sips)
    discipline_score = round((active_count / max(1, total_sips)) * 100, 0) if total_sips > 0 else 0

    # SIP list with details
    sip_list = []
    for r in recurring:
        r_id = str(r.pop("_id", ""))
        freq = r.get("frequency", "monthly")
        monthly = r["amount"] * (1 if freq == "monthly" else 1/3 if freq == "quarterly" else 1/12 if freq == "yearly" else 1)
        sip_list.append({
            "id": r.get("id", r_id),
            "name": r.get("name", ""),
            "amount": r["amount"],
            "frequency": freq,
            "category": r.get("category", "SIP"),
            "is_active": r.get("is_active", True),
            "monthly_equivalent": round(monthly, 2),
            "total_invested": r.get("total_invested", 0),
            "execution_count": r.get("execution_count", 0),
            "next_execution": r.get("next_execution", ""),
            "start_date": r.get("start_date", ""),
        })

    return {
        "summary": {
            "total_sips": total_sips,
            "active_sips": active_count,
            "paused_sips": total_sips - active_count,
            "total_monthly_commitment": round(total_monthly, 2),
            "total_invested": round(total_sip_invested, 2),
            "total_executions": total_executions,
            "estimated_portfolio_value": round(sip_holdings_value, 2),
            "discipline_score": discipline_score,
        },
        "category_allocation": category_allocation,
        "sips": sip_list,
    }


# ─── SIP: Wealth Projector ─────────────────────────────────────
@router.post("/sip-analytics/wealth-projection")
async def wealth_projection(body=Body(...), user=Depends(get_current_user)):
    """
    Project future wealth based on current SIPs with different return scenarios.
    Body: { monthly_sip, current_value, years, expected_return_pct (optional) }
    If no body params, uses actual SIP data.
    """
    user_id = user["id"]

    monthly_sip = body.get("monthly_sip", 0)
    current_value = body.get("current_value", 0)
    years = int(body.get("years", 10))
    custom_return = body.get("expected_return_pct")

    # If no inputs, use actual data
    if monthly_sip == 0:
        recurring = await db.recurring_transactions.find(
            {"user_id": user_id, "is_active": True}
        ).to_list(200)
        monthly_sip = sum(
            r["amount"] * (1 if r.get("frequency") == "monthly" else
                           1/3 if r.get("frequency") == "quarterly" else
                           1/12 if r.get("frequency") == "yearly" else 1)
            for r in recurring
        )

    if current_value == 0:
        holdings = await db.holdings.find({"user_id": user_id}, {"_id": 0}).to_list(500)
        current_value = sum(
            h.get("current_value", h.get("invested_value", 0)) for h in holdings
        )

    def project(monthly, current, annual_rate, num_years):
        """Future value = current * (1+r)^n + SIP * [((1+r)^n - 1) / r]"""
        months = num_years * 12
        total_invested = current + (monthly * months)
        if annual_rate <= 0:
            return {"future_value": total_invested, "total_invested": total_invested, "returns": 0}
        monthly_rate = annual_rate / 12 / 100
        fv_lumpsum = current * ((1 + monthly_rate) ** months)
        fv_sip = monthly * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
        future_value = fv_lumpsum + fv_sip
        return {
            "future_value": round(future_value, 2),
            "total_invested": round(total_invested, 2),
            "returns": round(future_value - total_invested, 2),
        }

    scenarios = {}
    rates = {"conservative": 8, "moderate": 12, "aggressive": 15}
    if custom_return is not None:
        rates["custom"] = float(custom_return)

    for label, rate in rates.items():
        scenarios[label] = project(monthly_sip, current_value, rate, years)
        scenarios[label]["annual_return_pct"] = rate

    # Year-by-year projection for moderate scenario
    yearly_projection = []
    mod_rate = rates.get("custom", rates["moderate"])
    for y in range(1, years + 1):
        p = project(monthly_sip, current_value, mod_rate, y)
        yearly_projection.append({
            "year": y,
            "future_value": p["future_value"],
            "total_invested": p["total_invested"],
            "returns": p["returns"],
        })

    return {
        "inputs": {
            "monthly_sip": round(monthly_sip, 2),
            "current_value": round(current_value, 2),
            "years": years,
        },
        "scenarios": scenarios,
        "yearly_projection": yearly_projection,
    }


# ─── SIP: Goal Mapping ─────────────────────────────────────────
@router.post("/sip-analytics/goal-map")
async def sip_goal_mapping(body=Body(...), user=Depends(get_current_user)):
    """
    Maps existing SIPs to financial goals and shows gap analysis.
    Body: { mappings: [{ sip_id, goal_id }] } (optional - saves mappings)
    If no body, returns auto-suggested mappings.
    """
    user_id = user["id"]

    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    recurring = await db.recurring_transactions.find({"user_id": user_id}).to_list(200)

    # If mappings provided, save them
    mappings = body.get("mappings", [])
    if mappings:
        for m in mappings:
            await db.recurring_transactions.update_one(
                {"user_id": user_id, "name": m.get("sip_name", "")},
                {"$set": {"mapped_goal_id": m.get("goal_id", "")}}
            )
        return {"message": f"Saved {len(mappings)} SIP-goal mappings"}

    # Auto-suggest mappings and gap analysis
    active_sips = []
    for r in recurring:
        r_id = str(r.pop("_id", ""))
        if r.get("is_active", True):
            freq = r.get("frequency", "monthly")
            monthly = r["amount"] * (1 if freq == "monthly" else 1/3 if freq == "quarterly" else 1/12 if freq == "yearly" else 1)
            active_sips.append({
                "id": r.get("id", r_id),
                "name": r.get("name", ""),
                "amount": r["amount"],
                "monthly_equivalent": round(monthly, 2),
                "category": r.get("category", "SIP"),
                "mapped_goal_id": r.get("mapped_goal_id", ""),
            })

    total_monthly_sip = sum(s["monthly_equivalent"] for s in active_sips)

    goal_analysis = []
    for goal in goals:
        target = goal.get("target_amount", 0)
        current = goal.get("current_amount", 0)
        gap = max(0, target - current)
        deadline = goal.get("deadline", "")

        # Calculate months to deadline
        months_left = 12  # default
        if deadline:
            try:
                dl = datetime.strptime(deadline, "%Y-%m-%d")
                months_left = max(1, (dl - datetime.now()).days // 30)
            except Exception:
                pass

        # Monthly SIP needed to reach goal (at 12% annual return)
        monthly_rate = 0.12 / 12
        if gap > 0 and months_left > 0:
            sip_needed = gap * monthly_rate / (((1 + monthly_rate) ** months_left - 1) * (1 + monthly_rate))
            sip_needed = round(sip_needed, 2)
        else:
            sip_needed = 0

        # Find mapped SIPs
        mapped_sips = [s for s in active_sips if s["mapped_goal_id"] == goal.get("id", "")]
        mapped_amount = sum(s["monthly_equivalent"] for s in mapped_sips)
        shortfall = max(0, sip_needed - mapped_amount)

        goal_analysis.append({
            "goal_id": goal.get("id", ""),
            "goal_title": goal.get("title", ""),
            "target_amount": target,
            "current_amount": current,
            "gap": round(gap, 2),
            "deadline": deadline,
            "months_left": months_left,
            "sip_needed_monthly": sip_needed,
            "mapped_sip_amount": round(mapped_amount, 2),
            "shortfall": round(shortfall, 2),
            "on_track": shortfall <= 0,
            "mapped_sips": [s["name"] for s in mapped_sips],
        })

    # Unmapped SIPs
    unmapped_sips = [s for s in active_sips if not s["mapped_goal_id"]]

    return {
        "total_monthly_sip": round(total_monthly_sip, 2),
        "total_goals": len(goals),
        "goals_on_track": sum(1 for g in goal_analysis if g["on_track"]),
        "goal_analysis": goal_analysis,
        "unmapped_sips": unmapped_sips,
        "active_sips": active_sips,
    }
