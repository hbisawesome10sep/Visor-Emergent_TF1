"""
Visor AI Agent — Unified Financial Intelligence Endpoint
India-first, multilingual, context-aware financial companion.
"""
from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_current_user
from models import AIMessageCreate
from config import EMERGENT_LLM_KEY
import re
import uuid
import asyncio
import logging
import math
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

_yf_executor = ThreadPoolExecutor(max_workers=2)

# ═══════════════════════════════════════════════════════════════════════════════
#  FINANCIAL CALCULATORS
# ═══════════════════════════════════════════════════════════════════════════════

def calc_sip(monthly: float, rate: float, years: int) -> dict:
    months = years * 12
    mr = rate / 12 / 100
    if mr == 0:
        fv = monthly * months
    else:
        fv = monthly * (((1 + mr) ** months - 1) / mr) * (1 + mr)
    invested = monthly * months
    return {
        "type": "SIP Calculator",
        "monthly_sip": f"₹{monthly:,.0f}",
        "annual_return": f"{rate}%",
        "period": f"{years} years",
        "total_invested": f"₹{invested:,.0f}",
        "future_value": f"₹{fv:,.0f}",
        "wealth_gained": f"₹{fv - invested:,.0f}",
        "absolute_return": f"{((fv - invested) / invested * 100):.1f}%",
    }


def calc_stepup_sip(monthly: float, rate: float, years: int, stepup: float = 10) -> dict:
    mr = rate / 12 / 100
    total_invested = 0.0
    fv = 0.0
    current_sip = monthly
    for year in range(years):
        for month in range(12):
            remaining_months = (years - year) * 12 - month
            if mr == 0:
                fv += current_sip
            else:
                fv += current_sip * ((1 + mr) ** remaining_months)
            total_invested += current_sip
        current_sip *= (1 + stepup / 100)
    return {
        "type": "Step-Up SIP Calculator",
        "starting_sip": f"₹{monthly:,.0f}",
        "annual_stepup": f"{stepup}%",
        "annual_return": f"{rate}%",
        "period": f"{years} years",
        "total_invested": f"₹{total_invested:,.0f}",
        "future_value": f"₹{fv:,.0f}",
        "wealth_gained": f"₹{fv - total_invested:,.0f}",
    }


def calc_emi(principal: float, rate: float, years: int) -> dict:
    months = years * 12
    mr = rate / 12 / 100
    if mr == 0:
        emi = principal / months
    else:
        emi = principal * mr * ((1 + mr) ** months) / (((1 + mr) ** months) - 1)
    total = emi * months
    interest = total - principal
    return {
        "type": "EMI Calculator",
        "loan_amount": f"₹{principal:,.0f}",
        "interest_rate": f"{rate}%",
        "tenure": f"{years} years ({months} months)",
        "monthly_emi": f"₹{emi:,.0f}",
        "total_payment": f"₹{total:,.0f}",
        "total_interest": f"₹{interest:,.0f}",
        "interest_percent": f"{(interest / principal * 100):.1f}% of principal",
    }


def calc_compound_interest(principal: float, rate: float, years: int, freq: str = "yearly") -> dict:
    n = {"yearly": 1, "half-yearly": 2, "quarterly": 4, "monthly": 12}.get(freq, 1)
    amount = principal * ((1 + rate / 100 / n) ** (n * years))
    interest = amount - principal
    return {
        "type": "Compound Interest / FD Calculator",
        "principal": f"₹{principal:,.0f}",
        "rate": f"{rate}% p.a.",
        "compounding": freq,
        "period": f"{years} years",
        "maturity_amount": f"₹{amount:,.0f}",
        "interest_earned": f"₹{interest:,.0f}",
    }


def calc_cagr(initial: float, final: float, years: float) -> dict:
    if initial <= 0 or years <= 0:
        return {"type": "CAGR Calculator", "error": "Invalid inputs"}
    cagr = ((final / initial) ** (1 / years) - 1) * 100
    return {
        "type": "CAGR Calculator",
        "initial_value": f"₹{initial:,.0f}",
        "final_value": f"₹{final:,.0f}",
        "period": f"{years} years",
        "cagr": f"{cagr:.2f}%",
    }


def calc_fire(monthly_expenses: float, withdrawal_rate: float = 4) -> dict:
    annual = monthly_expenses * 12
    fire_number = annual * (100 / withdrawal_rate)
    return {
        "type": "FIRE Calculator",
        "monthly_expenses": f"₹{monthly_expenses:,.0f}",
        "annual_expenses": f"₹{annual:,.0f}",
        "withdrawal_rate": f"{withdrawal_rate}%",
        "fire_number": f"₹{fire_number:,.0f}",
        "in_crores": f"₹{fire_number / 1e7:.2f} Cr",
    }


