"""
Bank Statement Parser & Importer

Handles PDF, CSV, and Excel bank statements from multiple Indian banks.
Supports password-protected PDFs.

Key feature: Reverses bank's debit/credit to user's perspective.

Supported Banks:
- ICICI Bank
- SBI (State Bank of India)
- HDFC Bank
- Axis Bank
- (Generic fallback for others)
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional, Tuple
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

# Supported banks with their detection keywords
SUPPORTED_BANKS = {
    "icici": ["icici", "icici bank"],
    "sbi": ["sbi", "state bank of india", "state bank"],
    "hdfc": ["hdfc", "hdfc bank"],
    "axis": ["axis", "axis bank"],
    "kotak": ["kotak", "kotak mahindra"],
    "pnb": ["pnb", "punjab national bank"],
    "bob": ["bob", "bank of baroda"],
    "canara": ["canara", "canara bank"],
    "union": ["union", "union bank"],
    "idbi": ["idbi", "idbi bank"],
    "indusind": ["indusind", "indusind bank"],
}

# Common date formats in Indian bank statements
DATE_FORMATS = [
    "%d.%m.%Y", "%d.%m.%y",  # ICICI format: 01.01.2026
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%d %b %y",
    "%d-%b-%Y", "%d-%b-%y", "%d %B %Y", "%m/%d/%Y",
]


def detect_bank(user_input: str, pdf_text: str = "") -> str:
    """Detect bank from user input or PDF content.
    User input takes priority over PDF content detection.
    """
    # First, check user input (highest priority)
    user_lower = user_input.lower().strip()
    if user_lower:
        for bank_code, keywords in SUPPORTED_BANKS.items():
            if any(kw in user_lower for kw in keywords):
                return bank_code
    
    # Then, check PDF text
    # Use smarter detection - check for statement/account headers
    pdf_lower = pdf_text.lower()
    
    # Look for specific bank statement headers
    bank_patterns = {
        "indusind": ["indusind bank", "indusind"],
        "axis": ["axis bank", "axis account", "statement of axis"],
        "icici": ["icici bank", "icici account", "statement of icici", "statement of transactions in saving account"],
        "sbi": ["state bank of india", "sbi account", "sbi statement"],
        "hdfc": ["hdfc bank", "hdfc account", "hdfc statement"],
        "kotak": ["kotak mahindra", "kotak bank"],
        "pnb": ["punjab national bank"],
        "bob": ["bank of baroda"],
    }
    
    for bank_code, patterns in bank_patterns.items():
        if any(p in pdf_lower for p in patterns):
            return bank_code
    
    # Fallback to generic keyword matching
    for bank_code, keywords in SUPPORTED_BANKS.items():
        if any(kw in pdf_lower for kw in keywords):
            return bank_code
    
    return "generic"


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


def clean_icici_description(raw_desc: str) -> str:
    """Clean up ICICI transaction description by extracting key info."""
    # Remove trailing slashes and clean up
    desc = raw_desc.strip().rstrip('/')
    
    # Known merchants to extract
    known_merchants = {
        'netflix': 'Netflix',
        'apple': 'Apple',
        'amazon': 'Amazon', 
        'uber': 'Uber',
        'swiggy': 'Swiggy',
        'zomato': 'Zomato',
        'blinkit': 'Blinkit',
        'gokiwi': 'Gokiwi',
        'shanti sto': 'Shanti Store',
        'npci': 'NPCI Cashback',
        'yash bhati': 'Yash Bhati',
        'harsh bhat': 'Self Transfer',
        'dinesh': 'Dinesh',
    }
    
    lower_desc = desc.lower()
    
    # Check for known merchants first
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # Handle descriptions that start with reference numbers (like MA/123...)
    # and contain UPI/ somewhere later
    if desc.startswith('MA/') or desc.startswith('L/'):
        if 'upi/' in lower_desc:
            parts = desc.split('/')
            for i, part in enumerate(parts):
                if part.upper() == 'UPI' and i+1 < len(parts):
                    name = parts[i+1].strip()
                    if name and len(name) > 2 and not name.startswith('@') and any(c.isalpha() for c in name):
                        if name.lower().startswith('mr ') or name.lower().startswith('ms '):
                            name = name[3:]
                        return f"UPI - {name.title()}"
        return "Bank Transfer"
    
    # Handle WITHDR (withdrawal) descriptions  
    if desc.startswith('WITHDR'):
        return "ATM/Cash Withdrawal"
    
    # Try to extract meaningful parts from UPI format
    # UPI format: UPI/Name/UPI_ID/Purpose/Bank/RefNo/...
    if 'upi/' in lower_desc:
        parts = desc.split('/')
        for i, part in enumerate(parts):
            if part.upper() == 'UPI' and i+1 < len(parts):
                name = parts[i+1].strip()
                # Clean up name - should have letters and be meaningful
                if name and len(name) > 2 and not name.startswith('@') and any(c.isalpha() for c in name):
                    # Clean common prefixes
                    if name.lower().startswith('mr ') or name.lower().startswith('ms '):
                        name = name[3:]
                    return f"UPI - {name.title()}"
    
    # IMPS/MMT format
    if 'imps/' in lower_desc or 'mmt/' in lower_desc:
        parts = desc.split('/')
        for part in parts:
            part = part.strip()
            if part and not part.isdigit() and len(part) > 3 and '@' not in part:
                if any(c.isalpha() for c in part) and not part.startswith('L'):
                    return f"IMPS - {part.title()}"
        return "IMPS Transfer"
    
    # ACH format - auto-debit
    if 'ach/' in lower_desc or '/cms/' in lower_desc:
        return "ACH - Auto-debit"
    
    # CMS - Cash Management
    if 'cms/' in lower_desc:
        return "CMS - Collection"
    
    # If starts with BANK/, it's likely a bank reference
    if desc.startswith('BANK/') or desc.startswith('Bank/'):
        return "Bank Transfer"
    
    # Fallback: return first 50 chars cleaned
    return desc[:50] if len(desc) > 50 else desc


def parse_icici_pdf_text(all_text: str) -> list:
    """
    Parse ICICI Bank PDF statement from raw text.
    ICICI format: S.No | Date (DD.MM.YYYY) | Amount | Balance on one line,
    followed by description (UPI/...) on subsequent lines.
    """
    transactions = []
    lines = all_text.split('\n')
    
    # Pattern: Line starts with S.No (digits), followed by date DD.MM.YYYY, then amounts
    # Example: "1 01.01.2026 466.00 97402.59"
    # Or with deposit: "4 03.01.2026 22500.00 119877.59"
    txn_line_pattern = re.compile(r'^(\d+)\s+(\d{2}\.\d{2}\.\d{4})\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$')
    
    current_txn = None
    description_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip header lines and non-transaction content
        if any(skip in line.lower() for skip in ['s no', 'transaction date', 'cheque number', 'legends', 'sincerly', 'team icici', 'statement of transactions']):
            if current_txn and description_lines:
                raw_desc = ' '.join(description_lines)
                current_txn['description'] = clean_icici_description(raw_desc)
                transactions.append(current_txn)
                current_txn = None
                description_lines = []
            continue
        
        match = txn_line_pattern.match(line)
        if match:
            # Save previous transaction
            if current_txn and description_lines:
                raw_desc = ' '.join(description_lines)
                current_txn['description'] = clean_icici_description(raw_desc)
                transactions.append(current_txn)
            
            # Start new transaction
            s_no, date_str, amount1, amount2 = match.groups()
            date = parse_date(date_str)
            if not date:
                continue
            
            amount1_val = parse_amount(amount1)
            amount2_val = parse_amount(amount2)
            
            # amount2 is always the balance. Determine if amount1 is debit or credit
            # by looking at subsequent lines for UPI patterns
            current_txn = {
                'date': date,
                's_no': int(s_no),
                'amount1': amount1_val,  # This is the transaction amount
                'balance': amount2_val,
                'bank_debit': 0,
                'bank_credit': 0,
            }
            description_lines = []
        elif current_txn:
            # This line is part of the description
            description_lines.append(line)
    
    # Save last transaction
    if current_txn and description_lines:
        raw_desc = ' '.join(description_lines)
        current_txn['description'] = clean_icici_description(raw_desc)
        transactions.append(current_txn)
    
    # Now determine debit/credit based on transaction type in description
    # ICICI: If balance decreases -> withdrawal (debit), if increases -> deposit (credit)
    for i, txn in enumerate(transactions):
        desc = txn.get('description', '').lower()
        amount = txn['amount1']
        
        # Check if it's a credit (deposit) based on keywords
        is_credit = any(kw in desc for kw in ['salary', 'cashback', 'refund', 'reversal', 'interest credit', 'int.cr'])
        
        # Also check by looking at balance changes between transactions
        if i > 0:
            prev_balance = transactions[i-1]['balance']
            curr_balance = txn['balance']
            balance_change = curr_balance - prev_balance
            
            if abs(balance_change - amount) < 1:
                # Balance increased by this amount -> credit (deposit)
                is_credit = True
            elif abs(balance_change + amount) < 1:
                # Balance decreased by this amount -> debit (withdrawal)
                is_credit = False
        
        if is_credit:
            txn['bank_credit'] = amount
            txn['bank_debit'] = 0
        else:
            txn['bank_debit'] = amount
            txn['bank_credit'] = 0
    
    # Clean up and return
    return [{
        'date': t['date'],
        'description': t.get('description', 'Bank Transaction'),
        'bank_debit': t['bank_debit'],
        'bank_credit': t['bank_credit'],
    } for t in transactions]


def clean_sbi_description(raw_desc: str) -> str:
    """Clean up SBI transaction description by extracting key info."""
    desc = raw_desc.strip()
    
    # Known merchants
    known_merchants = {
        'zepto': 'Zepto',
        'zomato': 'Zomato',
        'swiggy': 'Swiggy',
        'amazon': 'Amazon',
        'flipkart': 'Flipkart',
        'paytm': 'Paytm',
        'phonepe': 'PhonePe',
        'gpay': 'Google Pay',
        'netflix': 'Netflix',
        'spotify': 'Spotify',
        'uber': 'Uber',
        'ola': 'Ola',
        'rapido': 'Rapido',
        'blinkit': 'Blinkit',
    }
    
    lower_desc = desc.lower()
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # SBI UPI format: UPI/CR/refno/Name/BankCode/upiid/...
    # or UPI/DR/refno/Name/BankCode/upiid/...
    if 'upi/' in lower_desc:
        parts = desc.split('/')
        # Find the name - usually after CR or DR and ref number
        for i, part in enumerate(parts):
            if part.upper() in ('CR', 'DR') and i+2 < len(parts):
                # Skip the reference number (all digits)
                name_part = parts[i+2].strip()
                if name_part and not name_part.isdigit() and len(name_part) > 2:
                    # Clean the name
                    name_part = name_part.title()
                    return f"UPI - {name_part}"
    
    # NEFT/RTGS/IMPS transfers
    if 'neft' in lower_desc:
        return "NEFT Transfer"
    if 'rtgs' in lower_desc:
        return "RTGS Transfer"
    if 'imps' in lower_desc:
        return "IMPS Transfer"
    
    # ATM withdrawal
    if 'atm' in lower_desc or 'cash wdl' in lower_desc:
        return "ATM Withdrawal"
    
    # Interest credit
    if 'int' in lower_desc and ('cr' in lower_desc or 'credit' in lower_desc):
        return "Interest Credit"
    
    # DEP TFR / WDL TFR - strip these prefixes
    if desc.startswith('DEP TFR'):
        desc = desc[7:].strip()
    elif desc.startswith('WDL TFR'):
        desc = desc[7:].strip()
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def clean_axis_description(raw_desc: str) -> str:
    """Clean up Axis Bank transaction description."""
    # First, always clean newlines and extra spaces
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    # Known merchants
    known_merchants = {
        'zepto': 'Zepto',
        'zomato': 'Zomato',
        'swiggy': 'Swiggy',
        'amazon': 'Amazon',
        'flipkart': 'Flipkart',
        'paytm': 'Paytm',
        'phonepe': 'PhonePe',
        'gpay': 'Google Pay',
        'netflix': 'Netflix',
        'spotify': 'Spotify',
        'uber': 'Uber',
        'ola': 'Ola',
        'groww': 'Groww',
        'cashfree': 'Cashfree',
        'meesho': 'Meesho',
        'pennydrop': 'Penny Drop',
    }
    
    lower_desc = desc.lower()
    
    # Check for known merchants first
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # ATM withdrawal
    if 'atm-cash' in lower_desc or 'atm cash' in lower_desc:
        return "ATM Withdrawal"
    
    # NEFT transfer - extract name
    if desc.startswith('NEFT'):
        if 'salary' in lower_desc:
            return "NEFT - Salary"
        # Try to extract company/person name after the reference number
        parts = desc.split('-')
        for part in parts:
            part = part.strip()
            # Look for company names (all caps, multiple words)
            if part and len(part) > 3 and part.isupper() and ' ' not in part:
                if part not in ('NEFT', 'CR', 'DR'):
                    return f"NEFT - {part.title()}"
        return "NEFT Transfer"
    
    # IMPS transfer
    if desc.startswith('IMPS'):
        parts = desc.split('/')
        for part in parts:
            part = part.strip()
            if part and len(part) > 3 and any(c.isalpha() for c in part) and not part.isdigit():
                if part not in ('IMPS', 'P2A', 'P2M'):
                    return f"IMPS - {part.title()}"
        return "IMPS Transfer"
    
    # ACH (Auto-debit)
    if 'ach-dr' in lower_desc or 'ach dr' in lower_desc:
        return "ACH - Auto-debit"
    
    # UPI format: UPI/P2A/refno/Name/Bank or UPI/P2M/refno/Name/Bank
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        # Find name - usually 4th part (after UPI, P2A/P2M, refno)
        if len(parts) >= 4:
            name = parts[3].strip()
            if name and len(name) > 2 and any(c.isalpha() for c in name):
                # Clean up name (remove bank suffix if present)
                name = name.split('/')[0].strip()
                return f"UPI - {name.title()}"
    
    # Interest credit
    if 'int.pd' in lower_desc or 'interest' in lower_desc:
        return "Interest Credit"
    
    # Credit adjustment
    if 'cradj' in lower_desc:
        return "UPI Reversal/Refund"
    
    # Return first 50 chars (already cleaned of newlines)
    return desc[:50] if len(desc) > 50 else desc


def parse_axis_pdf(pdf, all_text: str) -> list:
    """
    Parse Axis Bank PDF statement.
    Axis format: Tran Date | Chq No | Particulars | Debit | Credit | Balance | Init. Br
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row or len(row) < 6:
                    continue
                
                # Clean the row - replace newlines with spaces
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header and empty rows
                if not cleaned[0] or 'tran date' in cleaned[0].lower() or 'opening balance' in ' '.join(cleaned).lower():
                    continue
                
                # Parse date (DD-MM-YYYY format)
                date = parse_date(cleaned[0])
                if not date:
                    continue
                
                # Get description (column 2 - Particulars)
                description = cleaned[2] if len(cleaned) > 2 else ""
                if not description:
                    continue
                
                # Get debit and credit (columns 3 and 4)
                bank_debit = parse_amount(cleaned[3]) if len(cleaned) > 3 else 0
                bank_credit = parse_amount(cleaned[4]) if len(cleaned) > 4 else 0
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_axis_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def clean_indusind_description(raw_desc: str) -> str:
    """Clean up IndusInd Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    # Known merchants
    known_merchants = {
        'paytm': 'Paytm',
        'phonepe': 'PhonePe',
        'gpay': 'Google Pay',
        'amazon': 'Amazon',
        'flipkart': 'Flipkart',
        'swiggy': 'Swiggy',
        'zomato': 'Zomato',
        'uber': 'Uber',
        'ola': 'Ola',
        'slice': 'Slice',
        'liquiloans': 'Liquiloans',
    }
    
    lower_desc = desc.lower()
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # UPI format: UPI/refno/CR or DR/Name/Bank/upiid
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        # Find CR or DR and get the name after it
        for i, part in enumerate(parts):
            if part in ('CR', 'DR') and i+1 < len(parts):
                name = parts[i+1].strip()
                if name and len(name) > 2 and any(c.isalpha() for c in name):
                    return f"UPI - {name.title()}"
    
    # IMPS format: IMPS/P2A/refno/Bank/Name
    if desc.startswith('IMPS/'):
        parts = desc.split('/')
        # Name is usually the last meaningful part
        for part in reversed(parts):
            part = part.strip()
            if part and len(part) > 3 and any(c.isalpha() for c in part):
                if part not in ('IMPS', 'P2A', 'P2M'):
                    return f"IMPS - {part.title()}"
        return "IMPS Transfer"
    
    # TRF FRM - Transfer from another account
    if 'trf frm' in lower_desc:
        return "Internal Transfer"
    
    # NEFT transfer
    if desc.startswith('N/') or 'neft' in lower_desc:
        # Try to extract company name
        parts = desc.split('/')
        for part in parts:
            if len(part) > 5 and part.isupper() and ' ' in part:
                return f"NEFT - {part.title()}"
        return "NEFT Transfer"
    
    # MC POS TXN - Card transaction
    if 'mc pos txn' in lower_desc or 'pos txn' in lower_desc:
        return "Card Purchase"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def parse_indusind_pdf(pdf, all_text: str) -> list:
    """
    Parse IndusInd Bank PDF statement.
    IndusInd format varies by page:
    - Page 1: Date | Particulars | Chq./Ref.No. | Withdrawl | Deposit | Balance
    - Page 2+: Date | Particulars | Ref | EMPTY | Withdrawl/Deposit | Withdrawl/Deposit | Balance
    
    We detect debit vs credit by looking at /DR/ or /CR/ in the description.
    """
    transactions = []
    
    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or len(row) < 5:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header and info rows
                first_col = cleaned[0].lower()
                if not cleaned[0] or 'date' in first_col or 'indusind' in first_col:
                    continue
                if 'rajesh' in first_col or 'account' in first_col or 'page' in first_col:
                    continue
                if first_col in ('empty', ''):
                    continue
                
                # Parse date (DD-Mon-YYYY format like 02-Oct-2023)
                date = parse_date(cleaned[0])
                if not date:
                    continue
                
                # Get description (column 1 - Particulars)
                description = cleaned[1] if len(cleaned) > 1 else ""
                if not description:
                    continue
                
                # Determine debit or credit from description pattern
                is_debit = '/DR/' in description or '/dr/' in description
                is_credit = '/CR/' in description or '/cr/' in description or 'TRF FRM' in description
                
                # Find the amount - look for non-empty numeric value in columns 3-6
                amount = 0
                for i in range(3, min(7, len(cleaned))):
                    val = parse_amount(cleaned[i])
                    if val > 0:
                        amount = val
                        break
                
                if amount == 0:
                    continue
                
                # Assign to debit or credit
                if is_debit:
                    bank_debit = amount
                    bank_credit = 0
                elif is_credit:
                    bank_debit = 0
                    bank_credit = amount
                else:
                    # For IMPS without clear indicator, check description keywords
                    if 'IMPS/P2A' in description:
                        # P2A is usually incoming
                        bank_credit = amount
                        bank_debit = 0
                    else:
                        # Default to debit
                        bank_debit = amount
                        bank_credit = 0
                
                transactions.append({
                    'date': date,
                    'description': clean_indusind_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_sbi_pdf(pdf, all_text: str) -> list:
    """
    Parse SBI Bank PDF statement.
    SBI format: Uses table extraction with columns:
    Txn Date | Value Date | Description | Ref/Cheque | Debit | Credit | Balance
    """
    transactions = []
    
    # SBI uses table extraction
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row or len(row) < 6:
                    continue
                
                # Clean the row
                cleaned = [str(cell).strip().replace('\n', ' ') if cell else "" for cell in row]
                
                # Skip header rows
                if any(h in cleaned[0].lower() for h in ['date', 'txn', 'balance', '']):
                    if 'balance' in ' '.join(cleaned).lower():
                        continue
                
                # Try to parse date from first column
                date = parse_date(cleaned[0])
                if not date:
                    continue
                
                # Get description (usually 3rd column)
                description = cleaned[2] if len(cleaned) > 2 else ""
                if not description:
                    continue
                
                # Get debit and credit (columns 4 and 5 typically)
                # SBI format: col 4 = debit, col 5 = credit (or col 3 = debit, col 4 = credit)
                debit_col = 4 if len(cleaned) > 5 else 3
                credit_col = 5 if len(cleaned) > 5 else 4
                
                bank_debit = parse_amount(cleaned[debit_col]) if len(cleaned) > debit_col else 0
                bank_credit = parse_amount(cleaned[credit_col]) if len(cleaned) > credit_col else 0
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_sbi_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_pdf_statement(file_bytes: bytes, password: str = None, bank_hint: str = "") -> list:
    """
    Parse a PDF bank statement using pdfplumber.
    Supports password-protected PDFs.
    
    Args:
        file_bytes: PDF file content
        password: Optional password for encrypted PDFs
        bank_hint: User-provided bank name hint for parser selection
    """
    import pdfplumber
    transactions = []
    
    # Try to open PDF, with or without password
    try:
        if password:
            pdf = pdfplumber.open(io.BytesIO(file_bytes), password=password)
        else:
            pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as e:
        error_str = str(e).lower()
        error_type = type(e).__name__
        
        # Check for password-protected PDF
        if 'password' in error_str or 'encrypted' in error_str or 'pdfminer' in error_type.lower():
            if not password:
                raise ValueError("This PDF is password-protected. Please provide the password in the 'PDF Password' field.")
            else:
                raise ValueError("Incorrect PDF password. Please check and try again.")
        raise ValueError(f"Could not open PDF: {str(e) or 'Unknown error'}")
    
    with pdf:
        # Extract all text for bank detection
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"
        
        # Detect bank
        bank = detect_bank(bank_hint, all_text)
        logger.info(f"Detected bank: {bank}")
        
        # Use bank-specific parser
        if bank == "sbi":
            transactions = parse_sbi_pdf(pdf, all_text)
            if transactions:
                logger.info(f"Parsed {len(transactions)} transactions using SBI parser")
                return transactions
        
        elif bank == "icici":
            icici_txns = parse_icici_pdf_text(all_text)
            if icici_txns:
                logger.info(f"Parsed {len(icici_txns)} transactions using ICICI parser")
                return icici_txns
        
        elif bank == "axis":
            axis_txns = parse_axis_pdf(pdf, all_text)
            if axis_txns:
                logger.info(f"Parsed {len(axis_txns)} transactions using Axis parser")
                return axis_txns
        
        elif bank == "indusind":
            indusind_txns = parse_indusind_pdf(pdf, all_text)
            if indusind_txns:
                logger.info(f"Parsed {len(indusind_txns)} transactions using IndusInd parser")
                return indusind_txns
        
        # Standard table-based parsing for other banks
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
    password: str = Form(""),  # Optional password for encrypted PDFs
    user=Depends(get_current_user),
):
    """
    Upload a bank statement (PDF/CSV/Excel) and import transactions.
    Supports password-protected PDFs.
    
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
            # Pass password and bank_name hint to PDF parser
            raw_txns = parse_pdf_statement(file_bytes, password=password or None, bank_hint=bank_name)
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
