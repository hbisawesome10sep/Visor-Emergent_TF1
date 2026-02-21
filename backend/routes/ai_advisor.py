from fastapi import APIRouter, HTTPException, Depends
from database import db
from auth import get_current_user
from models import AdvisorChatMessage, AdvisorChatResponse
from config import EMERGENT_LLM_KEY
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# Financial Calculator Functions
def calculate_sip_returns(monthly_investment: float, annual_return: float, years: int) -> dict:
    """Calculate SIP returns with compound interest"""
    months = years * 12
    monthly_rate = annual_return / 12 / 100

    if monthly_rate == 0:
        future_value = monthly_investment * months
    else:
        future_value = monthly_investment * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)

    total_invested = monthly_investment * months
    wealth_gained = future_value - total_invested

    return {
        "monthly_investment": monthly_investment,
        "time_period_years": years,
        "expected_return_rate": annual_return,
        "total_invested": round(total_invested, 2),
        "future_value": round(future_value, 2),
        "wealth_gained": round(wealth_gained, 2),
        "absolute_returns": round((wealth_gained / total_invested) * 100, 2),
    }


def calculate_compound_interest(principal: float, annual_rate: float, years: int, compounding: str = "yearly") -> dict:
    """Calculate compound interest"""
    n = {"yearly": 1, "half-yearly": 2, "quarterly": 4, "monthly": 12}.get(compounding, 1)
    rate = annual_rate / 100

    amount = principal * ((1 + rate/n) ** (n * years))
    interest = amount - principal

    return {
        "principal": principal,
        "annual_rate": annual_rate,
        "time_years": years,
        "compounding": compounding,
        "maturity_amount": round(amount, 2),
        "interest_earned": round(interest, 2),
        "effective_rate": round(((amount/principal) ** (1/years) - 1) * 100, 2),
    }


def calculate_loan_emi_details(principal: float, annual_rate: float, tenure_years: int) -> dict:
    """Calculate EMI with full breakdown"""
    tenure_months = tenure_years * 12
    monthly_rate = annual_rate / 12 / 100

    if monthly_rate == 0:
        emi = principal / tenure_months
    else:
        emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1)

    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    return {
        "loan_amount": principal,
        "interest_rate": annual_rate,
        "tenure_years": tenure_years,
        "tenure_months": tenure_months,
        "monthly_emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "interest_to_principal_ratio": round((total_interest / principal) * 100, 2),
    }


def calculate_portfolio_returns(investments: list, years: int) -> dict:
    """Calculate weighted portfolio returns"""
    total_invested = sum(inv.get("amount", 0) for inv in investments)
    weighted_return = sum(
        (inv.get("amount", 0) / total_invested) * inv.get("expected_return", 0)
        for inv in investments if total_invested > 0
    )

    future_value = total_invested * ((1 + weighted_return/100) ** years)

    return {
        "total_invested": total_invested,
        "weighted_avg_return": round(weighted_return, 2),
        "time_years": years,
        "projected_value": round(future_value, 2),
        "projected_gain": round(future_value - total_invested, 2),
        "breakdown": investments,
    }


def calculate_tax_savings_80c(investments: dict) -> dict:
    """Calculate tax savings under Section 80C"""
    limit_80c = 150000
    total_claimed = min(sum(investments.values()), limit_80c)

    tax_saved_30_percent = total_claimed * 0.30
    tax_saved_20_percent = total_claimed * 0.20

    return {
        "section_80c_limit": limit_80c,
        "investments": investments,
        "total_claimed": total_claimed,
        "remaining_limit": limit_80c - total_claimed,
        "tax_saved_30_slab": round(tax_saved_30_percent, 2),
        "tax_saved_20_slab": round(tax_saved_20_percent, 2),
        "recommendation": "Maximize 80C limit for optimal tax savings" if total_claimed < limit_80c else "80C limit fully utilized",
    }


def calculate_fire_number(monthly_expenses: float, withdrawal_rate: float = 4) -> dict:
    """Calculate FIRE (Financial Independence Retire Early) number"""
    annual_expenses = monthly_expenses * 12
    fire_number = annual_expenses * (100 / withdrawal_rate)

    return {
        "monthly_expenses": monthly_expenses,
        "annual_expenses": annual_expenses,
        "withdrawal_rate": withdrawal_rate,
        "fire_number": round(fire_number, 2),
        "explanation": f"You need ₹{round(fire_number/100000, 2)} lakhs to be financially independent at {withdrawal_rate}% withdrawal rate",
    }


