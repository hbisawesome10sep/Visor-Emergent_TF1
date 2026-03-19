"""
Dashboard V2 — Enhanced dashboard endpoints with:
  - 8-Dimension Financial Health Score (0-1000)
  - Net Worth calculation
  - Investment Summary with XIRR
  - Upcoming Dues (CC + Loan)
  - AI-Personalized Insight
  - Insurance CRUD
"""

from fastapi import APIRouter, Depends, Body
from typing import Optional
from datetime import datetime, timezone, timedelta
from database import db
from auth import get_current_user
import uuid
import math
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# ─── XIRR Calculator ───────────────────────────────────────────
def xirr(cashflows: list[tuple[datetime, float]], guess: float = 0.1) -> Optional[float]:
    """Calculate XIRR given list of (date, amount) tuples. Outflows negative, inflows positive."""
    if not cashflows or len(cashflows) < 2:
        return None
    try:
        dates = [cf[0] for cf in cashflows]
        amounts = [cf[1] for cf in cashflows]
        min_date = min(dates)
        days = [(d - min_date).days / 365.25 for d in dates]

        # Need at least some time span
        if max(days) < 0.01:
            return None

        rate = guess
        for _ in range(300):
            npv = sum(a / max(1e-15, (1 + rate) ** t) for a, t in zip(amounts, days))
            dnpv = sum(-t * a / max(1e-15, (1 + rate) ** (t + 1)) for a, t in zip(amounts, days))
            if abs(dnpv) < 1e-10:
                break
            new_rate = rate - npv / dnpv
            # Clamp rate to reasonable bounds
            new_rate = max(-0.99, min(10.0, new_rate))
            if abs(new_rate - rate) < 1e-7:
                return round(new_rate * 100, 2)
            rate = new_rate
        # Only return if result is reasonable (between -99% and 1000%)
        if -0.99 <= rate <= 10.0:
            return round(rate * 100, 2)
        return None
    except Exception:
        return None


