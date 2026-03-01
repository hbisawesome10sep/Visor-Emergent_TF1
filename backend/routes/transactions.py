from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timezone
from database import db
from auth import get_current_user
from models import TransactionCreate, TransactionResponse
from routes.tax import process_auto_tax_deduction, remove_auto_tax_deduction, update_auto_tax_deduction
from routes.journal import create_journal_from_transaction, delete_journal_for_reference
from routes.credit_cards import detect_special_transaction

router = APIRouter(prefix="/api")


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    type: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user)
):
    query = {"user_id": user["id"]}
    if type:
        query["type"] = type
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"description": {"$regex": search, "$options": "i"}},
            {"category": {"$regex": search, "$options": "i"}},
            {"notes": {"$regex": search, "$options": "i"}},
            {"payment_account_name": {"$regex": search, "$options": "i"}},
        ]
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["date"] = date_filter

    txns = await db.transactions.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    return txns


@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(txn: TransactionCreate, user=Depends(get_current_user)):
    txn_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    payment_mode = txn.payment_mode or "cash"
    payment_account_name = txn.payment_account_name or "Cash"

    # Detect EMI/SIP/Subscription patterns for flagging
    detected_type, is_flagged = detect_special_transaction(txn.description or "", txn.amount)
    
    txn_doc = {
        "id": txn_id,
        "user_id": user["id"],
        "type": txn.type,
        "amount": txn.amount,
        "category": txn.category,
        "description": txn.description,
        "date": txn.date,
        "is_recurring": txn.is_recurring,
        "recurring_frequency": txn.recurring_frequency,
        "is_split": txn.is_split,
        "split_count": txn.split_count,
        "notes": txn.notes,
        "buy_sell": txn.buy_sell,
        "units": txn.units,
        "price_per_unit": txn.price_per_unit,
        "payment_mode": payment_mode,
        "payment_account_name": payment_account_name,
        "is_flagged": is_flagged,
        "flagged_type": detected_type,
        "is_approved": False,
        "created_at": now,
    }
    await db.transactions.insert_one(txn_doc)

    await process_auto_tax_deduction(
        user_id=user["id"], txn_id=txn_id,
        category=txn.category, description=txn.description,
        notes=txn.notes or "", txn_type=txn.type,
        amount=txn.amount, date_str=txn.date,
    )

    # Auto-create journal entry (double-entry)
    await create_journal_from_transaction(
        user_id=user["id"],
        txn_id=txn_id,
        txn_type=txn.type,
        category=txn.category,
        description=txn.description,
        amount=txn.amount,
        date=txn.date,
        payment_mode=payment_mode,
        payment_account_name=payment_account_name,
    )

    return TransactionResponse(**txn_doc)


@router.delete("/transactions/{txn_id}")
async def delete_transaction(txn_id: str, user=Depends(get_current_user)):
    result = await db.transactions.delete_one({"id": txn_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await remove_auto_tax_deduction(user["id"], txn_id)
    await delete_journal_for_reference(user["id"], txn_id)
    return {"message": "Transaction deleted"}


@router.put("/transactions/{txn_id}", response_model=TransactionResponse)
async def update_transaction(txn_id: str, txn: TransactionCreate, user=Depends(get_current_user)):
    existing = await db.transactions.find_one({"id": txn_id, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Transaction not found")

    payment_mode = txn.payment_mode or "cash"
    payment_account_name = txn.payment_account_name or "Cash"

    update_data = {
        "type": txn.type,
        "amount": txn.amount,
        "category": txn.category,
        "description": txn.description,
        "date": txn.date,
        "is_recurring": txn.is_recurring,
        "recurring_frequency": txn.recurring_frequency,
        "is_split": txn.is_split,
        "split_count": txn.split_count,
        "notes": txn.notes,
        "buy_sell": txn.buy_sell,
        "units": txn.units,
        "price_per_unit": txn.price_per_unit,
        "payment_mode": payment_mode,
        "payment_account_name": payment_account_name,
    }
    await db.transactions.update_one({"id": txn_id, "user_id": user["id"]}, {"$set": update_data})
    await update_auto_tax_deduction(
        user_id=user["id"], txn_id=txn_id,
        category=txn.category, description=txn.description,
        notes=txn.notes or "", txn_type=txn.type,
        amount=txn.amount, date_str=txn.date,
    )

    # Re-create journal entry for updated transaction
    await delete_journal_for_reference(user["id"], txn_id)
    await create_journal_from_transaction(
        user_id=user["id"],
        txn_id=txn_id,
        txn_type=txn.type,
        category=txn.category,
        description=txn.description,
        amount=txn.amount,
        date=txn.date,
        payment_mode=payment_mode,
        payment_account_name=payment_account_name,
    )

    updated = await db.transactions.find_one({"id": txn_id}, {"_id": 0})
    return TransactionResponse(**updated)
