"""
Credit Card Analytics — Phase 2 Enhancements:
  - Due Date Calendar with smart reminders
  - Interest Calculator (minimum payment scenario)
  - Rewards Tracker (points, cashback, miles + INR equivalent)
  - Best Card Recommender (AI-powered)
"""

from fastapi import APIRouter, Depends, Body
from datetime import datetime, timezone, timedelta
from database import db
from auth import get_current_user
import os
import logging
import math

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# ─── Known card reward structures (expandable) ─────────────────
CARD_REWARDS_DB = {
    "hdfc regalia": {
        "reward_rate": 4,  # 4 reward points per Rs 150
        "reward_per_spend": 150,
        "point_value": 0.50,  # Rs per point
        "categories": {
            "Travel": {"multiplier": 2, "note": "2x points on travel"},
            "Dining": {"multiplier": 2, "note": "2x points on dining"},
            "default": {"multiplier": 1, "note": "Base rewards"},
        },
        "benefits": ["Airport lounge access (8/year)", "Milestone benefits at 5L spend", "2x on travel & dining"],
        "annual_fee": 2500,
        "interest_rate_monthly": 3.49,
    },
    "hdfc millennia": {
        "reward_rate": 5,
        "reward_per_spend": 150,
        "point_value": 0.25,
        "categories": {
            "Shopping": {"multiplier": 2, "note": "5% cashback on Amazon/Flipkart"},
            "default": {"multiplier": 1, "note": "1% cashback on all spends"},
        },
        "benefits": ["5% cashback on Amazon/Flipkart/Myntra", "1% cashback on all other spends"],
        "annual_fee": 1000,
        "interest_rate_monthly": 3.49,
    },
    "sbi cashback": {
        "reward_rate": 5,
        "reward_per_spend": 100,
        "point_value": 1.0,
        "categories": {
            "Shopping": {"multiplier": 1, "note": "5% cashback online"},
            "default": {"multiplier": 1, "note": "1% cashback offline"},
        },
        "benefits": ["5% cashback on all online spends", "1% on offline POS"],
        "annual_fee": 999,
        "interest_rate_monthly": 3.35,
    },
    "default": {
        "reward_rate": 2,
        "reward_per_spend": 100,
        "point_value": 0.25,
        "categories": {"default": {"multiplier": 1, "note": "Base rewards"}},
        "benefits": ["Standard reward points"],
        "annual_fee": 500,
        "interest_rate_monthly": 3.49,
    },
}


def get_card_rewards_config(card_name: str) -> dict:
    """Match card name to known reward config."""
    name_lower = card_name.lower()
    for key, config in CARD_REWARDS_DB.items():
        if key in name_lower:
            return config
    return CARD_REWARDS_DB["default"]


# ─── Due Date Calendar & Reminders ─────────────────────────────
@router.get("/credit-cards/due-calendar")
async def get_due_calendar(user=Depends(get_current_user)):
    user_id = user["id"]
    cards = await db.credit_cards.find(
        {"user_id": user_id, "is_active": True}, {"_id": 0}
    ).to_list(20)

    now = datetime.now(timezone.utc)
    calendar = []

    for card in cards:
        due_day = card.get("due_day", 15)
        billing_day = card.get("billing_cycle_day", 1)

        # Calculate next due date
        try:
            if now.day <= due_day:
                next_due = now.replace(day=due_day)
            else:
                if now.month == 12:
                    next_due = now.replace(year=now.year + 1, month=1, day=due_day)
                else:
                    next_due = now.replace(month=now.month + 1, day=due_day)
        except ValueError:
            next_due = now.replace(day=min(due_day, 28))

        days_until = (next_due.date() - now.date()).days

        # Determine reminder status
        reminders = []
        if days_until <= 1:
            reminders.append({"type": "critical", "message": "Payment due today!" if days_until == 0 else "Payment due tomorrow!"})
        if days_until <= 3:
            reminders.append({"type": "warning", "message": f"Payment due in {days_until} days"})
        elif days_until <= 7:
            reminders.append({"type": "upcoming", "message": f"Payment due in {days_until} days"})

        # Get outstanding from transactions
        outstanding = card.get("current_outstanding", 0)
        if outstanding == 0:
            # Calculate from transactions
            txns = await db.credit_card_transactions.find(
                {"user_id": user_id, "card_id": card["id"]}, {"_id": 0, "type": 1, "amount": 1}
            ).to_list(5000)
            expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
            payments = sum(t["amount"] for t in txns if t["type"] == "payment")
            outstanding = max(0, expenses - payments)

        calendar.append({
            "card_id": card["id"],
            "card_name": card.get("card_name", ""),
            "issuer": card.get("issuer", ""),
            "last_four": card.get("last_four", ""),
            "due_day": due_day,
            "billing_day": billing_day,
            "next_due_date": next_due.strftime("%Y-%m-%d"),
            "days_until_due": days_until,
            "outstanding": round(outstanding, 2),
            "minimum_due": round(outstanding * 0.05, 2),  # 5% min payment
            "reminders": reminders,
            "urgency": "critical" if days_until <= 1 else "warning" if days_until <= 3 else "upcoming" if days_until <= 7 else "normal",
        })

    calendar.sort(key=lambda c: c["days_until_due"])
    return {"calendar": calendar}