# ─── 8-Dimension Financial Health Score (0-1000) ───────────────
@router.get("/dashboard/financial-health-v2")
async def get_financial_health_v2(user=Depends(get_current_user)):
    user_id = user["id"]

    # Fetch all data in parallel
    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(5000)
    cc_txns = await db.credit_card_transactions.find({"user_id": user_id}, {"_id": 0}).to_list(2000)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    credit_cards = await db.credit_cards.find({"user_id": user_id, "is_active": True}, {"_id": 0}).to_list(20)
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    holdings = await db.holdings.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    insurance = await db.insurance_policies.find({"user_id": user_id}, {"_id": 0}).to_list(50)

    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
    cc_expenses = sum(t["amount"] for t in cc_txns if t["type"] == "expense")
    cc_payments = sum(t["amount"] for t in cc_txns if t["type"] == "payment")

    combined_expenses = total_expenses + cc_expenses
    has_data = total_income > 0

    # ─── 1. Savings Rate (0-100) ──
    if has_data:
        raw_savings_rate = max(0, (total_income - combined_expenses) / total_income * 100)
        savings_score = min(100, raw_savings_rate * 2.5)  # 40% savings = 100 score
    else:
        raw_savings_rate = 0
        savings_score = 0

    # ─── 2. Debt Load (0-100) ──
    total_loan_outstanding = sum(l.get("principal_amount", 0) - l.get("total_paid", 0) for l in loans)
    if total_loan_outstanding < 0:
        total_loan_outstanding = sum(l.get("principal_amount", 0) for l in loans)
    cc_outstanding = max(0, cc_expenses - cc_payments)
    total_debt = total_loan_outstanding + cc_outstanding
    annual_income = total_income * (12 / max(1, len(set(t.get("date", "")[:7] for t in txns if t["type"] == "income"))))
    debt_to_income = (total_debt / annual_income) if annual_income > 0 else 0
    debt_score = max(0, min(100, 100 - debt_to_income * 100))  # 0% DTI = 100, 100% DTI = 0

    # ─── 3. Investment Rate (0-100) ──
    if has_data:
        raw_invest_rate = min(100, total_investments / total_income * 100)
        invest_score = min(100, raw_invest_rate * 4)  # 25% invest = 100 score
    else:
        raw_invest_rate = 0
        invest_score = 0

    # ─── 4. Emergency Fund (0-100) ──
    num_expense_months = max(1, len(set(t.get("date", "")[:7] for t in txns if t["type"] == "expense")))
    avg_monthly_expense = combined_expenses / num_expense_months if num_expense_months > 0 else 0
    net_savings = max(0, total_income - combined_expenses - total_investments)
    emergency_months = net_savings / avg_monthly_expense if avg_monthly_expense > 0 else 0
    emergency_score = min(100, (emergency_months / 6) * 100)  # 6 months = 100 score

    # ─── 5. CC Utilization (0-100) ──
    cc_total_limit = sum(c.get("credit_limit", 0) for c in credit_cards)
    cc_utilization_pct = (cc_outstanding / cc_total_limit * 100) if cc_total_limit > 0 else 0
    if len(credit_cards) == 0:
        cc_util_score = 80  # No CC = decent score (not penalized)
    else:
        cc_util_score = max(0, 100 - cc_utilization_pct * 1.25)  # 80% util = 0 score

    # ─── 6. Goal Progress (0-100) ──
    total_goal_target = sum(g.get("target_amount", 0) for g in goals)
    total_goal_current = sum(g.get("current_amount", 0) for g in goals)
    goal_score = min(100, (total_goal_current / total_goal_target * 100)) if total_goal_target > 0 else 0

    # ─── 7. Insurance Cover (0-100) ──
    total_life_cover = sum(p.get("cover_amount", 0) for p in insurance if p.get("policy_type") in ["term_life", "life"])
    total_health_cover = sum(p.get("cover_amount", 0) for p in insurance if p.get("policy_type") == "health")
    # Life cover should be 10x annual income, health cover >= 10L
    life_adequacy = min(100, (total_life_cover / max(1, annual_income * 10)) * 100) if annual_income > 0 else 0
    health_adequacy = min(100, (total_health_cover / 1000000) * 100)  # 10L = 100%
    insurance_score = (life_adequacy * 0.6 + health_adequacy * 0.4) if insurance else 0

    # ─── 8. Net Worth Growth (0-100) ──
    # Compare current net worth with 3 months ago
    now = datetime.now(timezone.utc)
    three_months_ago = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    old_txns = [t for t in txns if t.get("date", "") <= three_months_ago]
    old_income = sum(t["amount"] for t in old_txns if t["type"] == "income")
    old_expenses = sum(t["amount"] for t in old_txns if t["type"] == "expense")
    old_investments = sum(t["amount"] for t in old_txns if t["type"] == "investment")
    old_net = old_income - old_expenses
    current_net = total_income - combined_expenses

    if old_net > 0:
        nw_growth_pct = ((current_net - old_net) / old_net) * 100
        nw_growth_score = min(100, max(0, 50 + nw_growth_pct))  # Neutral at 50, positive growth increases
    elif current_net > 0:
        nw_growth_score = 70  # Positive net worth but no comparison data
    else:
        nw_growth_score = 20 if has_data else 0

    # ─── Composite Score (0-1000) ──
    weights = {
        "savings_rate": 0.15,
        "debt_load": 0.15,
        "investment_rate": 0.12,
        "emergency_fund": 0.13,
        "cc_utilization": 0.12,
        "goal_progress": 0.10,
        "insurance_cover": 0.10,
        "net_worth_growth": 0.13,
    }
    raw_composite = (
        savings_score * weights["savings_rate"]
        + debt_score * weights["debt_load"]
        + invest_score * weights["investment_rate"]
        + emergency_score * weights["emergency_fund"]
        + cc_util_score * weights["cc_utilization"]
        + goal_score * weights["goal_progress"]
        + insurance_score * weights["insurance_cover"]
        + nw_growth_score * weights["net_worth_growth"]
    )
    composite_score = round(min(1000, max(0, raw_composite * 10)), 0)

    # Grade
    if not has_data:
        grade = "No Data"
    elif composite_score >= 800:
        grade = "Excellent"
    elif composite_score >= 650:
        grade = "Good"
    elif composite_score >= 450:
        grade = "Fair"
    elif composite_score >= 250:
        grade = "Needs Work"
    else:
        grade = "Critical"

    # Month-over-month score change (simulated from data trend)
    score_change = round(nw_growth_score - 50, 0) if has_data else 0

    # Biggest drag dimension
    dimensions = {
        "Savings Rate": savings_score,
        "Debt Load": debt_score,
        "Investment Rate": invest_score,
        "Emergency Fund": emergency_score,
        "CC Utilization": cc_util_score,
        "Goal Progress": goal_score,
        "Insurance Cover": insurance_score,
        "Net Worth Growth": nw_growth_score,
    }
    lowest_dim = min(dimensions, key=dimensions.get) if has_data else "Savings Rate"
    lowest_score = dimensions.get(lowest_dim, 0)

    # Improvement tip
    tips = {
        "Savings Rate": f"Increase your savings rate by cutting discretionary spending. Target 30%+ to add ~{int(15-savings_score*0.15)} points.",
        "Debt Load": f"Focus on paying down high-interest debt first. Reducing DTI by 10% adds ~15 points.",
        "Investment Rate": f"Try to invest at least 20% of your income. Start a SIP to automate investing.",
        "Emergency Fund": f"Build a buffer of {int(6-emergency_months)} more months of expenses to add ~{int(emergency_score*0.3)} points.",
        "CC Utilization": f"Keep CC utilization below 30%. Pay off outstanding balance to boost your score.",
        "Goal Progress": "Set specific financial goals and make regular contributions toward them.",
        "Insurance Cover": "Get adequate term life (10x income) and health insurance (min 10L) coverage.",
        "Net Worth Growth": "Focus on growing assets and reducing liabilities each quarter.",
    }

    return {
        "composite_score": int(composite_score),
        "grade": grade,
        "has_data": has_data,
        "score_change": int(score_change),
        "biggest_drag": lowest_dim,
        "improvement_tip": tips.get(lowest_dim, ""),
        "dimensions": {
            "savings_rate": {"score": round(savings_score), "raw_value": round(raw_savings_rate, 1)},
            "debt_load": {"score": round(debt_score), "raw_value": round(debt_to_income * 100, 1)},
            "investment_rate": {"score": round(invest_score), "raw_value": round(raw_invest_rate, 1)},
            "emergency_fund": {"score": round(emergency_score), "raw_value": round(emergency_months, 1)},
            "cc_utilization": {"score": round(cc_util_score), "raw_value": round(cc_utilization_pct, 1)},
            "goal_progress": {"score": round(goal_score), "raw_value": round(total_goal_current / max(1, total_goal_target) * 100, 1)},
            "insurance_cover": {"score": round(insurance_score), "raw_value": round(total_life_cover + total_health_cover)},
            "net_worth_growth": {"score": round(nw_growth_score), "raw_value": round(nw_growth_score, 1)},
        },
    }


