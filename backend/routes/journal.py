from fastapi import APIRouter, Depends
from typing import Optional
from database import db
from auth import get_current_user
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# ══════════════════════════════════════
# Account classification for Indian Double Entry
# ══════════════════════════════════════

ACCOUNT_TYPE_MAP = {
    # Income categories → Nominal/Income
    "Salary": ("Nominal", "Income"),
    "Business Income": ("Nominal", "Income"),
    "Freelance": ("Nominal", "Income"),
    "Consulting": ("Nominal", "Income"),
    "Interest": ("Nominal", "Income"),
    "Dividends": ("Nominal", "Income"),
    "Rental Income": ("Nominal", "Income"),
    "Bonus": ("Nominal", "Income"),
    "Commission": ("Nominal", "Income"),
    "Capital Gains": ("Nominal", "Income"),
    "Pension": ("Nominal", "Income"),
    "Refund": ("Nominal", "Income"),
    # Expense categories → Nominal/Expense
    "Groceries": ("Nominal", "Expense"),
    "Rent": ("Nominal", "Expense"),
    "Food & Dining": ("Nominal", "Expense"),
    "Transport": ("Nominal", "Expense"),
    "Fuel": ("Nominal", "Expense"),
    "Shopping": ("Nominal", "Expense"),
    "Utilities": ("Nominal", "Expense"),
    "Electricity": ("Nominal", "Expense"),
    "Water": ("Nominal", "Expense"),
    "Internet": ("Nominal", "Expense"),
    "Mobile Recharge": ("Nominal", "Expense"),
    "Entertainment": ("Nominal", "Expense"),
    "Health": ("Nominal", "Expense"),
    "Medicine": ("Nominal", "Expense"),
    "Insurance": ("Nominal", "Expense"),
    "Education": ("Nominal", "Expense"),
    "EMI": ("Nominal", "Expense"),
    "Loan Repayment": ("Nominal", "Expense"),
    "Subscriptions": ("Nominal", "Expense"),
    "Personal Care": ("Nominal", "Expense"),
    "Clothing": ("Nominal", "Expense"),
    "Home Maintenance": ("Nominal", "Expense"),
    "Travel": ("Nominal", "Expense"),
    "Gifts": ("Nominal", "Expense"),
    "Donations": ("Nominal", "Expense"),
    "Taxes": ("Nominal", "Expense"),
    "Bank Charges": ("Nominal", "Expense"),
    "TDS": ("Nominal", "Expense"),
    # Investment categories → Real/Asset
    "Mutual Funds": ("Real", "Asset"),
    "SIP": ("Real", "Asset"),
    "Stocks": ("Real", "Asset"),
    "ETFs": ("Real", "Asset"),
    "Fixed Deposit": ("Real", "Asset"),
    "PPF": ("Real", "Asset"),
    "NPS": ("Real", "Asset"),
    "EPF": ("Real", "Asset"),
    "Gold": ("Real", "Asset"),
    "Silver": ("Real", "Asset"),
    "Copper": ("Real", "Asset"),
    "Bonds": ("Real", "Asset"),
    "Real Estate": ("Real", "Asset"),
    "Crypto": ("Real", "Asset"),
    "ULIP": ("Real", "Asset"),
    "Sovereign Gold Bond": ("Real", "Asset"),
    "Government Securities": ("Real", "Asset"),
}


def get_account_classification(category: str, txn_type: str):
    """Get account type and group for a category based on Indian accounting."""
    if category in ACCOUNT_TYPE_MAP:
        return ACCOUNT_TYPE_MAP[category]
    if txn_type == "income":
        return ("Nominal", "Income")
    if txn_type == "expense":
        return ("Nominal", "Expense")
    if txn_type == "investment":
        return ("Real", "Asset")
    return ("Nominal", "Expense")


def get_payment_account_info(payment_mode: str, payment_account_name: str):
    """Get account classification for the payment/receipt account."""
    if payment_mode == "cash" or not payment_mode:
        return "Cash A/c", "Real", "Asset"
    return f"{payment_account_name} A/c", "Personal", "Asset"


def build_account_name(category: str, txn_type: str):
    """Build the account name for the category side of the journal entry."""
    return f"{category} A/c"


