"""
Credit Card Management and Transactions
- CRUD for credit cards
- Credit card transactions (separate from bank/UPI transactions)
- Statement upload and parsing
- EMI/SIP detection and approval
- Double-entry bookkeeping integration
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from database import db
from auth import get_current_user
from encryption import encrypt_field, decrypt_field
from routes.journal import create_journal_entry_direct
import logging
import re

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Major Indian credit card issuers
CREDIT_CARD_ISSUERS = [
    "HDFC Bank", "ICICI Bank", "SBI Card", "Axis Bank", "Kotak Mahindra Bank",
    "RBL Bank", "IndusInd Bank", "Yes Bank", "IDFC First Bank", "American Express",
    "Citibank", "Standard Chartered", "HSBC", "Bank of Baroda", "Punjab National Bank",
    "Canara Bank", "Union Bank of India", "Federal Bank", "AU Small Finance Bank",
    "OneCard", "Slice", "Jupiter", "Fi Money", "Other"
]

# EMI/SIP detection keywords
EMI_KEYWORDS = [
    "emi", "equated monthly", "loan emi", "car emi", "home emi", "bike emi",
    "personal loan", "consumer durable", "bajaj finserv", "hdfc loan",
    "iciciloan", "tata capital", "home credit", "zestmoney", "simpl",
    "lazypay emi", "flexmoney", "creditbee", "kreditbee", "moneyview"
]

SIP_KEYWORDS = [
    "sip", "systematic investment", "mutual fund", "mf purchase",
    "groww sip", "zerodha sip", "kuvera", "paytm money", "coin sip",
    "nps", "national pension", "atal pension", "ppf", "elss",
    "nippon", "hdfc mf", "icici pru", "sbi mf", "axis mf", "kotak mf",
    "dsp", "aditya birla", "franklin", "mirae", "motilal"
]

SUBSCRIPTION_KEYWORDS = [
    "netflix", "amazon prime", "hotstar", "disney", "spotify", "youtube premium",
    "apple music", "zee5", "sonyliv", "jiocinema", "linkedin premium",
    "microsoft 365", "google one", "icloud", "dropbox", "notion",
    "canva", "adobe", "figma", "slack", "zoom", "gym", "fitness"
]


# ══════════════════════════════════════════════════════════════════════════════
# CREDIT CARD CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/credit-cards")
async def get_credit_cards(user=Depends(get_current_user)):
    """Get all credit cards for the user."""
    cards = await db.credit_cards.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    dek = user.get("encryption_key", "")
    for card in cards:
        if dek and card.get("card_number", "").startswith("ENC:"):
            card["card_number"] = decrypt_field(card["card_number"], dek)
    
    # Add current outstanding and available credit
    for card in cards:
        outstanding = await get_card_outstanding(user["id"], card["id"])
        card["current_outstanding"] = outstanding
        card["available_credit"] = max(0, card.get("credit_limit", 0) - outstanding)
    
    return cards


@router.get("/credit-cards/issuers-list")
async def get_issuers_list():
    """Get list of credit card issuers."""
    return {"issuers": CREDIT_CARD_ISSUERS}


@router.post("/credit-cards")
async def create_credit_card(data: dict, user=Depends(get_current_user)):
    """Create a new credit card."""
    card_name = data.get("card_name", "").strip()
    issuer = data.get("issuer", "").strip()
    
    if not card_name or not issuer:
        raise HTTPException(400, "card_name and issuer are required")
    
    card_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    dek = user.get("encryption_key", "")
    
    # Encrypt card number (last 4 digits visible)
    card_number_raw = data.get("card_number", "")
    last_four = card_number_raw[-4:] if len(card_number_raw) >= 4 else card_number_raw
    card_number_enc = encrypt_field(card_number_raw, dek) if dek and card_number_raw else card_number_raw
    
    is_default = data.get("is_default", False)
    if is_default:
        await db.credit_cards.update_many(
            {"user_id": user["id"]}, {"$set": {"is_default": False}}
        )
    
    doc = {
        "id": card_id,
        "user_id": user["id"],
        "card_name": card_name,
        "issuer": issuer,
        "card_number": card_number_enc,
        "last_four": last_four,
        "credit_limit": data.get("credit_limit", 0),
        "billing_cycle_day": data.get("billing_cycle_day", 1),  # Day of month when bill generates
        "due_day": data.get("due_day", 15),  # Day of month when payment is due
        "is_default": is_default,
        "is_active": True,
        "created_at": now,
    }
    await db.credit_cards.insert_one(doc)
    
    return {
        **doc,
        "card_number": card_number_raw,
        "current_outstanding": 0,
        "available_credit": doc["credit_limit"],
    }


@router.put("/credit-cards/{card_id}")
async def update_credit_card(card_id: str, data: dict, user=Depends(get_current_user)):
    """Update a credit card."""
    existing = await db.credit_cards.find_one(
        {"id": card_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Credit card not found")
    
    dek = user.get("encryption_key", "")
    update = {}
    
    if "card_name" in data:
        update["card_name"] = data["card_name"]
    if "issuer" in data:
        update["issuer"] = data["issuer"]
    if "card_number" in data:
        raw = data["card_number"]
        update["card_number"] = encrypt_field(raw, dek) if dek and raw else raw
        update["last_four"] = raw[-4:] if len(raw) >= 4 else raw
    if "credit_limit" in data:
        update["credit_limit"] = data["credit_limit"]
    if "billing_cycle_day" in data:
        update["billing_cycle_day"] = data["billing_cycle_day"]
    if "due_day" in data:
        update["due_day"] = data["due_day"]
    if "is_default" in data:
        if data["is_default"]:
            await db.credit_cards.update_many(
                {"user_id": user["id"]}, {"$set": {"is_default": False}}
            )
        update["is_default"] = data["is_default"]
    if "is_active" in data:
        update["is_active"] = data["is_active"]
    
    if update:
        await db.credit_cards.update_one(
            {"id": card_id, "user_id": user["id"]}, {"$set": update}
        )
    
    updated = await db.credit_cards.find_one(
        {"id": card_id, "user_id": user["id"]}, {"_id": 0}
    )
    if dek and updated.get("card_number", "").startswith("ENC:"):
        updated["card_number"] = decrypt_field(updated["card_number"], dek)
    
    outstanding = await get_card_outstanding(user["id"], card_id)
    updated["current_outstanding"] = outstanding
    updated["available_credit"] = max(0, updated.get("credit_limit", 0) - outstanding)
    
    return updated


@router.delete("/credit-cards/{card_id}")
async def delete_credit_card(card_id: str, user=Depends(get_current_user)):
    """Delete a credit card and all its transactions."""
    result = await db.credit_cards.delete_one(
        {"id": card_id, "user_id": user["id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Credit card not found")
    
    # Delete associated transactions
    await db.credit_card_transactions.delete_many(
        {"card_id": card_id, "user_id": user["id"]}
    )
    
    return {"message": "Credit card and associated transactions deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# CREDIT CARD TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════

async def get_card_outstanding(user_id: str, card_id: str) -> float:
    """Calculate current outstanding for a credit card."""
    pipeline = [
        {"$match": {"user_id": user_id, "card_id": card_id}},
        {"$group": {
            "_id": None,
            "total_expenses": {"$sum": {"$cond": [{"$eq": ["$type", "expense"]}, "$amount", 0]}},
            "total_payments": {"$sum": {"$cond": [{"$eq": ["$type", "payment"]}, "$amount", 0]}},
        }}
    ]
    result = await db.credit_card_transactions.aggregate(pipeline).to_list(1)
    if result:
        return round(result[0]["total_expenses"] - result[0]["total_payments"], 2)
    return 0


@router.get("/credit-card-transactions")
async def get_credit_card_transactions(
    card_id: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    flagged_only: bool = False,
    user=Depends(get_current_user)
):
    """Get credit card transactions."""
    query = {"user_id": user["id"]}
    
    if card_id:
        query["card_id"] = card_id
    if category:
        query["category"] = category
    if flagged_only:
        query["is_flagged"] = True
    if search:
        query["$or"] = [
            {"description": {"$regex": search, "$options": "i"}},
            {"category": {"$regex": search, "$options": "i"}},
            {"merchant": {"$regex": search, "$options": "i"}},
        ]
    
    txns = await db.credit_card_transactions.find(
        query, {"_id": 0}
    ).sort("date", -1).to_list(500)
    
    return txns


@router.post("/credit-card-transactions")
async def create_credit_card_transaction(data: dict, user=Depends(get_current_user)):
    """Create a credit card transaction (expense or payment)."""
    card_id = data.get("card_id")
    txn_type = data.get("type", "expense")  # expense or payment
    amount = data.get("amount", 0)
    
    if not card_id:
        raise HTTPException(400, "card_id is required")
    
    # Verify card exists
    card = await db.credit_cards.find_one(
        {"id": card_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not card:
        raise HTTPException(404, "Credit card not found")
    
    txn_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Detect EMI/SIP/Subscription patterns
    description = data.get("description", "").lower()
    category = data.get("category", "Other")
    detected_type = None
    is_flagged = False
    
    if txn_type == "expense":
        detected_type, is_flagged = detect_special_transaction(description, amount)
        if detected_type and not category:
            category = detected_type
    
    doc = {
        "id": txn_id,
        "user_id": user["id"],
        "card_id": card_id,
        "card_name": card.get("card_name", ""),
        "type": txn_type,
        "amount": amount,
        "category": category,
        "description": data.get("description", ""),
        "merchant": data.get("merchant", ""),
        "date": data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "is_recurring": data.get("is_recurring", False),
        "recurring_frequency": data.get("recurring_frequency"),
        "is_flagged": is_flagged,
        "flagged_type": detected_type,
        "is_approved": False,
        "notes": data.get("notes", ""),
        "statement_ref": data.get("statement_ref"),
        "created_at": now,
    }
    await db.credit_card_transactions.insert_one(doc)
    
    # Create journal entry for double-entry bookkeeping
    await create_cc_journal_entry(user["id"], doc, card)
    
    return doc


@router.put("/credit-card-transactions/{txn_id}")
async def update_credit_card_transaction(txn_id: str, data: dict, user=Depends(get_current_user)):
    """Update a credit card transaction."""
    existing = await db.credit_card_transactions.find_one(
        {"id": txn_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Transaction not found")
    
    update = {}
    for field in ["category", "description", "merchant", "date", "is_recurring", 
                  "recurring_frequency", "notes", "amount"]:
        if field in data:
            update[field] = data[field]
    
    if update:
        await db.credit_card_transactions.update_one(
            {"id": txn_id, "user_id": user["id"]}, {"$set": update}
        )
    
    updated = await db.credit_card_transactions.find_one(
        {"id": txn_id, "user_id": user["id"]}, {"_id": 0}
    )
    return updated


@router.delete("/credit-card-transactions/{txn_id}")
async def delete_credit_card_transaction(txn_id: str, user=Depends(get_current_user)):
    """Delete a credit card transaction."""
    result = await db.credit_card_transactions.delete_one(
        {"id": txn_id, "user_id": user["id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Transaction not found")
    
    # Delete associated journal entry
    await db.journal_entries.delete_many(
        {"user_id": user["id"], "reference_id": txn_id, "reference_type": "credit_card"}
    )
    
    return {"message": "Transaction deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# EMI/SIP DETECTION AND APPROVAL
# ══════════════════════════════════════════════════════════════════════════════

def detect_special_transaction(description: str, amount: float) -> tuple:
    """
    Detect if a transaction is EMI, SIP, or Subscription.
    Returns (detected_type, should_flag).
    """
    desc_lower = description.lower()
    
    # Check EMI
    for keyword in EMI_KEYWORDS:
        if keyword in desc_lower:
            return ("EMI", True)
    
    # Check SIP
    for keyword in SIP_KEYWORDS:
        if keyword in desc_lower:
            return ("SIP", True)
    
    # Check Subscription
    for keyword in SUBSCRIPTION_KEYWORDS:
        if keyword in desc_lower:
            return ("Subscription", True)
    
    # Pattern-based detection (round numbers often indicate EMI)
    if amount > 1000 and amount == round(amount):
        # Could be EMI - flag for review
        return (None, False)  # Don't auto-flag just based on amount
    
    return (None, False)


@router.get("/flagged-transactions")
async def get_flagged_transactions(
    source: Optional[str] = None,  # "bank" or "credit_card" or None for all
    user=Depends(get_current_user)
):
    """Get all flagged transactions (EMI/SIP candidates) for approval."""
    flagged = []
    
    # Get flagged bank/UPI transactions
    if source in (None, "bank"):
        bank_flagged = await db.transactions.find(
            {"user_id": user["id"], "is_flagged": True}, {"_id": 0}
        ).to_list(100)
        for t in bank_flagged:
            t["source"] = "bank"
        flagged.extend(bank_flagged)
    
    # Get flagged credit card transactions
    if source in (None, "credit_card"):
        cc_flagged = await db.credit_card_transactions.find(
            {"user_id": user["id"], "is_flagged": True, "is_approved": False}, {"_id": 0}
        ).to_list(100)
        for t in cc_flagged:
            t["source"] = "credit_card"
        flagged.extend(cc_flagged)
    
    # Sort by date
    flagged.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    return flagged


@router.post("/approve-flagged/{txn_id}")
async def approve_flagged_transaction(
    txn_id: str,
    data: dict,
    user=Depends(get_current_user)
):
    """
    Approve a flagged transaction as EMI/SIP/Subscription.
    This will:
    1. Update the transaction category
    2. Create a recurring transaction if applicable
    3. Update investments (for SIP) or loans (for EMI)
    """
    source = data.get("source", "credit_card")
    approved_type = data.get("approved_type")  # EMI, SIP, Subscription
    create_recurring = data.get("create_recurring", True)
    
    if approved_type not in ["EMI", "SIP", "Subscription"]:
        raise HTTPException(400, "approved_type must be EMI, SIP, or Subscription")
    
    # Get the transaction
    if source == "credit_card":
        txn = await db.credit_card_transactions.find_one(
            {"id": txn_id, "user_id": user["id"]}, {"_id": 0}
        )
        collection = db.credit_card_transactions
    else:
        txn = await db.transactions.find_one(
            {"id": txn_id, "user_id": user["id"]}, {"_id": 0}
        )
        collection = db.transactions
    
    if not txn:
        raise HTTPException(404, "Transaction not found")
    
    # Update transaction
    update_data = {
        "is_approved": True,
        "category": approved_type,
        "is_recurring": True,
        "recurring_frequency": "monthly",
    }
    await collection.update_one(
        {"id": txn_id, "user_id": user["id"]}, {"$set": update_data}
    )
    
    # Create recurring transaction entry
    if create_recurring:
        recurring_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        recurring_doc = {
            "id": recurring_id,
            "user_id": user["id"],
            "name": txn.get("description", approved_type),
            "amount": txn["amount"],
            "frequency": "monthly",
            "category": approved_type,
            "start_date": txn.get("date", datetime.now().strftime("%Y-%m-%d")),
            "day_of_month": int(txn.get("date", "2025-01-15").split("-")[2]),
            "is_active": True,
            "source": source,
            "source_card_id": txn.get("card_id") if source == "credit_card" else None,
            "created_at": now,
        }
        await db.recurring_transactions.insert_one(recurring_doc)
    
    # Handle SIP - create/update investment entry
    if approved_type == "SIP":
        await handle_sip_approval(user["id"], txn)
    
    # Handle EMI - update loan tracking if exists
    if approved_type == "EMI":
        await handle_emi_approval(user["id"], txn)
    
    return {"message": f"Transaction approved as {approved_type}", "recurring_created": create_recurring}


@router.post("/reject-flagged/{txn_id}")
async def reject_flagged_transaction(txn_id: str, data: dict, user=Depends(get_current_user)):
    """Reject a flagged transaction - it's not EMI/SIP."""
    source = data.get("source", "credit_card")
    
    if source == "credit_card":
        collection = db.credit_card_transactions
    else:
        collection = db.transactions
    
    await collection.update_one(
        {"id": txn_id, "user_id": user["id"]},
        {"$set": {"is_flagged": False, "is_approved": False}}
    )
    
    return {"message": "Transaction unflagged"}