# ─── Net Worth Calculation ──────────────────────────────────────
@router.get("/dashboard/net-worth")
async def get_net_worth(user=Depends(get_current_user)):
    user_id = user["id"]

    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(5000)
    cc_txns = await db.credit_card_transactions.find({"user_id": user_id}, {"_id": 0}).to_list(2000)
    holdings = await db.holdings.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    credit_cards = await db.credit_cards.find({"user_id": user_id, "is_active": True}, {"_id": 0}).to_list(20)
    bank_accounts = await db.bank_accounts.find({"user_id": user_id}, {"_id": 0}).to_list(20)

    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments_flow = sum(t["amount"] for t in txns if t["type"] == "investment")
    cc_expenses = sum(t["amount"] for t in cc_txns if t["type"] == "expense")
    cc_payments = sum(t["amount"] for t in cc_txns if t["type"] == "payment")

    # Assets
    cash_savings = max(0, total_income - total_expenses - total_investments_flow)
    investment_value = sum(h.get("total_current_value", h.get("current_value", h.get("invested_value", 0))) for h in holdings)
    bank_balance = cash_savings  # Approximation from transaction data
    total_assets = bank_balance + investment_value

    # Liabilities
    loan_outstanding = sum(l.get("principal_amount", 0) for l in loans)
    cc_outstanding = max(0, cc_expenses - cc_payments)
    total_liabilities = loan_outstanding + cc_outstanding

    net_worth = total_assets - total_liabilities

    return {
        "net_worth": round(net_worth, 2),
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "breakdown": {
            "assets": {
                "bank_balance": round(bank_balance, 2),
                "investments": round(investment_value, 2),
            },
            "liabilities": {
                "loans": round(loan_outstanding, 2),
                "credit_cards": round(cc_outstanding, 2),
            },
        },
    }