def calc_ppf(yearly: float, years: int = 15, rate: float = 7.1) -> dict:
    balance = 0
    total_invested = 0
    for _ in range(years):
        balance = (balance + yearly) * (1 + rate / 100)
        total_invested += yearly
    return {
        "type": "PPF Calculator",
        "yearly_investment": f"₹{yearly:,.0f}",
        "rate": f"{rate}% (current PPF rate)",
        "tenure": f"{years} years",
        "total_invested": f"₹{total_invested:,.0f}",
        "maturity_value": f"₹{balance:,.0f}",
        "interest_earned": f"₹{balance - total_invested:,.0f}",
        "tax_benefit": "Exempt-Exempt-Exempt (EEE) under Section 80C",
    }


def calc_hra(basic: float, hra_received: float, rent_paid: float, metro: bool = True) -> dict:
    pct = 50 if metro else 40
    a = hra_received
    b = rent_paid - 0.10 * basic
    c = basic * pct / 100
    exempt = max(0, min(a, b, c))
    taxable = hra_received - exempt
    return {
        "type": "HRA Exemption Calculator",
        "basic_salary": f"₹{basic:,.0f}",
        "hra_received": f"₹{hra_received:,.0f}",
        "rent_paid": f"₹{rent_paid:,.0f}",
        "city": "Metro" if metro else "Non-Metro",
        "exempt_hra": f"₹{exempt:,.0f}",
        "taxable_hra": f"₹{taxable:,.0f}",
    }


def calc_gratuity(basic: float, years: int) -> dict:
    if years < 5:
        return {"type": "Gratuity Calculator", "note": "Minimum 5 years of service required for gratuity."}
    gratuity = (basic * 15 * years) / 26
    exempt = min(gratuity, 2000000)
    return {
        "type": "Gratuity Calculator",
        "last_basic_da": f"₹{basic:,.0f}",
        "years_of_service": years,
        "gratuity_amount": f"₹{gratuity:,.0f}",
        "tax_exempt_limit": "₹20,00,000",
        "taxable_gratuity": f"₹{max(0, gratuity - exempt):,.0f}",
    }