async def handle_sip_approval(user_id: str, txn: dict):
    """Handle SIP approval - create/update investment tracking."""
    description = txn.get("description", "SIP Investment")
    amount = txn["amount"]
    
    # Check if similar SIP exists
    existing_sip = await db.holdings.find_one({
        "user_id": user_id,
        "category": "Mutual Fund",
        "is_sip": True,
        "sip_amount": amount,
    }, {"_id": 0})
    
    if not existing_sip:
        # Create new SIP holding entry
        holding_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        holding_doc = {
            "id": holding_id,
            "user_id": user_id,
            "name": description,
            "ticker": "",
            "isin": "",
            "category": "Mutual Fund",
            "quantity": 0,
            "buy_price": amount,
            "buy_date": txn.get("date", ""),
            "current_value": amount,
            "is_sip": True,
            "sip_amount": amount,
            "sip_date": int(txn.get("date", "2025-01-15").split("-")[2]),
            "created_at": now,
        }
        await db.holdings.insert_one(holding_doc)


async def handle_emi_approval(user_id: str, txn: dict):
    """Handle EMI approval - update loan tracking."""
    description = txn.get("description", "")
    amount = txn["amount"]
    
    # Check if there's a loan with matching EMI amount
    loan = await db.loans.find_one({
        "user_id": user_id,
        "emi_amount": {"$gte": amount * 0.95, "$lte": amount * 1.05},  # 5% tolerance
    }, {"_id": 0})
    
    if loan:
        # Update loan payment tracking
        await db.loans.update_one(
            {"id": loan["id"], "user_id": user_id},
            {"$inc": {"total_principal_paid": amount * 0.7, "total_interest_paid": amount * 0.3}}
        )


