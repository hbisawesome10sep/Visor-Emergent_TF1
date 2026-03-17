"""
Visor AI — Financial Calculators
All India-specific financial calculators used by the AI agent.
"""
import math


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
        "monthly_sip": f"\u20b9{monthly:,.0f}",
        "annual_return": f"{rate}%",
        "period": f"{years} years",
        "total_invested": f"\u20b9{invested:,.0f}",
        "future_value": f"\u20b9{fv:,.0f}",
        "wealth_gained": f"\u20b9{fv - invested:,.0f}",
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
        "starting_sip": f"\u20b9{monthly:,.0f}",
        "annual_stepup": f"{stepup}%",
        "annual_return": f"{rate}%",
        "period": f"{years} years",
        "total_invested": f"\u20b9{total_invested:,.0f}",
        "future_value": f"\u20b9{fv:,.0f}",
        "wealth_gained": f"\u20b9{fv - total_invested:,.0f}",
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
        "loan_amount": f"\u20b9{principal:,.0f}",
        "interest_rate": f"{rate}%",
        "tenure": f"{years} years ({months} months)",
        "monthly_emi": f"\u20b9{emi:,.0f}",
        "total_payment": f"\u20b9{total:,.0f}",
        "total_interest": f"\u20b9{interest:,.0f}",
        "interest_percent": f"{(interest / principal * 100):.1f}% of principal",
    }


def calc_compound_interest(principal: float, rate: float, years: int, freq: str = "yearly") -> dict:
    n = {"yearly": 1, "half-yearly": 2, "quarterly": 4, "monthly": 12}.get(freq, 1)
    amount = principal * ((1 + rate / 100 / n) ** (n * years))
    interest = amount - principal
    return {
        "type": "Compound Interest / FD Calculator",
        "principal": f"\u20b9{principal:,.0f}",
        "rate": f"{rate}% p.a.",
        "compounding": freq,
        "period": f"{years} years",
        "maturity_amount": f"\u20b9{amount:,.0f}",
        "interest_earned": f"\u20b9{interest:,.0f}",
    }


def calc_cagr(initial: float, final: float, years: float) -> dict:
    if initial <= 0 or years <= 0:
        return {"type": "CAGR Calculator", "error": "Invalid inputs"}
    cagr = ((final / initial) ** (1 / years) - 1) * 100
    return {
        "type": "CAGR Calculator",
        "initial_value": f"\u20b9{initial:,.0f}",
        "final_value": f"\u20b9{final:,.0f}",
        "period": f"{years} years",
        "cagr": f"{cagr:.2f}%",
    }


def calc_fire(monthly_expenses: float, withdrawal_rate: float = 4) -> dict:
    annual = monthly_expenses * 12
    fire_number = annual * (100 / withdrawal_rate)
    return {
        "type": "FIRE Calculator",
        "monthly_expenses": f"\u20b9{monthly_expenses:,.0f}",
        "annual_expenses": f"\u20b9{annual:,.0f}",
        "withdrawal_rate": f"{withdrawal_rate}%",
        "fire_number": f"\u20b9{fire_number:,.0f}",
        "in_crores": f"\u20b9{fire_number / 1e7:.2f} Cr",
    }


def calc_ppf(yearly: float, years: int = 15, rate: float = 7.1) -> dict:
    balance = 0
    total_invested = 0
    for _ in range(years):
        balance = (balance + yearly) * (1 + rate / 100)
        total_invested += yearly
    return {
        "type": "PPF Calculator",
        "yearly_investment": f"\u20b9{yearly:,.0f}",
        "rate": f"{rate}% (current PPF rate)",
        "tenure": f"{years} years",
        "total_invested": f"\u20b9{total_invested:,.0f}",
        "maturity_value": f"\u20b9{balance:,.0f}",
        "interest_earned": f"\u20b9{balance - total_invested:,.0f}",
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
        "basic_salary": f"\u20b9{basic:,.0f}",
        "hra_received": f"\u20b9{hra_received:,.0f}",
        "rent_paid": f"\u20b9{rent_paid:,.0f}",
        "city": "Metro" if metro else "Non-Metro",
        "exempt_hra": f"\u20b9{exempt:,.0f}",
        "taxable_hra": f"\u20b9{taxable:,.0f}",
    }


def calc_gratuity(basic: float, years: int) -> dict:
    if years < 5:
        return {"type": "Gratuity Calculator", "note": "Minimum 5 years of service required for gratuity."}
    gratuity = (basic * 15 * years) / 26
    exempt = min(gratuity, 2000000)
    return {
        "type": "Gratuity Calculator",
        "last_basic_da": f"\u20b9{basic:,.0f}",
        "years_of_service": years,
        "gratuity_amount": f"\u20b9{gratuity:,.0f}",
        "tax_exempt_limit": "\u20b920,00,000",
        "taxable_gratuity": f"\u20b9{max(0, gratuity - exempt):,.0f}",
    }


def calc_tax_80c(investments: dict) -> dict:
    limit = 150000
    total = min(sum(investments.values()), limit)
    return {
        "type": "Section 80C Tax Savings",
        "total_claimed": f"\u20b9{total:,.0f}",
        "limit": f"\u20b9{limit:,.0f}",
        "remaining": f"\u20b9{limit - total:,.0f}",
        "tax_saved_30_slab": f"\u20b9{total * 0.30:,.0f}",
        "tax_saved_20_slab": f"\u20b9{total * 0.20:,.0f}",
        "investments": {k: f"\u20b9{v:,.0f}" for k, v in investments.items()},
    }
