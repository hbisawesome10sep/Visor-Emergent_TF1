from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_current_user
from models import AIMessageCreate
from config import EMERGENT_LLM_KEY
import re
import uuid
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Common Indian stocks/indices mapping to yfinance tickers
TICKER_MAP = {
    "reliance": "RELIANCE.NS", "ril": "RELIANCE.NS", "tcs": "TCS.NS", "infosys": "INFY.NS", "infy": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS", "hdfc": "HDFCBANK.NS", "icici bank": "ICICIBANK.NS",
    "icici": "ICICIBANK.NS", "sbi": "SBIN.NS", "kotak": "KOTAKBANK.NS",
    "axis bank": "AXISBANK.NS", "bajaj finance": "BAJFINANCE.NS",
    "wipro": "WIPRO.NS", "hcl tech": "HCLTECH.NS", "hcl": "HCLTECH.NS",
    "bharti airtel": "BHARTIARTL.NS", "airtel": "BHARTIARTL.NS",
    "itc": "ITC.NS", "maruti": "MARUTI.NS", "maruti suzuki": "MARUTI.NS",
    "asian paints": "ASIANPAINT.NS", "larsen": "LT.NS", "l&t": "LT.NS",
    "titan": "TITAN.NS", "sun pharma": "SUNPHARMA.NS", "bajaj finserv": "BAJAJFINSV.NS",
    "adani ports": "ADANIPORTS.NS", "adani enterprises": "ADANIENT.NS",
    "adani green": "ADANIGREEN.NS", "adani power": "ADANIPOWER.NS",
    "tata motors": "TATAMOTORS.NS", "tata steel": "TATASTEEL.NS",
    "tata power": "TATAPOWER.NS", "tata consumer": "TATACONSUM.NS",
    "tech mahindra": "TECHM.NS", "power grid": "POWERGRID.NS",
    "ntpc": "NTPC.NS", "ongc": "ONGC.NS", "coal india": "COALINDIA.NS",
    "ultratech": "ULTRACEMCO.NS", "grasim": "GRASIM.NS",
    "hindustan unilever": "HINDUNILVR.NS", "hul": "HINDUNILVR.NS",
    "nestle": "NESTLEIND.NS", "britannia": "BRITANNIA.NS",
    "divis lab": "DIVISLAB.NS", "dmart": "DMART.NS", "avenue supermarts": "DMART.NS",
    "zomato": "ZOMATO.NS", "paytm": "PAYTM.NS", "bhel": "BHEL.NS",
    "bpcl": "BPCL.NS", "ioc": "IOC.NS", "gail": "GAIL.NS", "sail": "SAIL.NS",
    "vedanta": "VEDL.NS", "hindalco": "HINDALCO.NS", "jswsteel": "JSWSTEEL.NS",
    "jsw steel": "JSWSTEEL.NS", "m&m": "M&M.NS", "mahindra": "M&M.NS",
    "bajaj auto": "BAJAJ-AUTO.NS", "hero": "HEROMOTOCO.NS",
    "indigo": "INDIGO.NS", "irctc": "IRCTC.NS", "hal": "HAL.NS",
    "torrent power": "TORNTPOWER.NS", "torrent pharma": "TORNTPHARM.NS",
    "tata elxsi": "TATAELXSI.NS", "dixon": "DIXON.NS", "polycab": "POLYCAB.NS",
    "pidilite": "PIDILITE.NS", "dabur": "DABUR.NS", "godrej": "GODREJCP.NS",
    "sbilife": "SBILIFE.NS", "sbi life": "SBILIFE.NS", "hdfc life": "HDFCLIFE.NS",
    "icici pru": "ICICIPRULI.NS", "lic": "LICI.NS", "ipl": "IPL.NS",
    "nifty": "^NSEI", "nifty 50": "^NSEI", "sensex": "^BSESN", "nifty bank": "^NSEBANK",
    "bank nifty": "^NSEBANK", "nifty it": "^CNXIT", "nifty pharma": "^CNXPHARMA",
    "gold": "INDIAN_MARKET:Gold", "silver": "INDIAN_MARKET:Silver",
    "copper": "HG=F",
    "crude oil": "CL=F", "crude": "CL=F", "natural gas": "NG=F",
    "gold etf": "GOLDBEES.NS", "goldbees": "GOLDBEES.NS",
    "nifty bees": "NIFTYBEES.NS", "niftybees": "NIFTYBEES.NS",
    "bank bees": "BANKBEES.NS", "bankbees": "BANKBEES.NS",
    "liquidbees": "LIQUIDBEES.NS", "silver etf": "SILVERBEES.NS",
}