# ─── Investment Summary with XIRR ──────────────────────────────
@router.get("/dashboard/investment-summary")
async def get_investment_summary(user=Depends(get_current_user)):
    user_id = user["id"]

    holdings = []
    async for doc in db.holdings.find({"user_id": user_id}):
        doc["id"] = str(doc.pop("_id"))
        holdings.append(doc)

    if not holdings:
        return {
            "total_invested": 0,
            "current_value": 0,
            "absolute_gain": 0,
            "absolute_return_pct": 0,
            "xirr": None,
            "holdings_count": 0,
        }

    # Fetch live prices for holdings with tickers
    tickers = list(set(h["ticker"] for h in holdings if h.get("ticker")))
    prices = {}
    if tickers:
        from routes.holdings import _fetch_live_prices
        from concurrent.futures import ThreadPoolExecutor
        import asyncio
        loop = asyncio.get_running_loop()
        _executor = ThreadPoolExecutor(max_workers=2)
        prices = await loop.run_in_executor(_executor, _fetch_live_prices, tickers)

    total_invested = 0
    total_current = 0
    cashflows = []

    for h in holdings:
        invested = h.get("invested_value", 0) or (h["quantity"] * h["buy_price"])
        stored_current = h.get("current_value", 0)

        if h.get("ticker") and h["ticker"] in prices and prices[h["ticker"]]["price"] > 0:
            current_value = h["quantity"] * prices[h["ticker"]]["price"]
        elif stored_current > 0:
            current_value = stored_current
        else:
            current_value = invested

        total_invested += invested
        total_current += current_value

        # XIRR cashflow
        buy_date = h.get("buy_date", "")
        if buy_date:
            try:
                dt = datetime.strptime(buy_date, "%Y-%m-%d")
                cashflows.append((dt, -abs(invested)))
            except Exception:
                pass

    abs_gain = total_current - total_invested
    abs_return_pct = (abs_gain / total_invested * 100) if total_invested > 0 else 0

    if total_current > 0 and cashflows:
        cashflows.append((datetime.now(), total_current))
        xirr_val = xirr(cashflows)
    else:
        xirr_val = None

    return {
        "total_invested": round(total_invested, 2),
        "current_value": round(total_current, 2),
        "absolute_gain": round(abs_gain, 2),
        "absolute_return_pct": round(abs_return_pct, 2),
        "xirr": xirr_val,
        "holdings_count": len(holdings),
    }


