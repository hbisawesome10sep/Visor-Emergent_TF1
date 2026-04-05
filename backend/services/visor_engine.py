"""
Visor AI — Core Processing Engine
Shared by both text and voice chat endpoints.
Handles: message storage, financial context, live prices, news, calculator, LLM call.
Integrates: Multi-model routing (P0) + Persistent AI memory (P0).
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from database import db
from config import EMERGENT_LLM_KEY
from services.visor_prompt import VISOR_SYSTEM_PROMPT
from services.visor_helpers import (
    detect_tickers, fetch_commodity_prices, fetch_yf_prices,
    needs_web_search, web_search_financial, auto_calculate, _yf_executor,
)
from services.query_router import get_model_for_query
from services.ai_memory import extract_and_store_memory, get_memory_context
from services.financial_personality import compute_financial_personality, get_cached_personality, get_personality_context
from services.tax_knowledge_base import get_tax_knowledge_context

logger = logging.getLogger(__name__)


async def process_visor_message(
    user_id: str,
    message: str,
    screen_context: str = None,
    input_type: str = "text",
) -> dict:
    """
    Core Visor AI processing pipeline.
    Returns dict with: id, user_msg_id, role, content, calculator_result, input_type, created_at
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    now = datetime.now(timezone.utc).isoformat()

    # ── Save user message ────────────────────────────────────────────
    user_msg_id = str(uuid.uuid4())
    await db.visor_chat.insert_one({
        "id": user_msg_id, "user_id": user_id,
        "role": "user", "content": message,
        "input_type": input_type, "created_at": now,
    })

    # ── Gather ALL user financial data ───────────────────────────────
    txns, goals, risk_doc, holdings, sips, budgets, loans, credit_cards, bank_accounts, assets, tax_deds, salary_profile, income_profile, auto_deds, tax_docs, freelancer_profile, business_profile, investor_profile, rental_profile = (
        await asyncio.gather(
            db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(500),
            db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(50),
            db.risk_profiles.find_one({"user_id": user_id}, {"_id": 0}),
            db.holdings.find({"user_id": user_id}, {"_id": 0}).to_list(100),
            db.recurring_transactions.find({"user_id": user_id}, {"_id": 0}).to_list(50),
            db.budgets.find({"user_id": user_id}, {"_id": 0}).to_list(50),
            db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(20),
            db.credit_cards.find({"user_id": user_id}, {"_id": 0}).to_list(10),
            db.bank_accounts.find({"user_id": user_id}, {"_id": 0}).to_list(10),
            db.fixed_assets.find({"user_id": user_id}, {"_id": 0}).to_list(50),
            db.user_tax_deductions.find({"user_id": user_id}, {"_id": 0}).to_list(50),
            db.salary_profiles.find_one({"user_id": user_id}, {"_id": 0}),
            db.tax_income_profiles.find_one({"user_id": user_id}, {"_id": 0}),
            db.auto_tax_deductions.find({"user_id": user_id, "fy": "2025-26"}, {"_id": 0}).to_list(100),
            db.tax_documents.find({"user_id": user_id}, {"_id": 0}).to_list(10),
            db.freelancer_profiles.find_one({"user_id": user_id, "fy": "2025-26"}, {"_id": 0}),
            db.business_profiles.find_one({"user_id": user_id, "fy": "2025-26"}, {"_id": 0}),
            db.investor_profiles.find_one({"user_id": user_id, "fy": "2025-26"}, {"_id": 0}),
            db.rental_profiles.find_one({"user_id": user_id, "fy": "2025-26"}, {"_id": 0}),
            return_exceptions=True,
        )
    )

    for name, val in [("txns", txns), ("goals", goals), ("holdings", holdings), ("sips", sips),
                      ("budgets", budgets), ("loans", loans), ("credit_cards", credit_cards),
                      ("bank_accounts", bank_accounts), ("assets", assets), ("tax_deds", tax_deds),
                      ("auto_deds", auto_deds), ("tax_docs", tax_docs)]:
        if isinstance(val, Exception):
            logger.warning(f"Failed to fetch {name}: {val}")
            locals()[name] = []
    if isinstance(risk_doc, Exception):
        risk_doc = None
    if isinstance(salary_profile, Exception):
        salary_profile = None
    if isinstance(income_profile, Exception):
        income_profile = None
    if isinstance(freelancer_profile, Exception):
        freelancer_profile = None
    if isinstance(business_profile, Exception):
        business_profile = None
    if isinstance(investor_profile, Exception):
        investor_profile = None
    if isinstance(rental_profile, Exception):
        rental_profile = None

    # ── Build financial context ──────────────────────────────────────
    total_income = sum(t["amount"] for t in txns if t.get("type") == "income") if isinstance(txns, list) else 0
    total_expenses = sum(t["amount"] for t in txns if t.get("type") == "expense") if isinstance(txns, list) else 0
    total_inv_txn = sum(t["amount"] for t in txns if t.get("type") == "investment") if isinstance(txns, list) else 0

    total_inv_value = sum(h.get("invested_value", 0) or (h.get("buy_price", 0) * h.get("quantity", 0)) for h in holdings) if isinstance(holdings, list) else 0
    total_cur_value = sum(h.get("current_value", 0) or total_inv_value for h in holdings) if isinstance(holdings, list) else 0
    gain_loss = total_cur_value - total_inv_value
    gain_pct = (gain_loss / total_inv_value * 100) if total_inv_value > 0 else 0

    cat_exp = {}
    if isinstance(txns, list):
        for t in txns:
            if t.get("type") == "expense":
                cat_exp[t["category"]] = cat_exp.get(t["category"], 0) + t["amount"]

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

    h_summary = []
    if isinstance(holdings, list):
        for h in holdings[:15]:
            inv = h.get("invested_value", 0) or (h.get("buy_price", 0) * h.get("quantity", 0))
            cur = h.get("current_value", 0) or inv
            g = ((cur - inv) / inv * 100) if inv > 0 else 0
            h_summary.append(f"  {h.get('name','?')}: Qty {h.get('quantity',0):.2f}, Invested \u20b9{inv:,.0f}, Current \u20b9{cur:,.0f} ({g:+.1f}%)")

    goal_str = "\n".join(f"  {g['title']}: \u20b9{g['current_amount']:,.0f}/\u20b9{g['target_amount']:,.0f} ({(g['current_amount']/g['target_amount']*100) if g['target_amount']>0 else 0:.0f}%)" for g in goals) if isinstance(goals, list) and goals else "  None set"
    sip_str = "\n".join(f"  {s.get('description', s.get('name','SIP'))}: \u20b9{s.get('amount',0):,.0f}/{s.get('frequency','monthly')}" for s in sips) if isinstance(sips, list) and sips else "  None"
    budget_str = "\n".join(f"  {b.get('category','?')}: \u20b9{b.get('spent',0):,.0f}/\u20b9{b.get('limit',0) or b.get('amount',0):,.0f}" for b in budgets) if isinstance(budgets, list) and budgets else "  None"
    loan_str = "\n".join(f"  {l.get('name','Loan')}: \u20b9{l.get('principal_amount', l.get('principal',0)):,.0f} @ {l.get('interest_rate',0)}%, EMI \u20b9{l.get('emi_amount', l.get('emi',0)):,.0f}" for l in loans) if isinstance(loans, list) and loans else "  None"
    cc_str = "\n".join(f"  {c.get('card_name', c.get('name','Card'))}: Limit \u20b9{c.get('credit_limit',0):,.0f}, Outstanding \u20b9{c.get('outstanding',0):,.0f}" for c in credit_cards) if isinstance(credit_cards, list) and credit_cards else "  None"
    bank_str = "\n".join(f"  {b.get('bank_name', b.get('name','Account'))}: \u20b9{b.get('balance',0):,.0f}" for b in bank_accounts) if isinstance(bank_accounts, list) and bank_accounts else "  None"
    asset_str = "\n".join(f"  {a.get('name','?')}: \u20b9{a.get('current_value', a.get('purchase_value',0)):,.0f}" for a in assets) if isinstance(assets, list) and assets else "  None"
    tax_str = "\n".join(f"  {d.get('section','?')} - {d.get('name','?')}: \u20b9{d.get('invested_amount',0):,.0f}" for d in tax_deds) if isinstance(tax_deds, list) and tax_deds else "  None claimed"

    # Auto-detected deductions from transactions
    auto_ded_str = ""
    if isinstance(auto_deds, list) and auto_deds:
        # Group by section
        section_totals = {}
        for d in auto_deds:
            sec = d.get("section", "Other")
            section_totals[sec] = section_totals.get(sec, 0) + d.get("amount", 0)
        auto_ded_str = "\n  Auto-detected: " + ", ".join(f"{s}: \u20b9{a:,.0f}" for s, a in section_totals.items())
    
    # Uploaded tax documents
    tax_docs_str = ""
    if isinstance(tax_docs, list) and tax_docs:
        tax_docs_str = f"\n  Uploaded Docs: {', '.join(d.get('document_type', 'Unknown') for d in tax_docs)}"

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

    # ── Build salary / tax context ────────────────────────────────────
    salary_ctx = ""
    if salary_profile and isinstance(salary_profile, dict):
        city_type = salary_profile.get("city_type", "non_metro")
        # Inline HRA computation (mirror of tax_enhanced.compute_hra)
        monthly_basic = salary_profile.get("monthly_basic", 0)
        monthly_hra = salary_profile.get("monthly_hra", 0)
        monthly_rent = salary_profile.get("monthly_rent", 0)
        c1 = monthly_hra * 12
        c2 = monthly_basic * 12 * (0.50 if city_type == "metro" else 0.40)
        c3 = max(0, monthly_rent * 12 - monthly_basic * 12 * 0.10)
        hra_exemption = min(c1, c2, c3) if salary_profile.get("is_rent_paid") and monthly_rent > 0 else 0
        rupee = "\u20b9"
        rent_str = f"Yes, {rupee}{monthly_rent:,.0f}/month" if salary_profile.get("is_rent_paid") else "No"
        salary_ctx = (
            f"\nSALARY PROFILE (FY {salary_profile.get('fy', '2025-26')}):"
            f"\n- Employer: {salary_profile.get('employer_name', 'N/A')}, City: {salary_profile.get('residence_city', 'N/A')} ({city_type})"
            f"\n- Monthly Basic: {rupee}{monthly_basic:,.0f} | HRA: {rupee}{monthly_hra:,.0f} | Gross Monthly: {rupee}{salary_profile.get('gross_monthly', 0):,.0f}"
            f"\n- Annual Gross (incl. bonus): {rupee}{salary_profile.get('gross_annual', 0):,.0f}"
            f"\n- EPF (Employee): {rupee}{salary_profile.get('employee_pf_monthly', 0):,.0f}/month"
            f"\n- Monthly TDS by employer: {rupee}{salary_profile.get('tds_monthly', 0):,.0f}"
            f"\n- Rent Paid: {rent_str}"
            f"\n- HRA Exemption (computed): {rupee}{hra_exemption:,.0f}/year"
        )

    income_profile_ctx = ""
    if income_profile and isinstance(income_profile, dict):
        income_types = income_profile.get("income_types", [])
        if income_types:
            income_profile_ctx = f"\nINCOME PROFILE: {', '.join(income_types)} (Primary: {income_profile.get('primary_income_type', 'salaried')})"

    # Non-salaried income profiles context
    nonsalaried_ctx = ""
    if freelancer_profile and isinstance(freelancer_profile, dict):
        gross = freelancer_profile.get("gross_receipts", 0)
        taxable = gross * 0.50 if freelancer_profile.get("use_presumptive") else gross - freelancer_profile.get("expenses_claimed", gross * 0.30)
        nonsalaried_ctx += f"\n  Freelancer (44ADA): Gross \u20b9{gross:,.0f}, Taxable \u20b9{taxable:,.0f}, Profession: {freelancer_profile.get('profession', 'N/A')}"
    if business_profile and isinstance(business_profile, dict):
        turnover = business_profile.get("gross_turnover", 0)
        digital_pct = business_profile.get("digital_receipts_pct", 60) / 100
        taxable = turnover * digital_pct * 0.06 + turnover * (1 - digital_pct) * 0.08
        nonsalaried_ctx += f"\n  Business (44AD): Turnover \u20b9{turnover:,.0f}, Taxable \u20b9{taxable:,.0f}, Type: {business_profile.get('business_type', 'N/A')}"
    if investor_profile and isinstance(investor_profile, dict):
        fo_profit = investor_profile.get("futures_profit", 0) + investor_profile.get("options_profit", 0)
        intraday = investor_profile.get("intraday_profit", 0)
        crypto = investor_profile.get("crypto_profit", 0)
        if fo_profit or intraday or crypto:
            nonsalaried_ctx += f"\n  Investor/Trader: F&O P/L \u20b9{fo_profit:,.0f}, Intraday \u20b9{intraday:,.0f}, Crypto \u20b9{crypto:,.0f}"
    if rental_profile and isinstance(rental_profile, dict):
        props = rental_profile.get("properties", [])
        total_rent = sum(p.get("gross_annual_rent", 0) for p in props)
        if total_rent:
            nonsalaried_ctx += f"\n  Rental Income: {len(props)} properties, Gross \u20b9{total_rent:,.0f}/year"

    context = f"""USER FINANCIAL PROFILE:

SUMMARY:
- Total Income: \u20b9{total_income:,.0f} | Total Expenses: \u20b9{total_expenses:,.0f}
- Savings Rate: {savings_rate:.1f}% | Investment Transactions: \u20b9{total_inv_txn:,.0f}
- {risk_str}{income_profile_ctx}

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
TAX DEDUCTIONS: {tax_str}{auto_ded_str}{tax_docs_str}{salary_ctx}{nonsalaried_ctx}

RECENT TRANSACTIONS:
{recent_txn or '  None'}"""

    if screen_context:
        context += f"\n\nCURRENT SCREEN: {screen_context}"

    # ── Live prices ──────────────────────────────────────────────────
    live_prices = ""
    try:
        tickers = detect_tickers(message)
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

    # ── Web search for news ──────────────────────────────────────────
    news_context = ""
    if needs_web_search(message):
        news_context = await web_search_financial(message)
        if news_context:
            news_context = "\n\n" + news_context

    # ── Auto calculator ──────────────────────────────────────────────
    calc_result = auto_calculate(message)
    calc_context = ""
    if calc_result:
        calc_context = "\n\nCALCULATOR RESULT (include this naturally in your response):\n" + "\n".join(f"  {k}: {v}" for k, v in calc_result.items())

    # ── Chat history ─────────────────────────────────────────────────
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

    # ── Fetch persistent memory ───────────────────────────────────────
    memory_context = ""
    try:
        memory_context = await get_memory_context(user_id)
    except Exception as e:
        logger.warning(f"Memory fetch failed: {e}")

    # ── Financial personality context ─────────────────────────────────
    personality_context = ""
    try:
        cached_personality = await get_cached_personality(user_id)
        if cached_personality:
            personality_context = get_personality_context(cached_personality)
    except Exception as e:
        logger.warning(f"Personality fetch failed: {e}")

    # ── Tax knowledge base (RAG-lite) ─────────────────────────────────
    tax_knowledge = ""
    try:
        tax_knowledge = get_tax_knowledge_context(message)
    except Exception as e:
        logger.warning(f"Tax knowledge fetch failed: {e}")

    # ── Select model via query router ────────────────────────────────
    selected_model = get_model_for_query(message, has_calculator_result=bool(calc_result))
    logger.info(f"Visor AI model: {selected_model} for user {user_id}")

    # ── Send to LLM ──────────────────────────────────────────────────
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"visor-{user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            system_message=VISOR_SYSTEM_PROMPT,
        )
        chat.with_model("openai", selected_model)

        full_message = f"{context}{memory_context}{personality_context}{tax_knowledge}{live_prices}{news_context}{calc_context}{history_context}\n\nUser: {message}"
        response_text = await chat.send_message(UserMessage(text=full_message))
    except Exception as e:
        logger.error(f"Visor AI error: {e}")
        response_text = "Abhi connection mein thoda issue aa raha hai. Ek baar phir try kar. Tab tak ye tip le: Apne monthly expenses review kar aur jo subscriptions use nahi ho rahe, unhe cancel kar — chhoti savings bhi badi hoti hain!"

    # ── Save AI response ─────────────────────────────────────────────
    ai_msg_id = str(uuid.uuid4())
    ai_now = datetime.now(timezone.utc).isoformat()
    await db.visor_chat.insert_one({
        "id": ai_msg_id, "user_id": user_id,
        "role": "assistant", "content": response_text,
        "input_type": input_type, "created_at": ai_now,
        "model_used": selected_model,
    })

    # ── Extract and store memory (background, non-blocking) ──────────
    asyncio.create_task(extract_and_store_memory(user_id, message, response_text))

    return {
        "id": ai_msg_id,
        "user_msg_id": user_msg_id,
        "role": "assistant",
        "content": response_text,
        "calculator_result": calc_result,
        "input_type": input_type,
        "created_at": ai_now,
        "model_used": selected_model,
    }
