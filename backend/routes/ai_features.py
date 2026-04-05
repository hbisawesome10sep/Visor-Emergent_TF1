"""
Visor AI — Morning Brief & Categorization Feedback Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from services.morning_brief import compute_morning_brief, get_cached_brief
from services.categorization_feedback import (
    get_user_overrides, delete_user_override, clear_user_overrides,
)

router = APIRouter(prefix="/api")


# ── Morning Brief ─────────────────────────────────────────────────────

@router.get("/ai/morning-brief")
async def get_morning_brief(user=Depends(get_current_user)):
    """Get today's morning financial brief. Computes fresh if not cached."""
    cached = await get_cached_brief(user["id"])
    if cached:
        return cached
    return await compute_morning_brief(user["id"])


@router.post("/ai/morning-brief/refresh")
async def refresh_morning_brief(user=Depends(get_current_user)):
    """Force recompute today's morning brief."""
    return await compute_morning_brief(user["id"])


# ── Categorization Feedback ──────────────────────────────────────────

@router.get("/categorization/overrides")
async def get_overrides(user=Depends(get_current_user)):
    """Get all user's category overrides (learning from past corrections)."""
    overrides = await get_user_overrides(user["id"])
    return {"overrides": overrides, "count": len(overrides)}


class DeleteOverrideRequest(BaseModel):
    pattern: str


@router.delete("/categorization/overrides")
async def delete_override(req: DeleteOverrideRequest, user=Depends(get_current_user)):
    """Delete a specific category override."""
    deleted = await delete_user_override(user["id"], req.pattern)
    if not deleted:
        raise HTTPException(status_code=404, detail="Override not found")
    return {"message": "Override deleted"}


@router.delete("/categorization/overrides/all")
async def clear_overrides(user=Depends(get_current_user)):
    """Clear all category overrides for this user."""
    count = await clear_user_overrides(user["id"])
    return {"message": f"Cleared {count} override(s)"}