# ─── Upcoming Dues (CC + Loans) ────────────────────────────────
@router.get("/dashboard/upcoming-dues")
async def get_upcoming_dues(user=Depends(get_current_user)):
    user_id = user["id"]
    now = datetime.now(timezone.utc)

    credit_cards = await db.credit_cards.find({"user_id": user_id, "is_active": True}, {"_id": 0}).to_list(20)
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)

    dues = []
    for cc in credit_cards:
        due_day = cc.get("due_day", 1)
        outstanding = cc.get("current_outstanding", 0)
        # Calculate next due date
        if now.day <= due_day:
            next_due = now.replace(day=due_day)
        else:
            if now.month == 12:
                next_due = now.replace(year=now.year + 1, month=1, day=due_day)
            else:
                next_due = now.replace(month=now.month + 1, day=due_day)
        days_until = (next_due - now).days

        dues.append({
            "id": cc.get("id", ""),
            "name": cc.get("card_name", "Credit Card"),
            "type": "credit_card",
            "amount": round(outstanding, 2),
            "due_date": next_due.strftime("%Y-%m-%d"),
            "days_until": days_until,
            "urgency": "critical" if days_until <= 1 else "warning" if days_until <= 3 else "upcoming" if days_until <= 7 else "normal",
            "icon": "credit-card",
        })

    for loan in loans:
        emi = loan.get("emi_amount", 0)
        if not emi:
            p = loan.get("principal_amount", 0)
            r = loan.get("interest_rate", 0) / 12 / 100
            n = loan.get("tenure_months", 1)
            emi = p * r * (1 + r) ** n / ((1 + r) ** n - 1) if r > 0 else p / n

        # EMI due date: assume same day each month as start_date
        start = loan.get("start_date", "")
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            emi_day = start_dt.day
        except Exception:
            emi_day = 5

        if now.day <= emi_day:
            next_due = now.replace(day=min(emi_day, 28))
        else:
            if now.month == 12:
                next_due = now.replace(year=now.year + 1, month=1, day=min(emi_day, 28))
            else:
                next_due = now.replace(month=now.month + 1, day=min(emi_day, 28))
        days_until = (next_due - now).days

        dues.append({
            "id": loan.get("id", ""),
            "name": loan.get("name", "Loan EMI"),
            "type": "loan",
            "amount": round(emi, 2),
            "due_date": next_due.strftime("%Y-%m-%d"),
            "days_until": days_until,
            "urgency": "critical" if days_until <= 1 else "warning" if days_until <= 3 else "upcoming" if days_until <= 7 else "normal",
            "icon": "bank",
        })

    dues.sort(key=lambda d: d["days_until"])
    return {"dues": dues}