# ══════════════════════════════════════════════════════════════════════════════
# JOURNAL ENTRY CREATION FOR CREDIT CARD
# ══════════════════════════════════════════════════════════════════════════════

async def create_cc_journal_entry(user_id: str, txn: dict, card: dict):
    """
    Create double-entry journal for credit card transactions.
    
    For EXPENSE (purchase on credit card):
        Dr. Expense A/c (Nominal - Expense)
        Cr. Credit Card Payable A/c (Personal - Liability)
    
    For PAYMENT (paying credit card bill):
        Dr. Credit Card Payable A/c (Personal - Liability)
        Cr. Bank A/c (Real - Asset)
    """
    entry_number = await get_next_entry_number(user_id)
    now = datetime.now(timezone.utc).isoformat()
    
    card_account_name = f"Credit Card - {card.get('card_name', 'Card')} A/c"
    
    if txn["type"] == "expense":
        # Expense on credit card
        expense_account = f"{txn['category']} A/c"
        entries = [
            {
                "account_name": expense_account,
                "account_type": "Nominal",
                "account_group": "Expense",
                "debit": txn["amount"],
                "credit": 0,
            },
            {
                "account_name": card_account_name,
                "account_type": "Personal",
                "account_group": "Liability",
                "debit": 0,
                "credit": txn["amount"],
            },
        ]
        narration = f"Credit card expense - {txn.get('description', txn['category'])}"
    else:
        # Payment to credit card
        entries = [
            {
                "account_name": card_account_name,
                "account_type": "Personal",
                "account_group": "Liability",
                "debit": txn["amount"],
                "credit": 0,
            },
            {
                "account_name": "Bank A/c",
                "account_type": "Real",
                "account_group": "Asset",
                "debit": 0,
                "credit": txn["amount"],
            },
        ]
        narration = f"Credit card payment - {card.get('card_name', 'Card')}"
    
    journal_doc = {
        "id": str(uuid4()),
        "user_id": user_id,
        "entry_number": entry_number,
        "date": txn["date"],
        "entries": entries,
        "narration": narration,
        "reference_type": "credit_card",
        "reference_id": txn["id"],
        "created_at": now,
    }
    await db.journal_entries.insert_one(journal_doc)


