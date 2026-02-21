from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import db
from auth import get_current_user
from models import GoalCreate, GoalUpdate, GoalResponse
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/api")


@router.get("/goals", response_model=List[GoalResponse])
async def get_goals(user=Depends(get_current_user)):
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    return goals


@router.post("/goals", response_model=GoalResponse)
async def create_goal(goal: GoalCreate, user=Depends(get_current_user)):
    goal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    goal_doc = {
        "id": goal_id,
        "user_id": user["id"],
        "title": goal.title,
        "target_amount": goal.target_amount,
        "current_amount": goal.current_amount,
        "deadline": goal.deadline,
        "category": goal.category,
        "created_at": now,
    }
    await db.goals.insert_one(goal_doc)
    return GoalResponse(**goal_doc)


@router.put("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(goal_id: str, goal_update: GoalUpdate, user=Depends(get_current_user)):
    existing = await db.goals.find_one({"id": goal_id, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Goal not found")

    update_data = {k: v for k, v in goal_update.dict().items() if v is not None}
    if update_data:
        await db.goals.update_one({"id": goal_id}, {"$set": update_data})

    updated = await db.goals.find_one({"id": goal_id}, {"_id": 0})
    return GoalResponse(**updated)


@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user=Depends(get_current_user)):
    result = await db.goals.delete_one({"id": goal_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Goal deleted"}
