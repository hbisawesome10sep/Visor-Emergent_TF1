"""
Visor AI Agent — Text Chat Endpoint
Route handler only — business logic lives in /services/visor_engine.py
"""
from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_current_user
from models import AIMessageCreate
from services.visor_engine import process_visor_message

router = APIRouter(prefix="/api")


@router.post("/visor-ai/chat")
async def visor_ai_chat(msg: AIMessageCreate, user=Depends(get_current_user)):
    """Text chat endpoint — delegates to shared engine."""
    result = await process_visor_message(
        user_id=user["id"],
        message=msg.message,
        screen_context=msg.screen_context,
        input_type="text",
    )
    return result


@router.get("/visor-ai/history")
async def get_visor_history(user=Depends(get_current_user)):
    messages = await db.visor_chat.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return messages


@router.delete("/visor-ai/history")
async def clear_visor_history(user=Depends(get_current_user)):
    await db.visor_chat.delete_many({"user_id": user["id"]})
    return {"message": "Chat history cleared"}


@router.delete("/visor-ai/message/{message_id}")
async def delete_visor_message(message_id: str, user=Depends(get_current_user)):
    result = await db.visor_chat.delete_one({"id": message_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Message deleted"}