# ─── Interest Calculator ───────────────────────────────────────
@router.post("/credit-cards/interest-calculator")
async def calculate_interest(body=Body(...), user=Depends(get_current_user)):
    """Calculate total interest if paying only minimum amount."""
    outstanding = body.get("outstanding", 0)
    monthly_rate = body.get("monthly_rate", 3.49) / 100  # Default 3.49% monthly
    min_payment_pct = body.get("min_payment_pct", 5) / 100  # Default 5%
    card_id = body.get("card_id", "")

    if outstanding <= 0:
        return {"error": "No outstanding balance", "schedule": [], "summary": {}}

    # If card_id provided, get card-specific rate
    if card_id:
        card = await db.credit_cards.find_one(
            {"id": card_id, "user_id": user["id"]}, {"_id": 0}
        )
        if card:
            config = get_card_rewards_config(card.get("card_name", ""))
            monthly_rate = config.get("interest_rate_monthly", 3.49) / 100

    schedule = []
    balance = outstanding
    total_interest = 0
    total_paid = 0
    month = 0

    while balance > 0 and month < 120:  # Cap at 10 years
        month += 1
        interest = balance * monthly_rate
        total_interest += interest
        balance += interest

        min_payment = max(balance * min_payment_pct, 200)  # Min Rs 200
        payment = min(min_payment, balance)
        balance -= payment
        total_paid += payment

        if month <= 24:  # Only show first 24 months in schedule
            schedule.append({
                "month": month,
                "opening_balance": round(balance + payment, 2),
                "interest": round(interest, 2),
                "payment": round(payment, 2),
                "closing_balance": round(balance, 2),
            })

        if balance < 1:
            balance = 0
            break

    return {
        "summary": {
            "original_amount": round(outstanding, 2),
            "total_interest": round(total_interest, 2),
            "total_paid": round(total_paid, 2),
            "months_to_clear": month,
            "interest_pct_of_principal": round(total_interest / outstanding * 100, 2) if outstanding > 0 else 0,
            "monthly_rate": round(monthly_rate * 100, 2),
        },
        "schedule": schedule,
    }


# ─── Rewards Tracker ───────────────────────────────────────────
@router.get("/credit-cards/rewards")
async def get_rewards_tracker(user=Depends(get_current_user)):
    user_id = user["id"]
    cards = await db.credit_cards.find(
        {"user_id": user_id, "is_active": True}, {"_id": 0}
    ).to_list(20)

    all_rewards = []

    for card in cards:
        config = get_card_rewards_config(card.get("card_name", ""))

        # Get all expense transactions for this card
        txns = await db.credit_card_transactions.find(
            {"user_id": user_id, "card_id": card["id"], "type": "expense"},
            {"_id": 0, "amount": 1, "category": 1, "date": 1}
        ).to_list(5000)

        total_spend = sum(t["amount"] for t in txns)

        # Calculate rewards by category
        reward_points = 0
        category_rewards = {}
        for t in txns:
            cat = t.get("category", "Other")
            cat_config = config["categories"].get(cat, config["categories"]["default"])
            multiplier = cat_config["multiplier"]
            points = (t["amount"] / config["reward_per_spend"]) * config["reward_rate"] * multiplier
            reward_points += points
            if cat not in category_rewards:
                category_rewards[cat] = {"spend": 0, "points": 0}
            category_rewards[cat]["spend"] += t["amount"]
            category_rewards[cat]["points"] += points

        rupee_value = reward_points * config["point_value"]

        # Monthly trend (last 6 months)
        now = datetime.now(timezone.utc)
        monthly_rewards = []
        for i in range(5, -1, -1):
            month_date = now - timedelta(days=30 * i)
            month_key = month_date.strftime("%Y-%m")
            month_txns = [t for t in txns if t.get("date", "").startswith(month_key)]
            month_spend = sum(t["amount"] for t in month_txns)
            month_pts = (month_spend / config["reward_per_spend"]) * config["reward_rate"]
            monthly_rewards.append({
                "month": month_date.strftime("%b"),
                "points": round(month_pts),
                "spend": round(month_spend, 2),
            })

        all_rewards.append({
            "card_id": card["id"],
            "card_name": card.get("card_name", ""),
            "last_four": card.get("last_four", ""),
            "total_spend": round(total_spend, 2),
            "reward_points": round(reward_points),
            "rupee_value": round(rupee_value, 2),
            "point_value": config["point_value"],
            "benefits": config.get("benefits", []),
            "categories": {k: {"spend": round(v["spend"], 2), "points": round(v["points"])} for k, v in category_rewards.items()},
            "monthly_trend": monthly_rewards,
        })

    total_points = sum(r["reward_points"] for r in all_rewards)
    total_value = sum(r["rupee_value"] for r in all_rewards)

    return {
        "total_points": round(total_points),
        "total_rupee_value": round(total_value, 2),
        "cards": all_rewards,
    }


