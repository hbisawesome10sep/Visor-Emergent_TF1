from fastapi import APIRouter, Depends
from database import db
from auth import get_current_user
from models import RiskProfileCreate
from datetime import datetime, timezone

router = APIRouter(prefix="/api")


@router.post("/risk-profile")
async def save_risk_profile(data: RiskProfileCreate, user=Depends(get_current_user)):
    doc = {
        "user_id": user["id"],
        "answers": data.answers,
        "score": data.score,
        "profile": data.profile,
        "breakdown": data.breakdown,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.risk_profiles.delete_many({"user_id": user["id"]})
    await db.risk_profiles.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/risk-profile")
async def get_risk_profile(user=Depends(get_current_user)):
    doc = await db.risk_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not doc:
        return None
    return doc
