"""
Visor AI — Financial Personality Engine
Auto-computes a user's financial personality from their actual transaction,
investment, and behavioral data. Injected into AI context for personalized responses.

Personality dimensions:
- Spending archetype (Frugal / Balanced / Spender / Lifestyle Inflator)
- Savings consistency (Irregular / Improving / Steady / Disciplined)
- Investment behavior (Non-Investor / Passive / Active / Aggressive)
- Risk appetite (inferred from portfolio composition)
- Life stage (Student / Early Career / Family Builder / Peak Earner / Pre-Retirement)
- Financial strengths & blind spots
"""
import logging
from datetime import datetime, timezone
from collections import defaultdict

from database import db

logger = logging.getLogger(__name__)

PERSONALITY_COLLECTION = "financial_personalities"


async def compute_financial_personality(user_id: str) -> dict:
    """
    Compute a full financial personality profile from the user's actual data.
    Stores result in MongoDB and returns it.
    """
    # Fetch all relevant data
    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(5000)
    holdings = await db.holdings.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(20)
    credit_cards = await db.credit_cards.find({"user_id": user_id}, {"_id": 0}).to_list(10)
    sips = await db.recurring_transactions.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    salary_profile = await db.salary_profiles.find_one({"user_id": user_id}, {"_id": 0})
    risk_doc = await db.risk_profiles.find_one({"user_id": user_id}, {"_id": 0})

    if not txns:
        return _empty_personality(user_id)

    # ── Compute core metrics ─────────────────────────────────────────
    total_income = sum(t.get("amount", 0) for t in txns if t.get("type") == "income")
    total_expenses = sum(t.get("amount", 0) for t in txns if t.get("type") not in ("income", "investment"))
    total_investments = sum(t.get("amount", 0) for t in txns if t.get("type") == "investment")
    net_savings = total_income - total_expenses

    savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0
    investment_rate = (total_investments / total_income * 100) if total_income > 0 else 0

    # Monthly breakdown for consistency analysis
    monthly = defaultdict(lambda: {"income": 0, "expenses": 0, "investments": 0})
    for t in txns:
        month_key = t.get("date", "")[:7]
        t_type = t.get("type", "expense")
        amt = t.get("amount", 0) or 0
        if month_key:
            if t_type == "income":
                monthly[month_key]["income"] += amt
            elif t_type == "investment":
                monthly[month_key]["investments"] += amt
            else:
                monthly[month_key]["expenses"] += amt

    months_sorted = sorted(monthly.keys())
    monthly_savings_rates = []
    for m in months_sorted:
        d = monthly[m]
        if d["income"] > 0:
            monthly_savings_rates.append((d["income"] - d["expenses"]) / d["income"] * 100)

    # Category breakdown
    category_spend = defaultdict(float)
    for t in txns:
        if t.get("type") not in ("income", "investment"):
            category_spend[t.get("category", "Other")] += t.get("amount", 0) or 0

    top_categories = sorted(category_spend.items(), key=lambda x: -x[1])[:8]

    # Discretionary vs Essential spending
    essential_cats = {
        "Rent", "Groceries", "Utilities", "Electricity", "Water", "Gas",
        "Internet", "Mobile Recharge", "EMI", "Insurance", "Education",
        "Medical", "Health", "Fuel", "Metro", "Society Maintenance",
    }
    discretionary_cats = {
        "Food & Dining", "Entertainment", "Shopping", "Travel",
        "Subscriptions", "Personal Care", "Donations",
    }
    essential_spend = sum(v for k, v in category_spend.items() if k in essential_cats)
    discretionary_spend = sum(v for k, v in category_spend.items() if k in discretionary_cats)
    discretionary_ratio = (discretionary_spend / total_expenses * 100) if total_expenses > 0 else 0

    # ── Spending Archetype ───────────────────────────────────────────
    if savings_rate >= 35:
        spending_archetype = "Frugal Saver"
        spending_desc = "Exceptional discipline — saves aggressively, minimal discretionary spending"
    elif savings_rate >= 20:
        spending_archetype = "Balanced Spender"
        spending_desc = "Healthy balance between enjoying life and saving for the future"
    elif savings_rate >= 5:
        spending_archetype = "Lifestyle Spender"
        spending_desc = "Spends freely but maintains some savings buffer"
    else:
        spending_archetype = "Living on the Edge"
        spending_desc = "Expenses nearly match or exceed income — savings critical"

    # ── Savings Consistency ──────────────────────────────────────────
    if len(monthly_savings_rates) >= 3:
        positive_months = sum(1 for r in monthly_savings_rates if r > 5)
        consistency_pct = positive_months / len(monthly_savings_rates) * 100

        # Check trend (improving or declining)
        if len(monthly_savings_rates) >= 4:
            first_half = monthly_savings_rates[:len(monthly_savings_rates)//2]
            second_half = monthly_savings_rates[len(monthly_savings_rates)//2:]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            trend = "improving" if avg_second > avg_first + 3 else ("declining" if avg_first > avg_second + 3 else "stable")
        else:
            trend = "stable"

        if consistency_pct >= 80 and trend != "declining":
            savings_consistency = "Disciplined"
            savings_desc = "Consistently saves every month — excellent financial habit"
        elif consistency_pct >= 60:
            savings_consistency = "Steady"
            savings_desc = "Saves most months with occasional dips"
        elif trend == "improving":
            savings_consistency = "Improving"
            savings_desc = "Savings trend is getting better over time"
        else:
            savings_consistency = "Irregular"
            savings_desc = "Savings pattern varies significantly month to month"
    else:
        savings_consistency = "Insufficient Data"
        savings_desc = "Need at least 3 months of data to assess"
        trend = "unknown"

    # ── Investment Behavior ──────────────────────────────────────────
    portfolio_value = sum(
        h.get("current_value", 0) or (h.get("buy_price", 0) * h.get("quantity", 0))
        for h in holdings
    )
    num_holdings = len(holdings)
    active_sips = len([s for s in sips if s.get("status", "active") == "active"])

    # Asset diversification
    asset_types = set()
    for h in holdings:
        cat = h.get("category", "").lower()
        if "stock" in cat or "equity" in cat:
            asset_types.add("equity")
        elif "mutual" in cat or "mf" in cat:
            asset_types.add("mutual_funds")
        elif "gold" in cat:
            asset_types.add("gold")
        elif "fd" in cat or "fixed" in cat:
            asset_types.add("fixed_income")
        elif "bond" in cat or "ncd" in cat:
            asset_types.add("bonds")
        else:
            asset_types.add("other")

    if num_holdings == 0 and active_sips == 0:
        investment_behavior = "Non-Investor"
        investment_desc = "No investments yet — potential to start building wealth"
    elif active_sips >= 3 and len(asset_types) >= 3:
        investment_behavior = "Aggressive Builder"
        investment_desc = f"Active investor with {num_holdings} holdings across {len(asset_types)} asset classes and {active_sips} SIPs"
    elif active_sips >= 1 or num_holdings >= 3:
        investment_behavior = "Active Investor"
        investment_desc = f"Growing portfolio with {num_holdings} holdings and {active_sips} SIPs"
    elif num_holdings >= 1:
        investment_behavior = "Passive Investor"
        investment_desc = f"Has {num_holdings} holdings but limited active investing"
    else:
        investment_behavior = "Beginner"
        investment_desc = "Starting investment journey"

    # ── Life Stage Inference ─────────────────────────────────────────
    has_home_loan = any("home" in l.get("name", "").lower() or "housing" in l.get("name", "").lower() for l in loans)
    has_edu_loan = any("education" in l.get("name", "").lower() or "student" in l.get("name", "").lower() for l in loans)
    has_car_loan = any("car" in l.get("name", "").lower() or "vehicle" in l.get("name", "").lower() for l in loans)
    annual_income = salary_profile.get("gross_annual", 0) if salary_profile else total_income

    if has_edu_loan and annual_income < 600000:
        life_stage = "Early Career"
        life_stage_desc = "Building career foundation, managing education debt"
    elif has_home_loan and len(goals) >= 2:
        life_stage = "Family Builder"
        life_stage_desc = "Established with home, building for family goals"
    elif annual_income > 2500000 and num_holdings >= 5:
        life_stage = "Peak Earner"
        life_stage_desc = "High income phase — focus on wealth multiplication and tax optimization"
    elif annual_income > 1500000 and has_home_loan:
        life_stage = "Wealth Accumulator"
        life_stage_desc = "Mid-career with significant income — growing assets"
    elif annual_income > 0:
        life_stage = "Growth Phase"
        life_stage_desc = "Active income growth — time to build strong financial habits"
    else:
        life_stage = "Getting Started"
        life_stage_desc = "Beginning financial journey"

    # ── Strengths & Blind Spots ──────────────────────────────────────
    strengths = []
    blind_spots = []

    if savings_rate >= 20:
        strengths.append("Strong savings discipline")
    elif savings_rate < 10:
        blind_spots.append("Low savings rate — needs immediate attention")

    if active_sips >= 2:
        strengths.append("Regular SIP investing")
    elif num_holdings == 0:
        blind_spots.append("No investments — missing wealth compounding")

    if len(asset_types) >= 3:
        strengths.append("Diversified portfolio across asset classes")
    elif num_holdings > 0 and len(asset_types) <= 1:
        blind_spots.append("Portfolio concentrated in one asset class")

    cc_utilization = 0
    if credit_cards:
        total_limit = sum(c.get("credit_limit", 0) for c in credit_cards)
        total_outstanding = sum(c.get("outstanding", 0) for c in credit_cards)
        if total_limit > 0:
            cc_utilization = total_outstanding / total_limit * 100
        if cc_utilization < 30:
            strengths.append("Healthy credit card utilization")
        elif cc_utilization > 70:
            blind_spots.append("High credit card utilization — risk to credit score")

    if len(goals) >= 2:
        strengths.append("Clear financial goals set")
    elif len(goals) == 0:
        blind_spots.append("No financial goals defined")

    total_debt = sum(l.get("principal_amount", l.get("principal", 0)) for l in loans)
    if total_debt > 0 and annual_income > 0:
        debt_to_income = total_debt / annual_income
        if debt_to_income < 3:
            strengths.append("Manageable debt-to-income ratio")
        elif debt_to_income > 6:
            blind_spots.append("High debt relative to income")

    # ── Build personality document ───────────────────────────────────
    personality = {
        "user_id": user_id,
        "spending_archetype": spending_archetype,
        "spending_description": spending_desc,
        "savings_consistency": savings_consistency,
        "savings_description": savings_desc,
        "savings_trend": trend if savings_consistency != "Insufficient Data" else "unknown",
        "investment_behavior": investment_behavior,
        "investment_description": investment_desc,
        "life_stage": life_stage,
        "life_stage_description": life_stage_desc,
        "strengths": strengths[:5],
        "blind_spots": blind_spots[:5],
        "metrics": {
            "savings_rate": round(savings_rate, 1),
            "investment_rate": round(investment_rate, 1),
            "discretionary_ratio": round(discretionary_ratio, 1),
            "num_holdings": num_holdings,
            "active_sips": active_sips,
            "asset_classes": len(asset_types),
            "cc_utilization": round(cc_utilization, 1),
            "num_goals": len(goals),
            "total_debt": total_debt,
            "annual_income_estimate": round(annual_income, 0),
        },
        "top_expense_categories": [{"category": k, "amount": round(v, 0)} for k, v in top_categories],
        "risk_profile": risk_doc.get("profile", "Not assessed") if risk_doc else "Not assessed",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store in MongoDB
    await db[PERSONALITY_COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": personality},
        upsert=True,
    )

    return personality


def get_personality_context(personality: dict) -> str:
    """
    Format personality data for injection into AI context.
    Returns a concise string the AI can use to personalize responses.
    """
    if not personality or personality.get("spending_archetype") == "Unknown":
        return ""

    parts = [
        f"\nFINANCIAL PERSONALITY:",
        f"- Archetype: {personality['spending_archetype']} ({personality['spending_description']})",
        f"- Savings: {personality['savings_consistency']} (trend: {personality.get('savings_trend', 'unknown')})",
        f"- Investing: {personality['investment_behavior']} ({personality['investment_description']})",
        f"- Life Stage: {personality['life_stage']} ({personality['life_stage_description']})",
    ]

    strengths = personality.get("strengths", [])
    if strengths:
        parts.append(f"- Strengths: {', '.join(strengths)}")

    blind_spots = personality.get("blind_spots", [])
    if blind_spots:
        parts.append(f"- Blind Spots: {', '.join(blind_spots)}")

    parts.append("Use this personality profile to tailor your advice tone and recommendations.")

    return "\n".join(parts)


async def get_cached_personality(user_id: str) -> dict | None:
    """Get cached personality from MongoDB. Returns None if not computed yet."""
    return await db[PERSONALITY_COLLECTION].find_one(
        {"user_id": user_id}, {"_id": 0}
    )


def _empty_personality(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "spending_archetype": "Unknown",
        "spending_description": "Not enough transaction data to assess",
        "savings_consistency": "Insufficient Data",
        "savings_description": "Need transaction history to analyze",
        "savings_trend": "unknown",
        "investment_behavior": "Unknown",
        "investment_description": "No data available",
        "life_stage": "Getting Started",
        "life_stage_description": "Beginning financial journey",
        "strengths": [],
        "blind_spots": ["Add transactions to get personalized insights"],
        "metrics": {},
        "top_expense_categories": [],
        "risk_profile": "Not assessed",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
