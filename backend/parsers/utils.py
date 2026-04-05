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
        "canara": ["canara bank", "canarabank"],
        "union": ["union bank of india", "union bank"],
        "bob": ["bank of baroda", "barb0"],
        "idbi": ["idbi bank"],
        "indusind": ["indusind bank", "indusind"],
        "yes": ["yes bank"],
        "axis": ["axis bank", "axis account", "statement of axis"],
        "icici": ["icici bank", "icici account", "statement of icici", "statement of transactions in saving account"],
        "sbi": ["state bank of india", "sbi account", "sbi statement"],
        "hdfc": ["hdfc bank", "hdfc account", "hdfc statement"],
        "kotak": ["kotak mahindra", "kotak bank", "cust.reln.no"],
        "pnb": ["punjab national bank"],
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

    # Strip "(via Cred)" annotation before category matching — this is just payment method info
    via_cred = "(via cred)" in desc
    clean_desc = desc.replace("(via cred)", "").strip() if via_cred else desc

    category_rules = [
        # Income categories (checked first)
        (["salary credit", "salary", "payroll", "wages", "stipend"], "Salary", "income"),
        (["interest credit", "interest", "int.cr", "int cr", "int.pd", "interest paid", "int credit"], "Interest", "income"),
        (["dividend", "div credit"], "Dividends", "income"),
        (["upi refund", "refund", "reversal", "cashback", "cash back", "refund credit", "upi reversal"], "Refund", "income"),
        (["rent received", "rental income"], "Rental Income", "income"),
        (["neft cr", "neft credit", "imps cr", "imps credit", "rtgs cr", "fund transfer -",
          "clearing credit", "clearing -", "by clg"], "Bank Transfer In", "income"),

        # Food & Dining (specific merchants first, before generic keywords)
        (["sodexo", "swiggy", "zomato", "cloud kitchen", "sai siddhi"], "Food & Dining", "expense"),
        (["food", "restaurant", "dining", "cafe", "pizza", "burger", "mcdonald",
          "kfc", "domino", "starbucks", "chaayos", "haldiram", "barbeque",
          "biryani", "dhaba", "eatery", "quickbite", "burmaburma", "bhukkad",
          "catering", "coffee",
          # Regional & emerging
          "behrouz", "faasos", "box8", "oven story", "licious", "freshmenu",
          "eat fit", "rebel foods", "wow momo", "chai point", "third wave",
          "blue tokai", "sleepy owl", "mad over donuts", "bikanervala",
          "sagar ratna", "saravana bhavan", "adyar ananda", "murugan idli",
          "anand bhavan", "ccd", "barista", "dunkin", "subway", "taco bell",
          "wendy", "popeyes", "eatsure", "magicpin food", "dineout",
          "thali", "tiffin", "mess", "canteen"], "Food & Dining", "expense"),

        # Groceries
        (["grocery", "groceries", "bigbasket", "blinkit", "zepto", "instamart",
          "dmart", "d-mart", "d mart", "more supermarket", "reliance fresh", "spencer",
          "nature basket", "jiomart", "kirana", "vegetables", "fruits", "supermarket",
          "fresh n green", "freshngreen",
          # Regional & emerging
          "swiggy instamart", "bb daily", "milkbasket", "country delight",
          "supr daily", "dunzo daily", "bbdaily", "lulu hypermarket",
          "star bazaar", "hypercity", "easyday", "vishal mega mart",
          "metro cash", "spar hypermarket", "nilgiris", "heritage fresh",
          "ratnadeep", "reliance smart"], "Groceries", "expense"),

        # Crypto & Web3 (BEFORE Transport to prevent 'uber' substring match on 'kuber')
        (["wazirx", "coinswitch", "coindcx", "zebpay", "giottus",
          "buyucoin", "bitbns", "unocoin", "binance", "coinbase",
          "crypto", "bitcoin", "ethereum"], "Crypto", "investment"),

        # Transport & Travel
        (["uber ", "ola ", "rapido", "taxi", "cab ", "auto ", "rickshaw",
          # Regional & emerging
          "namma yatri", "blu smart", "meru", "mega cabs", "s ride",
          "jugnoo", "shuttl", "chalo"], "Transport", "expense"),
        (["petrol", "diesel", "fuel", "hp petrol", "iocl", "bpcl", "indian oil",
          "bharat petroleum", "hindustan petroleum", "shell", "essar",
          "reliance fuel", "nayara energy"], "Fuel", "expense"),
        (["irctc", "indian railway", "train", "railway", "railways", "ecatering",
          "confirmtkt", "ixigo train", "railyatri"], "Travel", "expense"),
        (["flight", "airline", "indigo", "spicejet", "air india", "vistara",
          "goair", "akasa", "makemytrip", "goibibo", "cleartrip", "yatra",
          "ixigo", "easemytrip", "happyeasygo", "skyscanner",
          "air asia", "emirates", "qatar airways", "etihad"], "Travel", "expense"),
        (["metro", "dmrc", "bmrc", "mmrc", "rapidx", "mumbai metro", "mahamumbaimetro",
          "chennai metro", "kochi metro", "kolkata metro", "lucknow metro",
          "nagpur metro", "pune metro"], "Transport", "expense"),
        (["parking", "fastag", "toll", "park+", "bharat highway"], "Transport", "expense"),
        (["hotel", "oyo", "fab hotel", "treebo", "zostel", "airbnb",
          "booking.com", "agoda", "trivago", "taj hotel", "oberoi",
          "itc hotel", "marriott", "hyatt", "radisson"], "Travel", "expense"),

        # Utilities
        (["electricity", "power", "bescom", "msedcl", "tata power", "adani electricity",
          "bses", "cesc", "torrent power",
          "uhbvn", "jbvnl", "wbsedcl", "kseb", "tneb", "pspcl",
          "dvvnl", "avvnl", "jvvnl"], "Electricity", "expense"),
        (["water", "bwssb", "water bill", "water supply",
          "delhi jal board", "mcgm water"], "Water", "expense"),
        (["gas service", "deogasservice", "jodhpurgas", "png", "lpg", "indane",
          "bharat gas", "hp gas", "mahanagar gas", "gas cylinder",
          "adani gas", "gl gas", "sabarmati gas"], "Gas", "expense"),
        (["internet", "broadband", "wifi", "act fibernet", "hathway", "tikona",
          "airtel broadband", "jio fiber", "bsnl broadband", "spectra",
          "excitel", "tata play fiber"], "Internet", "expense"),

        # Mobile / Telecom (specific patterns before generic)
        (["airtel recharge", "vi recharge", "vodafoneidea", "bhartihexacom",
          "recharge", "prepaid recharge", "postpaid", "jio", "vodafone",
          "bsnl", "mobile recharge",
          "mtnl", "reliance jio"], "Mobile Recharge", "expense"),
        (["dth", "tata sky", "dish tv", "airtel dth", "videocon", "sun direct",
          "tata play", "d2h"], "DTH", "expense"),

        # Subscriptions & Entertainment
        (["netflix", "hotstar", "prime video", "amazon prime", "spotify", "gaana",
          "youtube premium", "zee5", "sonyliv", "jiocinema", "apple tv", "disney",
          "subscription", "oneplay", "apple music", "audible", "steam (valve)",
          "jiocinema/viacom18",
          # New platforms
          "lionsgate play", "mubi", "curiosity stream", "discovery+",
          "aha video", "hoichoi", "sun nxt", "erosnow",
          "kindle unlimited", "notion", "figma", "canva", "chatgpt plus",
          "grammarly", "headspace", "calm app", "apple one"], "Subscriptions", "expense"),
        (["movie", "cinema", "pvr", "inox", "bookmyshow", "paytm movie",
          "cinepolis", "carnival cinema", "miraj cinema"], "Entertainment", "expense"),
        (["dream11", "fantasy", "mpl", "winzo", "my11circle", "astrotalk",
          "rummy", "poker", "ludo king"], "Entertainment", "expense"),

        # Shopping
        (["amazon", "flipkart", "myntra", "ajio", "meesho", "snapdeal", "tatacliq",
          "nykaa", "purplle", "mamaearth", "innovist", "artpillz",
          # Emerging & regional
          "firstcry", "hopscotch", "lenskart", "titan eye", "tanishq",
          "malabar gold", "kalyan jewellers", "pepperfry", "urban ladder",
          "ikea", "home centre", "wakefit", "sleepycat",
          "bewakoof", "souled store", "bonkers corner",
          "sugar cosmetics", "boat lifestyle", "noise",
          "shoppers stop", "lifestyle", "max fashion", "pantaloons",
          "westside", "central", "reliance trends"], "Shopping", "expense"),
        (["decathlon", "croma", "reliance digital", "vijay sales",
          "chroma", "samsung store", "apple store", "oneplus store",
          "xiaomi store"], "Shopping", "expense"),

        # Financial
        (["insurance", "lic", "icici pru", "hdfc life", "max life", "sbi life",
          "bajaj allianz", "health ins", "term ins", "policy",
          "star health", "care health", "niva bupa", "digit insurance",
          "acko", "tata aia", "kotak life", "aditya birla health"], "Insurance", "expense"),
        (["emi payment", "emi", "loan", "home loan", "car loan", "personal loan",
          "education loan", "bajaj finance", "bajajfinance", "hdfc credila",
          "tata capital", "shriram finance", "manappuram", "muthoot",
          "fullerton", "idfc first", "paysense"], "EMI", "expense"),
        (["cc payment", "credit card bill", "federal bank cc", "onecard cc",
          "credit card", "cred bill", "cred -", "slice", "onecard", "hdfc cc",
          "sbi card", "kotak card", "icici card", "axis card",
          "au bank card", "rbl card", "yes card", "indusind card",
          "hsbc card", "amex", "american express", "diners club"], "Credit Card", "expense"),

        # Investments
        (["sip", "mutual fund", "mf invest", "elss", "groww", "zerodha", "upstox",
          "kuvera", "paytm money", "coin by zerodha",
          "angel one", "5paisa", "motilal oswal", "iifl", "hdfc securities",
          "icici direct", "kotak securities", "axis direct",
          "smallcase", "indmoney", "etmoney", "niyo", "fi money",
          "jupiter money", "cred mint"], "SIP", "investment"),
        (["ppf", "provident fund"], "PPF", "investment"),
        (["nps", "national pension"], "NPS", "investment"),
        (["fd", "fixed deposit"], "Fixed Deposit", "investment"),
        (["gold", "sovereign gold", "sgb", "gold bond"], "Gold", "investment"),
        (["stocks", "shares", "equity", "demat"], "Stocks", "investment"),

        # Housing
        (["rent", "house rent", "rental", "pg rent", "hostel", "cash rent"], "Rent", "expense"),
        (["maintenance", "society", "apartment", "flat maintenance"], "Maintenance", "expense"),

        # Health & Medical
        (["hospital", "medical", "pharmacy", "medicine", "doctor",
          "clinic", "apollo", "fortis", "max hospital", "medplus", "netmeds",
          "1mg", "pharmeasy", "truemeds", "diagnostic", "lab test", "pathology",
          "aiims", "medico", "umeshmedical",
          # New additions
          "manipal hospital", "narayana health", "medanta", "lilavati",
          "kokilaben", "hinduja", "wockhardt", "columbia asia",
          "practo", "tata health", "thyrocare", "lal path labs",
          "dr. lal", "srl diagnostics", "healthians", "cult.fit health",
          "tata 1mg", "davaindia", "wellness forever",
          "dentist", "dental", "clove dental", "sabka dentist",
          "eye care", "lenskart eye", "vision express"], "Health", "expense"),

        # Education
        (["school", "college", "tuition", "education", "course", "coaching",
          "udemy", "coursera", "upgrad", "byjus", "unacademy", "vedantu",
          "icai", "institute of cha",
          # New additions
          "linkedin learning", "skillshare", "edx", "masterclass",
          "great learning", "simplilearn", "scaler", "newton school",
          "coding ninjas", "interviewbit", "physics wallah", "allen",
          "aakash", "resonance", "fiitjee", "bansal classes",
          "whitehat jr", "toppr", "doubtnut", "embibe",
          "british council", "ielts", "toefl"], "Education", "expense"),

        # Personal Care
        (["salon", "parlour", "spa", "haircut", "grooming", "urban company",
          "urbanclap", "fascino",
          # New additions
          "jawed habib", "naturals salon", "lakme salon", "vlcc",
          "enrich salon", "bodycraft", "toni & guy", "b blunt",
          "manly", "bombay shaving", "beardo", "ustraa",
          "nykaa man", "man matters", "traya", "vedix",
          "gym", "cult fit", "cult.fit", "gold's gym", "anytime fitness",
          "fitness first", "talwalkar", "golds gym", "crossfit"], "Personal Care", "expense"),

        # Donations
        (["donation", "charity", "ngo", "temple", "church", "mosque",
          "gurudwara", "seva bharati",
          "milaap", "ketto", "give india", "akshaya patra",
          "cry", "helpage", "pm cares", "pm relief"], "Donations", "expense"),

        # Taxes & Fees
        (["gst", "income tax", "tds", "government", "challan", "passport",
          "stamps", "registration", "godaddy",
          "property tax", "municipal", "mcd", "bbmp", "pmc",
          "road tax", "vehicle tax", "professional tax", "advance tax",
          "court fee", "legal"], "Taxes & Fees", "expense"),

        # Household & Home Services
        (["carpenter", "plumber", "electrician", "painter", "pest control",
          "home cleaning", "deep cleaning", "ac repair", "ac service",
          "water purifier", "ro service", "appliance repair",
          "amazon home services", "urban clap home",
          "furniture", "mattress", "curtain"], "Household", "expense"),

        # Bank Charges
        (["bank charge", "service charge", "sms charge", "sms alert",
          "debit card", "atm charge", "annual fee", "maintenance charge",
          "minimum balance", "consolidated charge", "instaalertchg",
          "imps charge", "cheque book", "cheque return charge", "chq rtn chg",
          "chq bk", "rtgs service charge", "rtgs 00"], "Bank Charges", "expense"),

        # Cash
        (["atm", "cash withdrawal", "cash deposit", "self withdrawal", "nwd-"], "Cash", "expense"),
    ]

    for keywords, category, txn_type in category_rules:
        if any(kw in clean_desc for kw in keywords):
            return category, txn_type

    # Fallback: categorize UPI person-to-person transfers
    if clean_desc.startswith("upi -") or clean_desc.startswith("imps -") or clean_desc.startswith("neft -"):
        if is_credit:
            return "Transfer In", "income"
        return "Transfer", "expense"

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
