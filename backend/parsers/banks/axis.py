"""
AXIS Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


def clean_axis_description(raw_desc: str) -> str:
    """Clean up Axis Bank transaction description.
    Axis UPI format: UPI/P2A_or_P2M/ref/PayeeName/BankOrApp/purpose
    P2A = Person to Account, P2M = Person to Merchant.
    """
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    if not desc:
        return "Bank Transaction"

    upper = desc.upper()

    # ── ATM withdrawal ───────────────────────────────────────────────────
    if 'ATM-CASH' in upper or 'ATM CASH' in upper:
        return "ATM Withdrawal"

    # ── Interest credit ──────────────────────────────────────────────────
    if 'INT.PD' in upper or ':INT.' in upper:
        return "Interest Credit"

    # ── Bank charges ─────────────────────────────────────────────────────
    if 'ECS TXN CHRGS' in upper or 'ECS CHRG' in upper:
        return "Bank Charges - ECS"
    if 'SMS CHRG' in upper or 'SMS ALERT' in upper:
        return "Bank Charges - SMS"
    if 'DR CARD CHARGES' in upper or 'CARD CHARGES' in upper:
        return "Card Charges - Annual Fee"

    # ── Credit adjustment (UPI refund) ───────────────────────────────────
    if 'CRADJ' in upper:
        return "UPI Refund"

    # ── UPI transactions (extract payee FIRST, before keyword scan) ──────
    if upper.startswith('UPI/'):
        return _clean_axis_upi(desc)

    # ── NEFT ─────────────────────────────────────────────────────────────
    if upper.startswith('NEFT'):
        return _clean_axis_neft(desc)

    # ── IMPS ─────────────────────────────────────────────────────────────
    if upper.startswith('IMPS'):
        parts = desc.split('/')
        for part in parts:
            part = part.strip()
            if part and len(part) > 3 and any(c.isalpha() for c in part) and not part.isdigit():
                if part.upper() not in ('IMPS', 'P2A', 'P2M'):
                    return f"IMPS - {part.title()}"
        return "IMPS Transfer"

    # ── ACH (Auto-debit) ─────────────────────────────────────────────────
    if 'ACH-DR' in upper or 'ACH DR' in upper:
        # Try to extract company name
        if 'ICICI' in upper:
            return "ACH - ICICI (EMI/Insurance)"
        if 'HDFC' in upper:
            return "ACH - HDFC (EMI/Insurance)"
        return "ACH - Auto-debit"

    # ── Fallback ─────────────────────────────────────────────────────────
    return desc[:60] if len(desc) > 60 else desc


# Axis Bank payment processors (payee is the processor, not the actual merchant)
_AXIS_PROCESSORS = {'cashfree', 'phonepe p', 'phonepe', 'paytm pay', 'razorpay'}

# Axis Bank merchant mapping
_AXIS_MERCHANT_MAP = {
    'sodexo': 'Sodexo', 'swiggy': 'Swiggy', 'zomato': 'Zomato',
    'zepto': 'Zepto', 'blinkit': 'Blinkit',
    'amazon': 'Amazon', 'flipkart': 'Flipkart', 'myntra': 'Myntra',
    'uber': 'Uber', 'rapido': 'Rapido', 'olacabs': 'Ola',
    'netflix': 'Netflix', 'spotify': 'Spotify',
    'google': 'Google', 'apple': 'Apple',
    'cred': 'Cred', 'groww': 'Groww', 'zerodha': 'Zerodha',
    'irctc': 'IRCTC', 'meesho': 'Meesho',
    'navi technologies lim': 'Navi Insurance',
    'mindtree infotech': 'Mindtree Infotech',
    'm g motors': 'M G Motors',
    'sanwariya transport': 'Sanwariya Transport',
    'pennydro': 'PennyDrop',
    'delhivery limited': 'Delhivery',
    'innovativ': 'Innovative',
}


def _clean_axis_upi(desc: str) -> str:
    """Extract payee from Axis Bank UPI narration.
    Format: UPI/P2A_or_P2M/ref/PayeeName/BankOrApp/purpose
    """
    parts = desc.split('/')

    # Need at least: UPI / type / ref / payee
    if len(parts) < 4:
        return "UPI Transfer"

    txn_type = parts[1].strip().upper()  # P2A, P2M, CRADJ
    payee_raw = parts[3].strip()

    if not payee_raw or payee_raw.isdigit():
        return "UPI Transfer"

    # Check if payee is actually a payment processor
    payee_lower = payee_raw.lower().strip()
    if payee_lower in _AXIS_PROCESSORS:
        # Look for actual merchant in remaining parts (purpose field)
        for part in parts[4:]:
            p = part.strip()
            if p and len(p) > 2 and any(c.isalpha() for c in p):
                pl = p.lower()
                # Skip bank names and generic terms
                if pl not in ('payment', 'na', 'yes bank', 'yes bank ltd', 'paytm payments bank',
                              'state bank of india', 'icici bank', 'axis bank ltd.',
                              'hdfc bank', 'punjab national bank', 'kotak mahindra bank',
                              'idfc first bank', 'standard', 'ujjivan small finance',
                              'indusind bank', 'acc', 'nef', 'transfer', 'fttransf'):
                    # Detect "cred" in purpose field (payment via Cred)
                    if 'cred' in pl.lower():
                        return "UPI - Cred"
                    # Check merchant mapping
                    merchant = _AXIS_MERCHANT_MAP.get(pl)
                    if merchant:
                        return f"UPI - {merchant}"
                    return f"UPI - {p.title()}"
        # Processor itself is the payee (e.g., PhonePe bill payment)
        return f"UPI - {payee_raw.title()}"

    # Check merchant mapping on payee name
    payee_key = payee_lower.replace(' ', '')
    merchant = _AXIS_MERCHANT_MAP.get(payee_lower)
    if not merchant:
        for key, val in _AXIS_MERCHANT_MAP.items():
            if payee_key.startswith(key.replace(' ', '')) or key.replace(' ', '').startswith(payee_key):
                merchant = val
                break

    if merchant:
        return f"UPI - {merchant}"

    # Title-case person names
    clean_name = payee_raw.title()
    # Truncate overly long names
    if len(clean_name) > 35:
        clean_name = clean_name[:35].rsplit(' ', 1)[0]

    return f"UPI - {clean_name}"


def _clean_axis_neft(desc: str) -> str:
    """Extract payee from Axis Bank NEFT narration.
    Formats:
      NEFT/CODE/PayeeName/BankName/ref
      NEFT CR-CODE-BankCode-PayeeName--/purpose/
    """
    upper = desc.upper()

    # Detect salary
    if '/SALARY/' in upper or 'SALARY' in upper:
        # Extract company name from the NEFT narration
        # Format: NEFT CR-CODE-BankCode-CompanyName--/SALARY/
        company_match = re.search(r'-([A-Z][A-Z\s]+[A-Z])[-/]', desc)
        if company_match:
            company = company_match.group(1).strip()
            if company.upper() not in ('NEFT', 'CR', 'DR', 'SALARY'):
                return f"Salary Credit - {company.title()}"
        return "Salary Credit"

    # Standard NEFT format: NEFT/CODE/PayeeName/BankName
    parts = desc.split('/')
    if len(parts) >= 3:
        payee = parts[2].strip()
        if payee and len(payee) > 2 and any(c.isalpha() for c in payee):
            # Check merchant mapping
            pl = payee.lower()
            merchant = _AXIS_MERCHANT_MAP.get(pl)
            if merchant:
                return f"NEFT - {merchant}"
            return f"NEFT - {payee.title()}"

    # Fallback: try hyphen-separated format
    parts = desc.split('-')
    for part in parts:
        part = part.strip()
        if part and len(part) > 4 and any(c.isalpha() for c in part):
            if part.upper() not in ('NEFT', 'CR', 'DR', 'NEFT CR'):
                return f"NEFT - {part.title()}"

    return "NEFT Transfer"


def parse_axis_pdf(pdf, all_text: str) -> list:
    """
    Parse Axis Bank PDF statement.
    Axis format: Tran Date | Chq No | Particulars | Debit | Credit | Balance | Init. Br
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row or len(row) < 6:
                    continue
                
                # Clean the row - replace newlines with spaces
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header and empty rows
                if not cleaned[0] or 'tran date' in cleaned[0].lower() or 'opening balance' in ' '.join(cleaned).lower():
                    continue
                
                # Parse date (DD-MM-YYYY format)
                date = parse_date(cleaned[0])
                if not date:
                    continue
                
                # Get description (column 2 - Particulars)
                description = cleaned[2] if len(cleaned) > 2 else ""
                if not description:
                    continue
                
                # Get debit and credit (columns 3 and 4)
                bank_debit = parse_amount(cleaned[3]) if len(cleaned) > 3 else 0
                bank_credit = parse_amount(cleaned[4]) if len(cleaned) > 4 else 0
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_axis_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