async def create_journal_entry(
    user_id: str,
    date: str,
    narration: str,
    entries: list,
    reference_type: str = "transaction",
    reference_id: str = "",
):
    """Create a journal entry in the database."""
    from uuid import uuid4

    last_entry = await db.journal_entries.find_one(
        {"user_id": user_id}, {"_id": 0, "entry_number": 1},
        sort=[("entry_number", -1)]
    )
    entry_number = (last_entry["entry_number"] + 1) if last_entry else 1

    doc = {
        "id": str(uuid4()),
        "user_id": user_id,
        "date": date,
        "entry_number": entry_number,
        "narration": narration,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "entries": entries,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.journal_entries.insert_one(doc)
    return doc["id"]


async def create_journal_from_transaction(
    user_id: str,
    txn_id: str,
    txn_type: str,
    category: str,
    description: str,
    amount: float,
    date: str,
    payment_mode: str = "cash",
    payment_account_name: str = "Cash",
):
    """Auto-create a journal entry from a transaction."""
    cat_account = build_account_name(category, txn_type)
    cat_type, cat_group = get_account_classification(category, txn_type)
    pay_account, pay_type, pay_group = get_payment_account_info(payment_mode, payment_account_name)

    entries = []
    if txn_type == "income":
        # Dr. Cash/Bank (what comes in), Cr. Income account
        narration = f"Being {category.lower()} received"
        if description:
            narration += f" - {description}"
        entries = [
            {"account_name": pay_account, "account_type": pay_type, "account_group": pay_group, "debit": amount, "credit": 0},
            {"account_name": cat_account, "account_type": cat_type, "account_group": cat_group, "debit": 0, "credit": amount},
        ]
    elif txn_type == "expense":
        # Dr. Expense account (debit expenses), Cr. Cash/Bank (what goes out)
        narration = f"Being {category.lower()} paid"
        if description:
            narration += f" - {description}"
        entries = [
            {"account_name": cat_account, "account_type": cat_type, "account_group": cat_group, "debit": amount, "credit": 0},
            {"account_name": pay_account, "account_type": pay_type, "account_group": pay_group, "debit": 0, "credit": amount},
        ]
    elif txn_type == "investment":
        # Dr. Investment account (asset comes in), Cr. Cash/Bank (goes out)
        narration = f"Being investment in {category.lower()}"
        if description:
            narration += f" - {description}"
        entries = [
            {"account_name": cat_account, "account_type": cat_type, "account_group": cat_group, "debit": amount, "credit": 0},
            {"account_name": pay_account, "account_type": pay_type, "account_group": pay_group, "debit": 0, "credit": amount},
        ]

    if entries:
        return await create_journal_entry(
            user_id=user_id,
            date=date,
            narration=narration,
            entries=entries,
            reference_type="transaction",
            reference_id=txn_id,
        )
    return None


async def delete_journal_for_reference(user_id: str, reference_id: str):
    """Delete journal entries linked to a reference (e.g., transaction)."""
    await db.journal_entries.delete_many(
        {"user_id": user_id, "reference_id": reference_id}
    )


@router.get("/journal")
async def get_journal_entries(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    reference_type: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    user=Depends(get_current_user),
):
    """Get journal entries with optional filters."""
    query = {"user_id": user["id"]}

    if start_date:
        query.setdefault("date", {})["$gte"] = start_date
    if end_date:
        query.setdefault("date", {})["$lte"] = end_date
    if reference_type:
        query["reference_type"] = reference_type
    if search:
        query["$or"] = [
            {"narration": {"$regex": search, "$options": "i"}},
            {"entries.account_name": {"$regex": search, "$options": "i"}},
        ]

    total = await db.journal_entries.count_documents(query)
    skip = (page - 1) * limit

    entries = await db.journal_entries.find(
        query, {"_id": 0}
    ).sort("date", -1).skip(skip).limit(limit).to_list(limit)

    return {
        "entries": entries,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/journal/accounts")
async def get_all_accounts(
    search: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Get all unique accounts from journal entries for the user."""
    pipeline = [
        {"$match": {"user_id": user["id"]}},
        {"$unwind": "$entries"},
        {"$group": {
            "_id": "$entries.account_name",
            "account_type": {"$first": "$entries.account_type"},
            "account_group": {"$first": "$entries.account_group"},
            "total_debit": {"$sum": "$entries.debit"},
            "total_credit": {"$sum": "$entries.credit"},
            "entry_count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    if search:
        pipeline.insert(2, {
            "$match": {"entries.account_name": {"$regex": search, "$options": "i"}}
        })

    results = await db.journal_entries.aggregate(pipeline).to_list(500)
    accounts = []
    for r in results:
        balance = r["total_debit"] - r["total_credit"]
        accounts.append({
            "name": r["_id"],
            "account_type": r["account_type"],
            "account_group": r["account_group"],
            "total_debit": round(r["total_debit"], 2),
            "total_credit": round(r["total_credit"], 2),
            "balance": round(balance, 2),
            "entry_count": r["entry_count"],
        })
    return {"accounts": accounts}


@router.get("/journal/ledger/{account_name:path}")
async def get_account_ledger(
    account_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Get individual ledger for a specific account."""
    query = {
        "user_id": user["id"],
        "entries.account_name": account_name,
    }
    if start_date:
        query.setdefault("date", {})["$gte"] = start_date
    if end_date:
        query.setdefault("date", {})["$lte"] = end_date

    journal_docs = await db.journal_entries.find(
        query, {"_id": 0}
    ).sort("date", 1).to_list(2000)

    ledger_entries = []
    running_balance = 0.0

    for jdoc in journal_docs:
        for entry in jdoc["entries"]:
            if entry["account_name"] == account_name:
                running_balance += entry["debit"] - entry["credit"]
                # Find the contra account(s)
                contra_accounts = [
                    e["account_name"] for e in jdoc["entries"]
                    if e["account_name"] != account_name
                ]
                ledger_entries.append({
                    "date": jdoc["date"],
                    "entry_number": jdoc["entry_number"],
                    "narration": jdoc["narration"],
                    "contra_account": ", ".join(contra_accounts) if contra_accounts else "",
                    "reference_type": jdoc["reference_type"],
                    "reference_id": jdoc["reference_id"],
                    "debit": entry["debit"],
                    "credit": entry["credit"],
                    "balance": round(running_balance, 2),
                })

    total_debit = sum(e["debit"] for e in ledger_entries)
    total_credit = sum(e["credit"] for e in ledger_entries)

    # Determine account info from first entry
    account_type = ""
    account_group = ""
    if journal_docs:
        for entry in journal_docs[0]["entries"]:
            if entry["account_name"] == account_name:
                account_type = entry["account_type"]
                account_group = entry["account_group"]
                break

    return {
        "account_name": account_name,
        "account_type": account_type,
        "account_group": account_group,
        "start_date": start_date,
        "end_date": end_date,
        "entries": ledger_entries,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "closing_balance": round(running_balance, 2),
        "entry_count": len(ledger_entries),
    }
