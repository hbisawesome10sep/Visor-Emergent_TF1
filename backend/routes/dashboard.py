from fastapi import APIRouter, Depends
from typing import Optional
from datetime import datetime, timezone, timedelta
from database import db
from auth import get_current_user

router = APIRouter(prefix="/api")


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user),
):
    user_id = user["id"]

    query = {"user_id": user_id}
    cc_query = {"user_id": user_id}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
        cc_query["date"] = {"$gte": start_date, "$lte": end_date}

    txns = await db.transactions.find(query, {"_id": 0}).to_list(1000)
    cc_txns = await db.credit_card_transactions.find(cc_query, {"_id": 0}).to_list(500)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    credit_cards = await db.credit_cards.find({"user_id": user_id, "is_active": True}, {"_id": 0}).to_list(20)

    # Also fetch holdings for portfolio invested total (aligns Investment card values)
    holdings = await db.holdings.find({"user_id": user_id}, {"_id": 0, "invested_value": 1, "current_value": 1, "quantity": 1, "buy_price": 1}).to_list(500)
    portfolio_invested = sum(h.get("invested_value", 0) or (h.get("quantity", 0) * h.get("buy_price", 0)) for h in holdings)
    portfolio_current = sum(h.get("current_value", 0) or h.get("invested_value", 0) for h in holdings)

    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
    
    # Credit Card metrics
    cc_total_expenses = sum(t["amount"] for t in cc_txns if t["type"] == "expense")
    cc_total_payments = sum(t["amount"] for t in cc_txns if t["type"] == "payment")
    cc_outstanding = cc_total_expenses - cc_total_payments
    cc_total_limit = sum(c.get("credit_limit", 0) for c in credit_cards)
    cc_utilization = (cc_outstanding / cc_total_limit * 100) if cc_total_limit > 0 else 0
    
    net_balance = total_income - total_expenses - total_investments

    category_breakdown = {}
    for t in txns:
        if t["type"] == "expense":
            cat = t["category"]
            category_breakdown[cat] = category_breakdown.get(cat, 0) + t["amount"]
    
    # Add credit card expenses to category breakdown
    for t in cc_txns:
        if t["type"] == "expense":
            cat = t.get("category", "Other")
            category_breakdown[cat] = category_breakdown.get(cat, 0) + t["amount"]

    recent = sorted(txns, key=lambda x: x.get("date", ""), reverse=True)[:5]

    now = datetime.now(timezone.utc)
    current_month = now.strftime("%Y-%m")
    monthly_income = sum(t["amount"] for t in txns if t["type"] == "income" and t.get("date", "").startswith(current_month))
    monthly_expenses = sum(t["amount"] for t in txns if t["type"] == "expense" and t.get("date", "").startswith(current_month))
    monthly_investments = sum(t["amount"] for t in txns if t["type"] == "investment" and t.get("date", "").startswith(current_month))
    monthly_cc_expenses = sum(t["amount"] for t in cc_txns if t["type"] == "expense" and t.get("date", "").startswith(current_month))

    total_goal_target = sum(g["target_amount"] for g in goals) if goals else 0
    total_goal_current = sum(g["current_amount"] for g in goals) if goals else 0
    goal_progress = (total_goal_current / total_goal_target * 100) if total_goal_target > 0 else 0

    # Include credit card expenses in total spending for accurate metrics
    combined_expenses = total_expenses + cc_total_expenses
    savings = total_income - combined_expenses - total_investments
    savings_rate = max(-100, min((savings / total_income * 100) if total_income > 0 else 0, 100))
    expense_ratio = (combined_expenses / total_income * 100) if total_income > 0 else 0
    investment_ratio = (total_investments / total_income * 100) if total_income > 0 else 0
    monthly_savings = monthly_income - monthly_expenses - monthly_cc_expenses - monthly_investments

    budget_items = []
    for cat, amount in sorted(category_breakdown.items(), key=lambda x: -x[1]):
        pct = (amount / total_income * 100) if total_income > 0 else 0
        budget_items.append({"category": cat, "amount": amount, "percentage": round(pct, 1)})

    invest_breakdown = {}
    for t in txns:
        if t["type"] == "investment":
            cat = t["category"]
            invest_breakdown[cat] = invest_breakdown.get(cat, 0) + t["amount"]

    user_created_at = user.get("created_at", now.isoformat())

    # Health Score Calculation
    # Use ONLY the transactions from the selected period for accurate scores
    hs_income = sum(t["amount"] for t in txns if t["type"] == "income")
    hs_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    hs_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
    
    # Handle zero income gracefully - don't calculate ratios when there's no income data
    has_income_data = hs_income > 0
    
    if has_income_data:
        hs_savings_rate = max(0, min(100, (hs_income - hs_expenses) / hs_income * 100))
        hs_investment_rate = min(100, hs_investments / hs_income * 100)
        hs_expense_ratio = min(200, hs_expenses / hs_income * 100)  # Cap at 200% to avoid huge numbers
    else:
        # No income data - can't calculate meaningful ratios
        hs_savings_rate = 0
        hs_investment_rate = 0
        hs_expense_ratio = 0 if hs_expenses == 0 else 100  # If no income but has expenses, 100% expense ratio

    hs_goal_target = sum(g["target_amount"] for g in goals) if goals else 0
    hs_goal_current = sum(g["current_amount"] for g in goals) if goals else 0
    hs_goal_score = min(100, (hs_goal_current / hs_goal_target * 100)) if hs_goal_target > 0 else 0

    hs_savings_score = min(100, hs_savings_rate * 2.5) if has_income_data else 0
    hs_invest_score = min(100, hs_investment_rate * 5) if has_income_data else 0
    hs_expense_score = max(0, 100 - hs_expense_ratio) if has_income_data else 0

    # Calculate overall score - but indicate if there's insufficient data
    if has_income_data or hs_goal_target > 0:
        hs_overall = (hs_savings_score * 0.3 + hs_invest_score * 0.2 + hs_expense_score * 0.3 + hs_goal_score * 0.2)
        hs_overall = min(100, max(0, hs_overall))
    else:
        hs_overall = 0  # No data to calculate score

    if not has_income_data and hs_expenses == 0 and hs_goal_target == 0:
        hs_grade = "No Data"
    elif hs_overall >= 80:
        hs_grade = "Excellent"
    elif hs_overall >= 65:
        hs_grade = "Good"
    elif hs_overall >= 45:
        hs_grade = "Fair"
    elif hs_overall >= 25:
        hs_grade = "Needs Work"
    else:
        hs_grade = "Critical"

    # Trend Analysis
    trend_data = []
    trend_insights = []

    if txns:
        sorted_txns = sorted(txns, key=lambda x: x.get("date", ""))
        weekly_data = {}
        for t in sorted_txns:
            date_str = t.get("date", "")
            if not date_str:
                continue
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                week_start = dt - timedelta(days=dt.weekday())
                week_key = week_start.strftime("%b %d")
            except Exception:
                continue

            if week_key not in weekly_data:
                weekly_data[week_key] = {"income": 0, "expenses": 0, "investments": 0}

            if t["type"] == "income":
                weekly_data[week_key]["income"] += t["amount"]
            elif t["type"] == "expense":
                weekly_data[week_key]["expenses"] += t["amount"]
            elif t["type"] == "investment":
                weekly_data[week_key]["investments"] += t["amount"]

        for week_label, data in weekly_data.items():
            trend_data.append({
                "label": week_label,
                "income": round(data["income"], 2),
                "expenses": round(data["expenses"], 2),
                "investments": round(data["investments"], 2),
            })

        if len(weekly_data) >= 2:
            weeks = list(weekly_data.keys())
            last_week = weekly_data.get(weeks[-1], {})
            prev_week = weekly_data.get(weeks[-2], {})

            exp_change = last_week.get("expenses", 0) - prev_week.get("expenses", 0)
            if exp_change > 0:
                exp_pct = (exp_change / max(prev_week.get("expenses", 1), 1)) * 100
                trend_insights.append({"type": "warning", "icon": "trending-up", "title": "Expenses Increasing", "message": f"Your spending increased by ₹{exp_change:,.0f} ({exp_pct:.1f}%) from last week"})
            elif exp_change < 0:
                exp_pct = abs(exp_change / max(prev_week.get("expenses", 1), 1)) * 100
                trend_insights.append({"type": "success", "icon": "trending-down", "title": "Expenses Decreasing", "message": f"Great! You saved ₹{abs(exp_change):,.0f} ({exp_pct:.1f}%) compared to last week"})

            inc_change = last_week.get("income", 0) - prev_week.get("income", 0)
            if inc_change > 0:
                inc_pct = (inc_change / max(prev_week.get("income", 1), 1)) * 100
                trend_insights.append({"type": "success", "icon": "cash-plus", "title": "Income Growing", "message": f"Income increased by ₹{inc_change:,.0f} ({inc_pct:.1f}%)"})

            inv_change = last_week.get("investments", 0) - prev_week.get("investments", 0)
            if inv_change > 0:
                trend_insights.append({"type": "success", "icon": "chart-line", "title": "Investing More", "message": f"You invested ₹{last_week.get('investments', 0):,.0f} this week"})

        if category_breakdown:
            top_cat = max(category_breakdown.items(), key=lambda x: x[1])
            top_pct = (top_cat[1] / total_expenses * 100) if total_expenses > 0 else 0
            trend_insights.append({"type": "info", "icon": "tag", "title": f"Top Spending: {top_cat[0]}", "message": f"₹{top_cat[1]:,.0f} ({top_pct:.1f}% of total expenses)"})

        if savings > 0:
            trend_insights.append({"type": "success", "icon": "piggy-bank", "title": "Savings Summary", "message": f"You saved ₹{savings:,.0f} ({savings_rate:.1f}% of income) in this period"})
        elif savings < 0:
            trend_insights.append({"type": "warning", "icon": "alert", "title": "Spending Exceeds Income", "message": f"You're ₹{abs(savings):,.0f} over budget. Review your expenses."})

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "total_investments": total_investments,
        "portfolio_invested": portfolio_invested,
        "portfolio_current": portfolio_current,
        "net_balance": net_balance,
        "savings": savings,
        "savings_rate": round(savings_rate, 1),
        "expense_ratio": round(expense_ratio, 1),
        "investment_ratio": round(investment_ratio, 1),
        "category_breakdown": category_breakdown,
        "budget_items": budget_items,
        "invest_breakdown": invest_breakdown,
        "recent_transactions": recent,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "monthly_investments": monthly_investments,
        "monthly_savings": monthly_savings,
        "goal_count": len(goals),
        "goal_progress": round(goal_progress, 1),
        "transaction_count": len(txns),
        "user_created_at": user_created_at,
        "date_range": {"start": start_date, "end": end_date} if start_date and end_date else None,
        "trend_data": trend_data,
        "trend_insights": trend_insights,
        "health_score": {
            "overall": round(hs_overall, 1),
            "grade": hs_grade,
            "has_sufficient_data": has_income_data,
            "breakdown": {
                "savings": round(hs_savings_score, 1),
                "investments": round(hs_invest_score, 1),
                "spending": round(hs_expense_score, 1),
                "goals": round(hs_goal_score, 1),
            },
            "metrics": {
                "savings_rate": round(hs_savings_rate, 1),
                "investment_rate": round(hs_investment_rate, 1),
                "expense_ratio": round(hs_expense_ratio, 1),
                "goal_progress": round(hs_goal_score, 1),
            },
        },
        "credit_card_summary": {
            "total_outstanding": round(cc_outstanding, 2),
            "total_limit": round(cc_total_limit, 2),
            "utilization": round(cc_utilization, 1),
            "total_expenses": round(cc_total_expenses, 2),
            "total_payments": round(cc_total_payments, 2),
            "monthly_expenses": round(monthly_cc_expenses, 2),
            "cards_count": len(credit_cards),
        },
    }


