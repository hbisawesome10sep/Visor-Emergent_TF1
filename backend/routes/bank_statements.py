"""
Bank Statement Route Handlers
Upload, history, and recategorize endpoints.
Parsing logic lives in /parsers/ package.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from uuid import uuid4
from datetime import datetime, timezone
from database import db
from auth import get_current_user
from routes.journal import create_journal_from_transaction
from encryption import encrypt_field
import re
import logging

from parsers import (
    parse_csv_statement, parse_excel_statement, parse_pdf_statement,
    categorize_transaction,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.post("/bank-statements/upload")
async def upload_bank_statement(
    file: UploadFile = File(...),
    bank_name: str = Form(""),
    account_name: str = Form(""),
    password: str = Form(""),
    bank_hint: str = Form(""),
    user=Depends(get_current_user),
):
    """
    Upload a bank statement (PDF/CSV/Excel) and import transactions.
    Supports password-protected PDFs.

    Reverses bank's debit/credit to user's perspective:
    - Bank Credit (deposit) -> User: Dr. Bank A/c, Cr. Income A/c
    - Bank Debit (withdrawal) -> User: Dr. Expense A/c, Cr. Bank A/c
    """
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("csv", "xlsx", "xls", "pdf"):
        raise HTTPException(400, f"Unsupported format: .{ext}. Use PDF, CSV, or Excel (.xlsx)")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum 10MB.")

    # Parse the statement
    try:
        if ext == "csv":
            content = file_bytes.decode("utf-8", errors="replace")
            raw_txns = parse_csv_statement(content)
        elif ext in ("xlsx", "xls"):
            raw_txns = parse_excel_statement(file_bytes)
        elif ext == "pdf":
            hint = bank_hint.strip() if bank_hint and bank_hint.strip() else bank_name
            raw_txns = parse_pdf_statement(file_bytes, password=password or None, bank_hint=hint)
        else:
            raise HTTPException(400, "Unsupported format")
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error(f"Statement parse error: {e}")
        raise HTTPException(422, f"Failed to parse statement: {str(e)}")

    if not raw_txns:
        raise HTTPException(422, "No transactions found in the statement. Please check the file format.")

    # Step 1: Create or find bank account
    if not bank_name:
        bank_name = "Unknown Bank"
    if not account_name:
        account_name = f"{bank_name} Account"

    existing_account = await db.bank_accounts.find_one(
        {"user_id": user["id"], "account_name": account_name}, {"_id": 0}
    )
    if existing_account:
        bank_account_id = existing_account["id"]
    else:
        bank_account_id = str(uuid4())
        await db.bank_accounts.insert_one({
            "id": bank_account_id,
            "user_id": user["id"],
            "bank_name": bank_name,
            "account_name": account_name,
            "account_number": "",
            "ifsc_code": "",
            "is_default": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Step 2: Import transactions with perspective reversal
    imported = 0
    skipped = 0
    errors = 0

    for raw in raw_txns:
        try:
            is_credit = raw["bank_credit"] > 0

            if is_credit:
                amount = raw["bank_credit"]
                category, cat_type = categorize_transaction(raw["description"], is_credit=True)
                txn_type = "income"
            else:
                amount = raw["bank_debit"]
                category, cat_type = categorize_transaction(raw["description"], is_credit=False)
                txn_type = "investment" if cat_type == "investment" else "expense"

            if amount <= 0:
                skipped += 1
                continue

            # Check for duplicate
            existing = await db.transactions.find_one({
                "user_id": user["id"],
                "date": raw["date"],
                "amount": amount,
                "description": {"$regex": re.escape(raw["description"][:30]), "$options": "i"},
            })
            if existing:
                skipped += 1
                continue

            txn_id = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()

            txn_doc = {
                "id": txn_id,
                "user_id": user["id"],
                "type": txn_type,
                "amount": amount,
                "category": category,
                "description": raw["description"],
                "date": raw["date"],
                "is_recurring": False,
                "recurring_frequency": None,
                "is_split": False,
                "split_count": 1,
                "notes": f"Imported from {bank_name} statement",
                "buy_sell": None,
                "units": None,
                "price_per_unit": None,
                "payment_mode": "bank",
                "payment_account_name": account_name,
                "created_at": now,
            }
            await db.transactions.insert_one(txn_doc)

            await create_journal_from_transaction(
                user_id=user["id"],
                txn_id=txn_id,
                txn_type=txn_type,
                category=category,
                description=raw["description"],
                amount=amount,
                date=raw["date"],
                payment_mode="bank",
                payment_account_name=account_name,
            )

            imported += 1
        except Exception as e:
            logger.error(f"Error importing transaction: {e}")
            errors += 1

    return {
        "message": "Statement processed successfully",
        "bank_name": bank_name,
        "account_name": account_name,
        "bank_account_id": bank_account_id,
        "account_created": not bool(existing_account),
        "total_in_statement": len(raw_txns),
        "imported": imported,
        "skipped_duplicates": skipped,
        "errors": errors,
        "date_range": {
            "start": min(t["date"] for t in raw_txns) if raw_txns else None,
            "end": max(t["date"] for t in raw_txns) if raw_txns else None,
        },
    }


@router.get("/bank-statements/history")
async def get_upload_history(user=Depends(get_current_user)):
    """Get history of imported bank statements."""
    pipeline = [
        {"$match": {"user_id": user["id"], "notes": {"$regex": "Imported from.*statement"}}},
        {"$group": {
            "_id": "$payment_account_name",
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$amount"},
            "first_date": {"$min": "$date"},
            "last_date": {"$max": "$date"},
        }},
        {"$sort": {"last_date": -1}},
    ]
    results = await db.transactions.aggregate(pipeline).to_list(50)
    return {
        "imports": [
            {
                "account_name": r["_id"],
                "transaction_count": r["count"],
                "total_amount": round(r["total_amount"], 2),
                "date_range": {"start": r["first_date"], "end": r["last_date"]},
            }
            for r in results
        ]
    }


@router.post("/bank-statements/recategorize")
async def recategorize_transactions(user=Depends(get_current_user)):
    """Re-categorize all imported bank statement transactions."""
    imported_txns = await db.transactions.find({
        "user_id": user["id"],
        "notes": {"$regex": "Imported from.*statement", "$options": "i"}
    }).to_list(10000)

    if not imported_txns:
        return {"message": "No imported transactions found", "updated": 0, "unchanged": 0}

    updated = 0
    unchanged = 0
    errors = 0
    type_changes = 0

    for txn in imported_txns:
        try:
            description = txn.get("description", "")
            old_category = txn.get("category", "")
            old_type = txn.get("type", "expense")
            is_credit = old_type == "income"

            new_category, cat_type = categorize_transaction(description, is_credit=is_credit)

            if is_credit:
                new_type = "income"
            elif cat_type == "investment":
                new_type = "investment"
            else:
                new_type = "expense"

            if old_category == new_category and old_type == new_type:
                unchanged += 1
                continue

            if old_type != new_type:
                type_changes += 1

            await db.transactions.update_one(
                {"id": txn["id"]},
                {"$set": {"category": new_category, "type": new_type}}
            )

            await db.journal_entries.delete_many({
                "user_id": user["id"],
                "reference_type": "transaction",
                "reference_id": txn["id"]
            })

            await create_journal_from_transaction(
                user_id=user["id"],
                txn_id=txn["id"],
                txn_type=new_type,
                category=new_category,
                description=description,
                amount=txn.get("amount", 0),
                date=txn.get("date"),
                payment_mode=txn.get("payment_mode", "bank"),
                payment_account_name=txn.get("payment_account_name", "Bank Account"),
            )

            updated += 1
            logger.info(f"Re-categorized: '{description[:50]}' | {old_category}->{new_category} | {old_type}->{new_type}")

        except Exception as e:
            logger.error(f"Error re-categorizing transaction {txn.get('id')}: {e}")
            errors += 1

    return {
        "message": "Re-categorization complete",
        "total_transactions": len(imported_txns),
        "updated": updated,
        "unchanged": unchanged,
        "type_changes": type_changes,
        "errors": errors
    }