async def get_next_entry_number(user_id: str) -> int:
    """Get the next journal entry number for a user."""
    last_entry = await db.journal_entries.find_one(
        {"user_id": user_id},
        sort=[("entry_number", -1)]
    )
    return (last_entry.get("entry_number", 0) if last_entry else 0) + 1


# ══════════════════════════════════════════════════════════════════════════════
# CREDIT CARD STATEMENT UPLOAD (PLACEHOLDER)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/credit-cards/{card_id}/upload-statement")
async def upload_credit_card_statement(
    card_id: str,
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    user=Depends(get_current_user)
):
    """
    Upload and parse a credit card statement.
    Note: Parsing logic will be added when user provides statement templates.
    """
    # Verify card exists
    card = await db.credit_cards.find_one(
        {"id": card_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not card:
        raise HTTPException(404, "Credit card not found")
    
    # Check file type
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in [".pdf", ".csv", ".xlsx", ".xls"]):
        raise HTTPException(400, "Unsupported file format. Please upload PDF, CSV, or Excel file.")
    
    # Read file content
    content = await file.read()
    
    # For now, return a placeholder response
    # Actual parsing will be implemented when user provides templates
    return {
        "message": "Statement uploaded successfully. Parsing templates will be configured based on your bank's format.",
        "card_id": card_id,
        "filename": file.filename,
        "file_size": len(content),
        "status": "pending_template",
        "note": "Please provide a sample statement so we can configure the parser for your credit card issuer."
    }


# ══════════════════════════════════════════════════════════════════════════════
# CREDIT CARD SUMMARY/ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/credit-cards/summary")
async def get_credit_card_summary(user=Depends(get_current_user)):
    """Get summary of all credit cards."""
    cards = await db.credit_cards.find(
        {"user_id": user["id"], "is_active": True}, {"_id": 0}
    ).to_list(50)
    
    total_limit = 0
    total_outstanding = 0
    total_available = 0
    cards_summary = []
    
    for card in cards:
        outstanding = await get_card_outstanding(user["id"], card["id"])
        available = max(0, card.get("credit_limit", 0) - outstanding)
        
        total_limit += card.get("credit_limit", 0)
        total_outstanding += outstanding
        total_available += available
        
        cards_summary.append({
            "id": card["id"],
            "card_name": card["card_name"],
            "issuer": card["issuer"],
            "last_four": card.get("last_four", ""),
            "credit_limit": card.get("credit_limit", 0),
            "outstanding": outstanding,
            "available": available,
            "utilization": round((outstanding / card.get("credit_limit", 1)) * 100, 1) if card.get("credit_limit", 0) > 0 else 0,
            "due_day": card.get("due_day", 15),
        })
    
    # Get category breakdown of expenses
    pipeline = [
        {"$match": {"user_id": user["id"], "type": "expense"}},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1}},
    ]
    category_breakdown = await db.credit_card_transactions.aggregate(pipeline).to_list(20)
    
    return {
        "total_credit_limit": total_limit,
        "total_outstanding": total_outstanding,
        "total_available": total_available,
        "overall_utilization": round((total_outstanding / total_limit) * 100, 1) if total_limit > 0 else 0,
        "cards": cards_summary,
        "category_breakdown": {c["_id"]: c["total"] for c in category_breakdown},
    }


