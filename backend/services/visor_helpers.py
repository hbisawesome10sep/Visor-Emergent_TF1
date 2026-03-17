"""
Visor AI — Helper Functions
Ticker detection, live price fetching, web search, and auto-calculator intent detection.
"""
import re
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from database import db
from services.visor_calculators import (
    calc_sip, calc_stepup_sip, calc_emi, calc_compound_interest,
    calc_cagr, calc_fire, calc_ppf, calc_hra, calc_gratuity,
)

logger = logging.getLogger(__name__)
_yf_executor = ThreadPoolExecutor(max_workers=2)


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
    "sip", "emi", "hra", "ppf", "nps", "elss", "cagr", "fire",
    "fd", "rd", "nsc", "ulip", "epf", "vpf",
}


def detect_tickers(query: str) -> list:
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

async def fetch_commodity_prices(commodities: list) -> str:
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
                results.append(f"  {name.upper()}: \u20b9{price:,.0f} {unit}{chg}")
        except Exception:
            continue
    return "\n".join(results)


def fetch_yf_prices(tickers: list) -> str:
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
                        cap_str = f" | MCap: \u20b9{cap/1e12:.2f}T"
                    elif cap >= 1e9:
                        cap_str = f" | MCap: \u20b9{cap/1e7:.0f}Cr"
                results.append(f"  {name.upper()} ({ticker.replace('.NS','').replace('.BO','')}): \u20b9{price:,.2f}{chg}{cap_str}")
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


def needs_web_search(message: str) -> bool:
    return bool(_NEWS_TRIGGERS.search(message))


async def web_search_financial(query: str) -> str:
    try:
        from ddgs import DDGS
        loop = asyncio.get_running_loop()
        words = query.lower().split()
        hindi_map = {
            "aaj": "today", "kal": "yesterday", "khabar": "news", "naya": "new",
            "taza": "latest", "samachaar": "news", "bazaar": "market",
            "kya": "", "hai": "", "kaise": "how", "kitna": "how much",
            "mein": "in", "ka": "of", "ki": "of", "ke": "of",
            "batao": "", "dikhao": "", "bata": "", "scene": "update",
        }
        translated = []
        for w in words:
            if w in hindi_map:
                if hindi_map[w]: translated.append(hindi_map[w])
            else:
                translated.append(w)
        search_q = " ".join(translated[:10]) + " India finance"

        def _search():
            with DDGS() as ddgs:
                results = list(ddgs.text(search_q, max_results=5))
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


def auto_calculate(message: str) -> dict | None:
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
