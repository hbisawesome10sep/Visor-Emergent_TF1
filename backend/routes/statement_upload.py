"""
Statement Upload — Endpoints for uploading Groww/Zerodha XLSX statements.
"""
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from database import db
from auth import get_current_user
from services.statement_parser import parse_holdings_xlsx

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload-statement")
async def upload_statement(
    file: UploadFile = File(...),
    statement_type: str = Form("auto"),
    user=Depends(get_current_user),
):
    """
    Upload a Groww/Zerodha XLSX statement.
    statement_type: 'stock_statement', 'mf_statement', 'ecas', or 'auto'
    """
    user_id = user["id"]

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only XLSX/XLS files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 10MB)")

    try:
        result = parse_holdings_xlsx(content, statement_type, file.filename)
    except Exception as e:
        logger.error(f"Parse error for {file.filename}: {e}")
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    holdings = result["holdings"]
    metadata = result["metadata"]

    if not holdings:
        return {
            "status": "no_holdings",
            "message": "No holdings found in the uploaded file. Please check the file format.",
            "metadata": metadata,
        }

    saved = 0
    duplicates = 0
    errors = 0
    saved_holdings = []

    for h in holdings:
        # Check for duplicate (same user + ISIN or same name+category)
        dup_filter = {"user_id": user_id}
        if h["isin"]:
            dup_filter["isin"] = h["isin"]
        else:
            dup_filter["name"] = h["name"]
            dup_filter["category"] = h["category"]

        existing = await db.holdings.find_one(dup_filter)

        if existing:
            # Update existing holding instead of creating duplicate
            update_fields = {}
            if h["quantity"] > 0:
                update_fields["quantity"] = h["quantity"]
            if h["buy_price"] > 0:
                update_fields["buy_price"] = h["buy_price"]
            if h["invested_value"] > 0:
                update_fields["invested_value"] = h["invested_value"]
            if h.get("current_price") and h["current_price"] > 0:
                update_fields["current_price"] = h["current_price"]
                update_fields["current_value"] = h["current_price"] * h["quantity"]
            if h.get("current_value") and h["current_value"] > 0:
                update_fields["current_value"] = h["current_value"]
            update_fields["source"] = f"{metadata['source']}_statement"
            update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

            await db.holdings.update_one(
                {"_id": existing["_id"]},
                {"$set": update_fields},
            )
            duplicates += 1
            continue

        holding_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": h["name"],
            "ticker": h["ticker"],
            "isin": h["isin"],
            "category": h["category"],
            "sub_category": h.get("sub_category", ""),
            "sector": h.get("sector", ""),
            "amc": h.get("amc", ""),
            "folio": h.get("folio", ""),
            "quantity": h["quantity"],
            "buy_price": h["buy_price"],
            "buy_date": h["buy_date"] or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "invested_value": h["invested_value"],
            "current_price": h.get("current_price") or h["buy_price"],
            "current_value": h.get("current_value") or h["invested_value"],
            "gain_loss": h.get("gain_loss", 0),
            "gain_loss_pct": h.get("gain_loss_pct", 0),
            "xirr": h.get("xirr"),
            "source": f"{metadata['source']}_statement",
            "source_platform": h.get("source_platform", metadata["source"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await db.holdings.insert_one(holding_doc)
            saved += 1
            saved_holdings.append({
                "name": h["name"],
                "category": h["category"],
                "quantity": h["quantity"],
                "invested_value": h["invested_value"],
            })
        except Exception as e:
            logger.error(f"Insert error for {h['name']}: {e}")
            errors += 1

    # Log import history
    await db.import_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "statement_upload",
        "source": metadata["source"],
        "statement_type": statement_type,
        "filename": file.filename,
        "saved": saved,
        "duplicates": duplicates,
        "errors": errors,
        "total_parsed": len(holdings),
        "imported_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "status": "success",
        "message": f"Imported {saved} holdings ({duplicates} updated, {errors} errors)",
        "saved": saved,
        "duplicates": duplicates,
        "errors": errors,
        "total_parsed": len(holdings),
        "holdings": saved_holdings,
        "metadata": metadata,
    }


@router.post("/parse-statement-preview")
async def parse_statement_preview(
    file: UploadFile = File(...),
    statement_type: str = Form("auto"),
    user=Depends(get_current_user),
):
    """Preview parsed holdings before importing."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only XLSX/XLS files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 10MB)")

    try:
        result = parse_holdings_xlsx(content, statement_type, file.filename)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    return {
        "holdings": result["holdings"],
        "metadata": result["metadata"],
    }
