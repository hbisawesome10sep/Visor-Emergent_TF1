"""
ICICI Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


def clean_icici_description(raw_desc: str) -> str:
    """Clean up ICICI transaction description by extracting payee/merchant info.
    ICICI UPI format: UPI/upi_id/description/BANK NAME/ref/hash
    """
    desc = raw_desc.strip().rstrip('/')
    if not desc:
        return "Bank Transaction"

    upper = desc.upper()

    # ── Interest ─────────────────────────────────────────────────────────
    if upper.startswith('INT.') or 'INTEREST' in upper:
        return "Interest Credit"

    # ── Withdrawal ───────────────────────────────────────────────────────
    if upper.startswith('WITHDR'):
        return "ATM/Cash Withdrawal"

    # ── UPI transactions ─────────────────────────────────────────────────
    if upper.startswith('UPI/'):
        return _extract_icici_upi_description(desc)

    # ── NEFT ─────────────────────────────────────────────────────────────
    if upper.startswith('NEFT-') or upper.startswith('NEFT/'):
        return _extract_icici_neft_description(desc)

    # ── ACH / Auto-debit ─────────────────────────────────────────────────
    if upper.startswith('ACH/'):
        parts = desc.split('/')
        if len(parts) >= 2:
            company = parts[1].strip()
            if company and len(company) > 2:
                # Clean known ACH names
                cl = company.upper()
                if 'INDIAN CLEARING' in cl:
                    return "ACH - SIP/Mutual Fund"
                if 'GROWW' in cl:
                    return "ACH - Groww SIP"
                if 'ZERODHA' in cl:
                    return "ACH - Zerodha SIP"
                if 'BAJAJ' in cl:
                    return "ACH - Bajaj Finance"
                if 'INSURANCE' in cl or 'LIC' in cl:
                    return f"ACH - {company.title()}"
                return f"ACH - {company.title()}"
        return "ACH - Auto-debit"

    # ── IMPS ─────────────────────────────────────────────────────────────
    if upper.startswith('IMPS/') or upper.startswith('MMT/'):
        parts = desc.split('/')
        for part in parts[1:]:
            part = part.strip()
            if part and len(part) > 3 and any(c.isalpha() for c in part) and not part.isdigit():
                return f"IMPS - {part.title()}"
        return "IMPS Transfer"

    # ── CMS ──────────────────────────────────────────────────────────────
    if upper.startswith('CMS/') or '/CMS/' in upper:
        return "CMS - Collection"

    # ── Fallback ─────────────────────────────────────────────────────────
    return desc[:60] if len(desc) > 60 else desc


# Known ICICI UPI payee-to-merchant mappings
_ICICI_MERCHANT_MAP = {
    'paytm': 'Paytm', 'paytmqr': 'Paytm',
    'sodexo': 'Sodexo', 'sodexoindiaservice': 'Sodexo',
    'swiggy': 'Swiggy', 'swiggystores': 'Swiggy',
    'zomato': 'Zomato', 'zomatoonline': 'Zomato',
    'zepto': 'Zepto', 'zeptomarketplace': 'Zepto',
    'blinkit': 'Blinkit', 'blinkitcommerce': 'Blinkit',
    'amazon': 'Amazon', 'flipkart': 'Flipkart', 'myntra': 'Myntra',
    'uber': 'Uber', 'olacabs': 'Ola', 'rapido': 'Rapido',
    'gokiwitechprivate': 'Ola', 'gokiwi': 'Ola',
    'netflix': 'Netflix', 'spotify': 'Spotify',
    'apple': 'Apple', 'appleservices': 'Apple',
    'quickbite': 'QuickBite', 'quickbiteshop': 'QuickBite',
    'irctc': 'IRCTC', 'irctcecatering': 'IRCTC eCatering',
    'googleasiapacific': 'Google', 'google': 'Google',
    'cred': 'Cred', 'dreamplugservice': 'Cred',
    'vodafoneidea': 'Vi Recharge',
    'bajajfinancelimite': 'Bajaj Finance', 'bajajfinance': 'Bajaj Finance',
    'npci': 'NPCI Cashback',
    'groww': 'Groww', 'growwinvesttech': 'Groww',
    'tatastarbucks': 'Starbucks',
}


def _extract_icici_upi_description(desc: str) -> str:
    """Extract payee from ICICI UPI narration.
    ICICI format: UPI/upi_id_or_name/description/BANK NAME/ref/hash
    The first part after UPI/ is the UPI ID (user@bank or phone@bank).
    """
    upper = desc.upper()
    via_cred = 'PAID VIA CRED' in upper or 'VIA CRED' in upper

    parts = desc[4:].split('/')  # Remove 'UPI/' prefix and split

    if not parts:
        return "UPI Transfer"

    # The first part is the UPI ID (like tksaleem364@oki, paytm-83851273@, 8947819840@ptye)
    upi_id = parts[0].strip()

    # Extract payee name from UPI ID
    payee = _extract_payee_from_upi_id(upi_id)

    # Check merchant mapping
    payee_key = payee.lower().replace(' ', '').replace('.', '')
    merchant = _ICICI_MERCHANT_MAP.get(payee_key)

    # Also try prefix matching for partial names (e.g., 'quickbite.96156' -> 'quickbite')
    if not merchant:
        for key, val in _ICICI_MERCHANT_MAP.items():
            if payee_key.startswith(key) or key.startswith(payee_key):
                merchant = val
                break

    if merchant:
        payee = merchant

    # Check for refund
    if any(kw in upper for kw in ['REFUND', 'REVERSAL', 'CASHBACK']):
        return f"UPI Refund - {payee}"

    # Add "via Cred" annotation if applicable
    if via_cred and payee.lower() not in ('cred', 'dreamplugservice'):
        return f"UPI - {payee} (via Cred)"

    return f"UPI - {payee}"


def _extract_payee_from_upi_id(upi_id: str) -> str:
    """Extract a human-readable payee name from a UPI ID.
    Examples: tksaleem364@oki -> Tksaleem, paytm-83851273@ -> Paytm,
              8947819840@ptye -> 8947819840, quickbite.96156 -> Quickbite
    """
    # Remove @bank suffix
    name = upi_id.split('@')[0].strip()

    # Remove trailing phone numbers
    name = re.sub(r'[-.]?\d{7,}$', '', name).strip('-. ')

    # Remove known UPI app suffixes
    name = re.sub(r'[-.]?(payu|bharatpe|razorpay|okaxis|oksbi|okicici|okhdfcbank|ybl|ptyes|ptybl|ibl)$', '', name, flags=re.IGNORECASE).strip('-. ')

    if not name or name.isdigit():
        # It's a phone number UPI — use the original number
        return upi_id.split('@')[0]

    return name.title()


def _extract_icici_neft_description(desc: str) -> str:
    """Extract meaningful info from ICICI NEFT narration.
    Format: NEFT-CODE-DESCRIPTION
    """
    # Remove NEFT- prefix and transaction code
    rest = re.sub(r'^NEFT[-/][A-Z0-9]+[-/]', '', desc, count=1)

    if not rest:
        return "NEFT Transfer"

    # Check for mutual fund redemptions
    upper = rest.upper()
    if 'MUTUAL FUND' in upper or 'REDEMPTION' in upper:
        # Extract fund name
        fund_match = re.match(r'(.+?)(?:COMMON|REDEMPTION|A/C|-\d)', rest, re.IGNORECASE)
        if fund_match:
            fund = fund_match.group(1).strip().title()
            return f"NEFT - {fund} (MF Redemption)"
        return "NEFT - Mutual Fund Redemption"

    if 'SALARY' in upper:
        return "Salary Credit"

    # Extract first meaningful name
    parts = rest.split('-')
    for part in parts:
        part = part.strip()
        if part and len(part) > 3 and any(c.isalpha() for c in part) and not part.isdigit():
            return f"NEFT - {part.title()}"

    return "NEFT Transfer"


def parse_icici_pdf_text(all_text: str) -> list:
    """
    Parse ICICI Bank PDF statement from raw text.
    ICICI layout: Description lines (starting with UPI/, ACH/, NEFT-, etc.)
    are INTERLEAVED around the amount line (S.No Date Amount Balance).

    Structure per transaction:
      [NEW] Description start (UPI/..., ACH/..., NEFT-...)
      [AMT] S.No  Date  Amount  Balance
            Continuation lines...
    """
    transactions = []
    lines = all_text.split('\n')

    # Known transaction-start prefixes
    _TXN_PREFIXES = ('UPI/', 'ACH/', 'NEFT-', 'NEFT/', 'IMPS/', 'CMS/', 'MMT/',
                     'INT.', 'WITHDR', 'FT-', 'BIL/')

    # Amount line: S.No(digits) Date(DD.MM.YYYY) Amount Balance
    amt_re = re.compile(r'^(\d+)\s+(\d{2}\.\d{2}\.\d{4})\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$')

    # Skip patterns
    _SKIP_WORDS = ('s no', 'transaction date', 'cheque number', 'legends',
                   'sincerely', 'team icici', 'statement of transactions',
                   'withdrawal', 'deposit', 'balance', 'page', 'icici bank',
                   'your base branch', 'rajasthan', 'gurgaon', 'jodhpur',
                   'alwar', 'in,', 'harsh bhati')

    # Phase 1: Build transaction records by scanning lines
    pending_desc = []   # Description lines for current transaction
    pending_amt = None  # Amount data for current transaction

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip headers/footers
        if any(skip in line.lower() for skip in _SKIP_WORDS):
            continue

        # Check if this is an amount line
        m = amt_re.match(line)
        if m:
            s_no, date_str, amount_str, balance_str = m.groups()
            pending_amt = {
                's_no': int(s_no),
                'date': parse_date(date_str),
                'amount': parse_amount(amount_str),
                'balance': parse_amount(balance_str),
            }
            continue

        # Check if this starts a new transaction description
        is_new_txn = any(line.startswith(pfx) for pfx in _TXN_PREFIXES)

        if is_new_txn:
            # Save previous transaction if we have both description and amount
            if pending_desc and pending_amt and pending_amt['date']:
                raw_desc = ' '.join(pending_desc)
                transactions.append({
                    'date': pending_amt['date'],
                    'description': clean_icici_description(raw_desc),
                    'raw_description': raw_desc,
                    'amount': pending_amt['amount'],
                    'balance': pending_amt['balance'],
                    's_no': pending_amt['s_no'],
                    'bank_debit': 0,
                    'bank_credit': 0,
                })
            # Start new description
            pending_desc = [line]
            pending_amt = None
        else:
            # Continuation line — append to current description
            pending_desc.append(line)

    # Save last transaction
    if pending_desc and pending_amt and pending_amt['date']:
        raw_desc = ' '.join(pending_desc)
        transactions.append({
            'date': pending_amt['date'],
            'description': clean_icici_description(raw_desc),
            'raw_description': raw_desc,
            'amount': pending_amt['amount'],
            'balance': pending_amt['balance'],
            's_no': pending_amt['s_no'],
            'bank_debit': 0,
            'bank_credit': 0,
        })

    # Phase 2: Determine debit/credit by comparing consecutive balances
    for i, txn in enumerate(transactions):
        amount = txn['amount']
        is_credit = False

        # Check by balance change
        if i > 0:
            prev_balance = transactions[i - 1]['balance']
            balance_change = txn['balance'] - prev_balance
            if abs(balance_change - amount) < 1:
                is_credit = True
            elif abs(balance_change + amount) < 1:
                is_credit = False
            else:
                # Fallback: check description keywords
                desc_lower = txn['description'].lower()
                is_credit = any(kw in desc_lower for kw in
                                ['salary', 'cashback', 'refund', 'reversal',
                                 'interest credit', 'neft -', 'mf redemption', 'npci'])
        else:
            # First transaction: use description hints
            desc_lower = txn['description'].lower()
            is_credit = any(kw in desc_lower for kw in
                            ['salary', 'cashback', 'refund', 'reversal',
                             'interest credit', 'neft -', 'mf redemption', 'npci'])

        if is_credit:
            txn['bank_credit'] = amount
        else:
            txn['bank_debit'] = amount

    # Return cleaned results
    return [{
        'date': t['date'],
        'description': t['description'],
        'raw_description': t.get('raw_description', ''),
        'bank_debit': t['bank_debit'],
        'bank_credit': t['bank_credit'],
    } for t in transactions]