_STOP_WORDS = {
    "what", "about", "how", "much", "the", "and", "for", "are", "but",
    "not", "you", "all", "any", "can", "had", "her", "was", "one", "our",
    "out", "get", "has", "him", "his", "she", "too", "its", "may", "let",
    "say", "few", "now", "old", "see", "way", "who", "did", "got", "just",
    "than", "them", "been", "from", "have", "into", "each", "make", "like",
    "long", "look", "many", "some", "more", "over", "such", "take", "that",
    "them", "then", "they", "this", "very", "when", "will", "with", "come",
    "also", "back", "been", "call", "does", "even", "find", "give", "good",
    "help", "here", "high", "keep", "know", "last", "live", "made", "most",
    "must", "name", "need", "next", "only", "show", "tell", "want", "well",
    "work", "year", "your", "give", "today", "price", "prices", "stock",
    "share", "shares", "should", "could", "would", "which", "where", "there",
    "their", "these", "those", "being", "doing", "having", "current", "please",
    "check", "buy", "sell", "hold", "fund", "funds", "invest", "money", "bank",
    "rate", "value", "market", "trade", "power", "energy", "pharma", "what",
    "return", "returns", "risk", "profit", "loss", "gains", "gain",
    "amount", "pay", "paid", "cost", "total", "average", "spend", "save",
    "per", "gram", "grams", "half", "full", "kilo", "lakh", "crore",
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
    direct = re.findall(r'\b([A-Z]{3,15})\b', q.upper())
    for sym in direct:
        ticker = f"{sym}.NS"
        if ticker not in [t for t, _ in found] and sym.lower() not in TICKER_MAP and sym.lower() not in _STOP_WORDS:
            found.append((ticker, sym))
    return found[:5]


async def _fetch_indian_commodity_prices(commodities: list) -> str:
    results = []
    for name in commodities:
        try:
            md = await db.market_data.find_one({"key": {"$regex": name, "$options": "i"}}, {"_id": 0})
            if md and md.get("price"):
                price = md["price"]
                change = md.get("change", 0)
                change_pct = md.get("change_pct", 0)
                unit = "per 10g" if "gold" in name.lower() else "per 1Kg"
                chg_str = f" | Change: {'+'if change>=0 else ''}{change:.0f} ({'+'if change_pct>=0 else ''}{change_pct:.2f}%)" if change else ""
                results.append(f"  {name.upper()} (Indian Price): ₹{price:,.0f} {unit}{chg_str}")
                if "gold" in name.lower():
                    results.append(f"    → Per gram: ₹{price/10:,.0f} | Per 100g: ₹{price*10:,.0f}")
                elif "silver" in name.lower():
                    results.append(f"    → Per gram: ₹{price/1000:,.2f} | Per 100g: ₹{price/10:,.0f} | Per 500g: ₹{price/2:,.0f}")
        except Exception:
            continue
    return "\n".join(results) if results else ""


def _fetch_ai_live_prices(tickers: list) -> str:
    import yfinance as yf
    if not tickers:
        return ""
    results = []
    for ticker, name in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.fast_info
            price = getattr(info, 'last_price', None)
            prev_close = getattr(info, 'previous_close', None)
            if price and price > 0:
                change = ""
                if prev_close and prev_close > 0:
                    chg = price - prev_close
                    chg_pct = (chg / prev_close) * 100
                    change = f" | Change: {'+'if chg>=0 else ''}{chg:.2f} ({'+'if chg_pct>=0 else ''}{chg_pct:.2f}%)"
                day_high = getattr(info, 'day_high', None)
                day_low = getattr(info, 'day_low', None)
                cap = getattr(info, 'market_cap', None)
                extra = ""
                if day_high and day_low:
                    extra += f" | Day Range: {day_low:.2f}-{day_high:.2f}"
                if cap and cap > 0:
                    if cap >= 1e12:
                        extra += f" | MCap: ₹{cap/1e12:.2f}T"
                    elif cap >= 1e9:
                        extra += f" | MCap: ₹{cap/1e7:.0f}Cr"
                results.append(f"  {name.upper()} ({ticker}): ₹{price:,.2f}{change}{extra}")
        except Exception:
            continue
    if not results:
        return ""
    return "\nLIVE MARKET PRICES (fetched just now):\n" + "\n".join(results)


@router.post("/ai/chat")
async def ai_chat(msg: AIMessageCreate, user=Depends(get_current_user)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    user_id = user["id"]
    now = datetime.now(timezone.utc).isoformat()

    user_msg_id = str(uuid.uuid4())
    await db.chat_history.insert_one({
        "id": user_msg_id, "user_id": user_id,
        "role": "user", "content": msg.message, "created_at": now,
    })

    # Gather user data
    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    risk_doc = await db.risk_profiles.find_one({"user_id": user_id}, {"_id": 0})
    holdings = await db.holdings.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    sips = await db.recurring_transactions.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    budgets = await db.budgets.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(20)

    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments_txn = sum(t["amount"] for t in txns if t["type"] == "investment")

    total_holdings_invested = sum(h.get("invested_value", 0) or (h.get("buy_price", 0) * h.get("quantity", 0)) for h in holdings)
    total_holdings_current = sum(h.get("current_value", 0) or (h.get("buy_price", 0) * h.get("quantity", 0)) for h in holdings)
    holdings_gain_loss = total_holdings_current - total_holdings_invested
    holdings_gain_pct = (holdings_gain_loss / total_holdings_invested * 100) if total_holdings_invested > 0 else 0

    holdings_summary = []
    for h in holdings[:15]:
        name = h.get("name", "Unknown")
        qty = h.get("quantity", 0)
        invested = h.get("invested_value", 0) or (h.get("buy_price", 0) * qty)
        current = h.get("current_value", 0) or invested
        gain = current - invested
        gain_pct = (gain / invested * 100) if invested > 0 else 0
        holdings_summary.append(f"{name}: Qty={qty}, Invested=₹{invested:,.0f}, Current=₹{current:,.0f} ({gain_pct:+.1f}%)")

    category_breakdown = {}
    for t in txns:
        if t["type"] == "expense":
            cat = t["category"]
            category_breakdown[cat] = category_breakdown.get(cat, 0) + t["amount"]

    monthly_trends = {}
    for t in txns:
        dt_str = t.get("date", "")
        if dt_str:
            month_key = dt_str[:7]
            if month_key not in monthly_trends:
                monthly_trends[month_key] = {"income": 0, "expenses": 0, "investments": 0}
            if t["type"] == "income":
                monthly_trends[month_key]["income"] += t["amount"]
            elif t["type"] == "expense":
                monthly_trends[month_key]["expenses"] += t["amount"]
            elif t["type"] == "investment":
                monthly_trends[month_key]["investments"] += t["amount"]
    monthly_trend_str = "\n".join(f"  {m}: Income=₹{d['income']:,.0f}, Expenses=₹{d['expenses']:,.0f}, Invest=₹{d['investments']:,.0f}" for m, d in sorted(monthly_trends.items())[-6:])

    goal_summary = [f"{g['title']}: ₹{g['current_amount']:,.0f}/₹{g['target_amount']:,.0f} ({(g['current_amount']/g['target_amount']*100) if g['target_amount']>0 else 0:.0f}%) - Deadline: {g.get('deadline','N/A')}" for g in goals]
    sip_summary = [f"{s.get('description','SIP')}: ₹{s.get('amount',0):,.0f}/{s.get('frequency','monthly')} in {s.get('category','N/A')}" for s in sips]
    budget_summary = [f"{b.get('category','N/A')}: ₹{b.get('spent',0):,.0f}/₹{b.get('limit',0) or b.get('amount',0):,.0f} ({(b.get('spent',0)/(b.get('limit',0) or b.get('amount',0) or 1)*100):.0f}% used)" for b in budgets]
    loan_summary = [f"{l.get('name','Loan')}: ₹{l.get('principal',0):,.0f} @ {l.get('interest_rate',0)}% for {l.get('tenure_years',0)}yrs, EMI=₹{l.get('emi',0):,.0f}" for l in loans]

    hs_income = total_income or 1
    hs_savings_rate = max(0, (hs_income - total_expenses) / hs_income * 100)
    hs_investment_rate = (total_investments_txn / hs_income * 100)
    hs_overall = min(100, hs_savings_rate * 0.35 + min(hs_investment_rate, 30) * 0.25 + max(0, 100 - (total_expenses / hs_income * 100)) * 0.25 + min((len(goals) > 0) * 50 + sum(1 for g in goals if g['current_amount'] >= g['target_amount'] * 0.5) * 25, 100) * 0.15)

    buy_sells = [t for t in txns if t.get("buy_sell")]
    buy_sell_summary = [f"{t.get('buy_sell','').upper()} {t.get('description','')}: {t.get('units',0)} units @ ₹{t.get('price_per_unit',0):,.0f} = ₹{t['amount']:,.0f} on {t.get('date','')}" for t in buy_sells[:10]]

    cap_gains_context = ""
    sell_txns_for_cg = [t for t in txns if t.get("buy_sell") == "sell"]
    if sell_txns_for_cg:
        total_cg = 0
        for st in sell_txns_for_cg:
            desc = st.get("description", "")
            buy_match = next((b for b in txns if b.get("buy_sell") == "buy" and b.get("description", "").lower() == desc.lower()), None)
            if buy_match:
                total_cg += st["amount"] - buy_match.get("amount", 0)
        cap_gains_context = f"\n- Estimated Capital Gains from Sell Transactions: ₹{total_cg:,.0f}"

    risk_context = f"\n- Risk Profile: {risk_doc.get('profile', 'Not assessed')} (Score: {risk_doc.get('score', 0):.1f}/5)" if risk_doc else ""

    context = f"""User Financial Profile (COMPLETE APP DATA):

INCOME & EXPENSES:
- Total Income: ₹{total_income:,.2f}
- Total Expenses: ₹{total_expenses:,.2f}
- Investment Transactions: ₹{total_investments_txn:,.2f}
- Net Balance: ₹{total_income - total_expenses - total_investments_txn:,.2f}
- Savings Rate: {((total_income - total_expenses) / max(total_income, 1) * 100):.1f}%
- Top Expense Categories: {', '.join(f'{k}: ₹{v:,.0f}' for k, v in sorted(category_breakdown.items(), key=lambda x: -x[1])[:5])}

MONTHLY TRENDS (Last 6 Months):
{monthly_trend_str if monthly_trend_str else '  No monthly data available'}

FINANCIAL HEALTH SCORE: {hs_overall:.1f}/100{risk_context}

INVESTMENT PORTFOLIO ({len(holdings)} holdings):
- Total Invested: ₹{total_holdings_invested:,.2f}
- Current Value: ₹{total_holdings_current:,.2f}
- Total Gain/Loss: ₹{holdings_gain_loss:,.2f} ({holdings_gain_pct:+.1f}%)
- Holdings:
  {chr(10).join('  ' + h for h in holdings_summary) if holdings_summary else '  None'}

BUY/SELL TRANSACTIONS:
  {chr(10).join('  ' + b for b in buy_sell_summary) if buy_sell_summary else '  None'}{cap_gains_context}

SIPS & RECURRING INVESTMENTS ({len(sips)}):
  {chr(10).join('  ' + s for s in sip_summary) if sip_summary else '  None'}

FINANCIAL GOALS ({len(goals)}):
  {chr(10).join('  ' + g for g in goal_summary) if goal_summary else '  None set'}

BUDGETS:
  {chr(10).join('  ' + b for b in budget_summary) if budget_summary else '  No budgets set'}

LOANS/EMIs:
  {chr(10).join('  ' + l for l in loan_summary) if loan_summary else '  No loans'}

RECENT TRANSACTIONS (Last 10):
  {chr(10).join('  ' + f"{t['date']} | {t['type'].upper()} | {t['category']} | ₹{t['amount']:,.0f} | {t.get('description','')}" for t in sorted(txns, key=lambda x: x.get('date',''), reverse=True)[:10]) if txns else '  None'}
"""

    screen_context_info = ""
    if msg.screen_context:
        screen_context_info = f"""

CURRENT SCREEN CONTEXT:
The user is currently viewing a specific screen in the app. Here's what they're looking at:
{msg.screen_context}

Use this context to provide more relevant and contextual responses. If the user asks a general question,
you can proactively provide insights related to what they're viewing."""

    system_msg = f"""You are Visor AI — a STRICT Indian personal finance advisor. You have FULL access to the user's financial data in this app.

ABSOLUTE RULE — FINANCE ONLY:
You MUST ONLY discuss topics related to personal finance, money, investing, taxation, banking, insurance, loans, budgeting, savings, retirement planning, and the Indian/global financial markets.
If the user asks about ANYTHING outside finance (medical, health, cooking, entertainment, travel, technology, relationships, etc.), you MUST politely refuse with a response like:
"I'm Visor, your dedicated financial advisor. I can only help with finance, investing, taxes, and money-related topics. How can I help you with your finances today?"
Do NOT attempt to answer, speculate on, or engage with non-finance questions under ANY circumstances. Not even partially. No exceptions.

IDENTITY & PROFESSIONALISM:
- You ARE Visor. You are NOT a third-party tool, chatbot, or wrapper. Never reference any internal systems, data feeds, data sources, APIs, watchlists, or technical details.
- NEVER say things like "available in your app's feed", "your LIVE MARKET PRICES feed", "add it to your watchlist", "enable in your live prices", "your current feed" or similar.
- If you have the live price for a stock, share it naturally as if you looked it up yourself.
- If you DON'T have the live price for a specific stock, say something natural like: "I couldn't pull up the live price for [stock name] right now. You can check it on NSE/BSE directly. Want me to help with something else?"
- Never expose ticker symbols like ".NS" or ".BO" in your responses. Use the company name instead.
- You speak as Visor with full authority and confidence. You are the user's trusted financial advisor.

KEY GUIDELINES:
- Always use INR for currency, format in lakhs/crores
- Reference Indian tax slabs, Section 80C, 80D, 80CCD deductions where relevant
- Suggest Indian instruments: PPF, NPS, ELSS, SIP, FD, Gold ETFs, SGBs
- Consider Indian inflation (~5-6%) in calculations
- Be concise, actionable, and encouraging
- Reference the user's ACTUAL data from context when answering
- Keep responses under 200 words unless detailed analysis is needed
- If the user asks for live prices, use the LIVE MARKET PRICES data provided in context
- You can discuss stocks, mutual funds, ETFs, F&O, commodities (gold, silver, copper, crude), indices
- When discussing investments, provide balanced risk-reward perspectives
- PAY ATTENTION to which screen the user is viewing{screen_context_info}"""

    # Fetch live prices
    live_prices_context = ""
    try:
        tickers = _detect_tickers(msg.message)
        if tickers:
            indian_commodities = [(t, n) for t, n in tickers if t.startswith("INDIAN_MARKET:")]
            yf_tickers = [(t, n) for t, n in tickers if not t.startswith("INDIAN_MARKET:")]

            parts = []
            if indian_commodities:
                commodity_names = [t.split(":")[1] for t, _ in indian_commodities]
                indian_prices = await _fetch_indian_commodity_prices(commodity_names)
                if indian_prices:
                    parts.append(indian_prices)

            if yf_tickers:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as pool:
                    loop = asyncio.get_running_loop()
                    yf_prices = await loop.run_in_executor(pool, _fetch_ai_live_prices, yf_tickers)
                if yf_prices:
                    parts.append(yf_prices.replace("\nLIVE MARKET PRICES (fetched just now):\n", ""))

            if parts:
                live_prices_context = "\nLIVE MARKET PRICES (fetched just now, all in ₹ INR):\n" + "\n".join(parts)
                logger.info(f"Live prices fetched for: {[n for _, n in tickers]}")
    except Exception as e:
        logger.warning(f"Live price fetch failed: {e}")

    # Chat history
    chat_history_context = ""
    try:
        recent_msgs = await db.chat_history.find(
            {"user_id": user_id}, {"_id": 0, "role": 1, "content": 1}
        ).sort("created_at", -1).limit(10).to_list(10)
        if recent_msgs:
            recent_msgs.reverse()
            history_lines = []
            for m in recent_msgs:
                role = "User" if m["role"] == "user" else "Visor"
                content = m["content"][:300] + "..." if len(m["content"]) > 300 else m["content"]
                history_lines.append(f"  {role}: {content}")
            chat_history_context = f"\n\nRECENT CONVERSATION HISTORY (for context continuity):\n" + "\n".join(history_lines)
    except Exception:
        pass

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"visor-{user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            system_message=system_msg,
        )
        chat.with_model("openai", "gpt-5.2")

        user_message = UserMessage(text=f"{context}{live_prices_context}{chat_history_context}\n\nUser Question: {msg.message}")
        response_text = await chat.send_message(user_message)

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        response_text = "I'm having trouble connecting right now. Please try again in a moment. In the meantime, here's a tip: Review your monthly expenses and identify subscriptions you no longer use—small savings add up!"

    ai_msg_id = str(uuid.uuid4())
    ai_now = datetime.now(timezone.utc).isoformat()
    await db.chat_history.insert_one({
        "id": ai_msg_id, "user_id": user_id,
        "role": "assistant", "content": response_text, "created_at": ai_now,
    })

    return {
        "id": ai_msg_id, "user_msg_id": user_msg_id,
        "role": "assistant", "content": response_text, "created_at": ai_now,
    }


@router.get("/ai/history")
async def get_ai_history(user=Depends(get_current_user)):
    messages = await db.chat_history.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return messages


@router.delete("/ai/history")
async def clear_ai_history(user=Depends(get_current_user)):
    await db.chat_history.delete_many({"user_id": user["id"]})
    return {"message": "Chat history cleared"}


@router.delete("/ai/message/{message_id}")
async def delete_single_message(message_id: str, user=Depends(get_current_user)):
    result = await db.chat_history.delete_one({"id": message_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Message deleted"}