# ─── Best Card Recommender (AI-powered) ────────────────────────
@router.post("/credit-cards/recommend")
async def recommend_best_card(body=Body(...), user=Depends(get_current_user)):
    """AI-powered card recommendation for a specific transaction."""
    user_id = user["id"]
    transaction_type = body.get("category", "Shopping")
    amount = body.get("amount", 1000)
    merchant = body.get("merchant", "")

    cards = await db.credit_cards.find(
        {"user_id": user_id, "is_active": True}, {"_id": 0}
    ).to_list(20)

    if not cards:
        return {"recommendations": [], "message": "No active credit cards found"}

    # Score each card for this transaction
    recommendations = []
    for card in cards:
        config = get_card_rewards_config(card.get("card_name", ""))
        cat_config = config["categories"].get(transaction_type, config["categories"]["default"])
        multiplier = cat_config["multiplier"]

        points_earned = (amount / config["reward_per_spend"]) * config["reward_rate"] * multiplier
        value_earned = points_earned * config["point_value"]

        # Outstanding check - prefer cards with more available credit
        outstanding = card.get("current_outstanding", 0)
        credit_limit = card.get("credit_limit", 0)
        utilization_after = ((outstanding + amount) / credit_limit * 100) if credit_limit > 0 else 100

        # Score: higher rewards = better, lower utilization = better
        reward_score = value_earned * 10
        util_penalty = max(0, utilization_after - 30) * 0.5  # Penalty above 30% utilization
        total_score = reward_score - util_penalty

        recommendations.append({
            "card_id": card["id"],
            "card_name": card.get("card_name", ""),
            "last_four": card.get("last_four", ""),
            "issuer": card.get("issuer", ""),
            "points_earned": round(points_earned),
            "value_earned": round(value_earned, 2),
            "reward_note": cat_config.get("note", "Base rewards"),
            "utilization_after": round(utilization_after, 1),
            "credit_available": round(max(0, credit_limit - outstanding - amount), 2),
            "score": round(total_score, 2),
        })

    recommendations.sort(key=lambda r: -r["score"])

    # Generate AI recommendation text if LLM available
    ai_recommendation = ""
    if recommendations:
        best = recommendations[0]
        ai_recommendation = (
            f"Use {best['card_name']} for this Rs {amount:,.0f} {transaction_type} transaction. "
            f"You'll earn {best['points_earned']} points (worth Rs {best['value_earned']:.0f}). "
            f"{best['reward_note']}."
        )
        if best["utilization_after"] > 50:
            ai_recommendation += f" Note: Utilization will be {best['utilization_after']:.0f}% after this transaction."

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        card_info = "\n".join([
            f"- {r['card_name']} ({r['issuer']}): {r['points_earned']} pts (Rs {r['value_earned']:.0f}), "
            f"util: {r['utilization_after']:.0f}%, note: {r['reward_note']}"
            for r in recommendations[:5]
        ])

        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY", ""),
            session_id=f"visor-cc-rec-{user_id}",
            system_message=(
                "You are Visor, an expert Indian credit card advisor. Given the user's cards and a transaction, "
                "recommend the best card in 2-3 sentences. Be specific about why. Mention points earned and any special "
                "category benefits. Use a friendly, helpful tone. Keep it concise."
            ),
        ).with_model("openai", "gpt-4o")

        prompt = (
            f"Transaction: Rs {amount:,.0f} for {transaction_type}"
            f"{f' at {merchant}' if merchant else ''}.\n\n"
            f"Available cards:\n{card_info}\n\n"
            f"Which card should I use and why?"
        )
        ai_recommendation = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        logger.warning(f"AI recommendation failed: {e}")

    return {
        "recommendations": recommendations,
        "best_card": recommendations[0] if recommendations else None,
        "ai_recommendation": ai_recommendation,
        "transaction": {
            "category": transaction_type,
            "amount": amount,
            "merchant": merchant,
        },
    }