# ─── AI Personalized Insight ────────────────────────────────────
@router.get("/dashboard/ai-insight")
async def get_ai_insight(user=Depends(get_current_user)):
    user_id = user["id"]

    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(2000)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    holdings = await db.holdings.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(50)

    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
    invest_rate = (total_investments / total_income * 100) if total_income > 0 else 0
    total_holdings_value = sum(h.get("total_current_value", h.get("invested_value", 0)) for h in holdings)
    total_loan_amount = sum(l.get("principal_amount", 0) for l in loans)

    # Category breakdown for top spending
    cats = {}
    for t in txns:
        if t["type"] == "expense":
            cats[t["category"]] = cats.get(t["category"], 0) + t["amount"]
    top_cats = sorted(cats.items(), key=lambda x: -x[1])[:3]
    top_spending = ", ".join(f"{c}: {a:,.0f}" for c, a in top_cats)

    # Build context for LLM
    context = (
        f"User Financial Snapshot:\n"
        f"- Total Income: Rs {total_income:,.0f}\n"
        f"- Total Expenses: Rs {total_expenses:,.0f}\n"
        f"- Savings Rate: {savings_rate:.1f}%\n"
        f"- Investment Rate: {invest_rate:.1f}%\n"
        f"- Portfolio Value: Rs {total_holdings_value:,.0f}\n"
        f"- Total Loans: Rs {total_loan_amount:,.0f}\n"
        f"- Goals: {len(goals)} active\n"
        f"- Top Spending: {top_spending}\n"
    )

    prompt = (
        "You are Visor, an expert Indian financial advisor. Based on the user's data below, "
        "provide ONE specific, actionable financial insight in 2-3 sentences. "
        "Make it personal, data-driven, and motivating. Use Indian context (mention INR, Indian tax sections if relevant). "
        "Don't be generic. Reference specific numbers from their data.\n\n"
        f"{context}\n"
        "Insight:"
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY", ""),
            session_id=f"visor-insight-{user_id}",
            system_message="You are Visor, a concise Indian financial advisor. Give one sharp, personalized, actionable insight in 2-3 sentences based on the user's data. Use Indian context (INR, Indian tax sections). Reference specific numbers from their data. Don't be generic.",
        ).with_model("openai", "gpt-4o")

        user_msg = UserMessage(text=prompt)
        insight_text = await chat.send_message(user_msg)
        insight_text = insight_text.strip()
    except Exception as e:
        logger.warning(f"AI insight generation failed: {e}")
        # Fallback: Generate insight from data
        if savings_rate > 30:
            insight_text = f"Your savings rate of {savings_rate:.0f}% is impressive! If you maintain this, you could accumulate Rs {total_income * savings_rate / 100 * 12:,.0f} annually. Consider channeling more into equity SIPs for long-term wealth creation."
        elif savings_rate < 10:
            insight_text = f"Your savings rate is only {savings_rate:.0f}%. Your top spending categories are {top_spending}. Try the 50-30-20 rule: 50% needs, 30% wants, 20% savings to build a stronger financial foundation."
        elif invest_rate < 10:
            insight_text = f"You're saving {savings_rate:.0f}% but investing only {invest_rate:.0f}%. Start a SIP of Rs {total_income * 0.1:,.0f}/month in a diversified equity fund to grow your wealth faster than inflation."
        else:
            insight_text = f"You're on a solid path with {savings_rate:.0f}% savings and {invest_rate:.0f}% investments. Consider reviewing your top spend ({top_spending}) for optimization opportunities."

    return {
        "insight": insight_text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_points_used": len(txns) + len(holdings) + len(goals),
    }


# ─── Insurance CRUD ─────────────────────────────────────────────
@router.get("/insurance")
async def get_insurance(user=Depends(get_current_user)):
    policies = await db.insurance_policies.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).to_list(50)
    return policies


@router.post("/insurance")
async def add_insurance(body=Body(...), user=Depends(get_current_user)):
    policy = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "policy_name": body.get("policy_name", ""),
        "policy_type": body.get("policy_type", "term_life"),  # term_life, health, life, vehicle, home
        "provider": body.get("provider", ""),
        "cover_amount": body.get("cover_amount", 0),
        "premium_amount": body.get("premium_amount", 0),
        "premium_frequency": body.get("premium_frequency", "yearly"),
        "start_date": body.get("start_date", ""),
        "end_date": body.get("end_date", ""),
        "policy_number": body.get("policy_number", ""),
        "nominees": body.get("nominees", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.insurance_policies.insert_one(policy)
    return {k: v for k, v in policy.items() if k != "_id"}


@router.put("/insurance/{policy_id}")
async def update_insurance(policy_id: str, body=Body(...), user=Depends(get_current_user)):
    existing = await db.insurance_policies.find_one(
        {"id": policy_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not existing:
        return {"error": "Policy not found"}

    update = {k: v for k, v in body.items() if k not in ("id", "user_id", "_id")}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.insurance_policies.update_one({"id": policy_id}, {"$set": update})
    updated = await db.insurance_policies.find_one({"id": policy_id}, {"_id": 0})
    return updated


@router.delete("/insurance/{policy_id}")
async def delete_insurance(policy_id: str, user=Depends(get_current_user)):
    result = await db.insurance_policies.delete_one(
        {"id": policy_id, "user_id": user["id"]}
    )
    if result.deleted_count == 0:
        return {"error": "Policy not found"}
    return {"message": "Policy deleted"}
