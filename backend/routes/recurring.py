from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_current_user
from models import RecurringCreate, RecurringUpdate
from bson import ObjectId
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def calculate_next_execution(frequency: str, current_date: str, day_of_month: int = 1) -> str:
    """Calculate the next execution date based on frequency."""
    try:
        dt = datetime.strptime(current_date, "%Y-%m-%d")
    except Exception:
        dt = datetime.now()

    if frequency == "daily":
        next_dt = dt + relativedelta(days=1)
    elif frequency == "weekly":
        next_dt = dt + relativedelta(weeks=1)
    elif frequency == "monthly":
        next_dt = dt + relativedelta(months=1)
        try:
            next_dt = next_dt.replace(day=min(day_of_month, 28))
        except Exception:
            pass
    elif frequency == "quarterly":
        next_dt = dt + relativedelta(months=3)
    elif frequency == "yearly":
        next_dt = dt + relativedelta(years=1)
    else:
        next_dt = dt + relativedelta(months=1)

    return next_dt.strftime("%Y-%m-%d")


def get_upcoming_executions(recurring: dict, count: int = 3) -> list:
    """Get the next N execution dates."""
    executions = []
    current_date = recurring.get("next_execution") or datetime.now().strftime("%Y-%m-%d")

    for _ in range(count):
        executions.append(current_date)
        current_date = calculate_next_execution(
            recurring.get("frequency", "monthly"),
            current_date,
            recurring.get("day_of_month", 1)
        )
    return executions


@router.get("/recurring")
async def get_recurring_transactions(user=Depends(get_current_user)):
    """Get all recurring transactions (SIPs) for the user."""
    recurring_list = []
    cursor = db.recurring_transactions.find({"user_id": user["id"]})
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        doc["upcoming"] = get_upcoming_executions(doc, 3)
        recurring_list.append(doc)

    active = [r for r in recurring_list if r.get("is_active", True)]
    monthly_commitment = sum(
        r["amount"] * (12 if r["frequency"] == "yearly" else
                       4 if r["frequency"] == "quarterly" else
                       1 if r["frequency"] == "monthly" else
                       4.33 if r["frequency"] == "weekly" else 30)
        for r in active
    ) / 12

    return {
        "recurring": recurring_list,
        "summary": {
            "total_count": len(recurring_list),
            "active_count": len(active),
            "monthly_commitment": round(monthly_commitment, 2),
            "categories": list(set(r["category"] for r in recurring_list)),
        }
    }


@router.post("/recurring")
async def create_recurring_transaction(data: RecurringCreate, user=Depends(get_current_user)):
    """Create a new recurring transaction (SIP)."""
    now = datetime.now(timezone.utc).isoformat()

    start = datetime.strptime(data.start_date, "%Y-%m-%d")
    today = datetime.now()

    if start < today:
        next_exec = data.start_date
        while datetime.strptime(next_exec, "%Y-%m-%d") < today:
            next_exec = calculate_next_execution(data.frequency, next_exec, data.day_of_month)
    else:
        next_exec = data.start_date

    doc = {
        "user_id": user["id"],
        "name": data.name,
        "amount": data.amount,
        "frequency": data.frequency,
        "category": data.category,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "day_of_month": data.day_of_month,
        "notes": data.notes,
        "is_active": data.is_active,
        "next_execution": next_exec,
        "total_invested": 0,
        "execution_count": 0,
        "created_at": now,
    }
    result = await db.recurring_transactions.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["upcoming"] = get_upcoming_executions(doc, 3)
    return doc


@router.put("/recurring/{recurring_id}")
async def update_recurring_transaction(recurring_id: str, data: RecurringUpdate, user=Depends(get_current_user)):
    """Update a recurring transaction."""
    existing = await db.recurring_transactions.find_one(
        {"_id": ObjectId(recurring_id), "user_id": user["id"]}
    )
    if not existing:
        raise HTTPException(404, "Recurring transaction not found")

    update_data = {k: v for k, v in data.dict().items() if v is not None}

    if "frequency" in update_data or "day_of_month" in update_data:
        freq = update_data.get("frequency", existing["frequency"])
        day = update_data.get("day_of_month", existing.get("day_of_month", 1))
        today_str = datetime.now().strftime("%Y-%m-%d")
        update_data["next_execution"] = calculate_next_execution(freq, today_str, day)

    if update_data:
        await db.recurring_transactions.update_one(
            {"_id": ObjectId(recurring_id)}, {"$set": update_data}
        )

    updated = await db.recurring_transactions.find_one({"_id": ObjectId(recurring_id)})
    updated["id"] = str(updated.pop("_id"))
    updated["upcoming"] = get_upcoming_executions(updated, 3)
    return updated


@router.delete("/recurring/{recurring_id}")
async def delete_recurring_transaction(recurring_id: str, user=Depends(get_current_user)):
    """Delete a recurring transaction."""
    result = await db.recurring_transactions.delete_one(
        {"_id": ObjectId(recurring_id), "user_id": user["id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Recurring transaction not found")
    return {"message": "Deleted"}


@router.post("/recurring/{recurring_id}/execute")
async def execute_recurring_transaction(recurring_id: str, user=Depends(get_current_user)):
    """Manually execute a recurring transaction (create actual transaction)."""
    recurring = await db.recurring_transactions.find_one(
        {"_id": ObjectId(recurring_id), "user_id": user["id"]}
    )
    if not recurring:
        raise HTTPException(404, "Recurring transaction not found")

    txn_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    txn_doc = {
        "id": txn_id,
        "user_id": user["id"],
        "type": "investment",
        "amount": recurring["amount"],
        "category": recurring["category"],
        "description": f"{recurring['name']} - Auto SIP",
        "date": now.strftime("%Y-%m-%d"),
        "is_recurring": True,
        "recurring_frequency": recurring["frequency"],
        "recurring_id": recurring_id,
        "notes": recurring.get("notes"),
        "created_at": now.isoformat(),
    }
    await db.transactions.insert_one(txn_doc)

    next_exec = calculate_next_execution(
        recurring["frequency"],
        recurring["next_execution"],
        recurring.get("day_of_month", 1)
    )
    await db.recurring_transactions.update_one(
        {"_id": ObjectId(recurring_id)},
        {
            "$set": {
                "next_execution": next_exec,
                "last_execution": now.strftime("%Y-%m-%d"),
            },
            "$inc": {
                "total_invested": recurring["amount"],
                "execution_count": 1,
            }
        }
    )

    return {
        "message": "Transaction executed",
        "transaction_id": txn_id,
        "next_execution": next_exec,
    }


@router.post("/recurring/{recurring_id}/pause")
async def pause_recurring_transaction(recurring_id: str, user=Depends(get_current_user)):
    """Pause/Resume a recurring transaction."""
    recurring = await db.recurring_transactions.find_one(
        {"_id": ObjectId(recurring_id), "user_id": user["id"]}
    )
    if not recurring:
        raise HTTPException(404, "Recurring transaction not found")

    new_status = not recurring.get("is_active", True)
    await db.recurring_transactions.update_one(
        {"_id": ObjectId(recurring_id)},
        {"$set": {"is_active": new_status}}
    )

    return {"message": f"{'Resumed' if new_status else 'Paused'}", "is_active": new_status}
