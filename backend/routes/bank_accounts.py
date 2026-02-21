from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timezone
from database import db
from auth import get_current_user
from encryption import encrypt_field, decrypt_field
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

INDIAN_BANKS = [
    "State Bank of India (SBI)", "HDFC Bank", "ICICI Bank", "Axis Bank",
    "Kotak Mahindra Bank", "Punjab National Bank (PNB)", "Bank of Baroda (BOB)",
    "Canara Bank", "Union Bank of India", "IndusInd Bank", "Yes Bank",
    "IDFC First Bank", "Federal Bank", "Bank of India (BOI)", "Indian Bank",
    "Central Bank of India", "UCO Bank", "Indian Overseas Bank",
    "Karnataka Bank", "South Indian Bank", "Bandhan Bank", "IDBI Bank",
    "RBL Bank", "Jammu & Kashmir Bank", "City Union Bank",
    "Karur Vysya Bank", "Tamilnad Mercantile Bank", "DCB Bank",
    "Dhanlaxmi Bank", "Nainital Bank",
]


@router.get("/bank-accounts")
async def get_bank_accounts(user=Depends(get_current_user)):
    accounts = await db.bank_accounts.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    dek = user.get("encryption_key", "")
    for acc in accounts:
        if dek and acc.get("account_number", "").startswith("ENC:"):
            acc["account_number"] = decrypt_field(acc["account_number"], dek)
    return accounts


@router.get("/bank-accounts/banks-list")
async def get_banks_list():
    return {"banks": INDIAN_BANKS}


@router.post("/bank-accounts")
async def create_bank_account(data: dict, user=Depends(get_current_user)):
    bank_name = data.get("bank_name", "").strip()
    account_name = data.get("account_name", "").strip()
    if not bank_name or not account_name:
        raise HTTPException(400, "bank_name and account_name are required")

    account_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    dek = user.get("encryption_key", "")

    account_number_raw = data.get("account_number", "")
    account_number_enc = encrypt_field(account_number_raw, dek) if dek and account_number_raw else account_number_raw

    is_default = data.get("is_default", False)
    if is_default:
        await db.bank_accounts.update_many(
            {"user_id": user["id"]}, {"$set": {"is_default": False}}
        )

    doc = {
        "id": account_id,
        "user_id": user["id"],
        "bank_name": bank_name,
        "account_name": account_name,
        "account_number": account_number_enc,
        "ifsc_code": data.get("ifsc_code", ""),
        "is_default": is_default,
        "created_at": now,
    }
    await db.bank_accounts.insert_one(doc)

    return {
        "id": account_id,
        "user_id": user["id"],
        "bank_name": bank_name,
        "account_name": account_name,
        "account_number": account_number_raw,
        "ifsc_code": data.get("ifsc_code", ""),
        "is_default": is_default,
        "created_at": now,
    }


@router.put("/bank-accounts/{account_id}")
async def update_bank_account(account_id: str, data: dict, user=Depends(get_current_user)):
    existing = await db.bank_accounts.find_one(
        {"id": account_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Bank account not found")

    dek = user.get("encryption_key", "")
    update = {}

    if "bank_name" in data:
        update["bank_name"] = data["bank_name"]
    if "account_name" in data:
        update["account_name"] = data["account_name"]
    if "account_number" in data:
        raw = data["account_number"]
        update["account_number"] = encrypt_field(raw, dek) if dek and raw else raw
    if "ifsc_code" in data:
        update["ifsc_code"] = data["ifsc_code"]
    if "is_default" in data:
        if data["is_default"]:
            await db.bank_accounts.update_many(
                {"user_id": user["id"]}, {"$set": {"is_default": False}}
            )
        update["is_default"] = data["is_default"]

    if update:
        await db.bank_accounts.update_one(
            {"id": account_id, "user_id": user["id"]}, {"$set": update}
        )

    updated = await db.bank_accounts.find_one(
        {"id": account_id, "user_id": user["id"]}, {"_id": 0}
    )
    if dek and updated.get("account_number", "").startswith("ENC:"):
        updated["account_number"] = decrypt_field(updated["account_number"], dek)
    return updated


@router.delete("/bank-accounts/{account_id}")
async def delete_bank_account(account_id: str, user=Depends(get_current_user)):
    result = await db.bank_accounts.delete_one(
        {"id": account_id, "user_id": user["id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Bank account not found")
    return {"message": "Bank account deleted"}


@router.delete("/bank-accounts")
async def delete_all_bank_accounts(user=Depends(get_current_user)):
    result = await db.bank_accounts.delete_many({"user_id": user["id"]})
    return {"message": f"Deleted {result.deleted_count} bank account(s)"}


@router.put("/bank-accounts/{account_id}/set-default")
async def set_default_bank_account(account_id: str, user=Depends(get_current_user)):
    existing = await db.bank_accounts.find_one(
        {"id": account_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Bank account not found")

    await db.bank_accounts.update_many(
        {"user_id": user["id"]}, {"$set": {"is_default": False}}
    )
    await db.bank_accounts.update_one(
        {"id": account_id, "user_id": user["id"]}, {"$set": {"is_default": True}}
    )
    return {"message": "Default bank account updated"}