@router.get("/health-score")
async def get_health_score(user=Depends(get_current_user)):
    user_id = user["id"]
    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(100)

    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
    
    # Handle zero income gracefully
    has_income_data = total_income > 0
    
    if has_income_data:
        savings_rate = max(0, min(100, (total_income - total_expenses) / total_income * 100))
        investment_rate = min(100, total_investments / total_income * 100)
        expense_ratio = min(200, total_expenses / total_income * 100)
    else:
        savings_rate = 0
        investment_rate = 0
        expense_ratio = 0 if total_expenses == 0 else 100

    total_goal_target = sum(g["target_amount"] for g in goals) if goals else 0
    total_goal_current = sum(g["current_amount"] for g in goals) if goals else 0
    goal_score = min(100, (total_goal_current / total_goal_target * 100)) if total_goal_target > 0 else 0

    savings_score = min(100, savings_rate * 2.5) if has_income_data else 0
    invest_score = min(100, investment_rate * 5) if has_income_data else 0
    expense_score = max(0, 100 - expense_ratio) if has_income_data else 0

    if has_income_data or total_goal_target > 0:
        overall = (savings_score * 0.3 + invest_score * 0.2 + expense_score * 0.3 + goal_score * 0.2)
        overall = min(100, max(0, overall))
    else:
        overall = 0

    if not has_income_data and total_expenses == 0 and total_goal_target == 0:
        grade = "No Data"
    elif overall >= 80:
        grade = "Excellent"
    elif overall >= 65:
        grade = "Good"
    elif overall >= 45:
        grade = "Fair"
    elif overall >= 25:
        grade = "Needs Work"
    else:
        grade = "Critical"

    return {
        "overall_score": round(overall, 1),
        "grade": grade,
        "has_sufficient_data": has_income_data,
        "savings_rate": round(savings_rate, 1),
        "investment_rate": round(investment_rate, 1),
        "expense_ratio": round(expense_ratio, 1),
        "goal_progress": round(goal_score, 1),
        "breakdown": {
            "savings": round(savings_score, 1),
            "investments": round(invest_score, 1),
            "spending": round(expense_score, 1),
            "goals": round(goal_score, 1),
        }
    }


