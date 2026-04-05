# /app/backend/services/essential_mode_ai.py
"""
Essential Mode AI Service
AI-powered features specifically designed for Essential Mode users
Provides conversational interfaces instead of complex UI
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class EssentialModeAI:
    """AI features specifically for Essential Mode users"""
    
    async def generate_morning_brief(self, user_id: str, db, llm_client=None) -> Dict:
        """
        Generate a conversational morning brief instead of dashboard
        Returns a friendly, personalized financial summary
        """
        try:
            # Get user stats
            stats = await self._get_user_stats(user_id, db)
            alerts = await self._get_smart_alerts(user_id, db)
            
            # Build the brief message
            brief = self._build_brief_message(stats, alerts)
            
            return {
                "success": True,
                "message": brief["greeting"],
                "snapshot": brief["snapshot"],
                "alerts": brief["alerts"],
                "tip": brief["tip"],
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating morning brief: {e}")
            return {
                "success": False,
                "message": "Good morning! I'm having trouble fetching your data right now. Please try again in a moment.",
                "snapshot": None,
                "alerts": [],
                "tip": None
            }
    
    async def get_essential_snapshot(self, user_id: str, db) -> Dict:
        """
        Get the 3-card financial snapshot for Essential mode
        Cards: Spent This Month, Safe to Spend, Saved
        """
        try:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get transactions for this month
            transactions = await db.transactions.find({
                "user_id": user_id,
                "date": {"$gte": month_start.strftime("%Y-%m-%d")}
            }).to_list(None)
            
            # Calculate totals
            total_income = sum(t.get("amount", 0) for t in transactions if t.get("type") == "income")
            total_expenses = sum(abs(t.get("amount", 0)) for t in transactions if t.get("type") == "expense")
            
            # Get recurring expenses for "safe to spend" calculation
            recurring = await db.recurring_transactions.find({
                "user_id": user_id,
                "is_active": True,
                "category": {"$in": ["Bills", "EMI", "Insurance", "Rent"]}
            }).to_list(None)
            
            upcoming_bills = sum(r.get("amount", 0) for r in recurring)
            
            # Calculate metrics
            spent = total_expenses
            
            # Safe to spend = Income - Spent - Upcoming Bills - Savings Target (20% of income)
            savings_target = total_income * 0.20 if total_income > 0 else 0
            safe_to_spend = max(0, total_income - spent - upcoming_bills - savings_target)
            
            # Saved = What's been put into savings categories
            savings_categories = ["SIP", "Investment", "FD", "PPF", "NPS", "Savings"]
            saved = sum(
                abs(t.get("amount", 0)) 
                for t in transactions 
                if t.get("category") in savings_categories
            )
            
            # Calculate trends (compare to last month)
            last_month_start = (month_start - timedelta(days=1)).replace(day=1)
            last_month_end = month_start - timedelta(days=1)
            
            last_month_txns = await db.transactions.find({
                "user_id": user_id,
                "date": {
                    "$gte": last_month_start.strftime("%Y-%m-%d"),
                    "$lte": last_month_end.strftime("%Y-%m-%d")
                }
            }).to_list(None)
            
            last_month_expenses = sum(
                abs(t.get("amount", 0)) 
                for t in last_month_txns 
                if t.get("type") == "expense"
            )
            
            # Days elapsed in month for projection
            days_elapsed = now.day
            days_in_month = 30  # Simplified
            
            # Project full month spending
            if days_elapsed > 0:
                projected_spending = (spent / days_elapsed) * days_in_month
            else:
                projected_spending = 0
            
            spending_trend = "up" if projected_spending > last_month_expenses else "down"
            spending_trend_pct = (
                ((projected_spending - last_month_expenses) / last_month_expenses * 100)
                if last_month_expenses > 0 else 0
            )
            
            return {
                "spent": {
                    "amount": spent,
                    "label": "Spent This Month",
                    "trend": spending_trend,
                    "trend_pct": round(abs(spending_trend_pct), 1),
                    "color": "#EF4444"
                },
                "safe_to_spend": {
                    "amount": safe_to_spend,
                    "label": "Safe to Spend",
                    "days_remaining": days_in_month - days_elapsed,
                    "per_day": safe_to_spend / max(1, days_in_month - days_elapsed),
                    "color": "#10B981"
                },
                "saved": {
                    "amount": saved,
                    "label": "Saved",
                    "target": savings_target,
                    "progress_pct": (saved / savings_target * 100) if savings_target > 0 else 0,
                    "color": "#6366F1"
                },
                "month": now.strftime("%B %Y"),
                "as_of": now.strftime("%d %b, %I:%M %p")
            }
            
        except Exception as e:
            logger.error(f"Error getting essential snapshot: {e}")
            return {
                "spent": {"amount": 0, "label": "Spent This Month", "color": "#EF4444"},
                "safe_to_spend": {"amount": 0, "label": "Safe to Spend", "color": "#10B981"},
                "saved": {"amount": 0, "label": "Saved", "color": "#6366F1"},
                "error": str(e)
            }
    
    async def get_smart_alerts(self, user_id: str, db, limit: int = 5) -> List[Dict]:
        """
        Get AI-curated smart alerts
        Only shows what actually needs attention
        """
        alerts = []
        now = datetime.now(timezone.utc)
        
        try:
            # 1. Credit card dues in next 7 days
            credit_cards = await db.credit_cards.find({"user_id": user_id}).to_list(None)
            for card in credit_cards:
                due_date_str = card.get("due_date")
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                        days_until = (due_date - now.replace(tzinfo=None)).days
                        if 0 <= days_until <= 7:
                            outstanding = card.get("outstanding_balance", 0)
                            if outstanding > 0:
                                alerts.append({
                                    "type": "bill_due",
                                    "priority": "high" if days_until <= 3 else "medium",
                                    "icon": "credit-card",
                                    "color": "#EF4444" if days_until <= 3 else "#F59E0B",
                                    "title": f"{card.get('bank', 'Credit Card')} due in {days_until} days",
                                    "message": f"₹{outstanding:,.0f} outstanding",
                                    "action": {"type": "pay", "card_id": str(card.get("_id", ""))}
                                })
                    except:
                        pass
            
            # 2. Upcoming EMIs
            loans = await db.loans.find({"user_id": user_id}).to_list(None)
            for loan in loans:
                emi_date = loan.get("emi_date", 5)  # Default 5th of month
                next_emi = now.replace(day=emi_date)
                if next_emi < now:
                    next_emi = (next_emi + timedelta(days=32)).replace(day=emi_date)
                
                days_until = (next_emi - now).days
                if 0 <= days_until <= 5:
                    alerts.append({
                        "type": "emi_due",
                        "priority": "high" if days_until <= 2 else "medium",
                        "icon": "home",
                        "color": "#F59E0B",
                        "title": f"{loan.get('name', 'Loan')} EMI in {days_until} days",
                        "message": f"₹{loan.get('emi_amount', 0):,.0f}",
                        "action": None
                    })
            
            # 3. Unusual spending detection (simplified)
            month_start = now.replace(day=1)
            this_month_txns = await db.transactions.find({
                "user_id": user_id,
                "type": "expense",
                "date": {"$gte": month_start.strftime("%Y-%m-%d")}
            }).to_list(None)
            
            # Group by category
            category_totals = {}
            for txn in this_month_txns:
                cat = txn.get("category", "Other")
                category_totals[cat] = category_totals.get(cat, 0) + abs(txn.get("amount", 0))
            
            # Get last month for comparison
            last_month_start = (month_start - timedelta(days=1)).replace(day=1)
            last_month_txns = await db.transactions.find({
                "user_id": user_id,
                "type": "expense",
                "date": {
                    "$gte": last_month_start.strftime("%Y-%m-%d"),
                    "$lt": month_start.strftime("%Y-%m-%d")
                }
            }).to_list(None)
            
            last_month_totals = {}
            for txn in last_month_txns:
                cat = txn.get("category", "Other")
                last_month_totals[cat] = last_month_totals.get(cat, 0) + abs(txn.get("amount", 0))
            
            # Check for spikes (>50% increase)
            for cat, amount in category_totals.items():
                last_amount = last_month_totals.get(cat, 0)
                if last_amount > 0:
                    increase = (amount - last_amount) / last_amount
                    if increase > 0.5 and amount > 5000:  # >50% increase and significant amount
                        alerts.append({
                            "type": "unusual_spending",
                            "priority": "low",
                            "icon": "trending-up",
                            "color": "#F59E0B",
                            "title": f"{cat} spending is up",
                            "message": f"₹{amount:,.0f} this month vs ₹{last_amount:,.0f} last month",
                            "action": {"type": "analyze", "category": cat}
                        })
            
            # 4. Upcoming SIPs
            sips = await db.recurring_transactions.find({
                "user_id": user_id,
                "category": "SIP",
                "is_active": True
            }).to_list(None)
            
            for sip in sips:
                sip_day = sip.get("day_of_month", 5)
                next_sip = now.replace(day=min(sip_day, 28))
                if next_sip < now:
                    next_sip = (next_sip + timedelta(days=32)).replace(day=min(sip_day, 28))
                
                days_until = (next_sip - now).days
                if days_until == 0:
                    alerts.append({
                        "type": "sip_today",
                        "priority": "low",
                        "icon": "chart-line",
                        "color": "#10B981",
                        "title": f"{sip.get('name', 'SIP')} executes today",
                        "message": f"₹{sip.get('amount', 0):,.0f}",
                        "action": None
                    })
            
            # 5. Low balance prediction (if spending continues at current rate)
            # This would require more sophisticated calculation
            
            # Sort by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            alerts.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))
            
            return alerts[:limit]
            
        except Exception as e:
            logger.error(f"Error getting smart alerts: {e}")
            return []
    
    async def get_investment_glance(self, user_id: str, db) -> Dict:
        """
        Get simplified investment summary for Essential mode
        Just total value and gain/loss
        """
        try:
            holdings = await db.holdings.find({"user_id": user_id}).to_list(None)
            
            if not holdings:
                return {
                    "has_investments": False,
                    "total_value": 0,
                    "total_invested": 0,
                    "gain_loss": 0,
                    "gain_loss_pct": 0
                }
            
            total_value = sum(h.get("current_value", 0) or h.get("quantity", 0) * h.get("buy_price", 0) for h in holdings)
            total_invested = sum(h.get("quantity", 0) * h.get("buy_price", 0) for h in holdings)
            gain_loss = total_value - total_invested
            gain_loss_pct = (gain_loss / total_invested * 100) if total_invested > 0 else 0
            
            return {
                "has_investments": True,
                "total_value": total_value,
                "total_invested": total_invested,
                "gain_loss": gain_loss,
                "gain_loss_pct": round(gain_loss_pct, 2),
                "is_positive": gain_loss >= 0
            }
            
        except Exception as e:
            logger.error(f"Error getting investment glance: {e}")
            return {
                "has_investments": False,
                "total_value": 0,
                "error": str(e)
            }
    
    async def _get_user_stats(self, user_id: str, db) -> Dict:
        """Get basic user stats for brief generation"""
        snapshot = await self.get_essential_snapshot(user_id, db)
        investments = await self.get_investment_glance(user_id, db)
        
        return {
            "spent": snapshot.get("spent", {}).get("amount", 0),
            "safe_to_spend": snapshot.get("safe_to_spend", {}).get("amount", 0),
            "saved": snapshot.get("saved", {}).get("amount", 0),
            "investments_value": investments.get("total_value", 0),
            "investments_gain": investments.get("gain_loss", 0)
        }
    
    async def _get_smart_alerts(self, user_id: str, db) -> List[Dict]:
        """Get smart alerts for brief"""
        return await self.get_smart_alerts(user_id, db, limit=3)
    
    def _build_brief_message(self, stats: Dict, alerts: List[Dict]) -> Dict:
        """Build the morning brief message"""
        now = datetime.now(timezone.utc)
        hour = now.hour
        
        # Greeting based on time
        if hour < 12:
            greeting_time = "Good morning"
        elif hour < 17:
            greeting_time = "Good afternoon"
        else:
            greeting_time = "Good evening"
        
        # Build greeting with key stat
        spent = stats.get("spent", 0)
        safe = stats.get("safe_to_spend", 0)
        
        if safe > 20000:
            mood = "You're in good shape!"
            emoji = "💚"
        elif safe > 5000:
            mood = "Looking okay so far."
            emoji = "👍"
        else:
            mood = "Might want to watch spending."
            emoji = "⚠️"
        
        greeting = f"{greeting_time}! {mood} {emoji}"
        
        # Snapshot
        snapshot = {
            "spent": stats.get("spent", 0),
            "safe_to_spend": stats.get("safe_to_spend", 0),
            "saved": stats.get("saved", 0)
        }
        
        # Format alerts for display
        alert_messages = []
        for alert in alerts[:2]:  # Max 2 alerts in brief
            if alert.get("priority") == "high":
                alert_messages.append(f"⚡ {alert.get('title')}")
            else:
                alert_messages.append(f"📌 {alert.get('title')}")
        
        # Daily tip
        tips = [
            "Tip: Small daily savings add up! ₹100/day = ₹36,500/year 💰",
            "Tip: Review subscriptions you might not be using 📱",
            "Tip: Automating SIPs helps build wealth without thinking 📈",
            "Tip: Credit card dues? Pay in full to avoid 40%+ interest 💳",
            "Tip: Emergency fund = 6 months of expenses 🛡️",
        ]
        tip = tips[now.day % len(tips)]
        
        return {
            "greeting": greeting,
            "snapshot": snapshot,
            "alerts": alert_messages,
            "tip": tip
        }


# Singleton instance
essential_mode_ai = EssentialModeAI()
