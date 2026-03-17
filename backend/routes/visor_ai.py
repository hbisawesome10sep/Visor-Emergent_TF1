"""
Visor AI Agent — Unified Financial Intelligence Endpoint
India-first, multilingual, context-aware financial companion.

Route handler only — business logic lives in /services/
"""
from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_current_user
from models import AIMessageCreate
from config import EMERGENT_LLM_KEY
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from services.visor_prompt import VISOR_SYSTEM_PROMPT
from services.visor_helpers import (
    detect_tickers, fetch_commodity_prices, fetch_yf_prices,
    needs_web_search, web_search_financial, auto_calculate, _yf_executor,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


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
    trend_str = "\n".join(f"  {m}: Income \u20b9{d['income']:,.0f} | Expenses \u20b9{d['expenses']:,.0f} | Invest \u20b9{d['investments']:,.0f}" for m, d in sorted(monthly.items())[-6:])

    # Holdings summary
    h_summary = []
    if isinstance(holdings, list):
        for h in holdings[:15]:
            inv = h.get("invested_value", 0) or (h.get("buy_price", 0) * h.get("quantity", 0))
            cur = h.get("current_value", 0) or inv
            g = ((cur - inv) / inv * 100) if inv > 0 else 0
            h_summary.append(f"  {h.get('name','?')}: Qty {h.get('quantity',0):.2f}, Invested \u20b9{inv:,.0f}, Current \u20b9{cur:,.0f} ({g:+.1f}%)")

    # Goals, SIPs, Budgets, Loans, CCs, Bank accounts, Assets, Tax
    goal_str = "\n".join(f"  {g['title']}: \u20b9{g['current_amount']:,.0f}/\u20b9{g['target_amount']:,.0f} ({(g['current_amount']/g['target_amount']*100) if g['target_amount']>0 else 0:.0f}%)" for g in goals) if isinstance(goals, list) and goals else "  None set"
    sip_str = "\n".join(f"  {s.get('description', s.get('name','SIP'))}: \u20b9{s.get('amount',0):,.0f}/{s.get('frequency','monthly')}" for s in sips) if isinstance(sips, list) and sips else "  None"
    budget_str = "\n".join(f"  {b.get('category','?')}: \u20b9{b.get('spent',0):,.0f}/\u20b9{b.get('limit',0) or b.get('amount',0):,.0f}" for b in budgets) if isinstance(budgets, list) and budgets else "  None"
    loan_str = "\n".join(f"  {l.get('name','Loan')}: \u20b9{l.get('principal_amount', l.get('principal',0)):,.0f} @ {l.get('interest_rate',0)}%, EMI \u20b9{l.get('emi_amount', l.get('emi',0)):,.0f}" for l in loans) if isinstance(loans, list) and loans else "  None"
    cc_str = "\n".join(f"  {c.get('card_name', c.get('name','Card'))}: Limit \u20b9{c.get('credit_limit',0):,.0f}, Outstanding \u20b9{c.get('outstanding',0):,.0f}" for c in credit_cards) if isinstance(credit_cards, list) and credit_cards else "  None"
    bank_str = "\n".join(f"  {b.get('bank_name', b.get('name','Account'))}: \u20b9{b.get('balance',0):,.0f}" for b in bank_accounts) if isinstance(bank_accounts, list) and bank_accounts else "  None"
    asset_str = "\n".join(f"  {a.get('name','?')}: \u20b9{a.get('current_value', a.get('purchase_value',0)):,.0f}" for a in assets) if isinstance(assets, list) and assets else "  None"
    tax_str = "\n".join(f"  {d.get('section','?')} - {d.get('name','?')}: \u20b9{d.get('invested_amount',0):,.0f}" for d in tax_deds) if isinstance(tax_deds, list) and tax_deds else "  None claimed"

    risk_str = f"Risk Profile: {risk_doc.get('profile', 'Not assessed')} (Score: {risk_doc.get('score', 0):.1f}/5)" if risk_doc and isinstance(risk_doc, dict) else "Not assessed"

    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0

    recent_txn = ""
    if isinstance(txns, list):
        sorted_txns = sorted(txns, key=lambda x: x.get('date', ''), reverse=True)[:8]
        recent_txn = "\n".join(f"  {t['date']} | {t['type'].upper()} | {t['category']} | \u20b9{t['amount']:,.0f} | {t.get('description','')}" for t in sorted_txns)

    NL = "\n"
    holdings_str = NL.join(h_summary) if h_summary else "  No holdings"
    top_exp_str = ", ".join(f"{k}: \u20b9{v:,.0f}" for k, v in sorted(cat_exp.items(), key=lambda x: -x[1])[:5]) if cat_exp else "None"
    n_holdings = len(holdings) if isinstance(holdings, list) else 0

    context = f"""USER FINANCIAL PROFILE:

SUMMARY:
- Total Income: \u20b9{total_income:,.0f} | Total Expenses: \u20b9{total_expenses:,.0f}
- Savings Rate: {savings_rate:.1f}% | Investment Transactions: \u20b9{total_inv_txn:,.0f}
- {risk_str}

TOP EXPENSES: {top_exp_str}

MONTHLY TRENDS (Last 6 Months):
{trend_str or '  No data'}

PORTFOLIO ({n_holdings} holdings):
- Invested: \u20b9{total_inv_value:,.0f} | Current: \u20b9{total_cur_value:,.0f} | Gain/Loss: \u20b9{gain_loss:,.0f} ({gain_pct:+.1f}%)
{holdings_str}

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
        tickers = detect_tickers(msg.message)
        if tickers:
            indian_tickers = [(t, n) for t, n in tickers if t.startswith("INDIAN_MARKET:")]
            yf_tickers = [(t, n) for t, n in tickers if not t.startswith("INDIAN_MARKET:")]
            parts = []
            if indian_tickers:
                names = [t.split(":")[1] for t, _ in indian_tickers]
                p = await fetch_commodity_prices(names)
                if p: parts.append(p)
            if yf_tickers:
                loop = asyncio.get_running_loop()
                p = await loop.run_in_executor(_yf_executor, fetch_yf_prices, yf_tickers)
                if p: parts.append(p)
            if parts:
                live_prices = "\nLIVE PRICES (just fetched):\n" + "\n".join(parts)
    except Exception as e:
        logger.warning(f"Price fetch error: {e}")

    # ── Web search for news ─────────────────────────────────────────────
    news_context = ""
    if needs_web_search(msg.message):
        news_context = await web_search_financial(msg.message)
        if news_context:
            news_context = "\n\n" + news_context

    # ── Auto calculator ─────────────────────────────────────────────────
    calc_result = auto_calculate(msg.message)
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
