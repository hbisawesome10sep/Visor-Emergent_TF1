"""
Bank Statement Parser & Importer

Handles PDF, CSV, and Excel bank statements.
Key feature: Reverses bank's debit/credit to user's perspective.

Bank's perspective: Credit = Deposit, Debit = Withdrawal
User's perspective: Debit = Deposit (money comes in), Credit = Withdrawal (money goes out)
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone
from database import db
from auth import get_current_user
from routes.journal import create_journal_from_transaction
from encryption import encrypt_field
import io
import csv
import re
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Common date formats in Indian bank statements
DATE_FORMATS = [
    "%d.%m.%Y", "%d.%m.%y",  # ICICI format: 01.01.2026
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%d %b %y",
    "%d-%b-%Y", "%d-%b-%y", "%d %B %Y", "%m/%d/%Y",
]


def parse_date(date_str: str) -> Optional[str]:
    """Try to parse a date string into YYYY-MM-DD format."""
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year < 100:
                dt = dt.replace(year=dt.year + 2000)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_amount(amount_str: str) -> float:
    """Parse an amount string, handling Indian formats."""
    if not amount_str:
        return 0.0
    s = str(amount_str).strip()
    s = s.replace(",", "").replace("₹", "").replace("INR", "").replace(" ", "")
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return abs(float(s))
    except (ValueError, TypeError):
        return 0.0


def categorize_transaction(description: str) -> tuple:
    """Auto-categorize a transaction based on description keywords."""
    desc = description.lower()

    category_rules = [
        (["salary", "payroll", "wages"], "Salary", "income"),
        (["interest", "int.cr", "int cr", "interest credit"], "Interest", "income"),
        (["dividend"], "Dividends", "income"),
        (["refund", "reversal", "cashback"], "Refund", "income"),
        (["rent", "house rent"], "Rent", "expense"),
        (["electricity", "power", "bescom", "msedcl"], "Electricity", "expense"),
        (["water", "bwssb", "water bill"], "Water", "expense"),
        (["internet", "broadband", "wifi", "airtel", "jio"], "Internet", "expense"),
        (["mobile", "recharge", "prepaid", "postpaid"], "Mobile Recharge", "expense"),
        (["insurance", "lic", "icici pru", "hdfc life", "health ins"], "Insurance", "expense"),
        (["emi", "loan", "home loan", "car loan", "personal loan"], "EMI", "expense"),
        (["sip", "mutual fund", "mf", "elss"], "SIP", "investment"),
        (["ppf", "provident fund"], "PPF", "investment"),
        (["nps", "national pension"], "NPS", "investment"),
        (["fd", "fixed deposit"], "Fixed Deposit", "investment"),
        (["gold", "sovereign gold", "sgb"], "Gold", "investment"),
        (["grocery", "groceries", "bigbasket", "blinkit", "zepto"], "Groceries", "expense"),
        (["swiggy", "zomato", "food", "restaurant", "dining"], "Food & Dining", "expense"),
        (["uber", "ola", "rapido", "taxi", "cab"], "Transport", "expense"),
        (["petrol", "diesel", "fuel", "hp", "iocl", "bpcl"], "Fuel", "expense"),
        (["amazon", "flipkart", "myntra", "shopping"], "Shopping", "expense"),
        (["netflix", "hotstar", "prime", "spotify", "subscription"], "Subscriptions", "expense"),
        (["hospital", "medical", "pharmacy", "medicine", "doctor"], "Health", "expense"),
        (["school", "college", "tuition", "education", "course"], "Education", "expense"),
        (["irctc", "train", "railway"], "Travel", "expense"),
        (["flight", "airline", "indigo", "spicejet", "air india"], "Travel", "expense"),
        (["atm", "cash withdrawal", "self"], "Transport", "expense"),
        (["upi", "neft", "rtgs", "imps", "transfer"], "Transport", "expense"),
    ]

    for keywords, category, txn_type in category_rules:
        if any(kw in desc for kw in keywords):
            return category, txn_type

    return "Other", "expense"


def detect_header_columns(headers: list) -> dict:
    """Detect which columns contain date, description, debit, credit, balance."""
    mapping = {"date": -1, "description": -1, "debit": -1, "credit": -1, "balance": -1}
    for i, h in enumerate(headers):
        hl = str(h).lower().strip()
        if any(k in hl for k in ["date", "txn date", "transaction date", "value date", "posting date"]):
            if mapping["date"] == -1:
                mapping["date"] = i
        elif any(k in hl for k in ["narration", "description", "particulars", "details", "remarks", "transaction details", "transaction remarks"]):
            mapping["description"] = i
        elif any(k in hl for k in ["withdrawal", "debit", "dr", "debit amount", "withdrawal amt", "withdrawal amount"]):
            mapping["debit"] = i
        elif any(k in hl for k in ["deposit", "credit", "cr", "credit amount", "deposit amt", "deposit amount"]):
            mapping["credit"] = i
        elif any(k in hl for k in ["balance", "closing balance", "running balance"]):
            mapping["balance"] = i
        elif any(k in hl for k in ["amount"]):
            if mapping["debit"] == -1:
                mapping["debit"] = i
    return mapping


def parse_csv_statement(content: str) -> list:
    """Parse a CSV bank statement."""
    transactions = []
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return []

    # Find header row
    header_idx = 0
    mapping = {}
    for i, row in enumerate(rows[:10]):
        test_mapping = detect_header_columns(row)
        if test_mapping["date"] >= 0 and (test_mapping["debit"] >= 0 or test_mapping["credit"] >= 0):
            header_idx = i
            mapping = test_mapping
            break

    if not mapping or mapping["date"] < 0:
        raise ValueError("Could not detect column headers in CSV. Please ensure the file has Date, Description, Debit/Credit columns.")

    for row in rows[header_idx + 1:]:
        if len(row) <= max(v for v in mapping.values() if v >= 0):
            continue

        date_str = row[mapping["date"]] if mapping["date"] >= 0 else ""
        date = parse_date(date_str)
        if not date:
            continue

        description = row[mapping["description"]].strip() if mapping["description"] >= 0 else ""
        if not description:
            continue

        # Bank's perspective amounts
        bank_debit = parse_amount(row[mapping["debit"]]) if mapping["debit"] >= 0 else 0
        bank_credit = parse_amount(row[mapping["credit"]]) if mapping["credit"] >= 0 else 0

        if bank_debit == 0 and bank_credit == 0:
            continue

        transactions.append({
            "date": date,
            "description": description,
            "bank_debit": bank_debit,
            "bank_credit": bank_credit,
        })

    return transactions


def parse_excel_statement(file_bytes: bytes) -> list:
    """Parse an Excel bank statement."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active
    transactions = []

    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell) if cell is not None else "" for cell in row])

    if not rows:
        return []

    header_idx = 0
    mapping = {}
    for i, row in enumerate(rows[:10]):
        test_mapping = detect_header_columns(row)
        if test_mapping["date"] >= 0 and (test_mapping["debit"] >= 0 or test_mapping["credit"] >= 0):
            header_idx = i
            mapping = test_mapping
            break

    if not mapping or mapping["date"] < 0:
        raise ValueError("Could not detect column headers in Excel. Please ensure the file has Date, Description, Debit/Credit columns.")

    for row in rows[header_idx + 1:]:
        if len(row) <= max(v for v in mapping.values() if v >= 0):
            continue

        date_str = row[mapping["date"]] if mapping["date"] >= 0 else ""
        date = parse_date(date_str)
        if not date:
            continue

        description = row[mapping["description"]].strip() if mapping["description"] >= 0 else ""
        if not description:
            continue

        bank_debit = parse_amount(row[mapping["debit"]]) if mapping["debit"] >= 0 else 0
        bank_credit = parse_amount(row[mapping["credit"]]) if mapping["credit"] >= 0 else 0

        if bank_debit == 0 and bank_credit == 0:
            continue

        transactions.append({
            "date": date,
            "description": description,
            "bank_debit": bank_debit,
            "bank_credit": bank_credit,
        })

    return transactions


