"""
Credit Card Statement Parser — Completely Separate from Bank Statement Logic
=============================================================================
CC Statements are fundamentally different from bank statements:

BANK STATEMENT:
  - Bank Account is an ASSET
  - Deposit (Credit in bank ledger) → Dr. Bank A/c, Cr. Income/Transfer
  - Withdrawal (Debit in bank ledger) → Dr. Expense, Cr. Bank A/c

CREDIT CARD STATEMENT:
  - Credit Card is a LIABILITY (you owe money to the bank)
  - Purchase (Debit in CC ledger = you spent) → Dr. Expense, Cr. CC Payable
  - Payment (Credit in CC ledger = you paid) → Dr. CC Payable, Cr. Bank A/c
  - Interest/Fee (Debit in CC ledger) → Dr. Finance Charges, Cr. CC Payable
  - Cashback/Reward (Credit in CC ledger) → Dr. CC Payable, Cr. Other Income

Supported Issuers:
  - HDFC Credit Card
  - ICICI Credit Card
  - SBI Card (State Bank of India)
  - Axis Bank Credit Card
  - Kotak Credit Card
  - IndusInd Credit Card
  - Standard Chartered
  - Generic fallback (works for most tabular statements)
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone, date
from database import db
from auth import get_current_user
import io
import csv
import re
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# ── Date formats common in Indian CC statements ──────────────────────────────
DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%d %b %Y", "%d-%b-%Y", "%d %b %y", "%d-%b-%y",
    "%d.%m.%Y", "%d.%m.%y",
    "%Y-%m-%d", "%m/%d/%Y", "%d %B %Y",
]


def parse_date(raw: str) -> Optional[str]:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def clean_amount(raw: str) -> float:
    """Remove currency symbols, commas and parse float."""
    cleaned = re.sub(r"[₹,\s]", "", str(raw)).strip()
    cleaned = cleaned.replace("Dr", "").replace("Cr", "").replace("dr", "").replace("cr", "")
    try:
        return abs(float(cleaned))
    except ValueError:
        return 0.0


def is_credit_entry(desc: str, raw_amount: str = "") -> bool:
    """Return True if this is a payment/cashback/credit (reduces CC liability)."""
    desc_lower = (desc or "").lower()
    raw_lower = (raw_amount or "").lower()

    credit_patterns = [
        "payment", "payment received", "payment thankyou", "thank you",
        "payment - thank", "online payment", "neft payment", "rtgs payment",
        "imps payment", "upi payment", "cashback", "cash back", "reward",
        "reward redemption", "refund", "reversal", "waiver", "credit",
        "returned", "cancelled", "adjusted",
    ]
    for p in credit_patterns:
        if p in desc_lower:
            return True
    if "cr" in raw_lower or raw_lower.endswith("cr"):
        return True
    return False


def auto_categorize_cc(description: str) -> str:
    """Auto-categorize a CC transaction from its description."""
    desc = description.lower()
    rules = [
        (["zomato", "swiggy", "dominos", "mcdonald", "kfc", "pizza", "cafe", "restaurant", "food", "dining", "uber eats", "blinkit groceries"], "Food & Dining"),
        (["amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho", "shopping", "mall", "store", "retail"], "Shopping"),
        (["makemytrip", "irctc", "spicejet", "indigo", "airasia", "ola", "uber", "rapido", "yatra", "goibibo", "hotel", "airbnb", "flight", "train", "travel"], "Travel"),
        (["netflix", "prime", "hotstar", "spotify", "youtube", "jio", "airtel", "recharge", "subscription", "apple music", "zee5", "sonyliv", "canva", "adobe"], "Subscriptions"),
        (["electricity", "water", "gas", "broadband", "internet", "utility", "bill pay", "bsnl", "tata sky", "d2h"], "Utilities"),
        (["hospital", "pharmacy", "apollo", "medplus", "1mg", "netmeds", "doctor", "clinic", "healthcare", "med", "health"], "Healthcare"),
        (["hp", "bharat petroleum", "iocl", "fuel", "petrol", "diesel", "bpcl"], "Fuel"),
        (["emi", "equated", "loan", "bajaj", "hdfc loan", "iciciloan", "tata capital"], "EMI"),
        (["school", "college", "university", "coaching", "udemy", "coursera", "education", "fees"], "Education"),
        (["insurance", "lic", "premium", "policy", "star health", "hdfc life"], "Insurance"),
        (["payment", "payment received", "cashback", "refund", "reversal"], "Payment"),
        (["atm", "cash advance", "cash withdrawal"], "Cash Advance"),
        (["interest", "finance charge", "late fee", "annual fee", "joining fee", "overlimit", "penalty"], "Fees & Charges"),
    ]
    for keywords, category in rules:
        if any(k in desc for k in keywords):
            return category
    return "Other"


# ─────────────────────────────────────────────────────────────────────────────
# ISSUER DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_cc_issuer(text: str, hint: str = "") -> str:
    hint_lower = hint.lower()
    text_lower = text.lower()

    issuer_map = {
        "hdfc": "HDFC",
        "icici": "ICICI",
        "sbi": "SBI",
        "axis": "AXIS",
        "kotak": "KOTAK",
        "indusind": "INDUSIND",
        "standard chartered": "SC",
        "stanchart": "SC",
        "rbl": "RBL",
        "yes bank": "YES",
        "idfc": "IDFC",
        "amex": "AMEX",
        "american express": "AMEX",
        "citibank": "CITI",
        "citi": "CITI",
        "hsbc": "HSBC",
    }

    for key, code in issuer_map.items():
        if key in hint_lower or key in text_lower:
            return code
    return "GENERIC"


# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSER  (uses pdfplumber already installed)
# ─────────────────────────────────────────────────────────────────────────────

def parse_cc_pdf(file_bytes: bytes, password: Optional[str] = None, issuer_hint: str = "") -> List[Dict]:
    try:
        import pdfplumber
    except ImportError:
        raise ValueError("pdfplumber not installed. Run: pip install pdfplumber")

    open_kwargs = {"password": password} if password else {}
    transactions = []

    with pdfplumber.open(io.BytesIO(file_bytes), **open_kwargs) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        issuer = detect_cc_issuer(full_text, issuer_hint)
        logger.info(f"CC PDF detected issuer: {issuer}")

        # Try table extraction first (works for most structured PDFs)
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                parsed = _parse_cc_table(table, issuer)
                transactions.extend(parsed)

        # Fallback to text-line parsing if tables yielded nothing
        if not transactions:
            transactions = _parse_cc_text_lines(full_text, issuer)

    return transactions


def _parse_cc_table(table: list, issuer: str) -> List[Dict]:
    """Parse a table (list of row lists) extracted from CC PDF."""
    if not table or len(table) < 2:
        return []

    # Find header row
    header_idx = 0
    for i, row in enumerate(table):
        row_text = " ".join(str(c).lower() for c in row if c)
        if any(k in row_text for k in ["date", "transaction", "narration", "description", "amount", "debit", "credit"]):
            header_idx = i
            break

    headers = [str(h).lower().strip() if h else "" for h in table[header_idx]]
    results = []

    for row in table[header_idx + 1:]:
        if not row or all(not c for c in row):
            continue

        cells = [str(c).strip() if c else "" for c in row]
        txn = _map_cc_row_to_txn(headers, cells, issuer)
        if txn:
            results.append(txn)

    return results


def _map_cc_row_to_txn(headers: list, cells: list, issuer: str) -> Optional[Dict]:
    """Map a CC statement table row to a transaction dict."""
    data = dict(zip(headers, cells))

    # Find date
    raw_date = ""
    for key in ["date", "transaction date", "txn date", "trans date", "posting date", "value date"]:
        if key in data and data[key]:
            raw_date = data[key]
            break
    if not raw_date:
        # Try first cell as date
        if cells:
            raw_date = cells[0]

    parsed_date = parse_date(raw_date)
    if not parsed_date:
        return None

    # Find description
    description = ""
    for key in ["narration", "description", "transaction details", "transaction description",
                "details", "particulars", "merchant", "remarks", "transaction"]:
        if key in data and data[key]:
            description = data[key]
            break
    if not description:
        # Try second cell
        if len(cells) > 1:
            description = cells[1]

    if not description or len(description.strip()) < 2:
        return None

    # Find amounts
    debit_amount = 0.0
    credit_amount = 0.0
    txn_type = "purchase"

    # Check for separate debit/credit columns
    debit_keys = ["debit", "dr", "debit (inr)", "domestic debit", "amount (dr)", "withdrawal"]
    credit_keys = ["credit", "cr", "credit (inr)", "domestic credit", "amount (cr)", "payment", "deposit"]
    amount_keys = ["amount", "transaction amount", "inr amount", "amt", "rs.", "₹"]

    for key in debit_keys:
        if key in data and data[key] and clean_amount(data[key]) > 0:
            debit_amount = clean_amount(data[key])
            break

    for key in credit_keys:
        if key in data and data[key] and clean_amount(data[key]) > 0:
            credit_amount = clean_amount(data[key])
            break

    # If no separate columns, try combined amount column
    if debit_amount == 0 and credit_amount == 0:
        for key in amount_keys:
            if key in data and data[key]:
                raw_val = str(data[key])
                amount = clean_amount(raw_val)
                if amount > 0:
                    if is_credit_entry(description, raw_val):
                        credit_amount = amount
                    else:
                        debit_amount = amount
                break

    # Determine transaction type
    amount = 0.0
    if credit_amount > 0:
        amount = credit_amount
        txn_type = "payment" if is_credit_entry(description, "") else "cashback"
    elif debit_amount > 0:
        amount = debit_amount
        # Further classify debit
        desc_lower = description.lower()
        if any(k in desc_lower for k in ["interest", "finance charge", "late fee", "annual fee", "joining fee", "penalty", "overlimit"]):
            txn_type = "fee"
        elif any(k in desc_lower for k in ["emi", "equated monthly"]):
            txn_type = "emi"
        elif any(k in desc_lower for k in ["cash advance", "atm"]):
            txn_type = "cash_advance"
        else:
            txn_type = "purchase"
    else:
        return None

    if amount <= 0:
        return None

    category = auto_categorize_cc(description)
    if txn_type in ("payment", "cashback"):
        category = "Payment" if txn_type == "payment" else "Cashback"
    elif txn_type == "fee":
        category = "Fees & Charges"

    return {
        "date": parsed_date,
        "description": description.strip(),
        "amount": round(amount, 2),
        "type": txn_type,
        "category": category,
        "raw_date": raw_date,
    }


def _parse_cc_text_lines(text: str, issuer: str) -> List[Dict]:
    """Fallback: Parse CC transactions from raw PDF text lines."""
    transactions = []
    lines = text.split("\n")

    # Date pattern matcher
    date_pattern = re.compile(
        r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})\b"
    )
    amount_pattern = re.compile(r"[\d,]+\.\d{2}")

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        # Skip header/footer lines
        skip_words = ["statement", "opening balance", "closing balance", "total", "page",
                      "carry forward", "credit limit", "available", "minimum due", "payment due"]
        if any(w in line.lower() for w in skip_words):
            continue

        date_match = date_pattern.search(line)
        if not date_match:
            continue

        parsed_date = parse_date(date_match.group())
        if not parsed_date:
            continue

        amounts = amount_pattern.findall(line)
        if not amounts:
            continue

        # Description is text between date and amount
        desc_start = date_match.end()
        last_amount_pos = line.rfind(amounts[-1])
        description = line[desc_start:last_amount_pos].strip()
        if not description:
            description = line

        # Use last amount (usually the transaction amount, not running balance)
        amount = clean_amount(amounts[-1] if len(amounts) >= 1 else amounts[0])
        if amount <= 0:
            continue

        is_credit = is_credit_entry(description, line)
        txn_type = "payment" if is_credit else "purchase"

        # Check for Dr/Cr suffix in the line
        if re.search(r"\bCr\b", line):
            txn_type = "payment" if is_credit_entry(description) else "cashback"
        elif re.search(r"\bDr\b", line):
            txn_type = "purchase"

        category = auto_categorize_cc(description)

        transactions.append({
            "date": parsed_date,
            "description": description.strip(),
            "amount": round(amount, 2),
            "type": txn_type,
            "category": category,
        })

    return transactions


# ─────────────────────────────────────────────────────────────────────────────
# CSV PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_cc_csv(content: str, issuer_hint: str = "") -> List[Dict]:
    """Parse CC statement CSV. Handles most Indian bank CC CSV exports."""
    reader = csv.DictReader(io.StringIO(content))

    # Normalize headers
    raw_headers = reader.fieldnames or []
    header_map = {h.lower().strip().replace(" ", "_"): h for h in raw_headers}
    issuer = detect_cc_issuer(" ".join(raw_headers), issuer_hint)

    transactions = []
    for row in reader:
        # Normalize row keys
        norm_row = {k.lower().strip().replace(" ", "_"): v for k, v in row.items()}

        # Date
        raw_date = ""
        for key in ["date", "transaction_date", "txn_date", "trans._date", "value_date", "posting_date"]:
            if key in norm_row and norm_row[key]:
                raw_date = norm_row[key]
                break

        parsed_date = parse_date(raw_date)
        if not parsed_date:
            continue

        # Description
        description = ""
        for key in ["narration", "description", "transaction_details", "transaction_description",
                    "details", "particulars", "merchant_name", "remarks"]:
            if key in norm_row and norm_row[key]:
                description = norm_row[key]
                break

        if not description:
            continue

        # Amounts
        debit = 0.0
        credit = 0.0
        for key in ["debit", "dr", "debit_amount", "withdrawal", "amount_(dr)", "domestic_debit"]:
            if key in norm_row and norm_row[key]:
                debit = clean_amount(norm_row[key])
                if debit > 0:
                    break

        for key in ["credit", "cr", "credit_amount", "payment", "amount_(cr)", "domestic_credit"]:
            if key in norm_row and norm_row[key]:
                credit = clean_amount(norm_row[key])
                if credit > 0:
                    break

        # Combined amount column fallback
        if debit == 0 and credit == 0:
            for key in ["amount", "transaction_amount", "inr_amount", "amt"]:
                if key in norm_row and norm_row[key]:
                    raw_val = norm_row[key]
                    amt = clean_amount(raw_val)
                    if amt > 0:
                        if is_credit_entry(description, raw_val):
                            credit = amt
                        else:
                            debit = amt
                    break

        amount = 0.0
        txn_type = "purchase"
        if credit > 0:
            amount = credit
            txn_type = "payment" if is_credit_entry(description) else "cashback"
        elif debit > 0:
            amount = debit
            desc_lower = description.lower()
            if any(k in desc_lower for k in ["interest", "finance charge", "late fee", "annual fee", "penalty"]):
                txn_type = "fee"
            elif any(k in desc_lower for k in ["emi", "equated"]):
                txn_type = "emi"
            else:
                txn_type = "purchase"

        if amount <= 0:
            continue

        category = auto_categorize_cc(description)
        if txn_type == "payment":
            category = "Payment"
        elif txn_type == "cashback":
            category = "Cashback"
        elif txn_type == "fee":
            category = "Fees & Charges"

        transactions.append({
            "date": parsed_date,
            "description": description.strip(),
            "amount": round(amount, 2),
            "type": txn_type,
            "category": category,
        })

    return transactions


# ─────────────────────────────────────────────────────────────────────────────
# DOUBLE-ENTRY BOOKKEEPING FOR CC TRANSACTIONS
# (Completely separate from bank statement accounting)
# ─────────────────────────────────────────────────────────────────────────────

CC_JOURNAL_MAP = {
    # txn_type → (debit_account, credit_account, description)
    "purchase":     (None,                      "Credit Card Payable",  "CC Purchase"),
    "emi":          ("EMI Expenses",             "Credit Card Payable",  "CC EMI Payment"),
    "fee":          ("Finance Charges",          "Credit Card Payable",  "CC Fee/Interest"),
    "cash_advance": ("Cash",                     "Credit Card Payable",  "CC Cash Advance"),
    "payment":      ("Credit Card Payable",      None,                   "CC Payment"),
    "cashback":     ("Credit Card Payable",      "Other Income",         "CC Cashback"),
}

EXPENSE_CATEGORY_ACCOUNT = {
    "Food & Dining":    "Food Expenses",
    "Shopping":         "Shopping Expenses",
    "Travel":           "Travel Expenses",
    "Utilities":        "Utility Bills",
    "Healthcare":       "Medical Expenses",
    "Fuel":             "Fuel Expenses",
    "Subscriptions":    "Subscription Expenses",
    "Education":        "Education Expenses",
    "Insurance":        "Insurance Premium",
    "Entertainment":    "Entertainment Expenses",
    "Fees & Charges":   "Finance Charges",
    "Other":            "Miscellaneous Expenses",
}


async def create_cc_journal_entry(txn: dict, user_id: str, card_name: str, bank_account_name: str = "Bank Account"):
    """Create a double-entry journal for a CC transaction."""
    txn_type = txn.get("type", "purchase")
    amount = txn["amount"]
    date = txn["date"]
    description = txn["description"]
    category = txn.get("category", "Other")

    mapping = CC_JOURNAL_MAP.get(txn_type, CC_JOURNAL_MAP["purchase"])
    dr_account_template, cr_account_template, default_desc = mapping

    cc_payable_account = f"CC Payable - {card_name}"

    if txn_type == "purchase" or txn_type in ("emi", "fee", "cash_advance"):
        # Purchases: Dr. [Expense Account], Cr. CC Payable
        dr_account = EXPENSE_CATEGORY_ACCOUNT.get(category, "Miscellaneous Expenses")
        cr_account = cc_payable_account
    elif txn_type == "payment":
        # Payment: Dr. CC Payable, Cr. Bank Account
        dr_account = cc_payable_account
        cr_account = bank_account_name
    elif txn_type == "cashback":
        # Cashback: Dr. CC Payable, Cr. Other Income
        dr_account = cc_payable_account
        cr_account = "Other Income"
    else:
        dr_account = EXPENSE_CATEGORY_ACCOUNT.get(category, "Miscellaneous Expenses")
        cr_account = cc_payable_account

    now = datetime.now(timezone.utc).isoformat()
    journal_id = str(uuid4())

    journal_doc = {
        "id": journal_id,
        "user_id": user_id,
        "date": date,
        "narration": description,
        "source": "cc_statement",
        "entries": [
            {"account": dr_account, "type": "debit", "amount": amount},
            {"account": cr_account, "type": "credit", "amount": amount},
        ],
        "created_at": now,
    }

    await db.journal_entries.insert_one(journal_doc)
    journal_doc.pop("_id", None)
    return journal_doc


# ─────────────────────────────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/cc-statements/upload")
async def upload_cc_statement(
    file: UploadFile = File(...),
    card_id: str = Form(""),
    issuer: str = Form(""),       # e.g., "HDFC", "ICICI", "SBI"
    billing_period: str = Form(""),  # e.g., "Jan 2026"
    password: str = Form(""),
    create_journal: str = Form("true"),
    bank_account_for_payments: str = Form(""),
    user=Depends(get_current_user),
):
    """
    Upload a credit card statement and import transactions.

    This is COMPLETELY SEPARATE from bank statement upload:
    - Transactions go to credit_card_transactions collection
    - Double-entry uses CC Payable (LIABILITY) account, not Bank account
    - CC purchases: Dr. Expense → Cr. CC Payable
    - CC payments: Dr. CC Payable → Cr. Bank A/c
    """
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("csv", "xlsx", "xls", "pdf"):
        raise HTTPException(400, f"Unsupported format .{ext}. Use PDF, CSV, or Excel.")

    file_bytes = await file.read()
    if len(file_bytes) > 15 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum 15MB.")

    user_id = user["id"]

    # Resolve card info
    card_name = "Credit Card"
    if card_id:
        card_doc = await db.credit_cards.find_one({"id": card_id, "user_id": user_id}, {"_id": 0})
        if card_doc:
            card_name = card_doc.get("card_name", "Credit Card")
    
    # Resolve bank account for payment entries
    bank_acc_name = bank_account_for_payments or "Bank Account"
    if not bank_account_for_payments:
        default_bank = await db.bank_accounts.find_one({"user_id": user_id, "is_default": True}, {"_id": 0})
        if default_bank:
            bank_acc_name = default_bank.get("account_name", "Bank Account")

    # ── Parse Statement ──────────────────────────────────────────────────────
    try:
        if ext == "pdf":
            raw_txns = parse_cc_pdf(file_bytes, password=password or None, issuer_hint=issuer)
        elif ext == "csv":
            content = file_bytes.decode("utf-8", errors="replace")
            raw_txns = parse_cc_csv(content, issuer_hint=issuer)
        elif ext in ("xlsx", "xls"):
            raw_txns = _parse_cc_excel(file_bytes, issuer_hint=issuer)
        else:
            raise HTTPException(400, "Unsupported format")
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error(f"CC statement parse error: {e}", exc_info=True)
        raise HTTPException(422, f"Failed to parse CC statement: {str(e)}")

    if not raw_txns:
        raise HTTPException(422, "No transactions found. Check the file format or try selecting the issuer manually.")

    # ── Deduplicate & Save ───────────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    import_id = str(uuid4())
    saved = 0
    duplicates = 0
    journal_count = 0
    should_journal = create_journal.lower() in ("true", "1", "yes")

    for txn in raw_txns:
        # Deduplication: same card, date, description, amount
        existing = await db.credit_card_transactions.find_one({
            "user_id": user_id,
            "card_id": card_id,
            "date": txn["date"],
            "description": txn["description"],
            "amount": txn["amount"],
        })
        if existing:
            duplicates += 1
            continue

        txn_id = str(uuid4())
        doc = {
            "id": txn_id,
            "user_id": user_id,
            "card_id": card_id,
            "card_name": card_name,
            "date": txn["date"],
            "description": txn["description"],
            "merchant": txn.get("merchant", ""),
            "amount": txn["amount"],
            "type": txn["type"],
            "category": txn["category"],
            "billing_period": billing_period,
            "import_id": import_id,
            "source": "statement",
            "is_emi": txn["type"] == "emi",
            "is_sip": False,
            "flagged_for_review": txn["type"] in ("emi",),
            "created_at": now,
        }
        await db.credit_card_transactions.insert_one(doc)
        saved += 1

        # Create journal entry
        if should_journal:
            try:
                await create_cc_journal_entry(txn, user_id, card_name, bank_acc_name)
                journal_count += 1
            except Exception as e:
                logger.warning(f"Journal creation failed for CC txn: {e}")

    # ── Save import history ──────────────────────────────────────────────────
    history_doc = {
        "id": import_id,
        "user_id": user_id,
        "card_id": card_id,
        "card_name": card_name,
        "issuer": issuer or "Auto-detected",
        "filename": file.filename,
        "billing_period": billing_period,
        "total_parsed": len(raw_txns),
        "saved": saved,
        "duplicates": duplicates,
        "journal_entries_created": journal_count,
        "imported_at": now,
    }
    await db.cc_statement_history.insert_one(history_doc)

    return {
        "success": True,
        "import_id": import_id,
        "card_name": card_name,
        "total_parsed": len(raw_txns),
        "saved": saved,
        "duplicates": duplicates,
        "journal_entries_created": journal_count,
        "message": f"Imported {saved} transactions ({duplicates} duplicates skipped). {journal_count} journal entries created.",
    }


@router.get("/cc-statements/history")
async def get_cc_statement_history(
    card_id: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Get CC statement import history for the user."""
    query = {"user_id": user["id"]}
    if card_id:
        query["card_id"] = card_id

    cursor = db.cc_statement_history.find(query, {"_id": 0}).sort("imported_at", -1).limit(20)
    history = await cursor.to_list(20)
    return {"history": history}


# ─────────────────────────────────────────────────────────────────────────────
# EXCEL PARSER
# ─────────────────────────────────────────────────────────────────────────────

def _parse_cc_excel(file_bytes: bytes, issuer_hint: str = "") -> List[Dict]:
    """Parse CC statement from Excel (.xlsx/.xls)."""
    try:
        import openpyxl
    except ImportError:
        raise ValueError("openpyxl not installed.")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    # Find header row
    header_idx = 0
    for i, row in enumerate(rows[:15]):
        row_text = " ".join(str(c).lower() for c in row if c)
        if any(k in row_text for k in ["date", "narration", "amount", "debit", "credit"]):
            header_idx = i
            break

    headers = [str(h).lower().strip() if h else "" for h in rows[header_idx]]
    transactions = []

    for row in rows[header_idx + 1:]:
        if not row or all(c is None for c in row):
            continue
        cells = [str(c).strip() if c is not None else "" for c in row]
        txn = _map_cc_row_to_txn(headers, cells, detect_cc_issuer("", issuer_hint))
        if txn:
            transactions.append(txn)

    return transactions
