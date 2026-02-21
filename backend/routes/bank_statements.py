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
    "yes": ["yes bank", "yes"],
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
        "yes": ["yes bank"],
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


def clean_yesbank_description(raw_desc: str) -> str:
    """Clean up Yes Bank transaction description."""
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
    }
    
    lower_desc = desc.lower()
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # IMPS format: IMPS/Purpose/Name/Account/RRN/Bank
    if desc.startswith('IMPS/'):
        parts = desc.split('/')
        # Name is usually the 3rd part
        if len(parts) >= 3:
            name = parts[2].strip()
            if name and len(name) > 2 and any(c.isalpha() for c in name):
                return f"IMPS - {name.title()}"
        return "IMPS Transfer"
    
    # Funds Transfer
    if 'funds trf to' in lower_desc:
        return "Funds Transfer Out"
    if 'funds trf from' in lower_desc:
        return "Funds Transfer In"
    
    # UPI
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        if len(parts) >= 3:
            name = parts[2].strip()
            if name and len(name) > 2:
                return f"UPI - {name.title()}"
        return "UPI Transfer"
    
    # NEFT
    if 'neft' in lower_desc:
        return "NEFT Transfer"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def parse_yesbank_pdf(pdf, all_text: str) -> list:
    """
    Parse Yes Bank PDF statement.
    Yes Bank format: Reference No | Transaction Date | Credited Amount | Debited Amount | Balance | Description
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or len(row) < 5:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header and empty rows
                first_col = cleaned[0].lower()
                if not cleaned[0] or 'reference' in first_col or 'date' in first_col:
                    continue
                if first_col in ('', 'empty'):
                    continue
                
                # Yes Bank has date in column 1 (not column 0 which is Reference No)
                date_str = cleaned[1] if len(cleaned) > 1 else ""
                # Remove time portion if present (e.g., "2022-12-04 09:01:00" -> "2022-12-04")
                if ' ' in date_str:
                    date_str = date_str.split(' ')[0]
                
                date = parse_date(date_str)
                if not date:
                    continue
                
                # Get credit and debit amounts (columns 2 and 3)
                bank_credit = parse_amount(cleaned[2]) if len(cleaned) > 2 else 0
                bank_debit = parse_amount(cleaned[3]) if len(cleaned) > 3 else 0
                
                # Get description (column 5)
                description = cleaned[5] if len(cleaned) > 5 else ""
                if not description:
                    description = "Bank Transaction"
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_yesbank_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def clean_hdfc_description(raw_desc: str) -> str:
    """Clean up HDFC Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    # Known merchants
    known_merchants = {
        'amazon': 'Amazon',
        'flipkart': 'Flipkart',
        'swiggy': 'Swiggy',
        'zomato': 'Zomato',
        'paytm': 'Paytm',
        'uber': 'Uber',
        'ola': 'Ola',
        'vodafone': 'Vodafone',
        'airtel': 'Airtel',
        'jio': 'Jio',
        'reliance': 'Reliance',
    }
    
    lower_desc = desc.lower()
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            if 'pos' in lower_desc:
                return f"Card - {name}"
            return f"Payment - {name}"
    
    # UPI format: UPI-refno-upiid-ref-OK
    if desc.startswith('UPI-'):
        # Try to extract payee from UPI ID
        parts = desc.split('-')
        if len(parts) >= 3:
            upi_id = parts[2]
            if '@' in upi_id:
                name = upi_id.split('@')[0]
                return f"UPI - {name.title()}"
        return "UPI Transfer"
    
    # IMPS format: IMPS-ref-Name-Bank-Account-Purpose
    if desc.startswith('IMPS-'):
        parts = desc.split('-')
        if len(parts) >= 3:
            name = parts[2]
            if name and any(c.isalpha() for c in name):
                return f"IMPS - {name.title()}"
        return "IMPS Transfer"
    
    # NEFT format: NEFTDR-Bank-Name-NETBANK...
    if desc.startswith('NEFTDR') or desc.startswith('NEFT-'):
        parts = desc.split('-')
        for part in parts:
            # Look for person/company name (alphanumeric, not a bank code)
            if len(part) > 3 and part.isalpha():
                return f"NEFT - {part.title()}"
        return "NEFT Transfer"
    
    # EMI payment
    if desc.startswith('EMI'):
        return "EMI Payment"
    
    # ACH debit
    if desc.startswith('ACHD-') or desc.startswith('ACH-'):
        parts = desc.split('-')
        if len(parts) >= 2:
            company = parts[1]
            return f"Auto-debit - {company.title()}"
        return "Auto-debit"
    
    # Bill payment
    if 'BILLPAY' in desc:
        if 'HDFCPE' in desc:
            return "HDFC CC Payment"
        if 'SBICARDS' in desc:
            return "SBI Card Payment"
        if 'KOTAK' in desc:
            return "Kotak Card Payment"
        return "Bill Payment"
    
    # POS transaction (card swipe)
    if desc.startswith('POS') or 'POSDEBIT' in desc:
        # Try to extract merchant name
        parts = desc.split('XXXXXX')
        if len(parts) > 1:
            merchant = parts[-1].replace('POSDEBIT', '').strip()
            if merchant:
                return f"Card - {merchant.title()}"
        return "Card Purchase"
    
    # Interest credit
    if 'INTEREST' in desc.upper() or 'CREDITINTEREST' in desc:
        return "Interest Credit"
    
    # Cash deposit
    if 'CASHDEP' in desc or 'CASH DEP' in desc:
        return "Cash Deposit"
    
    # ATM
    if 'ATM' in desc.upper():
        if 'DEP' in desc.upper():
            return "ATM Deposit"
        return "ATM Withdrawal"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def clean_pnb_description(raw_desc: str) -> str:
    """Clean up PNB Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    lower_desc = desc.lower()
    
    # SMS charges
    if 'sms chrg' in lower_desc or 'smsch' in lower_desc:
        return "SMS Charges"
    
    # Interest credit
    if 'intt.' in lower_desc or 'interest' in lower_desc:
        return "Interest Credit"
    
    # Transfer from account
    if desc.startswith('Transfer From'):
        # Extract name if present
        parts = desc.split('SHREE')
        if len(parts) > 1:
            return "NEFT - Shree Shyamjee Transport"
        return "NEFT Inward"
    
    # NEFT IN
    if 'NEFT IN' in desc:
        # Try to extract company name
        parts = desc.split(':')
        if len(parts) >= 2:
            company = parts[1].strip()
            if company:
                return f"NEFT - {company.title()}"
        return "NEFT Inward"
    
    # NEFT OUT
    if 'NEFT OUT' in desc:
        parts = desc.split(':')
        if len(parts) >= 2:
            name = parts[1].strip()
            if name:
                return f"NEFT - {name.title()}"
        return "NEFT Outward"
    
    # RTGS
    if 'RTGS' in desc.upper():
        if 'RTGS To' in desc:
            return "RTGS Outward"
        if 'RTGS From' in desc:
            parts = desc.split('/')
            if len(parts) >= 2:
                company = parts[-1].strip()
                return f"RTGS - {company.title()}"
            return "RTGS Inward"
        return "RTGS Transfer"
    
    # IMPS
    if 'IMPS' in desc.upper():
        return "IMPS Transfer"
    
    # Cash Withdrawal
    if 'cash withdrawal' in lower_desc:
        return "Cash Withdrawal"
    
    # TRF (Transfer)
    if desc.startswith('TRF '):
        name = desc[4:].strip()
        return f"Transfer - {name.title()}"
    
    # PMSBY (Insurance)
    if 'PMSBY' in desc.upper():
        return "PMSBY Insurance"
    
    # Clearing
    if 'CLEARING' in desc.upper():
        return "Cheque Clearing"
    
    # ACH / Auto-debit
    if desc.startswith('ACH/'):
        parts = desc.split('/')
        if len(parts) >= 2:
            company = parts[1].strip()
            return f"Auto-debit - {company.title()}"
        return "Auto-debit"
    
    # LIC
    if 'lic of india' in lower_desc:
        return "LIC Premium"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def clean_idbi_description(raw_desc: str) -> str:
    """Clean up IDBI Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    lower_desc = desc.lower()
    
    # Known merchants
    known_merchants = {
        'phonepe': 'PhonePe',
        'paytm': 'Paytm',
        'amazon': 'Amazon',
        'flipkart': 'Flipkart',
        'swiggy': 'Swiggy',
        'zomato': 'Zomato',
        'uber': 'Uber',
        'bharatpe': 'BharatPe',
    }
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # UPI format: UPI/refno/Name
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        if len(parts) >= 3:
            name = parts[2].strip()
            if name and any(c.isalpha() for c in name):
                return f"UPI - {name.title()}"
        return "UPI Transfer"
    
    # VISA-POS (Card transactions)
    if desc.startswith('VISA-POS/'):
        merchant = desc[9:].split('/')[0].strip()
        return f"Card - {merchant.title()}"
    
    # ATM Withdrawal
    if desc.startswith('ATMWDL') or 'ATM' in desc.upper():
        return "ATM Charges"
    
    # NEFT
    if desc.startswith('NEFT'):
        parts = desc.split('-')
        if len(parts) >= 2:
            name = parts[-1].strip()
            return f"NEFT - {name.title()}"
        return "NEFT Transfer"
    
    # IMPS
    if desc.startswith('IMPS'):
        parts = desc.split('/')
        if len(parts) >= 2:
            name = parts[-1].strip()
            return f"IMPS - {name.title()}"
        return "IMPS Transfer"
    
    # IPAY/ESHP (E-Shop payment)
    if desc.startswith('IPAY/ESHP'):
        return "Online Payment"
    
    # ACH Payment
    if desc.startswith('ACH') or 'achpfm' in lower_desc:
        parts = desc.split('-')
        if len(parts) >= 2:
            purpose = parts[1].strip()
            return f"ACH - {purpose.title()}"
        return "ACH Payment"
    
    # CA Keeping Charges
    if 'ca keeping' in lower_desc or 'keeping chgs' in lower_desc:
        return "Account Maintenance Charges"
    
    # Cash deposit/withdrawal at branch
    if desc.startswith('BN') or desc.startswith('ID064') or desc.startswith('ID130'):
        return "Branch Transaction"
    
    # REF (Refund)
    if desc.startswith('REF\\') or desc.startswith('REF/'):
        return "Refund"
    
    # Interest
    if 'interest' in lower_desc or 'int.' in lower_desc:
        return "Interest Credit"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def clean_canara_description(raw_desc: str) -> str:
    """Clean up Canara Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    lower_desc = desc.lower()
    
    # Cash BNA (Cash Deposit via machine)
    if 'cash-bna' in lower_desc or 'cash bna' in lower_desc:
        return "Cash Deposit (BNA)"
    
    # Cheque Book Issue
    if 'chq bk issue' in lower_desc:
        return "Cheque Book Issue Charges"
    
    # RTGS Credit
    if desc.startswith('RTGS Cr'):
        parts = desc.split('-')
        for part in parts:
            if len(part) > 5 and part.isupper() and ' ' in part:
                return f"RTGS - {part.title()}"
        return "RTGS Inward"
    
    # NEFT Credit
    if desc.startswith('NEFT Cr'):
        parts = desc.split('-')
        for part in parts:
            if len(part) > 5 and any(c.isalpha() for c in part) and not part.startswith('ICIC') and not part.startswith('HDFC'):
                clean_part = part.strip()
                if clean_part and not clean_part.startswith('N0'):
                    return f"NEFT - {clean_part.title()}"
        return "NEFT Inward"
    
    # Funds Transfer Debit
    if 'funds transfer debit' in lower_desc:
        parts = desc.split('-')
        if len(parts) >= 2:
            name = parts[-1].strip()
            return f"Transfer - {name.title()}"
        return "Funds Transfer"
    
    # Self transfer
    if desc.lower().startswith('self'):
        parts = desc.split('-')
        if len(parts) >= 2:
            name = parts[0].replace('self', '').strip()
            if name:
                return f"Self - {name.title()}"
        return "Self Transfer"
    
    # Cheque Return
    if 'chq return' in lower_desc or 'i/w chq return' in lower_desc:
        return "Cheque Return"
    
    # Cheque Return Charges
    if 'chq rtn chg' in lower_desc:
        return "Cheque Return Charges"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def clean_union_description(raw_desc: str) -> str:
    """Clean up Union Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    lower_desc = desc.lower()
    
    # UPI Debit: UPIAR/refno/DR/Name/Bank
    if desc.startswith('UPIAR/'):
        parts = desc.split('/')
        for i, part in enumerate(parts):
            if part == 'DR' and i+1 < len(parts):
                name = parts[i+1].strip()
                if name and any(c.isalpha() for c in name):
                    return f"UPI - {name.title()}"
        return "UPI Transfer"
    
    # UPI Credit: UPIAB/refno/CR/Name/Bank
    if desc.startswith('UPIAB/'):
        parts = desc.split('/')
        for i, part in enumerate(parts):
            if part == 'CR' and i+1 < len(parts):
                name = parts[i+1].strip()
                if name and any(c.isalpha() for c in name):
                    return f"UPI - {name.title()}"
        return "UPI Transfer"
    
    # NEFT
    if desc.startswith('NEFT:'):
        name = desc[5:].strip().split('\n')[0]
        return f"NEFT - {name.title()}"
    
    # Mobile Fund Transfer
    if desc.startswith('MOBFT to:'):
        name = desc[9:].strip().split('/')[0]
        return f"IMPS - {name.title()}"
    
    # MAND DR (Mandate Debit / Auto-debit)
    if 'mand dr' in lower_desc:
        return "Auto-debit"
    
    # General Charges
    if 'general charges' in lower_desc:
        return "Service Charges"
    
    # Interest credit
    if 'int.pd' in lower_desc or ':int.' in lower_desc:
        return "Interest Credit"
    
    # SMS Charges
    if 'sms charges' in lower_desc:
        return "SMS Charges"
    
    # POS (Card purchase)
    if desc.startswith('POS:'):
        merchant = desc[4:].split('/')[0].strip()
        return f"Card - {merchant.title()}"
    
    # ATM
    if 'atm' in lower_desc:
        return "ATM Withdrawal"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def clean_kotak_description(raw_desc: str) -> str:
    """Clean up Kotak Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    lower_desc = desc.lower()
    
    # Known merchants
    known_merchants = {
        'paytm': 'Paytm',
        'phonepe': 'PhonePe',
        'bajaj finance': 'Bajaj Finance',
        'ullu digital': 'Ullu',
        'cashfree': 'Cashfree',
        'razorecom': 'Razorpay',
    }
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # UPI format: UPI/Name/refno/Purpose
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        if len(parts) >= 2:
            name = parts[1].strip()
            if name and any(c.isalpha() for c in name):
                return f"UPI - {name.title()}"
        return "UPI Transfer"
    
    # IMPS
    if desc.startswith('IMPS-') or desc.startswith('Recd:IMPS'):
        parts = desc.replace('Recd:IMPS/', '').replace('IMPS-', '').split('/')
        if parts:
            name = parts[0].strip()
            if name and any(c.isalpha() for c in name):
                return f"IMPS - {name.title()}"
        return "IMPS Transfer"
    
    # NEFT
    if 'NEFT' in desc.upper():
        parts = desc.split(' ')
        for part in parts:
            if len(part) > 5 and part.isupper() and part not in ('NEFT', 'NEFTINW'):
                return f"NEFT - {part.title()}"
        return "NEFT Transfer"
    
    # Own Transfer
    if 'own transfer' in lower_desc:
        return "Own Account Transfer"
    
    # Cash Deposit
    if 'cash deposit' in lower_desc:
        return "Cash Deposit"
    
    # OS (Online Services / Payment Gateway)
    if desc.startswith('OS '):
        merchant = desc[3:].split(' ')[0]
        return f"Payment - {merchant.title()}"
    
    # Chrg / Charges
    if desc.startswith('Chrg:') or desc.startswith('Rem Chrgs:'):
        return "Bank Charges"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def parse_kotak_pdf(pdf, all_text: str) -> list:
    """
    Parse Kotak Bank PDF statement.
    Supports two formats:
    - Format 1 (Text-based): Date | Narration | Chq/Ref No | Amount(Dr/Cr) | Balance
    - Format 2 (Table-based): # | TRANSACTION | DETAILS | REF | DEBIT | CREDIT | BALANCE
    """
    transactions = []
    
    # Try table-based parsing first (Format 2)
    table_txns = parse_kotak_table_format(pdf)
    if table_txns:
        return table_txns
    
    # Fall back to text-based parsing (Format 1)
    return parse_kotak_text_format(pdf, all_text)


def parse_kotak_table_format(pdf) -> list:
    """Parse Kotak Format 2 (table-based)."""
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Check if this is a transaction table
            first_row = [str(c).lower() if c else "" for c in table[0]]
            if 'transaction' not in ' '.join(first_row):
                continue
            
            for row in table[1:]:
                if not row or len(row) < 6:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header rows
                if cleaned[0] == '#' or not cleaned[0]:
                    continue
                
                # Parse date (column 1 - "DD Mon YYYY HH:MM AM/PM")
                date_str = cleaned[1].split(' ')[0:3]  # Get "DD Mon YYYY"
                date_str = ' '.join(date_str)
                date = parse_date(date_str)
                if not date:
                    continue
                
                # Get description (column 2)
                description = cleaned[2] if len(cleaned) > 2 else ""
                if not description:
                    continue
                
                # Get debit and credit (columns 4 and 5)
                debit_str = cleaned[4] if len(cleaned) > 4 else ""
                credit_str = cleaned[5] if len(cleaned) > 5 else ""
                
                # Kotak uses - prefix for debit and + prefix for credit
                bank_debit = parse_amount(debit_str.replace('-', '').replace('+', ''))
                bank_credit = parse_amount(credit_str.replace('-', '').replace('+', ''))
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_kotak_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_kotak_text_format(pdf, all_text: str) -> list:
    """Parse Kotak text-based formats (both Format 1 and Format 2)."""
    transactions = []
    
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Format 1: Line starts with date DD-MM-YYYY
            if re.match(r'^\d{2}-\d{2}-\d{4}', line):
                date_str = line[:10]
                date = parse_date(date_str)
                
                if date:
                    # Combine multi-line entries
                    full_line = line
                    j = i + 1
                    while j < len(lines) and j < i + 5:
                        next_line = lines[j].strip()
                        if re.match(r'^\d{2}-\d{2}-\d{4}', next_line):
                            break
                        if '(Dr)' in next_line or '(Cr)' in next_line:
                            full_line += ' ' + next_line
                            break
                        full_line += ' ' + next_line
                        j += 1
                    
                    # Extract amount with Dr/Cr
                    amount_match = re.search(r'([\d,]+\.?\d*)\s*\((Dr|Cr)\)', full_line)
                    if amount_match:
                        amount = parse_amount(amount_match.group(1))
                        is_credit = amount_match.group(2) == 'Cr'
                        
                        desc_end = full_line.find(amount_match.group(0))
                        description = full_line[10:desc_end].strip()
                        
                        if amount > 0:
                            transactions.append({
                                'date': date,
                                'description': clean_kotak_description(description),
                                'bank_debit': 0 if is_credit else amount,
                                'bank_credit': amount if is_credit else 0,
                            })
            
            # Format 2: Line starts with serial number then DD Mon YYYY
            elif re.match(r'^\d+\s+\d{2}\s+\w{3}\s+\d{4}', line):
                parts = line.split()
                if len(parts) >= 5:
                    # Date is parts[1:4]
                    date_str = ' '.join(parts[1:4])
                    date = parse_date(date_str)
                    
                    if date:
                        # Find amounts with +/- prefix AND decimal point (to avoid matching ref numbers)
                        # Pattern: +/-number,number.decimal
                        amount_matches = re.findall(r'([+-][\d,]+\.\d{2})\b', line)
                        
                        if amount_matches:
                            # The transaction amount is the one with +/- prefix
                            for amt_str in amount_matches:
                                is_credit = amt_str.startswith('+')
                                amount = parse_amount(amt_str.replace('+', '').replace('-', ''))
                                
                                if amount > 0:
                                    # Get description - between date and first amount
                                    desc_start = line.find(parts[3]) + len(parts[3]) + 1
                                    desc_end = line.find(amt_str)
                                    if desc_end > desc_start:
                                        description = line[desc_start:desc_end].strip()
                                        # Remove reference numbers
                                        description = re.sub(r'\b[A-Z]{2,}-?\d+\b', '', description).strip()
                                        description = re.sub(r'\s+', ' ', description)
                                    else:
                                        description = line[desc_start:].strip()
                                    
                                    transactions.append({
                                        'date': date,
                                        'description': clean_kotak_description(description),
                                        'bank_debit': 0 if is_credit else amount,
                                        'bank_credit': amount if is_credit else 0,
                                    })
                                    break  # Only take first amount per line
            
            i += 1
    
    return transactions


def parse_union_pdf(pdf, all_text: str) -> list:
    """
    Parse Union Bank PDF statement.
    Supports both formats:
    - Old format: S.No | Date | Transaction Id | Remarks | Amount(Rs.) | Balance(Rs.)
    - New format: Tran Id | Tran Date | Remarks | Amount (Rs.) | Balance (Rs.)
    
    Amount has (Dr) or (Cr) suffix for debit/credit.
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or len(row) < 4:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header rows and empty rows
                first_col = cleaned[0].lower()
                if 'tran' in first_col or 's.no' in first_col or not cleaned[0]:
                    continue
                if 'scan' in first_col or 'account' in first_col or 'closing' in first_col:
                    continue
                
                # Detect format based on row structure
                # Old format: S.No (number) | Date | Tran Id | Remarks | Amount | Balance
                # New format: Tran Id (alphanumeric) | Date | Remarks | Amount | Balance
                
                date_col = 1  # Default for old format
                remarks_col = 3  # Default for old format
                amount_col = 4  # Default for old format
                
                # Check if first column is a serial number (old format) or transaction ID (new format)
                if cleaned[0].isdigit() and len(cleaned[0]) <= 4:
                    # Old format with S.No
                    date_col = 1
                    remarks_col = 3
                    amount_col = 4
                elif cleaned[0].startswith('S') and len(cleaned[0]) > 4:
                    # New format with Transaction ID
                    date_col = 1
                    remarks_col = 2
                    amount_col = 3
                else:
                    continue
                
                # Parse date
                date = parse_date(cleaned[date_col])
                if not date:
                    continue
                
                # Get description
                description = cleaned[remarks_col] if len(cleaned) > remarks_col else ""
                if not description:
                    continue
                
                # Get amount with Dr/Cr indicator
                amount_str = cleaned[amount_col] if len(cleaned) > amount_col else ""
                if not amount_str:
                    continue
                
                # Parse amount and determine debit/credit
                is_credit = '(cr)' in amount_str.lower()
                is_debit = '(dr)' in amount_str.lower()
                
                # Remove the Dr/Cr indicator before parsing
                amount_clean = amount_str.replace('(Dr)', '').replace('(Cr)', '').replace('(dr)', '').replace('(cr)', '').strip()
                amount = parse_amount(amount_clean)
                
                if amount == 0:
                    continue
                
                if is_credit:
                    bank_credit = amount
                    bank_debit = 0
                else:
                    bank_debit = amount
                    bank_credit = 0
                
                transactions.append({
                    'date': date,
                    'description': clean_union_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_canara_pdf(pdf, all_text: str) -> list:
    """
    Parse Canara Bank PDF statement.
    Canara format: Txn Date | Value Date | Cheque No. | Description | Branch Code | Debit | Credit | Balance
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Check if this is a transaction table
            first_row = [str(c).lower() if c else "" for c in table[0]]
            is_txn_table = 'txn date' in first_row[0] or 'date' in first_row[0]
            
            start_idx = 1 if is_txn_table else 0
            
            for row in table[start_idx:]:
                if not row or len(row) < 7:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header and page rows
                first_col = cleaned[0].lower()
                if 'txn date' in first_col or 'page' in first_col or not cleaned[0]:
                    continue
                
                # Parse date (DD-MM-YYYY HH:MM:SS format)
                date_str = cleaned[0].split(' ')[0] if ' ' in cleaned[0] else cleaned[0]
                date = parse_date(date_str)
                if not date:
                    continue
                
                # Get description (column 3)
                description = cleaned[3] if len(cleaned) > 3 else ""
                if not description:
                    continue
                
                # Get debit and credit (columns 5 and 6)
                bank_debit = parse_amount(cleaned[5]) if len(cleaned) > 5 else 0
                bank_credit = parse_amount(cleaned[6]) if len(cleaned) > 6 else 0
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_canara_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_idbi_pdf(pdf, all_text: str) -> list:
    """
    Parse IDBI Bank PDF statement.
    IDBI format: Srl | Txn Date | Value Date | Description | Cheque No | CR/DR | CCY | Amount (INR) | Balance (INR)
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or len(row) < 7:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header rows
                first_col = cleaned[0].lower()
                if 'srl' in first_col or 'txn' in first_col or not cleaned[0]:
                    continue
                
                # Skip if first column is not a serial number
                if not cleaned[0].isdigit():
                    continue
                
                # Parse date (column 1 - Txn Date with timestamp)
                date_str = cleaned[1].split(' ')[0] if ' ' in cleaned[1] else cleaned[1]
                date = parse_date(date_str)
                if not date:
                    continue
                
                # Get description (column 3)
                description = cleaned[3] if len(cleaned) > 3 else ""
                if not description:
                    continue
                
                # Get CR/DR indicator (column 5)
                cr_dr = cleaned[5].lower() if len(cleaned) > 5 else ""
                
                # Get amount (column 7)
                amount = parse_amount(cleaned[7]) if len(cleaned) > 7 else 0
                
                if amount == 0:
                    continue
                
                # Determine debit or credit
                if 'cr' in cr_dr:
                    bank_credit = amount
                    bank_debit = 0
                else:
                    bank_debit = amount
                    bank_credit = 0
                
                transactions.append({
                    'date': date,
                    'description': clean_idbi_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_pnb_pdf(pdf, all_text: str) -> list:
    """
    Parse PNB Bank PDF statement.
    PNB format: Date | Withdrawal | Deposit | Balance | Alpha | CHQ. NO. | Narration
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Check if this is a transaction table (has Date header)
            first_row = [str(c).lower() if c else "" for c in table[0]]
            if 'date' not in first_row[0]:
                continue
            
            for row in table[1:]:  # Skip header
                if not row or len(row) < 6:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip empty rows and page totals
                first_col = cleaned[0].lower()
                if not cleaned[0] or 'page' in first_col or 'grand' in first_col:
                    continue
                
                # Parse date (DD-MM-YYYY format)
                date = parse_date(cleaned[0])
                if not date:
                    continue
                
                # Get withdrawal and deposit (columns 1 and 2)
                bank_debit = parse_amount(cleaned[1]) if len(cleaned) > 1 else 0
                bank_credit = parse_amount(cleaned[2]) if len(cleaned) > 2 else 0
                
                # Get description (last column - Narration)
                description = cleaned[6] if len(cleaned) > 6 else cleaned[-1]
                if not description:
                    description = "Bank Transaction"
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_pnb_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_hdfc_pdf(pdf, all_text: str) -> list:
    """
    Parse HDFC Bank PDF statement using text extraction.
    HDFC format: Date | Narration | Chq./Ref.No. | ValueDt | WithdrawalAmt. | DepositAmt. | ClosingBalance
    
    HDFC's PDF table extraction is unreliable (concatenates rows), so we use text parsing.
    We determine debit/credit by tracking balance changes.
    """
    transactions = []
    prev_balance = None
    
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip non-transaction lines
            if not line or not re.match(r'^\d{2}/\d{2}/\d{2}', line):
                continue
            
            # Extract date (first 8 chars)
            date_str = line[:8]
            date = parse_date(date_str)
            if not date:
                continue
            
            # Find amounts at the end of line
            # Pattern: ValueDate Amount(s) Balance
            # Balance is always the last number, transaction amount is before it
            
            amount_pattern = re.compile(r'([\d,]+\.\d{2})')
            amounts = amount_pattern.findall(line)
            
            if len(amounts) < 2:
                continue
            
            # Last amount is balance
            balance = parse_amount(amounts[-1])
            
            # Transaction amount is second-to-last (or we may have withdrawal AND deposit)
            if len(amounts) >= 3:
                # Could be: withdrawal, deposit, balance OR amount, balance
                # Check the structure
                amt1 = parse_amount(amounts[-3]) if len(amounts) >= 3 else 0
                amt2 = parse_amount(amounts[-2])
                
                # If amt1 and amt2 are both meaningful, one is withdrawal and one is deposit
                # Usually one is 0 or very small
                if amt1 > 0 and amt2 > 0:
                    # Both non-zero - likely one is the transaction, one is balance
                    # Use balance change to determine
                    if prev_balance is not None:
                        change = balance - prev_balance
                        if abs(change) > 0:
                            amount = abs(change)
                            if change > 0:
                                bank_credit = amount
                                bank_debit = 0
                            else:
                                bank_debit = amount
                                bank_credit = 0
                        else:
                            bank_debit = amt2
                            bank_credit = 0
                    else:
                        bank_debit = amt2
                        bank_credit = 0
                else:
                    # One is zero
                    if amt1 > 0:
                        bank_debit = amt1
                        bank_credit = 0
                    else:
                        bank_debit = amt2
                        bank_credit = 0
            else:
                # Only 2 amounts: transaction and balance
                amount = parse_amount(amounts[-2])
                
                # Use balance change to determine debit/credit
                if prev_balance is not None:
                    change = balance - prev_balance
                    if change > 0:
                        bank_credit = amount
                        bank_debit = 0
                    else:
                        bank_debit = amount
                        bank_credit = 0
                else:
                    # No previous balance - use description hints
                    rest = line[9:].strip()
                    if any(kw in rest.upper() for kw in ['DEP', 'CREDIT', 'INTEREST', 'CASHDEP']):
                        bank_credit = amount
                        bank_debit = 0
                    else:
                        bank_debit = amount
                        bank_credit = 0
            
            # Extract description (between date and value date)
            rest = line[9:].strip()
            # Find the value date position
            value_date_match = re.search(r'\d{2}/\d{2}/\d{2}', rest)
            if value_date_match:
                description = rest[:value_date_match.start()].strip()
            else:
                description = rest[:50]
            
            if bank_debit > 0 or bank_credit > 0:
                transactions.append({
                    'date': date,
                    'description': clean_hdfc_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
            
            prev_balance = balance
    
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
        
        elif bank == "yes":
            yes_txns = parse_yesbank_pdf(pdf, all_text)
            if yes_txns:
                logger.info(f"Parsed {len(yes_txns)} transactions using Yes Bank parser")
                return yes_txns
        
        elif bank == "hdfc":
            hdfc_txns = parse_hdfc_pdf(pdf, all_text)
            if hdfc_txns:
                logger.info(f"Parsed {len(hdfc_txns)} transactions using HDFC parser")
                return hdfc_txns
        
        elif bank == "pnb":
            pnb_txns = parse_pnb_pdf(pdf, all_text)
            if pnb_txns:
                logger.info(f"Parsed {len(pnb_txns)} transactions using PNB parser")
                return pnb_txns
        
        elif bank == "idbi":
            idbi_txns = parse_idbi_pdf(pdf, all_text)
            if idbi_txns:
                logger.info(f"Parsed {len(idbi_txns)} transactions using IDBI parser")
                return idbi_txns
        
        elif bank == "canara":
            canara_txns = parse_canara_pdf(pdf, all_text)
            if canara_txns:
                logger.info(f"Parsed {len(canara_txns)} transactions using Canara parser")
                return canara_txns
        
        elif bank == "union":
            union_txns = parse_union_pdf(pdf, all_text)
            if union_txns:
                logger.info(f"Parsed {len(union_txns)} transactions using Union Bank parser")
                return union_txns
        
        elif bank == "kotak":
            kotak_txns = parse_kotak_pdf(pdf, all_text)
            if kotak_txns:
                logger.info(f"Parsed {len(kotak_txns)} transactions using Kotak parser")
                return kotak_txns
        
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
    bank_hint: str = Form(""),  # Optional bank name hint for parser selection
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
            # Pass password and bank_hint to PDF parser
            # Use explicit bank_hint if provided, otherwise use bank_name as fallback
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
