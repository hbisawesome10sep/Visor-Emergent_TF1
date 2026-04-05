"""
Visor AI — Multi-Model Query Router
Routes simple queries to gpt-4o-mini (cheap/fast) and complex queries to gpt-5.2 (powerful).
Transparent to the user — same quality where it matters, 40-60% cost reduction overall.
"""
import re
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  QUERY COMPLEXITY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

# Simple query patterns — factual lookups, definitions, greetings, price checks
_SIMPLE_PATTERNS = [
    # Greetings / meta
    r'^(hi|hello|hey|namaste|good\s*(morning|evening|afternoon)|thanks|thank you|ok|okay|bye|dhanyavaad|shukriya)\b',
    r'^(kaise ho|kya haal|how are you)',
    # Single-fact definitions
    r'\b(what is|kya hai|kya hota hai|meaning of|define|explain)\b.{0,40}$',
    r'\b(what|kya)\s+(is|hai|hota)\s+(ppf|nps|elss|sip|emi|fd|rd|ulip|sgb|reit|invit|etf|nav|aum|cagr|pe ratio|sensex|nifty|ipo|tds|gst|cess|surcharge)\b',
    # Price checks (short queries)
    r'^.{0,60}(price|rate|kya chal raha|kitna hai|kitne|bhav|keemat|दाम|भाव|कीमत)\s*\??$',
    r'^.{0,40}(gold|silver|sona|chandi|nifty|sensex)\s*(price|rate|today|aaj|abhi)?\s*\??$',
    # Simple yes/no or short factual
    r'^.{0,30}\?$',
    # Thank you / acknowledgement patterns
    r'^(got it|samajh gaya|theek hai|accha|okay thanks|thik hai|sahi hai)',
]

# Complex query patterns — need full GPT-5.2 horsepower
_COMPLEX_PATTERNS = [
    # Tax planning / analysis
    r'\b(tax\s*(planning|saving|sav|optimization|liability|regime|old|new|comparison|80c|80d|deduction|refund|itr|return|advance))',
    r'\b(80c|80d|80ccd|80e|80g|80gg|80tta|80ttb|24\s*\(?\s*b\s*\)?|10\s*\(?\s*13a\s*\)?|section\s*\d)',
    r'\b(hra\s*(exempt|calculation|claim|benefit))',
    r'\b(capital\s*gain|stcg|ltcg|indexation|grandfathering)',
    # Portfolio analysis
    r'\b(portfolio|rebalanc|asset\s*allocation|diversif|risk\s*profile|wealth\s*project)',
    r'\b(invest\s*(strategy|plan|kaise|kahan|where|how\s*much|kitna))',
    r'\b(mutual fund|mf)\s*(recommend|suggest|best|compare|vs|switch)',
    # Financial planning
    r'\b(retirement|fire\s*number|financial\s*independence|goal\s*plan|emergency\s*fund)',
    r'\b(loan\s*(compare|prepay|foreclose|refinanc|balance\s*transfer))',
    r'\b(insurance\s*(compare|need|adequate|term|health|cover))',
    # Personalized advice requiring user data
    r'\b(my|mera|mere|meri|apna|apne|apni)\b.*(advice|suggest|recommend|review|analys|check|improve|optimize)',
    r'\b(should\s*i|kya\s*(karu|karun|karni|karna)|chahiye|suggest\s*kar)',
    r'\b(how\s*(can|do|should)\s*i\s*(save|invest|reduce|improve|plan|start))',
    # Multi-step / comparative analysis
    r'\b(compare|vs|versus|better|best|optimal|which\s*(is|one|fund|stock))',
    r'\b(breakdow|breakdown|detail|elaborate|step\s*by\s*step|samjha|explain\s*in\s*detail)',
    # Budget / spending analysis
    r'\b(budget|spend|kharcha|expense)\s*(analys|review|reduc|cut|optimize|pattern)',
]

_simple_re = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_PATTERNS]
_complex_re = [re.compile(p, re.IGNORECASE) for p in _COMPLEX_PATTERNS]

# Model constants
MODEL_FAST = "gpt-4o-mini"
MODEL_POWER = "gpt-5.2"


def classify_query(message: str) -> str:
    """
    Classify a user query as 'simple' or 'complex'.
    Returns the appropriate model name.
    """
    msg = message.strip()

    # Very short messages (< 15 chars) are almost always simple
    if len(msg) < 15 and not any(p.search(msg) for p in _complex_re):
        logger.info(f"Query router → {MODEL_FAST} (short message)")
        return MODEL_FAST

    # Check complex patterns first (they take priority)
    for pattern in _complex_re:
        if pattern.search(msg):
            logger.info(f"Query router → {MODEL_POWER} (complex pattern match)")
            return MODEL_POWER

    # Check simple patterns
    for pattern in _simple_re:
        if pattern.search(msg):
            logger.info(f"Query router → {MODEL_FAST} (simple pattern match)")
            return MODEL_FAST

    # If message is long (>150 chars), likely complex
    if len(msg) > 150:
        logger.info(f"Query router → {MODEL_POWER} (long message)")
        return MODEL_POWER

    # Default: use the powerful model for safety
    logger.info(f"Query router → {MODEL_POWER} (default)")
    return MODEL_POWER


def get_model_for_query(message: str, has_calculator_result: bool = False) -> str:
    """
    Main entry point for model selection.
    If a calculator result is present, always use the fast model
    (the heavy computation is already done, just need to explain it).
    """
    if has_calculator_result:
        logger.info(f"Query router → {MODEL_FAST} (calculator result present)")
        return MODEL_FAST

    return classify_query(message)