def calc_tax_80c(investments: dict) -> dict:
    limit = 150000
    total = min(sum(investments.values()), limit)
    return {
        "type": "Section 80C Tax Savings",
        "total_claimed": f"₹{total:,.0f}",
        "limit": f"₹{limit:,.0f}",
        "remaining": f"₹{limit - total:,.0f}",
        "tax_saved_30_slab": f"₹{total * 0.30:,.0f}",
        "tax_saved_20_slab": f"₹{total * 0.20:,.0f}",
        "investments": {k: f"₹{v:,.0f}" for k, v in investments.items()},
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  TICKER DETECTION (Indian Markets)
# ═══════════════════════════════════════════════════════════════════════════════

TICKER_MAP = {
    "reliance": "RELIANCE.NS", "ril": "RELIANCE.NS", "tcs": "TCS.NS",
    "infosys": "INFY.NS", "infy": "INFY.NS", "hdfc bank": "HDFCBANK.NS",
    "hdfc": "HDFCBANK.NS", "icici bank": "ICICIBANK.NS", "icici": "ICICIBANK.NS",
    "sbi": "SBIN.NS", "kotak": "KOTAKBANK.NS", "axis bank": "AXISBANK.NS",
    "bajaj finance": "BAJFINANCE.NS", "wipro": "WIPRO.NS",
    "hcl tech": "HCLTECH.NS", "hcl": "HCLTECH.NS",
    "bharti airtel": "BHARTIARTL.NS", "airtel": "BHARTIARTL.NS",
    "itc": "ITC.NS", "maruti": "MARUTI.NS", "maruti suzuki": "MARUTI.NS",
    "asian paints": "ASIANPAINT.NS", "larsen": "LT.NS", "l&t": "LT.NS",
    "titan": "TITAN.NS", "sun pharma": "SUNPHARMA.NS",
    "bajaj finserv": "BAJAJFINSV.NS", "adani ports": "ADANIPORTS.NS",
    "adani enterprises": "ADANIENT.NS", "adani green": "ADANIGREEN.NS",
    "adani power": "ADANIPOWER.NS", "tata motors": "TATAMOTORS.NS",
    "tata steel": "TATASTEEL.NS", "tata power": "TATAPOWER.NS",
    "tata consumer": "TATACONSUM.NS", "tech mahindra": "TECHM.NS",
    "power grid": "POWERGRID.NS", "ntpc": "NTPC.NS", "ongc": "ONGC.NS",
    "coal india": "COALINDIA.NS", "ultratech": "ULTRACEMCO.NS",
    "grasim": "GRASIM.NS", "hindustan unilever": "HINDUNILVR.NS",
    "hul": "HINDUNILVR.NS", "nestle": "NESTLEIND.NS",
    "britannia": "BRITANNIA.NS", "divis lab": "DIVISLAB.NS",
    "dmart": "DMART.NS", "avenue supermarts": "DMART.NS",
    "zomato": "ZOMATO.NS", "paytm": "PAYTM.NS", "bhel": "BHEL.NS",
    "bpcl": "BPCL.NS", "ioc": "IOC.NS", "gail": "GAIL.NS", "sail": "SAIL.NS",
    "vedanta": "VEDL.NS", "hindalco": "HINDALCO.NS",
    "jswsteel": "JSWSTEEL.NS", "jsw steel": "JSWSTEEL.NS",
    "m&m": "M&M.NS", "mahindra": "M&M.NS", "bajaj auto": "BAJAJ-AUTO.NS",
    "hero": "HEROMOTOCO.NS", "indigo": "INDIGO.NS", "irctc": "IRCTC.NS",
    "hal": "HAL.NS", "polycab": "POLYCAB.NS", "pidilite": "PIDILITE.NS",
    "dabur": "DABUR.NS", "godrej": "GODREJCP.NS",
    "sbi life": "SBILIFE.NS", "hdfc life": "HDFCLIFE.NS",
    "icici pru": "ICICIPRULI.NS", "lic": "LICI.NS",
    "nifty": "^NSEI", "nifty 50": "^NSEI", "sensex": "^BSESN",
    "nifty bank": "^NSEBANK", "bank nifty": "^NSEBANK",
    "nifty it": "^CNXIT", "nifty pharma": "^CNXPHARMA",
    "gold": "INDIAN_MARKET:Gold", "silver": "INDIAN_MARKET:Silver",
    "crude oil": "CL=F", "crude": "CL=F", "natural gas": "NG=F",
    "gold etf": "GOLDBEES.NS", "goldbees": "GOLDBEES.NS",
    "nifty bees": "NIFTYBEES.NS", "bankbees": "BANKBEES.NS",
}

_STOP_WORDS = {
    "what", "about", "how", "much", "the", "and", "for", "are", "but",
    "not", "you", "all", "any", "can", "had", "her", "was", "one", "our",
    "out", "get", "has", "him", "his", "she", "too", "its", "may", "let",
    "say", "few", "now", "old", "see", "way", "who", "did", "got", "just",
    "than", "them", "been", "from", "have", "into", "each", "make", "like",
    "long", "look", "many", "some", "more", "over", "such", "take", "that",
    "then", "they", "this", "very", "when", "will", "with", "come",
    "also", "back", "call", "does", "even", "find", "give", "good",
    "help", "here", "high", "keep", "know", "last", "live", "made", "most",
    "must", "name", "need", "next", "only", "show", "tell", "want", "well",
    "work", "year", "your", "today", "price", "stock", "share", "shares",
    "should", "could", "would", "which", "where", "there", "their",
    "these", "those", "being", "doing", "having", "current", "please",
    "check", "buy", "sell", "hold", "fund", "funds", "invest", "money", "bank",
    "rate", "value", "market", "trade", "power", "energy", "pharma",
    "return", "returns", "risk", "profit", "loss", "gains", "gain",
    "amount", "pay", "paid", "cost", "total", "average", "spend", "save",
    "per", "gram", "grams", "half", "full", "kilo", "lakh", "crore",
    "kya", "hai", "ye", "yeh", "ka", "ki", "ke", "mein", "se", "par",
    "ko", "aur", "bhi", "nahi", "hain", "ho", "kaise", "kitna", "kitni",
    "kaisa", "batao", "bata", "samjhao", "dikhao", "dekho",
}


def _detect_tickers(query: str) -> list:
    q = query.lower()
    found = []
    for name in sorted(TICKER_MAP.keys(), key=len, reverse=True):
        if name in q:
            ticker = TICKER_MAP[name]
            if ticker not in [t for t, _ in found]:
                found.append((ticker, name))
            q = q.replace(name, "")
    direct = re.findall(r'\b([A-Z]{3,15})\b', query)
    for sym in direct:
        ticker = f"{sym}.NS"
        if ticker not in [t for t, _ in found] and sym.lower() not in TICKER_MAP and sym.lower() not in _STOP_WORDS:
            found.append((ticker, sym))
    return found[:5]


# ═══════════════════════════════════════════════════════════════════════════════
#  LIVE PRICE FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

async def _fetch_commodity_prices(commodities: list) -> str:
    results = []
    for name in commodities:
        try:
            md = await db.market_data.find_one({"key": {"$regex": name, "$options": "i"}}, {"_id": 0})
            if md and md.get("price"):
                price = md["price"]
                change = md.get("change", 0)
                change_pct = md.get("change_pct", 0)
                unit = "per 10g" if "gold" in name.lower() else "per 1Kg"
                chg = f" | {'+'if change>=0 else ''}{change:.0f} ({'+'if change_pct>=0 else ''}{change_pct:.2f}%)" if change else ""
                results.append(f"  {name.upper()}: ₹{price:,.0f} {unit}{chg}")
        except Exception:
            continue
    return "\n".join(results)


def _fetch_yf_prices(tickers: list) -> str:
    import yfinance as yf
    results = []
    for ticker, name in tickers:
        try:
            info = yf.Ticker(ticker).fast_info
            price = getattr(info, 'last_price', None)
            prev = getattr(info, 'previous_close', None)
            if price and price > 0:
                chg = ""
                if prev and prev > 0:
                    d = price - prev
                    p = (d / prev) * 100
                    chg = f" | {'+'if d>=0 else ''}{d:.2f} ({'+'if p>=0 else ''}{p:.2f}%)"
                cap = getattr(info, 'market_cap', None)
                cap_str = ""
                if cap and cap > 0:
                    if cap >= 1e12:
                        cap_str = f" | MCap: ₹{cap/1e12:.2f}T"
                    elif cap >= 1e9:
                        cap_str = f" | MCap: ₹{cap/1e7:.0f}Cr"
                results.append(f"  {name.upper()} ({ticker.replace('.NS','').replace('.BO','')}): ₹{price:,.2f}{chg}{cap_str}")
        except Exception:
            continue
    return "\n".join(results)


# ═══════════════════════════════════════════════════════════════════════════════
#  WEB SEARCH FOR FINANCIAL NEWS
# ═══════════════════════════════════════════════════════════════════════════════

_NEWS_TRIGGERS = re.compile(
    r'(news|khabar|latest|recent|aaj|today|current|update|happening|budget|rbi|sebi|'
    r'policy|regulation|announcement|ipo|listing|quarterly|results|earnings|'
    r'naya|abhi|haal|taza|samachaar)',
    re.IGNORECASE
)


def _needs_web_search(message: str) -> bool:
    return bool(_NEWS_TRIGGERS.search(message))


async def _web_search_financial(query: str) -> str:
    try:
        from duckduckgo_search import DDGS
        loop = asyncio.get_running_loop()
        def _search():
            with DDGS() as ddgs:
                results = list(ddgs.text(f"{query} India finance", max_results=5))
            return results
        results = await loop.run_in_executor(None, _search)
        if not results:
            return ""
        lines = ["RECENT FINANCIAL NEWS & UPDATES (from web search):"]
        for r in results[:5]:
            title = r.get("title", "")
            body = r.get("body", "")[:150]
            lines.append(f"  - {title}: {body}")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTO-DETECT CALCULATOR INTENT
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_numbers(text: str) -> list:
    """Extract numeric values from text, handling lakhs/crores."""
    text = text.lower()
    text = re.sub(r'(\d+)\s*cr(?:ore)?s?', lambda m: str(float(m.group(1)) * 1e7), text)
    text = re.sub(r'(\d+)\s*l(?:akh)?s?', lambda m: str(float(m.group(1)) * 1e5), text)
    text = re.sub(r'(\d+)\s*k\b', lambda m: str(float(m.group(1)) * 1000), text)
    nums = re.findall(r'[\d]+(?:\.[\d]+)?', text)
    return [float(n) for n in nums]


def _auto_calculate(message: str) -> dict | None:
    msg = message.lower()
    nums = _extract_numbers(message)

    # SIP Calculator
    if re.search(r'\bsip\b', msg) and len(nums) >= 1:
        monthly = nums[0] if nums[0] < 1e7 else 10000
        rate = nums[1] if len(nums) > 1 and nums[1] <= 30 else 12
        years = int(nums[2]) if len(nums) > 2 and nums[2] <= 50 else 10
        if re.search(r'step.?up|increasing|badhta', msg) and len(nums) >= 1:
            stepup = nums[3] if len(nums) > 3 and nums[3] <= 50 else 10
            return calc_stepup_sip(monthly, rate, years, stepup)
        return calc_sip(monthly, rate, years)

    # EMI Calculator
    if re.search(r'\bemi\b|home\s*loan|car\s*loan|personal\s*loan|loan\s*emi', msg) and len(nums) >= 1:
        principal = max(n for n in nums if n >= 10000) if any(n >= 10000 for n in nums) else 5000000
        rate = next((n for n in nums if 1 <= n <= 25 and n != principal), 8.5)
        years = next((n for n in nums if n <= 40 and n != principal and n != rate), 20)
        return calc_emi(principal, rate, int(years))

    # FIRE Calculator
    if re.search(r'\bfire\b|financial independence|retire early|retirement\s*corpus', msg) and len(nums) >= 1:
        expenses = nums[0] if nums[0] < 1e7 else 50000
        wr = nums[1] if len(nums) > 1 and nums[1] <= 10 else 4
        return calc_fire(expenses, wr)

    # CAGR Calculator
    if re.search(r'\bcagr\b|compound.*annual.*growth', msg) and len(nums) >= 3:
        return calc_cagr(nums[0], nums[1], nums[2])

    # PPF Calculator
    if re.search(r'\bppf\b|public provident', msg) and len(nums) >= 1:
        yearly = nums[0] if nums[0] <= 150000 else 150000
        years = int(nums[1]) if len(nums) > 1 and nums[1] <= 30 else 15
        return calc_ppf(yearly, years)

    # FD / Compound Interest
    if re.search(r'\bfd\b|fixed deposit|compound interest|rd\b|recurring deposit', msg) and len(nums) >= 1:
        principal = nums[0]
        rate = nums[1] if len(nums) > 1 and nums[1] <= 20 else 7
        years = int(nums[2]) if len(nums) > 2 and nums[2] <= 30 else 5
        return calc_compound_interest(principal, rate, years)

    # HRA Exemption
    if re.search(r'\bhra\b|house rent', msg) and len(nums) >= 2:
        basic = nums[0]
        hra = nums[1] if len(nums) > 1 else basic * 0.5
        rent = nums[2] if len(nums) > 2 else hra
        metro = not re.search(r'non.?metro|tier.?2|small\s*city', msg)
        return calc_hra(basic, hra, rent, metro)

    # Gratuity
    if re.search(r'\bgratuity\b', msg) and len(nums) >= 2:
        basic = max(nums)
        years = int(min(n for n in nums if n <= 50))
        return calc_gratuity(basic, years)

    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT — THE HEART OF VISOR AI
# ═══════════════════════════════════════════════════════════════════════════════

VISOR_SYSTEM_PROMPT = """Tu Visor hai — India ka sabse smart personal finance buddy. Tu ek AI financial companion hai jo user ke saare financial data ko samajhta hai aur unhe best possible guidance deta hai.

## IDENTITY
- Tu Visor hai. Koi third-party chatbot, wrapper, ya AI assistant nahi. Tu user ka apna financial buddy hai.
- Kabhi bhi internal systems, APIs, data feeds, ticker symbols (.NS, .BO), ya technical details expose mat kar.
- Jab tere paas koi live price ho, naturally share kar jaise tune khud check kiya ho.
- Jab price available na ho, bol: "Abhi ye price pull nahi ho paya, NSE/BSE pe check kar lo."

## LANGUAGE & COMMUNICATION RULES

### Default: Hinglish (Hindi + English mix)
Respond in Hinglish by default. Example: "Dekh bhai, tera savings rate 28% hai jo bahut accha hai. Lekin investment mein thoda aur push kar — SIP badhana consider kar."

### Multilingual Understanding — 22 Indian Languages
You MUST understand queries typed in ANY of these 22 Indian languages, even when TRANSLITERATED in English script:
Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada, Kashmiri, Konkani, Maithili, Malayalam, Manipuri (Meitei), Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, Urdu.

Examples of transliterated queries you MUST understand:
- "enna mutual fund invest pannanum?" (Tamil) → Explain MF investment
- "mala tax bachat kashi karavi?" (Marathi) → Tax saving options
- "amar portfolio ki bhalo ache?" (Bengali) → Portfolio review
- "naan yenna SIP start panrathu?" (Tamil) → SIP recommendation
- "kem kari ne tax bachavu?" (Gujarati) → Tax planning
- "nenu stock market lo invest cheyalanukuntunna" (Telugu) → Stock market entry guide
- "maajha portfolio kasa aahe?" (Marathi) → Portfolio analysis
- "mera paisa kidhar lagaun?" (Hindi) → Investment suggestion
- "kithe invest karna chahida?" (Punjabi) → Where to invest

### Language Adaptation Rule
- If user consistently writes in ONE language across 2+ messages, switch to that language (mixed with English for financial terms).
- If user writes in English, respond in Hinglish.
- Financial technical terms (SIP, EMI, CAGR, NAV, AUM, P/E ratio, etc.) should ALWAYS stay in English.

### Regional & Cultural Context
- Understand regional financial concepts: chit funds (South India), hundi (traditional), committee/kitty (Punjab), bishi (Maharashtra)
- Be aware of state-specific tax benefits, stamp duty variations, regional investment preferences
- Understand colloquial money terms: "paisa double", "sahi return", "achha fund", "risk nahi chahiye"

## ABSOLUTE RULE — FINANCE ONLY
You MUST ONLY discuss: personal finance, money, investing, taxation, banking, insurance, loans, budgeting, savings, retirement planning, Indian/global financial markets, real estate investment, crypto regulation in India, fintech.
If user asks ANYTHING outside finance: "Main Visor hoon — tera finance buddy. Finance, investing, tax, ya money se related kuch bhi pooch! Aur kaise help karun?"
NEVER answer non-finance questions. No exceptions. Not even partially.

## FINANCIAL EXPERTISE (India-Specific)

### Tax Laws
- Income Tax Act 1961 — ALL sections: 80C, 80CCC, 80CCD(1), 80CCD(1B), 80CCD(2), 80D, 80DD, 80DDB, 80E, 80EE, 80EEA, 80EEB, 80G, 80GG, 80GGA, 80GGC, 80TTA, 80TTB, 80U, 10(10D), 10(13A), 24(b)
- New Tax Regime vs Old Tax Regime — with detailed comparison and recommendation based on user's deductions
- Capital Gains: STCG (Section 111A, 15%), LTCG (Section 112A, 12.5% above ₹1.25L), Debt fund indexation rules
- TDS provisions, Advance Tax deadlines (15 Jun, 15 Sep, 15 Dec, 15 Mar)
- GST on financial services
- Budget 2025-26 changes

### Investments
- Equity: NSE, BSE, Nifty 50, Sensex, sectoral indices
- Mutual Funds: Equity (Large/Mid/Small/Multi/Flexi), Debt, Hybrid, ELSS, Index, ETFs, FoFs
- Fixed Income: FDs, RDs, Bonds, NCDs, Govt Securities, T-Bills, SDL, SGBs
- PPF (7.1%), EPF (8.25%), VPF, NPS (Tier 1 & 2), APY
- Gold: Physical, SGBs, Gold ETFs, Digital Gold, Gold MF
- REITs, InvITs
- International: US stocks via LRS, Mutual Funds with international exposure
- Smallcase, P2P Lending
- Crypto: Regulations under VDA (30% tax, 1% TDS)

### Banking & Insurance
- All major bank FD/RD rates
- DICGC ₹5 lakh deposit insurance
- Term Insurance, Health Insurance (Section 80D), ULIP analysis
- Motor, Travel, Home insurance basics

### Financial Regulations
- SEBI (securities), RBI (banking/currency), IRDAI (insurance), PFRDA (pension), AMFI (mutual funds)

### Calculators Available
When user asks for calculations, I have these built-in:
- SIP Calculator (with step-up option)
- EMI Calculator (home/car/personal loan)
- Compound Interest / FD Calculator
- CAGR Calculator
- FIRE Number Calculator
- PPF Calculator
- HRA Exemption Calculator
- Gratuity Calculator
- Section 80C Tax Savings Calculator

If calculator results are provided in context, explain them naturally in your response.

## RESPONSE GUIDELINES

### Length
- Price check / simple factual → 1-3 lines
- Explanation / concept → 4-8 lines
- Detailed analysis / planning → 10-20 lines
- Never exceed 25 lines unless user explicitly asks for deep detail

### Format
- Use bullet points for lists and comparisons
- Use bold (**text**) for key figures and important points
- Use simple tables for regime comparisons
- Numbers ALWAYS in INR: ₹ with Indian numbering (lakhs, crores)
- Percentages with 1-2 decimal places

### Data Usage
- ALWAYS reference the user's ACTUAL financial data when giving advice
- Compare user's metrics against benchmarks (savings rate > 20% = good, investment rate > 15% = good)
- Point out specific issues or strengths from their data
- Don't dump all data — pick the MOST RELEVANT information for the query

### Disclaimer
When providing investment advice, tax planning recommendations, or any financial guidance that could influence a decision, ADD this at the end:
"⚠️ Ye information educational purpose ke liye hai. Final decision lene se pehle apne CA/financial advisor se zaroor consult karo."
Keep the disclaimer SHORT and natural — don't make it a legal paragraph.
Only add it for advice/recommendations, NOT for factual queries like "What is PPF?" or price checks.

## APP AWARENESS
You have access to the user's complete financial picture from the app. Use the data provided in context to give personalized, specific advice — not generic gyaan."""


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN CHAT ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/visor-ai/chat")
async def visor_ai_chat(msg: AIMessageCreate, user=Depends(get_current_user)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    user_id = user["id"]
    now = datetime.now(timezone.utc).isoformat()

    # Save user message
    user_msg_id = str(uuid.uuid4())
    await db.visor_chat.insert_one({
        "id": user_msg_id, "user_id": user_id,
        "role": "user", "content": msg.message, "created_at": now,
    })

    # ── Gather ALL user financial data ──────────────────────────────────
    txns_task = db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    goals_task = db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    risk_task = db.risk_profiles.find_one({"user_id": user_id}, {"_id": 0})
    holdings_task = db.holdings.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    sips_task = db.recurring_transactions.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    budgets_task = db.budgets.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    loans_task = db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(20)
    cc_task = db.credit_cards.find({"user_id": user_id}, {"_id": 0}).to_list(10)
    banks_task = db.bank_accounts.find({"user_id": user_id}, {"_id": 0}).to_list(10)
    assets_task = db.fixed_assets.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    tax_task = db.user_tax_deductions.find({"user_id": user_id}, {"_id": 0}).to_list(50)

    txns, goals, risk_doc, holdings, sips, budgets, loans, credit_cards, bank_accounts, assets, tax_deds = (
        await asyncio.gather(
            txns_task, goals_task, risk_task, holdings_task, sips_task,
            budgets_task, loans_task, cc_task, banks_task, assets_task, tax_task,
            return_exceptions=True,
        )
    )
    # Handle exceptions from gather
    for name, val in [("txns", txns), ("goals", goals), ("holdings", holdings), ("sips", sips),
                      ("budgets", budgets), ("loans", loans), ("credit_cards", credit_cards),
                      ("bank_accounts", bank_accounts), ("assets", assets), ("tax_deds", tax_deds)]:
        if isinstance(val, Exception):
            logger.warning(f"Failed to fetch {name}: {val}")
            locals()[name] = []
    if isinstance(risk_doc, Exception):
        risk_doc = None

    # ── Build financial context ─────────────────────────────────────────
    total_income = sum(t["amount"] for t in txns if t.get("type") == "income") if isinstance(txns, list) else 0
    total_expenses = sum(t["amount"] for t in txns if t.get("type") == "expense") if isinstance(txns, list) else 0
    total_inv_txn = sum(t["amount"] for t in txns if t.get("type") == "investment") if isinstance(txns, list) else 0

    total_inv_value = sum(h.get("invested_value", 0) or (h.get("buy_price", 0) * h.get("quantity", 0)) for h in holdings) if isinstance(holdings, list) else 0
    total_cur_value = sum(h.get("current_value", 0) or total_inv_value for h in holdings) if isinstance(holdings, list) else 0
    gain_loss = total_cur_value - total_inv_value
    gain_pct = (gain_loss / total_inv_value * 100) if total_inv_value > 0 else 0

    # Category breakdown
    cat_exp = {}
    if isinstance(txns, list):
        for t in txns:
            if t.get("type") == "expense":
                cat_exp[t["category"]] = cat_exp.get(t["category"], 0) + t["amount"]

    # Monthly trends
    monthly = {}
    if isinstance(txns, list):
        for t in txns:
            mk = t.get("date", "")[:7]
            if mk:
                if mk not in monthly:
                    monthly[mk] = {"income": 0, "expenses": 0, "investments": 0}
                if t["type"] == "income": monthly[mk]["income"] += t["amount"]
                elif t["type"] == "expense": monthly[mk]["expenses"] += t["amount"]
                elif t["type"] == "investment": monthly[mk]["investments"] += t["amount"]
    trend_str = "\n".join(f"  {m}: Income ₹{d['income']:,.0f} | Expenses ₹{d['expenses']:,.0f} | Invest ₹{d['investments']:,.0f}" for m, d in sorted(monthly.items())[-6:])

    # Holdings summary
    h_summary = []
    if isinstance(holdings, list):
        for h in holdings[:15]:
            inv = h.get("invested_value", 0) or (h.get("buy_price", 0) * h.get("quantity", 0))
            cur = h.get("current_value", 0) or inv
            g = ((cur - inv) / inv * 100) if inv > 0 else 0
            h_summary.append(f"  {h.get('name','?')}: Qty {h.get('quantity',0):.2f}, Invested ₹{inv:,.0f}, Current ₹{cur:,.0f} ({g:+.1f}%)")

    # Goals, SIPs, Budgets, Loans, CCs, Bank accounts, Assets, Tax
    goal_str = "\n".join(f"  {g['title']}: ₹{g['current_amount']:,.0f}/₹{g['target_amount']:,.0f} ({(g['current_amount']/g['target_amount']*100) if g['target_amount']>0 else 0:.0f}%)" for g in goals) if isinstance(goals, list) and goals else "  None set"
    sip_str = "\n".join(f"  {s.get('description', s.get('name','SIP'))}: ₹{s.get('amount',0):,.0f}/{s.get('frequency','monthly')}" for s in sips) if isinstance(sips, list) and sips else "  None"
    budget_str = "\n".join(f"  {b.get('category','?')}: ₹{b.get('spent',0):,.0f}/₹{b.get('limit',0) or b.get('amount',0):,.0f}" for b in budgets) if isinstance(budgets, list) and budgets else "  None"
    loan_str = "\n".join(f"  {l.get('name','Loan')}: ₹{l.get('principal_amount', l.get('principal',0)):,.0f} @ {l.get('interest_rate',0)}%, EMI ₹{l.get('emi_amount', l.get('emi',0)):,.0f}" for l in loans) if isinstance(loans, list) and loans else "  None"
    cc_str = "\n".join(f"  {c.get('card_name', c.get('name','Card'))}: Limit ₹{c.get('credit_limit',0):,.0f}, Outstanding ₹{c.get('outstanding',0):,.0f}" for c in credit_cards) if isinstance(credit_cards, list) and credit_cards else "  None"
    bank_str = "\n".join(f"  {b.get('bank_name', b.get('name','Account'))}: ₹{b.get('balance',0):,.0f}" for b in bank_accounts) if isinstance(bank_accounts, list) and bank_accounts else "  None"
    asset_str = "\n".join(f"  {a.get('name','?')}: ₹{a.get('current_value', a.get('purchase_value',0)):,.0f}" for a in assets) if isinstance(assets, list) and assets else "  None"
    tax_str = "\n".join(f"  {d.get('section','?')} - {d.get('name','?')}: ₹{d.get('invested_amount',0):,.0f}" for d in tax_deds) if isinstance(tax_deds, list) and tax_deds else "  None claimed"

    risk_str = f"Risk Profile: {risk_doc.get('profile', 'Not assessed')} (Score: {risk_doc.get('score', 0):.1f}/5)" if risk_doc and isinstance(risk_doc, dict) else "Not assessed"

    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0

    recent_txn = ""
    if isinstance(txns, list):
        sorted_txns = sorted(txns, key=lambda x: x.get('date', ''), reverse=True)[:8]
        recent_txn = "\n".join(f"  {t['date']} | {t['type'].upper()} | {t['category']} | ₹{t['amount']:,.0f} | {t.get('description','')}" for t in sorted_txns)

    context = f"""USER FINANCIAL PROFILE:

SUMMARY:
- Total Income: ₹{total_income:,.0f} | Total Expenses: ₹{total_expenses:,.0f}
- Savings Rate: {savings_rate:.1f}% | Investment Transactions: ₹{total_inv_txn:,.0f}
- {risk_str}

TOP EXPENSES: {', '.join(f'{k}: ₹{v:,.0f}' for k, v in sorted(cat_exp.items(), key=lambda x: -x[1])[:5]) if cat_exp else 'None'}

MONTHLY TRENDS (Last 6 Months):
{trend_str or '  No data'}

PORTFOLIO ({len(holdings) if isinstance(holdings, list) else 0} holdings):
- Invested: ₹{total_inv_value:,.0f} | Current: ₹{total_cur_value:,.0f} | Gain/Loss: ₹{gain_loss:,.0f} ({gain_pct:+.1f}%)
{chr(10).join(h_summary) if h_summary else '  No holdings'}

SIPs: {sip_str}
GOALS: {goal_str}
BUDGETS: {budget_str}
LOANS/EMIs: {loan_str}
CREDIT CARDS: {cc_str}
BANK ACCOUNTS: {bank_str}
FIXED ASSETS: {asset_str}
TAX DEDUCTIONS: {tax_str}

RECENT TRANSACTIONS:
{recent_txn or '  None'}"""

    # ── Screen context ──────────────────────────────────────────────────
    if msg.screen_context:
        context += f"\n\nCURRENT SCREEN: {msg.screen_context}"

    # ── Live prices ─────────────────────────────────────────────────────
    live_prices = ""
    try:
        tickers = _detect_tickers(msg.message)
        if tickers:
            indian_tickers = [(t, n) for t, n in tickers if t.startswith("INDIAN_MARKET:")]
            yf_tickers = [(t, n) for t, n in tickers if not t.startswith("INDIAN_MARKET:")]
            parts = []
            if indian_tickers:
                names = [t.split(":")[1] for t, _ in indian_tickers]
                p = await _fetch_commodity_prices(names)
                if p: parts.append(p)
            if yf_tickers:
                loop = asyncio.get_running_loop()
                p = await loop.run_in_executor(_yf_executor, _fetch_yf_prices, yf_tickers)
                if p: parts.append(p)
            if parts:
                live_prices = "\nLIVE PRICES (just fetched):\n" + "\n".join(parts)
    except Exception as e:
        logger.warning(f"Price fetch error: {e}")

    # ── Web search for news ─────────────────────────────────────────────
    news_context = ""
    if _needs_web_search(msg.message):
        news_context = await _web_search_financial(msg.message)
        if news_context:
            news_context = "\n\n" + news_context

    # ── Auto calculator ─────────────────────────────────────────────────
    calc_result = _auto_calculate(msg.message)
    calc_context = ""
    if calc_result:
        calc_context = "\n\nCALCULATOR RESULT (include this naturally in your response):\n" + "\n".join(f"  {k}: {v}" for k, v in calc_result.items())

    # ── Chat history ────────────────────────────────────────────────────
    history_context = ""
    try:
        recent_msgs = await db.visor_chat.find(
            {"user_id": user_id}, {"_id": 0, "role": 1, "content": 1}
        ).sort("created_at", -1).limit(12).to_list(12)
        if recent_msgs:
            recent_msgs.reverse()
            lines = []
            for m in recent_msgs:
                role = "User" if m["role"] == "user" else "Visor"
                c = m["content"][:250] + "..." if len(m["content"]) > 250 else m["content"]
                lines.append(f"  {role}: {c}")
            history_context = "\n\nRECENT CHAT:\n" + "\n".join(lines)
    except Exception:
        pass

    # ── Send to LLM ─────────────────────────────────────────────────────
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"visor-{user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            system_message=VISOR_SYSTEM_PROMPT,
        )
        chat.with_model("openai", "gpt-5.2")

        full_message = f"{context}{live_prices}{news_context}{calc_context}{history_context}\n\nUser: {msg.message}"
        response_text = await chat.send_message(UserMessage(text=full_message))
    except Exception as e:
        logger.error(f"Visor AI error: {e}")
        response_text = "Abhi connection mein thoda issue aa raha hai. Ek baar phir try kar. Tab tak ye tip le: Apne monthly expenses review kar aur jo subscriptions use nahi ho rahe, unhe cancel kar — chhoti savings bhi badi hoti hain!"

    # ── Save AI response ────────────────────────────────────────────────
    ai_msg_id = str(uuid.uuid4())
    ai_now = datetime.now(timezone.utc).isoformat()
    await db.visor_chat.insert_one({
        "id": ai_msg_id, "user_id": user_id,
        "role": "assistant", "content": response_text, "created_at": ai_now,
    })

    return {
        "id": ai_msg_id,
        "user_msg_id": user_msg_id,
        "role": "assistant",
        "content": response_text,
        "calculator_result": calc_result,
        "created_at": ai_now,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  HISTORY & MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/visor-ai/history")
async def get_visor_history(user=Depends(get_current_user)):
    messages = await db.visor_chat.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return messages


@router.delete("/visor-ai/history")
async def clear_visor_history(user=Depends(get_current_user)):
    await db.visor_chat.delete_many({"user_id": user["id"]})
    return {"message": "Chat history cleared"}


@router.delete("/visor-ai/message/{message_id}")
async def delete_visor_message(message_id: str, user=Depends(get_current_user)):
    result = await db.visor_chat.delete_one({"id": message_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Message deleted"}
