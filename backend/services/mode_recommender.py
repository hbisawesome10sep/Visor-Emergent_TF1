# /app/backend/services/mode_recommender.py
"""
AI-powered Mode Recommender
Analyzes user behavior and recommends mode upgrades
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from bson import ObjectId
import logging

from .experience_mode import ExperienceMode

logger = logging.getLogger(__name__)


class ModeRecommender:
    """Analyzes user behavior and recommends mode upgrades"""
    
    # Behavior signals that suggest upgrade
    UPGRADE_SIGNALS = {
        "essential_to_plus": {
            "min_days_on_mode": 3,
            "triggers": [
                {"type": "hidden_feature_attempts", "threshold": 3, "weight": 2.0},
                {"type": "ai_queries_category", "category": "investments", "threshold": 5, "weight": 1.5},
                {"type": "ai_queries_category", "category": "tax", "threshold": 3, "weight": 1.5},
                {"type": "ai_queries_category", "category": "transactions", "threshold": 8, "weight": 1.0},
                {"type": "screen_time", "screen": "investments", "threshold": 300, "weight": 1.2},
                {"type": "engagement_score_avg", "threshold": 60, "weight": 1.0},
                {"type": "app_sessions", "threshold": 10, "weight": 0.8},
            ],
            "min_triggers": 2  # At least 2 triggers must fire
        },
        "plus_to_full": {
            "min_days_on_mode": 7,
            "triggers": [
                {"type": "hidden_feature_attempts", "threshold": 5, "weight": 2.0},
                {"type": "ai_queries_category", "category": "bookkeeping", "threshold": 3, "weight": 1.8},
                {"type": "ai_queries_category", "category": "tax_advanced", "threshold": 4, "weight": 1.5},
                {"type": "screen_time", "screen": "tax", "threshold": 600, "weight": 1.2},
                {"type": "export_attempts", "threshold": 2, "weight": 2.0},
                {"type": "engagement_score_avg", "threshold": 75, "weight": 1.0},
            ],
            "min_triggers": 2
        }
    }
    
    NUDGE_MESSAGES = {
        # Essential -> Plus triggers
        "hidden_feature_attempts": {
            "message": "I noticed you tried to access some features that aren't in Essential mode. Want to upgrade to Plus for full control?",
            "cta": "Unlock Plus"
        },
        "investment_exploration": {
            "message": "You've been exploring your investments quite a bit! Upgrade to Plus to see detailed holdings, SIP tracking, and goal mapping.",
            "cta": "See Full Portfolio"
        },
        "tax_curious": {
            "message": "Interested in tax planning? Plus mode gives you deduction tracking and 80C optimization.",
            "cta": "Unlock Tax Features"
        },
        "transaction_power_user": {
            "message": "You're asking a lot about your transactions! With Plus, you can search, filter, and categorize everything yourself.",
            "cta": "Get Full Control"
        },
        "high_engagement": {
            "message": "You're really getting the hang of Visor! Ready to unlock more features with Plus mode?",
            "cta": "Upgrade to Plus"
        },
        
        # Plus -> Full triggers
        "bookkeeping_interest": {
            "message": "Looking for bookkeeping features? Full mode unlocks double-entry journal, P&L, and balance sheets.",
            "cta": "Unlock Bookkeeping"
        },
        "advanced_tax": {
            "message": "Ready for advanced tax planning? Full mode has capital gains tracking, Form 16 parsing, and tax-loss harvesting.",
            "cta": "Get Full Tax Module"
        },
        "export_needed": {
            "message": "Need to export your data? Full mode lets you download PDF and Excel reports for everything.",
            "cta": "Unlock Exports"
        },
        "power_user": {
            "message": "You're using Visor like a pro! Unlock the complete experience with Full mode.",
            "cta": "Go Full"
        },
        
        # Defaults
        "default_plus": {
            "message": "Based on how you've been using Visor, I think you'd love Plus mode. Want to try it?",
            "cta": "Try Plus"
        },
        "default_full": {
            "message": "You're ready for the full Visor experience! Want to unlock everything?",
            "cta": "Unlock Full"
        },
    }
    
    async def analyze_and_recommend(self, user_id: str, db) -> Optional[Dict]:
        """Analyze user behavior and generate nudge if appropriate"""
        
        try:
            # Get current mode and settings
            settings = await db.user_experience.find_one({"user_id": user_id})
            if not settings:
                return None
            
            current_mode = ExperienceMode(settings.get("current_mode", "essential"))
            
            # Already at max mode
            if current_mode == ExperienceMode.FULL:
                return None
            
            # Check if AI suggestions are enabled
            if not settings.get("ai_suggestions_enabled", True):
                return None
            
            # Check cooldown
            last_nudge = settings.get("last_nudge_at")
            cooldown_days = settings.get("nudge_cooldown_days", 7)
            if last_nudge:
                days_since = (datetime.now(timezone.utc) - last_nudge).days
                if days_since < cooldown_days:
                    return None
            
            # Check if there's already a pending nudge
            pending = await db.mode_nudges.find_one({
                "user_id": user_id,
                "status": "pending"
            })
            if pending:
                return None
            
            # Determine upgrade path
            if current_mode == ExperienceMode.ESSENTIAL:
                upgrade_key = "essential_to_plus"
                target_mode = ExperienceMode.PLUS
            else:
                upgrade_key = "plus_to_full"
                target_mode = ExperienceMode.FULL
            
            config = self.UPGRADE_SIGNALS.get(upgrade_key)
            if not config:
                return None
            
            # Check mode tenure
            mode_set_at = settings.get("updated_at") or settings.get("created_at")
            if mode_set_at:
                days_on_mode = (datetime.now(timezone.utc) - mode_set_at).days
                if days_on_mode < config["min_days_on_mode"]:
                    return None
            
            # Get recent behavior data
            days_to_analyze = max(config["min_days_on_mode"], 7)
            start_date = (datetime.now(timezone.utc) - timedelta(days=days_to_analyze)).strftime("%Y-%m-%d")
            
            behavior_docs = await db.user_behavior.find({
                "user_id": user_id,
                "date": {"$gte": start_date}
            }).to_list(None)
            
            if len(behavior_docs) < config["min_days_on_mode"]:
                return None  # Not enough data
            
            # Analyze triggers
            triggered = []
            for trigger in config["triggers"]:
                result = self._check_trigger(trigger, behavior_docs)
                if result["triggered"]:
                    triggered.append({
                        "type": trigger["type"],
                        "weight": trigger.get("weight", 1.0),
                        "details": result.get("details", {})
                    })
            
            # Check if minimum triggers met
            if len(triggered) < config.get("min_triggers", 1):
                return None
            
            # Sort by weight and pick primary reason
            triggered.sort(key=lambda x: x["weight"], reverse=True)
            primary_reason = self._map_trigger_to_reason(triggered[0]["type"], target_mode)
            
            # Get nudge message
            nudge_config = self.NUDGE_MESSAGES.get(primary_reason) or self.NUDGE_MESSAGES.get(
                f"default_{'plus' if target_mode == ExperienceMode.PLUS else 'full'}"
            )
            
            # Create nudge
            nudge = {
                "user_id": user_id,
                "suggested_mode": target_mode.value,
                "trigger_reason": primary_reason,
                "trigger_details": [t["type"] for t in triggered],
                "message": nudge_config["message"],
                "cta": nudge_config["cta"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            }
            
            # Save nudge
            await db.mode_nudges.insert_one(nudge)
            
            # Update last nudge time
            await db.user_experience.update_one(
                {"user_id": user_id},
                {"$set": {"last_nudge_at": datetime.now(timezone.utc)}}
            )
            
            logger.info(f"Created mode nudge for user {user_id}: {primary_reason} -> {target_mode.value}")
            
            return nudge
            
        except Exception as e:
            logger.error(f"Error analyzing mode recommendation: {e}")
            return None
    
    def _check_trigger(self, trigger: Dict, behavior_docs: List[Dict]) -> Dict:
        """Check if a specific trigger condition is met"""
        trigger_type = trigger["type"]
        threshold = trigger.get("threshold", 1)
        
        try:
            if trigger_type == "hidden_feature_attempts":
                total = sum(
                    len(doc.get("events", {}).get("features_attempted_hidden", [])) 
                    for doc in behavior_docs
                )
                return {"triggered": total >= threshold, "details": {"count": total}}
            
            elif trigger_type == "ai_queries_category":
                category = trigger.get("category", "")
                total = sum(
                    len([
                        q for q in doc.get("events", {}).get("ai_queries", []) 
                        if q.get("category") == category
                    ])
                    for doc in behavior_docs
                )
                return {"triggered": total >= threshold, "details": {"category": category, "count": total}}
            
            elif trigger_type == "screen_time":
                screen = trigger.get("screen", "")
                total = sum(
                    doc.get("events", {}).get("time_spent", {}).get(screen, 0) 
                    for doc in behavior_docs
                )
                return {"triggered": total >= threshold, "details": {"screen": screen, "seconds": total}}
            
            elif trigger_type == "engagement_score_avg":
                scores = [doc.get("engagement_score", 0) for doc in behavior_docs if doc.get("engagement_score")]
                avg = sum(scores) / len(scores) if scores else 0
                return {"triggered": avg >= threshold, "details": {"avg_score": avg}}
            
            elif trigger_type == "app_sessions":
                total = len(behavior_docs)
                return {"triggered": total >= threshold, "details": {"sessions": total}}
            
            elif trigger_type == "export_attempts":
                total = sum(
                    len(doc.get("events", {}).get("export_attempts", [])) 
                    for doc in behavior_docs
                )
                return {"triggered": total >= threshold, "details": {"count": total}}
            
        except Exception as e:
            logger.error(f"Error checking trigger {trigger_type}: {e}")
        
        return {"triggered": False}
    
    def _map_trigger_to_reason(self, trigger_type: str, target_mode: ExperienceMode) -> str:
        """Map trigger type to a human-readable nudge reason"""
        mapping = {
            "hidden_feature_attempts": "hidden_feature_attempts",
            "ai_queries_category:investments": "investment_exploration",
            "ai_queries_category:tax": "tax_curious",
            "ai_queries_category:transactions": "transaction_power_user",
            "ai_queries_category:bookkeeping": "bookkeeping_interest",
            "ai_queries_category:tax_advanced": "advanced_tax",
            "screen_time:investments": "investment_exploration",
            "screen_time:tax": "advanced_tax" if target_mode == ExperienceMode.FULL else "tax_curious",
            "engagement_score_avg": "high_engagement" if target_mode == ExperienceMode.PLUS else "power_user",
            "export_attempts": "export_needed",
        }
        
        return mapping.get(trigger_type, f"default_{'plus' if target_mode == ExperienceMode.PLUS else 'full'}")


# Singleton instance
mode_recommender = ModeRecommender()