@router.get("/credit-cards/{card_id}/statement-summary")
async def get_card_statement_summary(
    card_id: str,
    month: Optional[str] = None,  # Format: YYYY-MM
    user=Depends(get_current_user)
):
    """Get statement summary for a specific card."""
    card = await db.credit_cards.find_one(
        {"id": card_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not card:
        raise HTTPException(404, "Credit card not found")
    
    # Default to current month
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    # Get transactions for the month
    start_date = f"{month}-01"
    end_date = f"{month}-31"
    
    txns = await db.credit_card_transactions.find({
        "user_id": user["id"],
        "card_id": card_id,
        "date": {"$gte": start_date, "$lte": end_date},
    }, {"_id": 0}).sort("date", -1).to_list(500)
    
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_payments = sum(t["amount"] for t in txns if t["type"] == "payment")
    
    # Category breakdown
    category_totals = {}
    for t in txns:
        if t["type"] == "expense":
            cat = t.get("category", "Other")
            category_totals[cat] = category_totals.get(cat, 0) + t["amount"]
    
    return {
        "card_id": card_id,
        "card_name": card["card_name"],
        "month": month,
        "total_expenses": total_expenses,
        "total_payments": total_payments,
        "net_outstanding": total_expenses - total_payments,
        "transaction_count": len(txns),
        "category_breakdown": category_totals,
        "transactions": txns,
    }