FINANCIAL_ADVISOR_SYSTEM_PROMPT = """You are Visor, a friendly yet highly knowledgeable Indian Financial Advisor. You possess expertise equivalent to:
- Chartered Accountant (CA)
- Chartered Financial Analyst (CFA)
- Financial Risk Manager (FRM)
- ACCA qualified
- MBA in Finance from IIM

## Your Core Competencies:

### 1. Indian Tax Laws & Planning
- Income Tax Act 1961 - All sections (80C, 80D, 80CCD, 80G, 80E, 80EE, 80TTA, etc.)
- New Tax Regime vs Old Tax Regime comparison
- Capital Gains Tax (Short-term & Long-term)
- TDS provisions and compliance
- GST implications on investments
- Tax-saving investment instruments (ELSS, PPF, NPS, ULIP)
- HRA, LTA, Standard Deduction rules
- Advance Tax and TDS deadlines

### 2. Investment Knowledge
- Indian Equity Markets (NSE, BSE, NIFTY 50, Sensex)
- Mutual Funds (Equity, Debt, Hybrid, ELSS, Index, ETFs)
- Fixed Income (FDs, RDs, Bonds, NCDs, Government Securities)
- PPF, EPF, NPS, VPF
- Gold (Physical, SGB, Gold ETFs, Digital Gold)
- Silver, Copper, and other commodities (MCX)
- Real Estate investment considerations
- REITs and InvITs
- International investing (US stocks, Mutual Funds)

### 3. Financial Regulations
- SEBI regulations
- RBI guidelines
- IRDAI (Insurance)
- PFRDA (NPS/Pension)
- Banking regulations

### 4. Risk Management
- Risk profiling (Conservative, Moderate, Aggressive)
- Asset allocation strategies
- Diversification principles
- Emergency fund planning
- Insurance (Term, Health, ULIP analysis)

### 5. Financial Planning
- Goal-based investing
- Retirement planning (FIRE calculations)
- Education planning
- Marriage planning
- House purchase planning
- Estate planning basics

## Built-in Calculators You Can Use:
- **SIP Calculator**: Calculate SIP returns with compounding
- **EMI Calculator**: Loan EMI with amortization
- **Compound Interest**: FD/RD returns
- **Portfolio Returns**: Weighted average portfolio performance
- **Tax Savings (80C)**: Section 80C optimization
- **FIRE Calculator**: Financial Independence number

## Communication Style:
- Be friendly, educational, and supportive
- Explain complex concepts in simple Hindi-English (Hinglish) when appropriate
- Always provide specific numbers and calculations
- Give actionable recommendations
- Cite relevant sections/rules when discussing taxes
- Compare options with pros and cons
- Use Indian currency (₹) and Indian number system (lakhs, crores)

## Important Guidelines:
- Never provide specific stock tips or guarantee returns
- Always mention that past performance doesn't guarantee future returns
- Recommend consulting a registered financial advisor for large decisions
- Be transparent about risks involved in any investment
- Consider the user's specific situation before giving advice

When user asks for calculations, use the calculator tools provided and explain the results."""


@router.post("/ai-advisor/chat", response_model=AdvisorChatResponse)
async def chat_with_advisor(chat_msg: AdvisorChatMessage, user=Depends(get_current_user)):
    """Chat with the AI Financial Advisor"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        raise HTTPException(status_code=500, detail="AI service not available")

    transactions = await db.transactions.find({"user_id": user["id"]}, {"_id": 0}).to_list(1000)
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    loans = await db.loans.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    assets = await db.fixed_assets.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)

    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in transactions if t["type"] == "investment")
    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0

    user_age = None
    if user.get("dob"):
        try:
            dob = datetime.strptime(user["dob"], "%Y-%m-%d")
            user_age = (datetime.now() - dob).days // 365
        except Exception:
            pass

    financial_context = f"""
