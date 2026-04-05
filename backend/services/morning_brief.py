"""
Visor AI — Proactive Morning Brief
Computes a daily financial snapshot: yesterday's spending, upcoming dues,
SIP reminders, 80C progress, market pulse, and a personalized insight.
No LLM needed — pure data computation.
"""
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from database import db

logger = logging.getLogger(__name__)

BRIEF_COLLECTION = "morning_briefs"


async def compute_morning_brief(user_id: str) -> dict:
    """
    Compute today's morning financial brief for a user.
    Returns structured data that can be displayed as a card/notification.
    """
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    three_days = (now + timedelta(days=3)).strftime("%Y-%m-%d")

    # Current month for monthly average
    month_start = now.replace(day=1).strftime("%Y-%m-%d")

    # ── Yesterday's spending ─────────────────────────────────────────
    yesterday_txns = await db.transactions.find({
        "user_id": user_id,
        "type": {"$ne": "income"},
        "date": yesterday,
    }, {"_id": 0}).to_list(200)

    yesterday_total = sum(t.get("amount", 0) for t in yesterday_txns)
    yesterday_categories = defaultdict(float)
    for t in yesterday_txns:
        yesterday_categories[t.get("category", "Other")] += t.get("amount", 0)
    top_yesterday = sorted(yesterday_categories.items(), key=lambda x: -x[1])[:3]

    # Monthly spending for average comparison
    month_txns = await db.transactions.find({
        "user_id": user_id,
        "type": {"$ne": "income"},
        "date": {"$gte": month_start, "$lte": today},
    }, {"_id": 0, "amount": 1, "date": 1}).to_list(5000)

    days_elapsed = max(now.day - 1, 1)
    month_total = sum(t.get("amount", 0) for t in month_txns)
    daily_avg = month_total / days_elapsed if days_elapsed > 0 else 0

    spend_vs_avg = "above" if yesterday_total > daily_avg * 1.2 else ("below" if yesterday_total < daily_avg * 0.8 else "around")

    # ── Upcoming dues (3 days) ───────────────────────────────────────
    upcoming_dues = []

    # Credit card dues
    credit_cards = await db.credit_cards.find(
        {"user_id": user_id}, {"_id": 0}
    ).to_list(10)
    for cc in credit_cards:
        due_date = cc.get("due_date")
        outstanding = cc.get("outstanding", cc.get("min_due", 0))
        if due_date and outstanding > 0:
            # due_date could be int (day of month) or string (YYYY-MM-DD)
            if isinstance(due_date, int):
                try:
                    due_day = min(due_date, 28)
                    due_str = now.replace(day=due_day).strftime("%Y-%m-%d")
                    if due_str >= today and due_str <= three_days:
                        upcoming_dues.append({
                            "type": "Credit Card",
                            "name": cc.get("name", "Card"),
                            "amount": outstanding,
                            "due_date": due_str,
                        })
                except (ValueError, TypeError):
                    pass
            elif isinstance(due_date, str) and due_date >= today and due_date <= three_days:
                upcoming_dues.append({
                    "type": "Credit Card",
                    "name": cc.get("name", "Card"),
                    "amount": outstanding,
                    "due_date": due_date,
                })

    # Loan EMIs
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(20)
    for loan in loans:
        emi_date = loan.get("emi_date", 0)
        if emi_date and isinstance(emi_date, int):
            try:
                next_emi_day = min(emi_date, 28)
                next_emi = now.replace(day=next_emi_day).strftime("%Y-%m-%d")
                if next_emi >= today and next_emi <= three_days:
                    upcoming_dues.append({
                        "type": "EMI",
                        "name": loan.get("name", "Loan"),
                        "amount": loan.get("emi_amount", 0),
                        "due_date": next_emi,
                    })
            except (ValueError, TypeError):
                pass

    # ── SIP reminders ────────────────────────────────────────────────
    sip_reminders = []
    sips = await db.recurring_transactions.find({
        "user_id": user_id,
        "status": "active",
    }, {"_id": 0}).to_list(20)

    for sip in sips:
        sip_day = sip.get("day_of_month", 0)
        if sip_day:
            sip_date_this_month = min(sip_day, 28)
            sip_date = now.replace(day=sip_date_this_month).strftime("%Y-%m-%d")
            if sip_date >= today and sip_date <= three_days:
                sip_reminders.append({
                    "name": sip.get("description", sip.get("name", "SIP")),
                    "amount": sip.get("amount", 0),
                    "date": sip_date,
                })

    # ── 80C progress ─────────────────────────────────────────────────
    fy_start = f"{now.year}-04-01" if now.month >= 4 else f"{now.year - 1}-04-01"
    fy_end = f"{now.year + 1}-03-31" if now.month >= 4 else f"{now.year}-03-31"

    tax_deductions = await db.tax_deductions.find({
        "user_id": user_id,
        "fy": {"$regex": str(int(fy_start[:4]))},
    }, {"_id": 0}).to_list(100)

    section_80c_total = 0
    for ded in tax_deductions:
        if ded.get("section", "").startswith("80C"):
            section_80c_total += ded.get("amount", 0)

    # Also check auto-detected deductions
    auto_deds = await db.auto_detected_deductions.find({
        "user_id": user_id,
    }, {"_id": 0}).to_list(100)
    for ad in auto_deds:
        if ad.get("section", "").startswith("80C"):
            section_80c_total += ad.get("amount", 0)

    eighty_c_limit = 150000
    eighty_c_used = min(section_80c_total, eighty_c_limit)
    eighty_c_remaining = eighty_c_limit - eighty_c_used
    eighty_c_pct = round(eighty_c_used / eighty_c_limit * 100, 1)

    # ── Market snapshot ──────────────────────────────────────────────
    market_data = await db.market_data.find({}, {"_id": 0}).to_list(10)
    market_snapshot = {}
    for m in market_data:
        name = m.get("name", "")
        if name in ("Nifty 50", "SENSEX", "Gold (10g)", "Silver (1Kg)"):
            market_snapshot[name] = {
                "price": m.get("price", 0),
                "change_pct": m.get("change_pct", 0),
            }

    # ── Quick insight (rule-based, no LLM) ───────────────────────────
    insights = []
    if yesterday_total > daily_avg * 1.5:
        insights.append(f"Yesterday's spending was {round(yesterday_total / daily_avg, 1)}x your daily average. Consider checking if any expenses were one-time or can be avoided.")
    if eighty_c_remaining > 50000 and now.month >= 1 and now.month <= 3:
        months_left = 3 - (now.month - 1) if now.month <= 3 else 0
        if months_left > 0:
            insights.append(f"Only {months_left} month(s) left in FY! You can still invest Rs {eighty_c_remaining:,.0f} in 80C to save tax.")
    if len(upcoming_dues) > 0:
        total_dues = sum(d["amount"] for d in upcoming_dues)
        insights.append(f"{len(upcoming_dues)} payment(s) due in next 3 days totaling Rs {total_dues:,.0f}.")
    if len(sip_reminders) > 0:
        insights.append(f"{len(sip_reminders)} SIP(s) scheduled in next 3 days.")
    if not insights:
        insights.append("Your finances look steady today. Keep tracking your expenses!")

    # ── Assemble brief ───────────────────────────────────────────────
    brief = {
        "user_id": user_id,
        "date": today,
        "yesterday_spending": {
            "total": round(yesterday_total, 2),
            "vs_daily_avg": spend_vs_avg,
            "daily_avg": round(daily_avg, 2),
            "top_categories": [{"category": k, "amount": round(v, 2)} for k, v in top_yesterday],
            "transaction_count": len(yesterday_txns),
        },
        "month_to_date": {
            "total_spent": round(month_total, 2),
            "days_elapsed": days_elapsed,
            "projected_month_end": round(month_total / days_elapsed * 30, 2) if days_elapsed > 0 else 0,
        },
        "upcoming_dues": upcoming_dues,
        "sip_reminders": sip_reminders,
        "tax_80c": {
            "used": round(eighty_c_used, 2),
            "remaining": round(eighty_c_remaining, 2),
            "limit": eighty_c_limit,
            "pct_used": eighty_c_pct,
        },
        "market_snapshot": market_snapshot,
        "insights": insights,
        "computed_at": now.isoformat(),
    }

    # Cache it
    await db[BRIEF_COLLECTION].update_one(
        {"user_id": user_id, "date": today},
        {"$set": brief},
        upsert=True,
    )

    return brief


async def get_cached_brief(user_id: str) -> dict | None:
    """Get today's cached brief if it exists."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return await db[BRIEF_COLLECTION].find_one(
        {"user_id": user_id, "date": today}, {"_id": 0}
    )
