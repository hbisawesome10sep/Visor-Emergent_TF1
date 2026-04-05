# /app/backend/routes/experience_mode.py
"""
Experience Mode API Routes
Manages user experience modes: Essential, Plus, Full
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
import logging

from database import db
from auth import get_current_user
from services.experience_mode import (
    ExperienceMode, 
    FEATURE_REGISTRY, 
    MODE_INFO,
    is_feature_available, 
    get_user_features,
    get_hidden_features,
    get_upgrade_features,
    get_mode_summary
)
from services.mode_recommender import mode_recommender
from services.essential_mode_ai import essential_mode_ai

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/experience", tags=["Experience Mode"])


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ModeUpdateRequest(BaseModel):
    mode: str  # "essential", "plus", "full"
    source: str = "manual"  # manual, ai_nudge, onboarding


class NudgeResponseRequest(BaseModel):
    accepted: bool


class BehaviorEventRequest(BaseModel):
    event_type: str  # screen_visit, feature_attempt, ai_query, etc.
    data: dict = {}


# ═══════════════════════════════════════════════════════════════════════════════
# MODE MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/mode")
async def get_user_mode(user=Depends(get_current_user)):
    """Get user's current experience mode and available features"""
    user_id = user["id"]
    settings = await db.user_experience.find_one({"user_id": user_id})
    
    if not settings:
        # Default to Essential for new users
        settings = {
            "user_id": user_id,
            "current_mode": ExperienceMode.ESSENTIAL.value,
            "ai_suggestions_enabled": True,
            "onboarding_completed": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        await db.user_experience.insert_one(settings)
    
    mode = ExperienceMode(settings.get("current_mode", "essential"))
    available = get_user_features(mode)
    hidden = get_hidden_features(mode)
    
    # Determine upgrade path
    upgrade_map = {
        ExperienceMode.ESSENTIAL: ExperienceMode.PLUS,
        ExperienceMode.PLUS: ExperienceMode.FULL,
        ExperienceMode.FULL: None
    }
    
    can_upgrade_to = upgrade_map.get(mode)
    upgrade_features = []
    if can_upgrade_to:
        upgrade_features = get_upgrade_features(mode, can_upgrade_to)
    
    return {
        "current_mode": mode.value,
        "mode_info": MODE_INFO.get(mode, {}),
        "available_features": list(available),
        "hidden_features": list(hidden),
        "can_upgrade_to": can_upgrade_to.value if can_upgrade_to else None,
        "upgrade_features": upgrade_features[:10],
        "ai_suggestions_enabled": settings.get("ai_suggestions_enabled", True),
        "onboarding_completed": settings.get("onboarding_completed", False)
    }


@router.put("/mode")
async def update_user_mode(request: ModeUpdateRequest, user=Depends(get_current_user)):
    """Update user's experience mode"""
    user_id = user["id"]
    
    # Validate mode
    try:
        mode = ExperienceMode(request.mode)
    except ValueError:
        raise HTTPException(400, f"Invalid mode: {request.mode}. Must be one of: essential, plus, full")
    
    now = datetime.now(timezone.utc)
    
    # Get current settings
    settings = await db.user_experience.find_one({"user_id": user_id})
    old_mode = settings.get("current_mode") if settings else None
    
    # Update mode
    await db.user_experience.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "current_mode": mode.value,
                "updated_at": now
            },
            "$push": {
                "mode_history": {
                    "from_mode": old_mode,
                    "to_mode": mode.value,
                    "set_at": now,
                    "source": request.source
                }
            }
        },
        upsert=True
    )
    
    logger.info(f"User {user_id} changed mode from {old_mode} to {mode.value} (source: {request.source})")
    
    return {
        "status": "success",
        "mode": mode.value,
        "mode_info": MODE_INFO.get(mode, {}),
        "message": f"Switched to {MODE_INFO.get(mode, {}).get('title', mode.value)} mode"
    }


