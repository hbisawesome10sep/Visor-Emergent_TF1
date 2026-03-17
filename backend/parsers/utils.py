"""
Bank Statement Parser Utilities
Common functions for detecting banks, parsing dates/amounts, and categorizing transactions.
"""
import re
from typing import Optional
from datetime import datetime


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
    "%d.%m.%Y", "%d.%m.%y",
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%d %b %y",
    "%d-%b-%Y", "%d-%b-%y", "%d %B %Y", "%m/%d/%Y",
]


def detect_bank(user_input: str, pdf_text: str = "") -> str:
    """Detect bank from user input or PDF content."""
    user_lower = user_input.lower().strip()
    if user_lower:
        for bank_code, keywords in SUPPORTED_BANKS.items():
            if any(kw in user_lower for kw in keywords):
                return bank_code

    pdf_lower = pdf_text.lower()
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
    s = s.replace(",", "").replace("\u20b9", "").replace("INR", "").replace(" ", "")
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return abs(float(s))
    except (ValueError, TypeError):
        return 0.0


def categorize_transaction(description: str, is_credit: bool = False) -> tuple:
    """Auto-categorize a transaction based on description keywords."""
    desc = description.lower()

    category_rules = [
        (["salary", "payroll", "wages", "stipend"], "Salary", "income"),
        (["interest", "int.cr", "int cr", "interest credit", "int.pd", "interest paid", "int credit"], "Interest", "income"),
        (["dividend", "div credit"], "Dividends", "income"),
        (["refund", "reversal", "cashback", "cash back", "refund credit"], "Refund", "income"),
        (["rent received", "rental income"], "Rental Income", "income"),
        (["neft cr", "neft credit", "imps cr", "imps credit", "rtgs cr"], "Bank Transfer In", "income"),
        (["swiggy", "zomato", "food", "restaurant", "dining", "cafe", "pizza",
          "burger", "mcdonald", "kfc", "domino", "starbucks", "chaayos", "haldiram",
          "barbeque", "biryani", "hotel", "dhaba", "eatery"], "Food & Dining", "expense"),
        (["grocery", "groceries", "bigbasket", "blinkit", "zepto", "instamart",
          "dmart", "d-mart", "d mart", "more supermarket", "reliance fresh", "spencer",
          "nature basket", "jiomart", "kirana", "vegetables", "fruits", "supermarket"], "Groceries", "expense"),
        (["uber", "ola", "rapido", "taxi", "cab", "auto", "rickshaw"], "Transport", "expense"),
        (["petrol", "diesel", "fuel", "hp petrol", "iocl", "bpcl", "indian oil",
          "bharat petroleum", "hindustan petroleum", "shell", "essar"], "Fuel", "expense"),
        (["irctc", "train", "railway", "railways"], "Travel", "expense"),
        (["flight", "airline", "indigo", "spicejet", "air india", "vistara",
          "goair", "akasa", "makemytrip", "goibibo", "cleartrip", "yatra"], "Travel", "expense"),
        (["metro", "dmrc", "bmrc", "mmrc", "rapidx"], "Transport", "expense"),
        (["parking", "fastag", "toll"], "Transport", "expense"),
        (["electricity", "power", "bescom", "msedcl", "tata power", "adani electricity",
          "bses", "cesc", "torrent power"], "Electricity", "expense"),
        (["water", "bwssb", "water bill", "water supply"], "Water", "expense"),
        (["gas", "png", "lpg", "indane", "bharat gas", "hp gas", "mahanagar gas"], "Gas", "expense"),
        (["internet", "broadband", "wifi", "act fibernet", "hathway", "tikona"], "Internet", "expense"),
        (["recharge", "prepaid", "postpaid", "airtel", "jio", "vodafone",
          "vi ", "bsnl", "mobile recharge"], "Mobile Recharge", "expense"),
        (["dth", "tata sky", "dish tv", "airtel dth", "videocon", "sun direct"], "DTH", "expense"),
        (["netflix", "hotstar", "prime video", "amazon prime", "spotify", "gaana",
          "youtube premium", "zee5", "sonyliv", "jiocinema", "apple tv", "disney",
          "subscription", "oneplay", "apple music", "audible"], "Subscriptions", "expense"),
        (["movie", "cinema", "pvr", "inox", "bookmyshow", "paytm movie"], "Entertainment", "expense"),
        (["amazon", "flipkart", "myntra", "ajio", "meesho", "snapdeal", "tatacliq",
          "nykaa", "purplle", "mamaearth"], "Shopping", "expense"),
        (["decathlon", "croma", "reliance digital", "vijay sales"], "Shopping", "expense"),
        (["insurance", "lic", "icici pru", "hdfc life", "max life", "sbi life",
          "bajaj allianz", "health ins", "term ins", "policy"], "Insurance", "expense"),
        (["emi", "loan", "home loan", "car loan", "personal loan", "education loan",
          "bajaj finance", "hdfc credila", "tata capital"], "EMI", "expense"),
        (["sip", "mutual fund", "mf invest", "elss", "groww", "zerodha", "upstox",
          "kuvera", "paytm money", "coin by zerodha"], "SIP", "investment"),
        (["ppf", "provident fund"], "PPF", "investment"),
        (["nps", "national pension"], "NPS", "investment"),
        (["fd", "fixed deposit"], "Fixed Deposit", "investment"),
        (["gold", "sovereign gold", "sgb", "gold bond"], "Gold", "investment"),
        (["stocks", "shares", "equity", "demat"], "Stocks", "investment"),
        (["rent", "house rent", "rental", "pg rent", "hostel"], "Rent", "expense"),
        (["maintenance", "society", "apartment", "flat maintenance"], "Maintenance", "expense"),
        (["hospital", "medical", "pharmacy", "medicine", "doctor", "clinic",
          "apollo", "fortis", "max hospital", "medplus", "netmeds", "1mg",
          "pharmeasy", "truemeds", "diagnostic", "lab test", "pathology"], "Health", "expense"),
        (["school", "college", "tuition", "education", "course", "coaching",
          "udemy", "coursera", "upgrad", "byjus", "unacademy", "vedantu"], "Education", "expense"),
        (["salon", "parlour", "spa", "haircut", "grooming", "urban company",
          "urbanclap"], "Personal Care", "expense"),
        (["donation", "charity", "ngo", "temple", "church", "mosque", "gurudwara"], "Donations", "expense"),
        (["gst", "income tax", "tds", "government", "challan", "passport",
          "stamps", "registration"], "Taxes & Fees", "expense"),
        (["bank charge", "service charge", "sms charge", "debit card", "atm charge",
          "annual fee", "maintenance charge", "minimum balance", "consolidated charge"], "Bank Charges", "expense"),
        (["atm", "cash withdrawal", "cash deposit", "self withdrawal"], "Cash", "expense"),
    ]

    for keywords, category, txn_type in category_rules:
        if any(kw in desc for kw in keywords):
            return category, txn_type

    if is_credit:
        return "Transfer In", "income"

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