## Current User Financial Profile:
- **Name**: {user.get('full_name', 'User')}
- **Age**: {user_age or 'Not provided'} years
- **Account Created**: {user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'}

## Financial Summary (All Time):
- **Total Income**: ₹{total_income:,.0f}
- **Total Expenses**: ₹{total_expenses:,.0f}
- **Total Investments**: ₹{total_investments:,.0f}
- **Net Savings**: ₹{(total_income - total_expenses):,.0f}
- **Savings Rate**: {savings_rate:.1f}%
- **Investment Rate**: {(total_investments/total_income*100) if total_income > 0 else 0:.1f}%

## Investment Breakdown:
{chr(10).join([f"- {cat}: ₹{sum(t['amount'] for t in transactions if t['type']=='investment' and t['category']==cat):,.0f}" for cat in set(t['category'] for t in transactions if t['type']=='investment')])}

## Expense Categories:
{chr(10).join([f"- {cat}: ₹{sum(t['amount'] for t in transactions if t['type']=='expense' and t['category']==cat):,.0f}" for cat in set(t['category'] for t in transactions if t['type']=='expense')])}

## Active Loans:
{chr(10).join([f"- {l['name']}: ₹{l['principal_amount']:,.0f} at {l['interest_rate']}% ({l['tenure_months']} months)" for l in loans]) if loans else 'No active loans'}

## Fixed Assets:
{chr(10).join([f"- {a['name']}: ₹{a.get('current_value', a['purchase_value']):,.0f}" for a in assets]) if assets else 'No fixed assets recorded'}

## Financial Goals:
{chr(10).join([f"- {g['title']}: ₹{g['current_amount']:,.0f} / ₹{g['target_amount']:,.0f} ({(g['current_amount']/g['target_amount']*100):.0f}% complete)" for g in goals]) if goals else 'No goals set'}
"""

    calculator_result = None
    if chat_msg.calculator_type and chat_msg.calculator_params:
        params = chat_msg.calculator_params
        try:
            if chat_msg.calculator_type == "sip":
                calculator_result = calculate_sip_returns(
                    params.get("monthly_investment", 10000),
                    params.get("annual_return", 12),
                    params.get("years", 10)
                )
            elif chat_msg.calculator_type == "emi":
                calculator_result = calculate_loan_emi_details(
                    params.get("principal", 5000000),
                    params.get("annual_rate", 8.5),
                    params.get("tenure_years", 20)
                )
            elif chat_msg.calculator_type == "compound":
                calculator_result = calculate_compound_interest(
                    params.get("principal", 100000),
                    params.get("annual_rate", 7),
                    params.get("years", 5),
                    params.get("compounding", "yearly")
                )
            elif chat_msg.calculator_type == "portfolio":
                calculator_result = calculate_portfolio_returns(
                    params.get("investments", []),
                    params.get("years", 10)
                )
            elif chat_msg.calculator_type == "tax_80c":
                calculator_result = calculate_tax_savings_80c(params.get("investments", {}))
            elif chat_msg.calculator_type == "fire":
                calculator_result = calculate_fire_number(
                    params.get("monthly_expenses", 50000),
                    params.get("withdrawal_rate", 4)
                )
        except Exception as e:
            logger.error(f"Calculator error: {e}")

    session_id = f"advisor_{user['id']}"

    history = await db.chat_history.find(
        {"user_id": user["id"], "type": "advisor"}
    ).sort("created_at", -1).limit(20).to_list(20)
    history.reverse()

    user_message_text = f"""
{financial_context}

---
**User Question**: {chat_msg.message}
"""

    if calculator_result:
        user_message_text += f"\n\n**Calculator Result ({chat_msg.calculator_type})**: {calculator_result}"

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=FINANCIAL_ADVISOR_SYSTEM_PROMPT
        )
        chat.with_model("openai", "gpt-5.2")

        user_message = UserMessage(text=user_message_text)
        response_text = await chat.send_message(user_message)
    except Exception as e:
        logger.error(f"AI advisor error: {e}")
        response_text = "I'm having trouble connecting right now. Please try again in a moment."

    await db.chat_history.insert_one({
        "user_id": user["id"],
        "type": "advisor",
        "role": "user",
        "content": chat_msg.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.chat_history.insert_one({
        "user_id": user["id"],
        "type": "advisor",
        "role": "assistant",
        "content": response_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return AdvisorChatResponse(response=response_text, calculator_result=calculator_result)