@router.get("/modes")
async def get_all_modes():
    """Get information about all available modes"""
    modes = []
    for mode in [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL]:
        info = MODE_INFO.get(mode, {})
        summary = get_mode_summary(mode)
        modes.append({
            "mode": mode.value,
            "title": info.get("title", mode.value),
            "subtitle": info.get("subtitle", ""),
            "description": info.get("description", ""),
            "icon": info.get("icon", ""),
            "color": info.get("color", "#888"),
            "highlights": info.get("highlights", []),
            "feature_count": summary.get("total_features", 0)
        })
    return {"modes": modes}


@router.put("/settings")
async def update_mode_settings(ai_suggestions_enabled: bool = True, user=Depends(get_current_user)):
    """Update mode-related settings"""
    user_id = user["id"]
    
    await db.user_experience.update_one(
        {"user_id": user_id},
        {"$set": {
            "ai_suggestions_enabled": ai_suggestions_enabled,
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    return {"status": "success", "ai_suggestions_enabled": ai_suggestions_enabled}


@router.post("/onboarding-complete")
async def complete_onboarding(user=Depends(get_current_user)):
    """Mark onboarding as complete"""
    user_id = user["id"]
    
    await db.user_experience.update_one(
        {"user_id": user_id},
        {"$set": {
            "onboarding_completed": True,
            "onboarding_completed_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    return {"status": "success"}


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ACCESS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/features/{feature_id}")
async def check_feature_access(feature_id: str, user=Depends(get_current_user)):
    """Check if user has access to a specific feature"""
    user_id = user["id"]
    settings = await db.user_experience.find_one({"user_id": user_id})
    mode = ExperienceMode(settings.get("current_mode", "essential") if settings else "essential")
    
    available = is_feature_available(feature_id, mode)
    feature_info = FEATURE_REGISTRY.get(feature_id, {})
    
    # Track attempted access to hidden features (for AI recommendations)
    if not available:
        await db.user_behavior.update_one(
            {"user_id": user_id, "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")},
            {
                "$addToSet": {"events.features_attempted_hidden": feature_id},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            },
            upsert=True
        )
    
    # Find minimum mode required
    required_mode = None
    for m in [ExperienceMode.ESSENTIAL, ExperienceMode.PLUS, ExperienceMode.FULL]:
        if m in feature_info.get("modes", []):
            required_mode = m.value
            break
    
    return {
        "feature_id": feature_id,
        "available": available,
        "current_mode": mode.value,
        "required_mode": required_mode,
        "description": feature_info.get("description", ""),
        "category": feature_info.get("category", ""),
        "alternative": feature_info.get("essential_alternative") if not available else None
    }


@router.get("/features")
async def get_all_features(user=Depends(get_current_user)):
    """Get all features with availability status for current user"""
    user_id = user["id"]
    settings = await db.user_experience.find_one({"user_id": user_id})
    mode = ExperienceMode(settings.get("current_mode", "essential") if settings else "essential")
    
    features = []
    for feature_id, config in FEATURE_REGISTRY.items():
        features.append({
            "feature_id": feature_id,
            "available": mode in config.get("modes", []),
            "description": config.get("description", ""),
            "category": config.get("category", ""),
            "modes": [m.value for m in config.get("modes", [])]
        })
    
    return {"features": features, "current_mode": mode.value}


# ═══════════════════════════════════════════════════════════════════════════════
# AI NUDGE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/nudge")
async def get_pending_nudge(user=Depends(get_current_user)):
    """Get any pending mode upgrade nudge for the user"""
    user_id = user["id"]
    
    nudge = await db.mode_nudges.find_one({
        "user_id": user_id,
        "status": "pending"
    })
    
    if nudge:
        # Mark as shown
        await db.mode_nudges.update_one(
            {"_id": nudge["_id"]},
            {"$set": {"status": "shown", "shown_at": datetime.now(timezone.utc)}}
        )
        
        # Get mode info for the suggested mode
        suggested_mode = ExperienceMode(nudge["suggested_mode"])
        mode_info = MODE_INFO.get(suggested_mode, {})
        
        return {
            "has_nudge": True,
            "nudge_id": str(nudge["_id"]),
            "suggested_mode": nudge["suggested_mode"],
            "mode_info": mode_info,
            "message": nudge.get("message", ""),
            "cta": nudge.get("cta", "Upgrade"),
            "trigger_reason": nudge.get("trigger_reason", "")
        }
    
    return {"has_nudge": False}


@router.post("/nudge/{nudge_id}/respond")
async def respond_to_nudge(nudge_id: str, request: NudgeResponseRequest, user=Depends(get_current_user)):
    """User responds to a mode nudge"""
    user_id = user["id"]
    
    try:
        nudge = await db.mode_nudges.find_one({"_id": ObjectId(nudge_id), "user_id": user_id})
    except Exception:
        raise HTTPException(404, "Nudge not found")
    
    if not nudge:
        raise HTTPException(404, "Nudge not found")
    
    status = "accepted" if request.accepted else "dismissed"
    await db.mode_nudges.update_one(
        {"_id": ObjectId(nudge_id)},
        {"$set": {"status": status, "responded_at": datetime.now(timezone.utc)}}
    )
    
    if request.accepted:
        # Upgrade the user's mode
        await update_user_mode(
            ModeUpdateRequest(mode=nudge["suggested_mode"], source="ai_nudge"),
            user
        )
        
        return {
            "status": "upgraded",
            "new_mode": nudge["suggested_mode"],
            "message": f"Welcome to {MODE_INFO.get(ExperienceMode(nudge['suggested_mode']), {}).get('title', '')} mode!"
        }
    
    return {"status": "dismissed"}


@router.post("/nudge/check")
async def check_for_nudge(user=Depends(get_current_user)):
    """Manually trigger a check for mode upgrade nudge"""
    user_id = user["id"]
    
    nudge = await mode_recommender.analyze_and_recommend(user_id, db)
    
    if nudge:
        return {"nudge_created": True, "reason": nudge.get("trigger_reason")}
    
    return {"nudge_created": False}


# ═══════════════════════════════════════════════════════════════════════════════
# BEHAVIOR TRACKING ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/behavior")
async def track_behavior(request: BehaviorEventRequest, user=Depends(get_current_user)):
    """Track user behavior for AI-powered mode recommendations"""
    user_id = user["id"]
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    event_type = request.event_type
    data = request.data
    
    update_ops = {"$set": {"updated_at": datetime.now(timezone.utc)}}
    
    if event_type == "screen_visit":
        screen = data.get("screen", "")
        duration = data.get("duration", 0)
        update_ops["$addToSet"] = {"events.screens_visited": screen}
        update_ops["$inc"] = {f"events.time_spent.{screen}": duration}
    
    elif event_type == "feature_use":
        feature = data.get("feature", "")
        update_ops["$addToSet"] = {"events.features_used": feature}
    
    elif event_type == "ai_query":
        query = data.get("query", "")
        category = data.get("category", "general")
        update_ops["$push"] = {"events.ai_queries": {"query": query[:100], "category": category}}
    
    elif event_type == "export_attempt":
        export_type = data.get("type", "")
        update_ops["$push"] = {"events.export_attempts": export_type}
    
    await db.user_behavior.update_one(
        {"user_id": user_id, "date": today},
        update_ops,
        upsert=True
    )
    
    return {"status": "tracked"}


# ═══════════════════════════════════════════════════════════════════════════════
# ESSENTIAL MODE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/essential/snapshot")
async def get_essential_snapshot(user=Depends(get_current_user)):
    """Get the 3-card financial snapshot for Essential mode"""
    user_id = user["id"]
    return await essential_mode_ai.get_essential_snapshot(user_id, db)


@router.get("/essential/brief")
async def get_essential_brief(user=Depends(get_current_user)):
    """Get AI-powered morning brief for Essential mode"""
    user_id = user["id"]
    return await essential_mode_ai.generate_morning_brief(user_id, db)


@router.get("/essential/alerts")
async def get_essential_alerts(limit: int = 5, user=Depends(get_current_user)):
    """Get smart alerts for Essential mode"""
    user_id = user["id"]
    alerts = await essential_mode_ai.get_smart_alerts(user_id, db, limit)
    return {"alerts": alerts}


@router.get("/essential/investments")
async def get_essential_investments(user=Depends(get_current_user)):
    """Get simplified investment summary for Essential mode"""
    user_id = user["id"]
    return await essential_mode_ai.get_investment_glance(user_id, db)
