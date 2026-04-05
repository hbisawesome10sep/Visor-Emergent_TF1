"""
Visor AI — Tax Knowledge Base (RAG-lite)
Structured Indian tax law knowledge that can be injected into AI context
when a tax-related query is detected. Eliminates hallucination on tax specifics.

Each section includes: limit, conditions, eligible instruments, examples, common mistakes.
Query classifier detects tax intent → retrieves relevant sections.
"""
import re
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  COMPREHENSIVE INDIAN TAX KNOWLEDGE BASE (FY 2025-26 / AY 2026-27)
# ═══════════════════════════════════════════════════════════════════════════════

TAX_KNOWLEDGE = {
    "80c": {
        "section": "Section 80C",
        "title": "Deduction for Investments & Expenses",
        "limit": "Rs 1,50,000 per financial year",
        "applies_to": "Individual and HUF",
        "regime": "Old Regime only (NOT available in New Regime)",
        "eligible_instruments": [
            "ELSS Mutual Funds (3-year lock-in, lowest among 80C options)",
            "PPF - Public Provident Fund (15-year lock-in, 7.1% current rate, EEE status)",
            "EPF - Employee Provident Fund (employee's 12% contribution)",
            "VPF - Voluntary Provident Fund (additional contribution beyond 12%)",
            "NSC - National Savings Certificate (5-year lock-in, 7.7% current rate)",
            "Tax Saver FD (5-year lock-in, ~7% rate, interest taxable)",
            "Life Insurance Premium (max 10% of sum assured for policies after 2012)",
            "ULIP - Unit Linked Insurance Plan (5-year lock-in)",
            "Sukanya Samriddhi Yojana (for girl child, 8.2% rate, EEE)",
            "Senior Citizens Savings Scheme (SCSS, 8.2% rate)",
            "Home Loan Principal Repayment",
            "Stamp Duty & Registration charges for house purchase",
            "Tuition fees for up to 2 children (school/college, NOT coaching)",
            "NPS Tier-1 (also eligible under 80CCD(1) within 80C limit)",
        ],
        "common_mistakes": [
            "Confusing 80C limit (Rs 1.5L) with 80CCD(1B) (additional Rs 50K for NPS)",
            "Insurance premium exceeding 10% of sum assured is NOT deductible",
            "Tuition fee claim is ONLY for full-time courses, NOT coaching/tuition classes",
            "PPF annual deposit cap is Rs 1.5L — depositing more won't give extra deduction",
            "ELSS has the shortest lock-in (3 years) but returns are market-linked",
        ],
        "optimal_strategy": "Start with EPF (employer match = free money), then ELSS SIP for equity exposure + tax saving, PPF for risk-free EEE. Fill remaining with NSC or SCSS (senior citizens).",
    },

    "80ccd1b": {
        "section": "Section 80CCD(1B)",
        "title": "Additional NPS Deduction",
        "limit": "Rs 50,000 (over and above 80C limit)",
        "applies_to": "Individual (salaried or self-employed)",
        "regime": "Old Regime only",
        "details": [
            "Available for contributions to NPS Tier-1 account only",
            "This is ADDITIONAL to the Rs 1.5L limit of 80C",
            "Total NPS deduction: 80CCD(1) within 80C + 80CCD(1B) = up to Rs 2L",
            "At 30% tax bracket, saves Rs 15,600 (including cess)",
            "60% of corpus is tax-free on withdrawal at 60; 40% must buy annuity",
        ],
        "common_mistakes": [
            "Claiming 80CCD(1B) without having an NPS Tier-1 account",
            "Confusing NPS Tier-1 (tax benefit) with Tier-2 (no tax benefit under 80CCD1B)",
        ],
    },

    "80ccd2": {
        "section": "Section 80CCD(2)",
        "title": "Employer NPS Contribution",
        "limit": "10% of salary (Basic + DA) — no upper cap",
        "applies_to": "Salaried individuals",
        "regime": "Available in BOTH Old and New Regime",
        "details": [
            "Only employer's contribution to employee's NPS qualifies",
            "NOT counted within the Rs 1.5L limit of 80C",
            "This is one of the FEW deductions available in New Tax Regime",
            "For government employees: limit is 14% of salary",
        ],
    },

    "80d": {
        "section": "Section 80D",
        "title": "Health Insurance Premium",
        "limit": "Self/family: Rs 25,000 (Rs 50,000 if senior citizen) + Parents: Rs 25,000 (Rs 50,000 if senior citizen)",
        "applies_to": "Individual and HUF",
        "regime": "Old Regime only",
        "eligible_expenses": [
            "Health insurance premium for self, spouse, and dependent children: up to Rs 25,000",
            "Health insurance premium for parents: additional Rs 25,000",
            "If self or parent is senior citizen (60+): limit increases to Rs 50,000 each",
            "Preventive health check-up: Rs 5,000 (WITHIN the 25K/50K limit, not additional)",
            "Medical expenditure for senior citizen WITHOUT insurance: up to Rs 50,000",
        ],
        "maximum_deduction": "Rs 1,00,000 (if both self and parents are senior citizens: 50K + 50K)",
        "common_mistakes": [
            "Claiming preventive checkup OVER the insurance limit (it's within, not extra)",
            "Group insurance from employer does NOT qualify — only individual policies",
            "Premium for in-laws is NOT eligible (only own parents)",
            "GST on premium is NOT deductible — only the base premium amount",
        ],
    },

    "80e": {
        "section": "Section 80E",
        "title": "Education Loan Interest",
        "limit": "No upper limit — full interest amount deductible",
        "applies_to": "Individual only (NOT HUF)",
        "regime": "Old Regime only",
        "details": [
            "Deduction on INTEREST component only (not principal)",
            "Loan must be from a recognized financial institution or approved charitable trust",
            "For higher education of self, spouse, or children",
            "Available for 8 years from the year of first repayment, or until interest is fully paid",
            "Covers courses in India AND abroad",
            "Full-time courses: graduation, post-graduation, professional courses",
        ],
        "common_mistakes": [
            "Claiming principal repayment under 80E (only interest qualifies)",
            "Loans from relatives/friends do NOT qualify",
            "The 8-year window starts from repayment start, not loan disbursement",
        ],
    },

    "80g": {
        "section": "Section 80G",
        "title": "Donations to Charitable Organizations",
        "limit": "Varies: 100% or 50% deduction, with or without qualifying limit",
        "applies_to": "Individual, HUF, Company, Firm",
        "regime": "Old Regime only",
        "categories": [
            "100% without limit: PM CARES Fund, National Defence Fund, PM National Relief Fund",
            "50% without limit: Jawaharlal Nehru Memorial Fund, PM Drought Relief Fund",
            "100% with qualifying limit: Approved local institutions (limit = 10% of adjusted gross total income)",
            "50% with qualifying limit: Other approved funds/institutions",
        ],
        "details": [
            "Cash donations above Rs 2,000 are NOT eligible — use UPI/cheque/bank transfer",
            "Must have receipt with PAN of donee organization, 80G registration number",
            "Section 80GGA: For donations to scientific research/rural development (100% deduction)",
        ],
    },

    "80gg": {
        "section": "Section 80GG",
        "title": "Rent Paid (No HRA from employer)",
        "limit": "Least of: Rs 5,000/month, 25% of total income, or Rent paid minus 10% of total income",
        "applies_to": "Individual NOT receiving HRA",
        "regime": "Old Regime only",
        "details": [
            "For self-employed or salaried persons NOT getting HRA component",
            "Must file Form 10BA declaration",
            "Neither you, spouse, minor child, nor HUF should own residential property at the place of employment",
        ],
    },

    "hra_10_13a": {
        "section": "Section 10(13A)",
        "title": "House Rent Allowance (HRA) Exemption",
        "limit": "Least of 3 conditions",
        "applies_to": "Salaried individuals receiving HRA",
        "regime": "Old Regime only",
        "calculation": [
            "Condition 1: Actual HRA received from employer",
            "Condition 2: 50% of Basic Salary (metro cities: Mumbai, Delhi, Kolkata, Chennai) or 40% (non-metro)",
            "Condition 3: Actual rent paid minus 10% of Basic Salary",
            "HRA Exemption = MINIMUM of the three conditions above",
        ],
        "metro_cities": "Mumbai, Delhi, Kolkata, Chennai (and their suburbs)",
        "important_rules": [
            "If rent > Rs 1,00,000/year: Landlord PAN is MANDATORY",
            "If rent > Rs 50,000/month: TDS of 5% must be deducted by tenant",
            "Can claim HRA even for rent paid to parents (with rent agreement + their ITR showing rental income)",
            "Cannot claim both HRA and 80GG simultaneously",
            "Rent receipts are mandatory proof — maintain monthly receipts",
        ],
    },

    "24b": {
        "section": "Section 24(b)",
        "title": "Home Loan Interest Deduction",
        "limit": "Rs 2,00,000/year for self-occupied property; No limit for let-out property",
        "applies_to": "Individual and HUF",
        "regime": "Old Regime only (Rs 2L limit); New Regime: ONLY for let-out property (no limit)",
        "details": [
            "Self-occupied property: Max Rs 2,00,000 interest deduction per year",
            "Let-out property: Entire interest is deductible (no upper limit)",
            "Construction must be completed within 5 years from loan disbursement year",
            "Pre-construction interest: Deductible in 5 equal installments after construction completes",
            "Joint home loan: Each co-borrower can claim up to Rs 2L separately",
            "For affordable housing (stamp value ≤ Rs 45L): Additional Rs 1.5L under 80EEA (if applicable)",
        ],
        "common_mistakes": [
            "Claiming Rs 2L for under-construction property (limited to Rs 30,000 pre-completion)",
            "Not claiming pre-construction interest after possession",
            "Forgetting to get interest certificate from bank/NBFC",
        ],
    },

    "80tta_80ttb": {
        "section": "Section 80TTA / 80TTB",
        "title": "Savings Account / Senior Citizen Deposit Interest",
        "limit": "80TTA: Rs 10,000 | 80TTB: Rs 50,000 (senior citizens)",
        "applies_to": "80TTA: Individual/HUF below 60 | 80TTB: Senior citizens 60+",
        "regime": "Old Regime only",
        "details": [
            "80TTA: Interest from savings accounts in banks, co-operative societies, post office",
            "80TTA does NOT cover FD interest, RD interest, or corporate deposits",
            "80TTB (senior citizens): Covers ALL deposit interest — savings, FD, RD, post office",
            "80TTA and 80TTB are mutually exclusive — senior citizens claim 80TTB, not 80TTA",
        ],
    },

    "capital_gains": {
        "section": "Capital Gains Tax",
        "title": "STCG and LTCG on Various Assets (Post Budget 2024)",
        "details": {
            "equity_shares_and_equity_mf": {
                "holding_period": "12 months (1 year) for LTCG classification",
                "stcg_rate": "20% (Section 111A)",
                "ltcg_rate": "12.5% above Rs 1.25 lakh exemption (Section 112A)",
                "ltcg_exemption": "Rs 1,25,000 per financial year",
                "indexation": "NOT available for equity",
                "note": "Budget 2024 changed: STCG from 15% to 20%, LTCG from 10% to 12.5%",
            },
            "debt_mutual_funds": {
                "holding_period": "All gains taxed at slab rate regardless of holding period (post Apr 2023)",
                "note": "Indexation benefit removed for debt MFs purchased after April 1, 2023",
            },
            "real_estate": {
                "holding_period": "24 months (2 years) for LTCG classification",
                "stcg_rate": "Taxed at slab rate",
                "ltcg_rate": "12.5% WITHOUT indexation (post Budget 2024)",
                "exemptions": [
                    "Section 54: Reinvest in new residential house within 2 years",
                    "Section 54EC: Invest up to Rs 50L in NHAI/REC bonds within 6 months",
                    "Section 54F: Sale of any asset (non-house) → buy residential house",
                ],
            },
            "gold_and_sgb": {
                "holding_period": "24 months (2 years) for LTCG classification",
                "stcg_rate": "Taxed at slab rate",
                "ltcg_rate": "12.5% without indexation",
                "sgb_exception": "SGBs held to maturity (8 years): Capital gains are FULLY EXEMPT",
            },
        },
        "grandfathering": {
            "applies_to": "Equity shares / equity MFs held before Feb 1, 2018",
            "rule": "Cost of acquisition = HIGHER of (actual cost, fair market value as on Jan 31, 2018)",
            "note": "FMV on Jan 31, 2018 is the highest traded price on that date",
        },
    },

    "new_vs_old_regime": {
        "section": "Tax Regime Comparison (FY 2025-26)",
        "old_regime_slabs": [
            "Up to Rs 2.5L: NIL",
            "Rs 2.5L - 5L: 5%",
            "Rs 5L - 10L: 20%",
            "Above Rs 10L: 30%",
        ],
        "new_regime_slabs": [
            "Up to Rs 4L: NIL",
            "Rs 4L - 8L: 5%",
            "Rs 8L - 12L: 10%",
            "Rs 12L - 16L: 15%",
            "Rs 16L - 20L: 20%",
            "Rs 20L - 24L: 25%",
            "Above Rs 24L: 30%",
        ],
        "new_regime_benefits": [
            "Standard deduction: Rs 75,000 (increased from Rs 50,000)",
            "Section 87A rebate: Full tax rebate for income up to Rs 12L (effective zero tax up to Rs 12.75L with standard deduction)",
            "Lower tax rates for income up to Rs 24L",
            "Employer NPS contribution (80CCD(2)) is still deductible",
            "No need to maintain proof of investments/expenses",
        ],
        "old_regime_benefits": [
            "80C: Rs 1.5L deduction",
            "80D: Health insurance up to Rs 1L",
            "HRA exemption: Can be significant for metro renters",
            "80CCD(1B): Additional Rs 50K for NPS",
            "24(b): Home loan interest Rs 2L",
            "80E: Full education loan interest",
            "80G: Donation deductions",
            "80TTA/80TTB: Savings interest deduction",
        ],
        "when_old_is_better": "When total deductions (80C + 80D + HRA + 24b + 80CCD1B + others) exceed Rs 3.75L for income above Rs 15L",
        "when_new_is_better": "When total deductions are below Rs 3.75L, or income is below Rs 12.75L (zero tax with rebate)",
    },

    "advance_tax": {
        "section": "Advance Tax",
        "title": "Quarterly Advance Tax Deadlines",
        "applies_to": "Anyone with tax liability > Rs 10,000 in a FY (after TDS)",
        "deadlines": [
            "15 June: 15% of total tax",
            "15 September: 45% cumulative (30% in Q2)",
            "15 December: 75% cumulative (30% in Q3)",
            "15 March: 100% (25% in Q4)",
        ],
        "penalty": "Interest under Sec 234B (default) and 234C (deferment) at 1% per month",
        "exemption": "Salaried individuals with only salary income (employer deducts TDS) are generally exempt if TDS covers liability",
    },

    "tds_rates": {
        "section": "TDS Rates (Key Sections)",
        "rates": [
            "192: Salary — As per slab rates",
            "194A: Interest (non-bank, >Rs 5K): 10%",
            "194A: Senior citizen interest (>Rs 50K): 10%",
            "194B: Lottery/Game winnings (>Rs 10K): 30%",
            "194C: Contractor payments (>Rs 30K single / Rs 1L aggregate): 1% (Individual) / 2% (Others)",
            "194H: Commission (>Rs 15K): 5%",
            "194I: Rent — Land/Building (>Rs 2.4L): 10%; Plant/Machinery: 2%",
            "194IA: Property sale (>Rs 50L): 1%",
            "194IB: Rent by Individual/HUF (>Rs 50K/month): 5%",
            "194J: Professional fees (>Rs 30K): 10%",
            "194N: Cash withdrawal (>Rs 1Cr): 2%",
            "194Q: Purchase of goods (>Rs 50L): 0.1%",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
#  TAX QUERY CLASSIFIER & KNOWLEDGE RETRIEVAL
# ═══════════════════════════════════════════════════════════════════════════════

# Map keywords to relevant knowledge base sections
_TAX_KEYWORD_MAP = {
    # Section 80C and investments
    r'\b80c\b|elss|ppf|epf|vpf|nsc|tax\s*saver\s*fd|tuition\s*fee|sukanya|scss': ["80c"],
    r'\bnps\b|80ccd|national\s*pension': ["80ccd1b", "80ccd2"],
    r'\b80d\b|health\s*insurance|medical\s*insurance|preventive\s*check': ["80d"],
    r'\b80e\b|education\s*loan': ["80e"],
    r'\b80g\b|donat|charitable': ["80g"],
    r'\b80gg\b': ["80gg"],
    r'\bhra\b|house\s*rent\s*allow|rent\s*exempt|10\s*\(?13a\)?': ["hra_10_13a"],
    r'\b24\s*\(?b\)?|home\s*loan\s*interest|housing\s*loan\s*interest': ["24b"],
    r'\b80tta\b|80ttb\b|savings?\s*(account)?\s*interest': ["80tta_80ttb"],
    r'\bcapital\s*gain|stcg|ltcg|long\s*term\s*gain|short\s*term\s*gain|grandfath': ["capital_gains"],
    r'\bnew\s*regime|old\s*regime|regime\s*compar|which\s*regime|konsa\s*regime': ["new_vs_old_regime"],
    r'\badvance\s*tax|234b|234c|quarterly\s*tax': ["advance_tax"],
    r'\btds\b|tax\s*deduct': ["tds_rates"],
    # General tax queries → provide regime comparison + 80C
    r'\btax\s*(sav|plan|optimi|reduc|bach|kam\s*kar)': ["80c", "80ccd1b", "new_vs_old_regime"],
    r'\bdeduction|section\b': ["80c", "80d"],
    # Hindi tax keywords
    r'\bkar\s*bachao|tax\s*bachao|tax\s*bachat|कर\s*बचत|टैक्स\s*बचत': ["80c", "80ccd1b", "new_vs_old_regime"],
}

_compiled_tax_keywords = [(re.compile(pattern, re.IGNORECASE), sections) for pattern, sections in _TAX_KEYWORD_MAP.items()]


def detect_tax_sections(message: str) -> list[str]:
    """
    Detect which tax sections are relevant to the user's query.
    Returns a list of section keys from TAX_KNOWLEDGE.
    """
    matched_sections = set()
    for pattern, sections in _compiled_tax_keywords:
        if pattern.search(message):
            matched_sections.update(sections)

    return list(matched_sections)[:4]  # Max 4 sections to avoid context bloat


def get_tax_knowledge_context(message: str) -> str:
    """
    Main entry point: detect tax intent and return formatted knowledge for AI context.
    Returns empty string if query is not tax-related.
    """
    sections = detect_tax_sections(message)
    if not sections:
        return ""

    parts = ["\nTAX KNOWLEDGE BASE (use these EXACT details in your response):"]

    for section_key in sections:
        info = TAX_KNOWLEDGE.get(section_key)
        if not info:
            continue

        section_text = f"\n--- {info.get('section', section_key)} — {info.get('title', '')} ---"
        section_text += f"\nLimit: {info.get('limit', 'N/A')}"

        if info.get("regime"):
            section_text += f"\nRegime: {info['regime']}"

        if info.get("applies_to"):
            section_text += f"\nApplies to: {info['applies_to']}"

        # Handle different section structures
        if "eligible_instruments" in info:
            section_text += "\nEligible: " + " | ".join(info["eligible_instruments"][:8])

        if "eligible_expenses" in info:
            section_text += "\nEligible: " + " | ".join(info["eligible_expenses"])

        if "calculation" in info:
            section_text += "\nCalculation: " + " → ".join(info["calculation"])

        if "important_rules" in info:
            section_text += "\nRules: " + " | ".join(info["important_rules"][:5])

        if "categories" in info:
            section_text += "\nCategories: " + " | ".join(info["categories"])

        if "details" in info:
            details = info["details"]
            if isinstance(details, list):
                section_text += "\nDetails: " + " | ".join(details[:6])
            elif isinstance(details, dict):
                for sub_key, sub_info in details.items():
                    section_text += f"\n  {sub_key}: "
                    if isinstance(sub_info, dict):
                        section_text += " | ".join(f"{k}: {v}" for k, v in sub_info.items() if not isinstance(v, (list, dict)))

        if "common_mistakes" in info:
            section_text += "\nCommon Mistakes: " + " | ".join(info["common_mistakes"][:3])

        if "optimal_strategy" in info:
            section_text += f"\nOptimal Strategy: {info['optimal_strategy']}"

        # Regime comparison special handling
        if section_key == "new_vs_old_regime":
            section_text += f"\nNew Regime Slabs: " + " | ".join(info.get("new_regime_slabs", []))
            section_text += f"\nOld Regime Slabs: " + " | ".join(info.get("old_regime_slabs", []))
            section_text += f"\nNew Regime Benefits: " + " | ".join(info.get("new_regime_benefits", [])[:4])
            section_text += f"\nWhen Old > New: {info.get('when_old_is_better', '')}"
            section_text += f"\nWhen New > Old: {info.get('when_new_is_better', '')}"

        if "deadlines" in info:
            section_text += "\nDeadlines: " + " | ".join(info["deadlines"])

        if "rates" in info:
            section_text += "\nRates: " + " | ".join(info["rates"][:8])

        parts.append(section_text)

    if len(parts) <= 1:
        return ""

    return "\n".join(parts)