def parse_pdf_statement(file_bytes: bytes) -> list:
    """Parse a PDF bank statement using pdfplumber."""
    import pdfplumber
    transactions = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        all_rows = []
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        cleaned = [str(cell).strip() if cell else "" for cell in row]
                        all_rows.append(cleaned)

        if not all_rows:
            # Try text extraction as fallback
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    for line in text.split("\n"):
                        parts = line.split()
                        if len(parts) >= 3:
                            all_rows.append(parts)

    if not all_rows:
        raise ValueError("Could not extract any data from the PDF. The file may be scanned/image-based.")

    header_idx = 0
    mapping = {}
    for i, row in enumerate(all_rows[:15]):
        test_mapping = detect_header_columns(row)
        if test_mapping["date"] >= 0 and (test_mapping["debit"] >= 0 or test_mapping["credit"] >= 0):
            header_idx = i
            mapping = test_mapping
            break

    if not mapping or mapping["date"] < 0:
        raise ValueError("Could not detect column headers in PDF. The statement format may not be supported.")

    for row in all_rows[header_idx + 1:]:
        if len(row) <= max(v for v in mapping.values() if v >= 0):
            continue

        date_str = row[mapping["date"]] if mapping["date"] >= 0 else ""
        date = parse_date(date_str)
        if not date:
            continue

        description = row[mapping["description"]].strip() if mapping["description"] >= 0 else ""
        if not description:
            continue

        bank_debit = parse_amount(row[mapping["debit"]]) if mapping["debit"] >= 0 else 0
        bank_credit = parse_amount(row[mapping["credit"]]) if mapping["credit"] >= 0 else 0

        if bank_debit == 0 and bank_credit == 0:
            continue

        transactions.append({
            "date": date,
            "description": description,
            "bank_debit": bank_debit,
            "bank_credit": bank_credit,
        })

    return transactions


