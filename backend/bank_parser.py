"""
Parser for Indian bank transaction emails and SMS messages.
Supports: HDFC, ICICI, SBI, Axis, Kotak, Yes Bank, PNB, BOB, IndusInd, IDBI
"""
import re
from datetime import datetime
from typing import Optional

BANK_PATTERNS = [
    # HDFC Bank
    {
        "bank": "HDFC",
        "debit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was )?debited\s*(?:from|to)\s*(?:a/c|account|A/c)\s*[xX*]*(\d{3,4})",
            r"debited\s*(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*from\s*(?:a/c|account)\s*[xX*]*(\d{3,4})",
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*spent\s*(?:on|at|via)\s*(.+?)(?:\s+on|\s+at|\.|$)",
        ],
        "credit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was )?credited\s*(?:to|in)\s*(?:a/c|account|A/c)\s*[xX*]*(\d{3,4})",
            r"credited\s*(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:to|in)\s*(?:a/c|account)\s*[xX*]*(\d{3,4})",
        ],
        "sender_patterns": [r"hdfc", r"hdfcbank"],
    },
    # ICICI Bank
    {
        "bank": "ICICI",
        "debit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was )?debited\s*(?:from)\s*(?:a/c|account|Acct)\s*[xX*]*(\d{3,4})",
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*spent\s*(?:on|at|using)\s*(.+?)(?:\s+on|\.|$)",
        ],
        "credit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was )?credited\s*(?:to|in)\s*(?:a/c|account|Acct)\s*[xX*]*(\d{3,4})",
        ],
        "sender_patterns": [r"icici", r"icicibank"],
    },
    # SBI
    {
        "bank": "SBI",
        "debit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |is )?debited\s*(?:from|in)\s*(?:a/c|account)\s*[xX*]*(\d{3,4})",
            r"SBI:?\s*(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*debited",
        ],
        "credit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |is )?credited\s*(?:to|in)\s*(?:a/c|account)\s*[xX*]*(\d{3,4})",
            r"SBI:?\s*(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*credited",
        ],
        "sender_patterns": [r"sbi", r"onlinesbi"],
    },
    # Axis Bank
    {
        "bank": "Axis",
        "debit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was )?debited\s*(?:from)\s*(?:a/c|account)\s*[xX*]*(\d{3,4})",
        ],
        "credit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was )?credited\s*(?:to)\s*(?:a/c|account)\s*[xX*]*(\d{3,4})",
        ],
        "sender_patterns": [r"axis", r"axisbank"],
    },
    # Kotak
    {
        "bank": "Kotak",
        "debit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was )?debited\s*(?:from)\s*(?:a/c|account)\s*[xX*]*(\d{3,4})",
        ],
        "credit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was )?credited\s*(?:to)\s*(?:a/c|account)\s*[xX*]*(\d{3,4})",
        ],
        "sender_patterns": [r"kotak", r"kotakbank"],
    },
    # Generic fallback
    {
        "bank": "Unknown",
        "debit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was |is )?debited",
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:spent|withdrawn|paid)",
        ],
        "credit": [
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:has been |was |is )?credited",
            r"(?:Rs\.?|INR)\s*([\d,]+\.?\d*)\s*(?:received|deposited)",
        ],
        "sender_patterns": [r"bank", r"neft", r"imps", r"upi"],
    },
]

DATE_PATTERNS = [
    r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{2,4})",
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
]

MERCHANT_PATTERNS = [
    r"(?:at|to|towards|for|via)\s+([A-Z][A-Za-z0-9\s&'.-]{2,30}?)(?:\s+on|\s+via|\s+ref|\.|$)",
    r"Info:\s*(.+?)(?:\.|$)",
    r"txn\s+(?:at|to)\s+(.+?)(?:\s+on|\.|$)",
]


def parse_amount(amount_str: str) -> float:
    """Parse amount string like '1,500.00' to float."""
    return float(amount_str.replace(",", ""))


def extract_date(text: str) -> Optional[str]:
    """Extract date from text and return as YYYY-MM-DD."""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
                        "%d %b %Y", "%d %b %y", "%d %B %Y", "%Y-%m-%d", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return None


def extract_merchant(text: str) -> str:
    """Extract merchant/payee name from transaction text."""
    for pattern in MERCHANT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            merchant = match.group(1).strip()
            if len(merchant) > 3:
                return merchant[:50]
    return "Bank Transaction"


def categorize_transaction(text: str, merchant: str) -> str:
    """Auto-categorize based on keywords."""
    combined = (text + " " + merchant).lower()
    categories = {
        "Food": ["swiggy", "zomato", "restaurant", "food", "cafe", "dominos", "pizza", "dining", "mcdonalds", "kfc"],
        "Shopping": ["amazon", "flipkart", "myntra", "shopping", "retail", "store", "mall"],
        "Transport": ["uber", "ola", "fuel", "petrol", "diesel", "irctc", "metro", "parking", "rapido"],
        "Utilities": ["electricity", "water", "gas", "broadband", "wifi", "internet", "phone", "recharge", "jio", "airtel"],
        "Rent": ["rent", "housing", "flat"],
        "Medical": ["hospital", "medical", "pharmacy", "doctor", "health", "apollo", "medplus"],
        "Entertainment": ["netflix", "hotstar", "spotify", "movie", "prime", "youtube"],
        "Insurance": ["insurance", "lic", "policy", "premium"],
        "Education": ["school", "college", "tuition", "course", "education", "udemy"],
        "Salary": ["salary", "payroll", "wage", "stipend"],
        "Investment": ["mutual fund", "sip", "stock", "share", "zerodha", "groww", "upstox", "mf"],
        "Transfer": ["neft", "imps", "rtgs", "upi", "transfer", "self"],
        "Groceries": ["grofers", "blinkit", "bigbasket", "grocery", "dmart", "supermarket"],
    }
    for category, keywords in categories.items():
        if any(kw in combined for kw in keywords):
            return category
    return "Others"


def parse_transaction_text(text: str, sender: str = "") -> Optional[dict]:
    """Parse a single SMS/email text and extract transaction details."""
    combined = (sender + " " + text).lower()

    for bank_config in BANK_PATTERNS:
        bank_match = any(
            re.search(p, combined) for p in bank_config["sender_patterns"]
        )
        if not bank_match and bank_config["bank"] != "Unknown":
            continue

        # Check debit patterns
        for pattern in bank_config["debit"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = parse_amount(match.group(1))
                merchant = extract_merchant(text)
                category = categorize_transaction(text, merchant)
                date = extract_date(text) or datetime.now().strftime("%Y-%m-%d")
                return {
                    "type": "expense",
                    "amount": amount,
                    "category": category,
                    "description": f"{bank_config['bank']} - {merchant}",
                    "date": date,
                    "source": "email",
                    "bank": bank_config["bank"],
                    "raw_text": text[:200],
                }

        # Check credit patterns
        for pattern in bank_config["credit"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = parse_amount(match.group(1))
                merchant = extract_merchant(text)
                category = categorize_transaction(text, merchant)
                date = extract_date(text) or datetime.now().strftime("%Y-%m-%d")
                return {
                    "type": "income",
                    "amount": amount,
                    "category": category,
                    "description": f"{bank_config['bank']} - {merchant}",
                    "date": date,
                    "source": "email",
                    "bank": bank_config["bank"],
                    "raw_text": text[:200],
                }

    return None