@router.get("/dashboard/monthly-trends")
async def get_monthly_trends(user=Depends(get_current_user)):
    """Get monthly income/expense/savings trends for the last 6 months."""
    user_id = user["id"]
    
    # Get transactions from last 6 months
    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=180)
    
    txns = await db.transactions.find({
        "user_id": user_id,
        "date": {"$gte": six_months_ago.strftime("%Y-%m-%d")}
    }, {"_id": 0}).to_list(5000)
    
    # Group by month
    monthly_data = {}
    for t in txns:
        date_str = t.get("date", "")
        if not date_str:
            continue
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = dt.strftime("%Y-%m")
            month_label = dt.strftime("%b")
        except Exception:
            continue
        
        if month_key not in monthly_data:
            monthly_data[month_key] = {"month": month_label, "income": 0, "expenses": 0, "investments": 0}
        
        if t["type"] == "income":
            monthly_data[month_key]["income"] += t["amount"]
        elif t["type"] == "expense":
            monthly_data[month_key]["expenses"] += t["amount"]
        elif t["type"] == "investment":
            monthly_data[month_key]["investments"] += t["amount"]
    
    # Sort by month and calculate savings
    sorted_months = sorted(monthly_data.keys())
    result = []
    for month_key in sorted_months[-6:]:  # Last 6 months
        data = monthly_data[month_key]
        savings = data["income"] - data["expenses"] - data["investments"]
        result.append({
            "month": data["month"],
            "income": round(data["income"], 2),
            "expenses": round(data["expenses"], 2),
            "savings": round(savings, 2),
        })
    
    return {"trends": result}


