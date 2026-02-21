from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import db
from auth import get_current_user
from models import FixedAssetCreate, FixedAssetUpdate, FixedAssetResponse
from routes.journal import create_journal_entry, delete_journal_for_reference
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/assets", response_model=List[FixedAssetResponse])
async def get_fixed_assets(user=Depends(get_current_user)):
    assets = await db.fixed_assets.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    result = []
    for asset in assets:
        purchase_date = datetime.fromisoformat(asset["purchase_date"].replace("Z", "+00:00")) if "T" in asset["purchase_date"] else datetime.strptime(asset["purchase_date"], "%Y-%m-%d")
        years_held = (datetime.now(timezone.utc) - purchase_date.replace(tzinfo=timezone.utc)).days / 365.25
        acc_dep = min(asset["purchase_value"], asset["purchase_value"] * (asset.get("depreciation_rate", 10) / 100) * years_held)
        asset["accumulated_depreciation"] = round(acc_dep, 2)
        result.append(FixedAssetResponse(**asset))
    return result


@router.post("/assets", response_model=FixedAssetResponse)
async def create_fixed_asset(asset: FixedAssetCreate, user=Depends(get_current_user)):
    asset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    payment_mode = asset.payment_mode or "cash"
    payment_account_name = asset.payment_account_name or "Cash"

    asset_doc = {
        "id": asset_id,
        "user_id": user["id"],
        "name": asset.name,
        "category": asset.category,
        "purchase_date": asset.purchase_date,
        "purchase_value": asset.purchase_value,
        "current_value": asset.current_value,
        "depreciation_rate": asset.depreciation_rate,
        "notes": asset.notes,
        "payment_mode": payment_mode,
        "payment_account_name": payment_account_name,
        "created_at": now,
    }
    await db.fixed_assets.insert_one(asset_doc)

    # Auto-create journal entry: Dr. Asset A/c (Real), Cr. Cash/Bank A/c
    pay_account = "Cash A/c" if payment_mode == "cash" else f"{payment_account_name} A/c"
    pay_type = "Real" if payment_mode == "cash" else "Personal"
    await create_journal_entry(
        user_id=user["id"],
        date=asset.purchase_date,
        narration=f"Being {asset.name} ({asset.category}) purchased",
        entries=[
            {"account_name": f"{asset.name} A/c", "account_type": "Real", "account_group": "Asset", "debit": asset.purchase_value, "credit": 0},
            {"account_name": pay_account, "account_type": pay_type, "account_group": "Asset", "debit": 0, "credit": asset.purchase_value},
        ],
        reference_type="asset",
        reference_id=asset_id,
    )

    asset_doc["accumulated_depreciation"] = 0
    return FixedAssetResponse(**asset_doc)


@router.put("/assets/{asset_id}", response_model=FixedAssetResponse)
async def update_fixed_asset(asset_id: str, asset_update: FixedAssetUpdate, user=Depends(get_current_user)):
    existing = await db.fixed_assets.find_one({"id": asset_id, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Asset not found")

    update_data = {k: v for k, v in asset_update.dict().items() if v is not None}
    if update_data:
        await db.fixed_assets.update_one({"id": asset_id}, {"$set": update_data})

    updated = await db.fixed_assets.find_one({"id": asset_id}, {"_id": 0})
    purchase_date = datetime.fromisoformat(updated["purchase_date"].replace("Z", "+00:00")) if "T" in updated["purchase_date"] else datetime.strptime(updated["purchase_date"], "%Y-%m-%d")
    years_held = (datetime.now(timezone.utc) - purchase_date.replace(tzinfo=timezone.utc)).days / 365.25
    acc_dep = min(updated["purchase_value"], updated["purchase_value"] * (updated.get("depreciation_rate", 10) / 100) * years_held)
    updated["accumulated_depreciation"] = round(acc_dep, 2)
    return FixedAssetResponse(**updated)


@router.delete("/assets/{asset_id}")
async def delete_fixed_asset(asset_id: str, user=Depends(get_current_user)):
    result = await db.fixed_assets.delete_one({"id": asset_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Asset not found")
    # Delete linked journal entries
    await delete_journal_for_reference(user["id"], asset_id)
    return {"message": "Asset deleted"}
