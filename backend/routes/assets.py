from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import db
from auth import get_current_user
from models import FixedAssetCreate, FixedAssetUpdate, FixedAssetResponse
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
        "created_at": now,
    }
    await db.fixed_assets.insert_one(asset_doc)
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
    return {"message": "Asset deleted"}