@router.get("/dashboard/smart-alerts")
async def get_smart_alerts(user=Depends(get_current_user)):
    """Generate smart financial alerts based on user's data."""
    user_id = user["id"]
    
    now = datetime.now(timezone.utc)
    current_month = now.strftime("%Y-%m")
    last_month = (now - timedelta(days=30)).strftime("%Y-%m")
    
    # Fetch data
    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(5000)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    budgets = await db.budgets.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    alerts = []
    alert_id = 1
    
    # Calculate current month stats
    current_income = sum(t["amount"] for t in txns if t["type"] == "income" and t.get("date", "").startswith(current_month))
    current_expenses = sum(t["amount"] for t in txns if t["type"] == "expense" and t.get("date", "").startswith(current_month))
    last_month_expenses = sum(t["amount"] for t in txns if t["type"] == "expense" and t.get("date", "").startswith(last_month))
    
    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    
    # Alert 1: Overspending compared to last month
    if last_month_expenses > 0 and current_expenses > last_month_expenses * 1.2:
        pct_increase = ((current_expenses - last_month_expenses) / last_month_expenses) * 100
        alerts.append({
            "id": f"alert_{alert_id}",
            "type": "warning",
            "icon": "trending-up",
            "title": "Spending Up This Month",
            "message": f"You've spent {pct_increase:.0f}% more than last month. Consider reviewing discretionary expenses.",
            "value": f"₹{current_expenses:,.0f}",
            "action": "Review"
        })
        alert_id += 1
    
    # Alert 2: Low savings rate
    if total_income > 0:
        savings_rate = max(-100, min(((total_income - total_expenses) / total_income) * 100, 100))
        if savings_rate < 10:
            alerts.append({
                "id": f"alert_{alert_id}",
                "type": "critical",
                "icon": "piggy-bank-outline",
                "title": "Low Savings Rate",
                "message": "Your savings rate is below 10%. Aim for at least 20% to build wealth.",
                "value": f"{savings_rate:.1f}%",
                "action": "Plan"
            })
            alert_id += 1
        elif savings_rate >= 30:
            alerts.append({
                "id": f"alert_{alert_id}",
                "type": "success",
                "icon": "check-circle",
                "title": "Excellent Savings!",
                "message": "You're saving over 30% of your income. Great financial discipline!",
                "value": f"{savings_rate:.1f}%"
            })
            alert_id += 1
    
    # Alert 3: Budget alerts
    current_month_by_category = {}
    for t in txns:
        if t["type"] == "expense" and t.get("date", "").startswith(current_month):
            cat = t["category"]
            current_month_by_category[cat] = current_month_by_category.get(cat, 0) + t["amount"]
    
    for budget in budgets:
        cat = budget.get("category", "")
        limit = budget.get("amount", 0)
        spent = current_month_by_category.get(cat, 0)
        if limit > 0 and spent > limit * 0.9:
            alerts.append({
                "id": f"alert_{alert_id}",
                "type": "critical" if spent > limit else "warning",
                "icon": "alert-circle" if spent > limit else "alert",
                "title": f"{cat} Budget Alert",
                "message": f"{'Exceeded' if spent > limit else 'Near'} your {cat} budget limit.",
                "value": f"₹{spent:,.0f} / ₹{limit:,.0f}",
                "action": "Adjust"
            })
            alert_id += 1
    
    # Alert 4: Goal progress
    for goal in goals:
        target = goal.get("target_amount", 0)
        current = goal.get("current_amount", 0)
        deadline = goal.get("deadline", "")
        name = goal.get("name", "Goal")
        
        if target > 0:
            progress = (current / target) * 100
            if progress >= 100:
                alerts.append({
                    "id": f"alert_{alert_id}",
                    "type": "success",
                    "icon": "trophy",
                    "title": f"Goal Achieved: {name}",
                    "message": "Congratulations! You've reached your target.",
                    "value": f"₹{current:,.0f}"
                })
                alert_id += 1
            elif deadline:
                try:
                    deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
                    days_left = (deadline_dt - now).days
                    if 0 < days_left <= 30 and progress < 80:
                        alerts.append({
                            "id": f"alert_{alert_id}",
                            "type": "warning",
                            "icon": "clock-alert",
                            "title": f"Goal Deadline Near: {name}",
                            "message": f"Only {days_left} days left and {100-progress:.0f}% remaining.",
                            "value": f"₹{target - current:,.0f} to go",
                            "action": "Boost"
                        })
                        alert_id += 1
                except Exception:
                    pass
    
    # Alert 5: No income recorded this month
    if current_income == 0 and now.day > 10:
        alerts.append({
            "id": f"alert_{alert_id}",
            "type": "info",
            "icon": "cash-register",
            "title": "No Income Recorded",
            "message": "Record your income to get accurate financial insights.",
            "action": "Add"
        })
        alert_id += 1
    
    # Alert 6: Emergency fund check
    avg_monthly_expense = total_expenses / max(1, len(set(t.get("date", "")[:7] for t in txns if t["type"] == "expense")))
    emergency_fund_months = max(0, (total_income - total_expenses) / avg_monthly_expense) if avg_monthly_expense > 0 else 0
    
    if emergency_fund_months < 3 and total_income > 0:
        alerts.append({
            "id": f"alert_{alert_id}",
            "type": "warning",
            "icon": "shield-alert",
            "title": "Build Emergency Fund",
            "message": f"You have ~{emergency_fund_months:.1f} months of expenses saved. Aim for 6 months.",
            "action": "Plan"
        })
        alert_id += 1
    
    return {"alerts": alerts[:8]}  # Limit to 8 most important alerts