@router.post("/bank-statements/upload")
async def upload_bank_statement(
    file: UploadFile = File(...),
    bank_name: str = Form(""),
    account_name: str = Form(""),
    user=Depends(get_current_user),
):
    """
    Upload a bank statement (PDF/CSV/Excel) and import transactions.
    
    Reverses bank's debit/credit to user's perspective:
    - Bank Credit (deposit) → User: Dr. Bank A/c, Cr. Income A/c
    - Bank Debit (withdrawal) → User: Dr. Expense A/c, Cr. Bank A/c
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
            raw_txns = parse_pdf_statement(file_bytes)
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
        dek = user.get("encryption_key", "")
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
            # PERSPECTIVE REVERSAL:
            # Bank Credit (deposit to account) → User receives money → Income/Receipt
            # Bank Debit (withdrawal from account) → User pays money → Expense/Payment
            if raw["bank_credit"] > 0:
                # Bank credited user → deposit → user's income/receipt
                txn_type = "income"
                amount = raw["bank_credit"]
                category, _ = categorize_transaction(raw["description"])
                if category == "Other":
                    category = "Other"
            else:
                # Bank debited user → withdrawal → user's expense/payment
                txn_type = "expense"
                amount = raw["bank_debit"]
                category, cat_type = categorize_transaction(raw["description"])
                if cat_type == "investment":
                    txn_type = "investment"

            if amount <= 0:
                skipped += 1
                continue

            # Check for duplicate (same date, similar amount, similar description)
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

            # Auto-create journal entry (user's perspective)
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
        "message": f"Statement processed successfully",
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
    # Count transactions imported from statements per bank account
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
