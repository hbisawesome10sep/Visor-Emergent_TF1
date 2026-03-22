"""
Bank Statement PDF Parsers
All bank-specific PDF parsing logic for Indian bank statements.
"""
import re
import io
import logging
from parsers.utils import detect_bank, parse_date, parse_amount, detect_header_columns

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


def clean_sbi_description(raw_desc: str) -> str:
    """Clean up SBI transaction description by extracting key info.
    SBI table extraction provides truncated descriptions (~40 chars):
      WDL TFR UPI/DR/ref/PayeeName/Bank...
      DEP TFR UPI/CR/ref/PayeeName/Bank...
      WDL TFR INB AutoPay~Company~RefCode
      DEP TFR NEFT*Bank*Ref*PayeeName
      CEMTEX DEP ACHCr CompanyRef
    """
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    if not desc:
        return "Bank Transaction"

    # Strip SBI type prefixes
    for prefix in ('WDL TFR INB ', 'DEP TFR INB ', 'WDL TFR ', 'DEP TFR ', 'CEMTEX DEP ACHCr '):
        if desc.startswith(prefix):
            desc = desc[len(prefix):].strip()
            break

    upper = desc.upper()

    # ── Interest credit ──────────────────────────────────────────────────
    if 'INT.CR' in upper or 'INTEREST' in upper or 'INT CR' in upper:
        return "Interest Credit"

    # ── AutoPay (SIP auto-debit) ─────────────────────────────────────────
    if desc.startswith('AutoPay~') or desc.startswith('AUTOPAY~'):
        parts = desc.split('~')
        if len(parts) >= 2:
            company = parts[1].strip()
            return _clean_sbi_autopay(company)
        return "SIP Auto-debit"

    # ── UPI transactions ─────────────────────────────────────────────────
    if 'UPI/' in upper:
        return _clean_sbi_upi(desc)

    # ── NEFT ─────────────────────────────────────────────────────────────
    if upper.startswith('NEFT') or 'NEFT*' in upper:
        return _clean_sbi_neft(desc)

    # ── IMPS ─────────────────────────────────────────────────────────────
    if upper.startswith('IMPS') or 'IMPS/' in upper:
        return "IMPS Transfer"

    # ── ATM / Cash ───────────────────────────────────────────────────────
    if 'ATM' in upper or 'CASH WDL' in upper or 'CASH DEP' in upper:
        return "ATM Withdrawal" if 'WDL' in upper or 'ATM' in upper else "Cash Deposit"

    # ── ACH Credit (dividends etc.) ──────────────────────────────────────
    if 'ACHCR' in upper or 'ACH CR' in upper:
        # Try to extract company name from ref code
        if 'DIV' in upper:
            return "Dividend Credit"
        return "ACH Credit"

    # ── Dividend ─────────────────────────────────────────────────────────
    if 'DIV' in upper and ('TATA' in upper or 'HDFC' in upper or 'RELIANCE' in upper or 'TCPL' in upper):
        return "Dividend Credit"

    # ── Fallback ─────────────────────────────────────────────────────────
    return desc[:60] if len(desc) > 60 else desc


# SBI AutoPay company name mappings
_SBI_AUTOPAY_MAP = {
    'nipponindi': 'Nippon India MF', 'nippon': 'Nippon India MF',
    'dspblackro': 'DSP BlackRock MF', 'dsp': 'DSP BlackRock MF',
    'sbimutual': 'SBI Mutual Fund', 'sbi': 'SBI Mutual Fund',
    'icicipru': 'ICICI Pru MF', 'icici': 'ICICI Pru MF',
    'hdfcmutual': 'HDFC Mutual Fund', 'hdfc': 'HDFC Mutual Fund',
    'motilal': 'Motilal Oswal MF', 'motilalosa': 'Motilal Oswal MF',
    'tata': 'Tata MF', 'kotak': 'Kotak MF', 'axis': 'Axis MF',
    'canara': 'Canara Robeco MF', 'quant': 'Quant MF',
    'parag': 'PPFAS MF', 'ppfas': 'PPFAS MF',
    'bajaj': 'Bajaj Finance',
    'lic': 'LIC Insurance',
    'insurance': 'Insurance',
}


def _clean_sbi_autopay(company: str) -> str:
    """Clean SBI AutoPay company name."""
    cl = company.lower().replace(' ', '')
    for key, name in _SBI_AUTOPAY_MAP.items():
        if key in cl:
            return f"SIP - {name}"
    return f"SIP - {company.title()}"


# SBI UPI payee merchant mappings (reuse HDFC map + SBI-specific)
_SBI_MERCHANT_MAP = {
    'sodexo': 'Sodexo', 'sodexo j': 'Sodexo',
    'swiggy': 'Swiggy', 'swiggy s': 'Swiggy',
    'zomato': 'Zomato', 'zomato o': 'Zomato',
    'zepto': 'Zepto', 'zepto ma': 'Zepto',
    'blinkit': 'Blinkit', 'blinkit ': 'Blinkit',
    'amazon': 'Amazon', 'flipkart': 'Flipkart', 'myntra': 'Myntra',
    'uber': 'Uber', 'rapido': 'Rapido', 'ola': 'Ola',
    'netflix': 'Netflix', 'spotify': 'Spotify',
    'google p': 'Google Play', 'google': 'Google',
    'vi': 'Vi Recharge', 'vodafone': 'Vi Recharge',
    'cred': 'Cred', 'dreamplug': 'Cred',
    'zerodha': 'Zerodha', 'groww': 'Groww',
    'quick bite': 'QuickBite', 'quickbite': 'QuickBite',
    'irctc': 'IRCTC', 'apple': 'Apple', 'appleserv': 'Apple',
    'bharti he': 'Airtel Recharge', 'airtel': 'Airtel',
    'bajajfina': 'Bajaj Finance',
    'npci': 'NPCI Cashback',
    'sai sidd': 'Sai Siddhi (Food)', 'saisiddhi': 'Sai Siddhi (Food)',
    'paytm': 'Paytm',
}


def _clean_sbi_upi(desc: str) -> str:
    """Extract payee from SBI UPI description.
    Format: UPI/DR_or_CR/ref/PayeeName/BankCode/upiid/purpose
    Note: SBI truncates at ~35 chars, so payee may be cut off.
    """
    upper = desc.upper()
    via_cred = 'VIA CRED' in upper or 'PAID VIA' in upper
    is_refund = 'REFUND' in upper or 'REVERSAL' in upper

    parts = desc.split('/')
    # Find DR or CR to locate the payee
    payee = None
    for i, part in enumerate(parts):
        if part.strip().upper() in ('DR', 'CR') and i + 2 < len(parts):
            # parts[i+1] is the ref number (digits), parts[i+2] is the payee
            ref_candidate = parts[i + 1].strip()
            payee_raw = parts[i + 2].strip()

            # If ref is not all digits, it might be payee already
            if not ref_candidate.replace(' ', '').isdigit() and len(ref_candidate) > 3:
                payee_raw = ref_candidate

            if payee_raw and not payee_raw.isdigit():
                payee = payee_raw
            break

    if not payee:
        return "UPI Refund" if is_refund else "UPI Transfer"

    # Clean trailing single chars (from truncation) and bank codes
    payee = payee.rstrip()
    # Remove trailing single letter + optional space (truncation artifact like "Sodexo J")
    payee = re.sub(r'\s+[A-Z]$', '', payee).strip()

    # Check merchant mapping (try exact first, then prefix)
    payee_lower = payee.lower()
    merchant = _SBI_MERCHANT_MAP.get(payee_lower)
    if not merchant:
        for key, val in _SBI_MERCHANT_MAP.items():
            if payee_lower.startswith(key) or key.startswith(payee_lower):
                merchant = val
                break

    if merchant:
        payee = merchant

    # Title-case person names
    if not merchant:
        payee = payee.title()
        if len(payee) > 30:
            payee = payee[:30].rsplit(' ', 1)[0]

    if is_refund:
        return f"UPI Refund - {payee}"
    if via_cred and payee.lower() not in ('cred',):
        return f"UPI - {payee} (via Cred)"
    return f"UPI - {payee}"


def _clean_sbi_neft(desc: str) -> str:
    """Extract payee from SBI NEFT description.
    Format: NEFT*BankCode*RefCode*PayeeName
    """
    # Try * separator (common SBI format)
    parts = desc.split('*')
    if len(parts) >= 4:
        payee = parts[3].strip()
        if payee and len(payee) > 2:
            upper_payee = payee.upper()
            if 'MUTUAL FUND' in upper_payee or 'REDEMPTION' in upper_payee:
                return f"NEFT - {payee.title()} (MF)"
            if 'ZERODHA' in upper_payee:
                return f"NEFT - Zerodha"
            if 'GROWW' in upper_payee:
                return f"NEFT - Groww"
            return f"NEFT - {payee.title()}"

    # Try / separator
    parts = desc.split('/')
    for part in parts:
        part = part.strip()
        if part and len(part) > 3 and any(c.isalpha() for c in part) and not part.isdigit():
            if part.upper() not in ('NEFT', 'RTGS', 'IMPS', 'SBI', 'HDFC', 'ICICI'):
                return f"NEFT - {part.title()}"

    return "NEFT Transfer"


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


def clean_indusind_description(raw_desc: str) -> str:
    """Clean up IndusInd Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    # Known merchants
    known_merchants = {
        'paytm': 'Paytm',
        'phonepe': 'PhonePe',
        'gpay': 'Google Pay',
        'amazon': 'Amazon',
        'flipkart': 'Flipkart',
        'swiggy': 'Swiggy',
        'zomato': 'Zomato',
        'uber': 'Uber',
        'ola': 'Ola',
        'slice': 'Slice',
        'liquiloans': 'Liquiloans',
    }
    
    lower_desc = desc.lower()
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # UPI format: UPI/refno/CR or DR/Name/Bank/upiid
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        # Find CR or DR and get the name after it
        for i, part in enumerate(parts):
            if part in ('CR', 'DR') and i+1 < len(parts):
                name = parts[i+1].strip()
                if name and len(name) > 2 and any(c.isalpha() for c in name):
                    return f"UPI - {name.title()}"
    
    # IMPS format: IMPS/P2A/refno/Bank/Name
    if desc.startswith('IMPS/'):
        parts = desc.split('/')
        # Name is usually the last meaningful part
        for part in reversed(parts):
            part = part.strip()
            if part and len(part) > 3 and any(c.isalpha() for c in part):
                if part not in ('IMPS', 'P2A', 'P2M'):
                    return f"IMPS - {part.title()}"
        return "IMPS Transfer"
    
    # TRF FRM - Transfer from another account
    if 'trf frm' in lower_desc:
        return "Internal Transfer"
    
    # NEFT transfer
    if desc.startswith('N/') or 'neft' in lower_desc:
        # Try to extract company name
        parts = desc.split('/')
        for part in parts:
            if len(part) > 5 and part.isupper() and ' ' in part:
                return f"NEFT - {part.title()}"
        return "NEFT Transfer"
    
    # MC POS TXN - Card transaction
    if 'mc pos txn' in lower_desc or 'pos txn' in lower_desc:
        return "Card Purchase"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def parse_indusind_pdf(pdf, all_text: str) -> list:
    """
    Parse IndusInd Bank PDF statement.
    IndusInd format varies by page:
    - Page 1: Date | Particulars | Chq./Ref.No. | Withdrawl | Deposit | Balance
    - Page 2+: Date | Particulars | Ref | EMPTY | Withdrawl/Deposit | Withdrawl/Deposit | Balance
    
    We detect debit vs credit by looking at /DR/ or /CR/ in the description.
    """
    transactions = []
    
    for page_num, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or len(row) < 5:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header and info rows
                first_col = cleaned[0].lower()
                if not cleaned[0] or 'date' in first_col or 'indusind' in first_col:
                    continue
                if 'rajesh' in first_col or 'account' in first_col or 'page' in first_col:
                    continue
                if first_col in ('empty', ''):
                    continue
                
                # Parse date (DD-Mon-YYYY format like 02-Oct-2023)
                date = parse_date(cleaned[0])
                if not date:
                    continue
                
                # Get description (column 1 - Particulars)
                description = cleaned[1] if len(cleaned) > 1 else ""
                if not description:
                    continue
                
                # Determine debit or credit from description pattern
                is_debit = '/DR/' in description or '/dr/' in description
                is_credit = '/CR/' in description or '/cr/' in description or 'TRF FRM' in description
                
                # Find the amount - look for non-empty numeric value in columns 3-6
                amount = 0
                for i in range(3, min(7, len(cleaned))):
                    val = parse_amount(cleaned[i])
                    if val > 0:
                        amount = val
                        break
                
                if amount == 0:
                    continue
                
                # Assign to debit or credit
                if is_debit:
                    bank_debit = amount
                    bank_credit = 0
                elif is_credit:
                    bank_debit = 0
                    bank_credit = amount
                else:
                    # For IMPS without clear indicator, check description keywords
                    if 'IMPS/P2A' in description:
                        # P2A is usually incoming
                        bank_credit = amount
                        bank_debit = 0
                    else:
                        # Default to debit
                        bank_debit = amount
                        bank_credit = 0
                
                transactions.append({
                    'date': date,
                    'description': clean_indusind_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def clean_yesbank_description(raw_desc: str) -> str:
    """Clean up Yes Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    # Known merchants
    known_merchants = {
        'paytm': 'Paytm',
        'phonepe': 'PhonePe',
        'gpay': 'Google Pay',
        'amazon': 'Amazon',
        'flipkart': 'Flipkart',
        'swiggy': 'Swiggy',
        'zomato': 'Zomato',
    }
    
    lower_desc = desc.lower()
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # IMPS format: IMPS/Purpose/Name/Account/RRN/Bank
    if desc.startswith('IMPS/'):
        parts = desc.split('/')
        # Name is usually the 3rd part
        if len(parts) >= 3:
            name = parts[2].strip()
            if name and len(name) > 2 and any(c.isalpha() for c in name):
                return f"IMPS - {name.title()}"
        return "IMPS Transfer"
    
    # Funds Transfer
    if 'funds trf to' in lower_desc:
        return "Funds Transfer Out"
    if 'funds trf from' in lower_desc:
        return "Funds Transfer In"
    
    # UPI
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        if len(parts) >= 3:
            name = parts[2].strip()
            if name and len(name) > 2:
                return f"UPI - {name.title()}"
        return "UPI Transfer"
    
    # NEFT
    if 'neft' in lower_desc:
        return "NEFT Transfer"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def parse_yesbank_pdf(pdf, all_text: str) -> list:
    """
    Parse Yes Bank PDF statement.
    Yes Bank format: Reference No | Transaction Date | Credited Amount | Debited Amount | Balance | Description
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or len(row) < 5:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header and empty rows
                first_col = cleaned[0].lower()
                if not cleaned[0] or 'reference' in first_col or 'date' in first_col:
                    continue
                if first_col in ('', 'empty'):
                    continue
                
                # Yes Bank has date in column 1 (not column 0 which is Reference No)
                date_str = cleaned[1] if len(cleaned) > 1 else ""
                # Remove time portion if present (e.g., "2022-12-04 09:01:00" -> "2022-12-04")
                if ' ' in date_str:
                    date_str = date_str.split(' ')[0]
                
                date = parse_date(date_str)
                if not date:
                    continue
                
                # Get credit and debit amounts (columns 2 and 3)
                bank_credit = parse_amount(cleaned[2]) if len(cleaned) > 2 else 0
                bank_debit = parse_amount(cleaned[3]) if len(cleaned) > 3 else 0
                
                # Get description (column 5)
                description = cleaned[5] if len(cleaned) > 5 else ""
                if not description:
                    description = "Bank Transaction"
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_yesbank_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def clean_hdfc_description(raw_desc: str, ref_number: str = "") -> str:
    """Clean up HDFC Bank transaction description.
    Extracts meaningful merchant/payee names from full multi-line narrations.
    Priority: UPI payee extraction first, then pattern matching, then keyword fallback."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    if not desc:
        return f"Transaction {ref_number}" if ref_number else "Unknown Transaction"

    upper_desc = desc.upper()

    # ── Quick checks for non-UPI transaction types ───────────────────────
    if 'INTERESTPAID' in upper_desc or 'INTEREST PAID' in upper_desc or 'CREDITINTEREST' in upper_desc:
        return "Interest Credit"

    if any(kw in upper_desc for kw in ['JPMCSALARY', 'JPMC SALARY', 'SALARY']):
        return "Salary Credit"

    if upper_desc.startswith('CASHDEP') or 'CASH DEP' in upper_desc:
        return "Cash Deposit"

    if any(kw in upper_desc for kw in ['INSTAALERTCHG', 'INSTA ALERT', 'SMS CHARGES', 'SMSCHG']):
        return "Bank Charges - SMS Alert"

    # ── UPI transactions (MUST be checked before merchant keyword scan) ──
    if 'UPI-' in desc or 'UPI/' in desc:
        return _extract_upi_description(desc, ref_number)

    # ── REV-UPI (UPI reversal) ───────────────────────────────────────────
    if upper_desc.startswith('REV-UPI') or upper_desc.startswith('REV-'):
        payee_match = re.search(r'([A-Za-z][A-Za-z\s]+?)(?:\d{5,}|@|-\d)', desc[4:])
        if payee_match:
            return f"UPI Reversal - {payee_match.group(1).strip().title()}"
        return "UPI Reversal"

    # ── FT (Fund Transfer — often salary) ─────────────────────────────────
    if upper_desc.startswith('FT-') or upper_desc.startswith('FT '):
        if 'SALARY' in upper_desc or 'PAYROLL' in upper_desc:
            return "Salary Credit"
        alpha_parts = re.findall(r'[A-Z][A-Za-z]{3,}(?:\s+[A-Z][A-Za-z]+)*', desc)
        if alpha_parts:
            name = alpha_parts[-1] if len(alpha_parts) > 1 else alpha_parts[0]
            return f"Fund Transfer - {name.title()}"
        return "Fund Transfer"

    # ── IMPS ─────────────────────────────────────────────────────────────
    if upper_desc.startswith('IMPS-') or upper_desc.startswith('IMPS/'):
        parts = re.split(r'[\-/]', desc)
        for part in parts[1:]:
            part = part.strip()
            if len(part) > 3 and any(c.isalpha() for c in part) and not part.isdigit():
                return f"IMPS - {part.title()}"
        return "IMPS Transfer"

    # ── NEFT ─────────────────────────────────────────────────────────────
    if 'NEFT' in upper_desc:
        parts = re.split(r'[\-/]', desc)
        for part in parts:
            part = part.strip()
            if len(part) > 3 and part.replace(' ', '').isalpha():
                return f"NEFT - {part.title()}"
        return "NEFT Transfer"

    # ── EMI ──────────────────────────────────────────────────────────────
    if upper_desc.startswith('EMI') or 'EMI' in upper_desc:
        return "EMI Payment"

    # ── ACH debit ────────────────────────────────────────────────────────
    if upper_desc.startswith('ACHD-') or upper_desc.startswith('ACH-') or 'ACH D' in upper_desc:
        parts = re.split(r'[\-/]', desc)
        if len(parts) >= 2:
            company = parts[1].strip()
            if company:
                return f"Auto-debit - {company.title()}"
        return "Auto-debit"

    # ── Bill payment ─────────────────────────────────────────────────────
    if 'BILLPAY' in upper_desc or 'BIL/' in desc:
        if 'HDFCPE' in desc:
            return "HDFC CC Payment"
        if 'SBICARDS' in upper_desc:
            return "SBI Card Payment"
        return "Bill Payment"

    # ── POS / Card swipe ─────────────────────────────────────────────────
    if upper_desc.startswith('POS') or 'POSDEBIT' in upper_desc:
        parts = desc.split('XXXXXX')
        if len(parts) > 1:
            merchant = parts[-1].replace('POSDEBIT', '').strip()
            if merchant:
                return f"Card - {merchant.title()}"
        return "Card Purchase"

    # ── NWD (ATM / cash withdrawal) ──────────────────────────────────────
    if upper_desc.startswith('NWD') or upper_desc.startswith('AWD'):
        return "ATM Withdrawal"

    if 'ATM' in upper_desc:
        return "ATM Deposit" if 'DEP' in upper_desc else "ATM Withdrawal"

    # ── Fallback: preserve raw desc (trimmed) ────────────────────────────
    return desc[:60] if len(desc) > 60 else desc


# ── Known payee-to-merchant mappings for UPI ────────────────────────────
_UPI_MERCHANT_MAP = {
    'sodexo': 'Sodexo', 'sodexoindiaservice': 'Sodexo', 'sodexoindia': 'Sodexo',
    'swiggy': 'Swiggy', 'swiggystores': 'Swiggy',
    'zomato': 'Zomato', 'zomatoonline': 'Zomato',
    'zepto': 'Zepto', 'zeptomarketplace': 'Zepto',
    'blinkit': 'Blinkit', 'blinkitcommerce': 'Blinkit',
    'dreamplugservice': 'Cred', 'dreamplug': 'Cred',
    'cred': 'Cred',
    'bhartihexacom': 'Airtel Recharge', 'bhartihexacomlimit': 'Airtel Recharge',
    'airtelpayments': 'Airtel', 'wwwairtel': 'Airtel',
    'fpltechnologies': 'PhonePe',
    'gokiwitechprivate': 'Ola',
    'cloudkitchprivatel': 'Swiggy (Cloud Kitchen)',
    'rainboxmediapvt': 'JioCinema/Viacom18',
    'irctc': 'IRCTC', 'irctcecatering': 'IRCTC eCatering',
    'indianrailway': 'Indian Railways',
    'amazon': 'Amazon', 'flipkart': 'Flipkart', 'myntra': 'Myntra',
    'uber': 'Uber', 'uberindiasystems': 'Uber',
    'olacabs': 'Ola', 'rapido': 'Rapido',
    'mcdonalds': 'McDonalds', 'tatastarbucks': 'Starbucks',
    'vodafoneidea': 'Vi Recharge', 'vi': 'Vi Recharge',
    'googleasiapacific': 'Google', 'google': 'Google',
    'goibibo': 'Goibibo', 'makemytrip': 'MakeMyTrip',
    'godaddy': 'GoDaddy',
    'bajajfinancelimite': 'Bajaj Finance', 'bajajfinance': 'Bajaj Finance',
    'agionetechnologies': 'Agione Technologies',
    'innovist': 'Innovist',
    'netflix': 'Netflix', 'spotify': 'Spotify',
    'federalonecredit': 'Federal Bank CC Payment', 'onecard': 'OneCard CC Payment',
    'creditcardbill': 'Credit Card Bill',
    'theinstituteofcha': 'ICAI',
    'wefast': 'WeFast Delivery',
    'vendiman': 'Vendiman Vending',
    'astrotalkservices': 'AstroTalk',
    'emergentlabs': 'Emergent Labs',
    'valve': 'Steam (Valve)',
    'sevabharati': 'Seva Bharati',
    'okaydiagnostic': 'Diagnostic Lab',
    'allindiainstitute': 'AIIMS',
    'saisiddhihospitali': 'Sai Siddhi (Food)', 'saisiddhihospitality': 'Sai Siddhi (Food)',
    'anmolcateringand': 'Anmol Catering', 'anmolcatering': 'Anmol Catering',
    'tuljabhavanifastfo': 'Tulja Bhavani Foods',
    'manasgastro': 'Manas Gastro',
}

# Bank/UPI infrastructure codes to strip from payee names
_BANK_CODES = {
    'JPMC', 'PR', 'HDFC', 'ICIC', 'SBIN', 'PUNB', 'YESB', 'UTIB', 'KKBK',
    'BARB', 'IPOS', 'FDRL', 'AIRP', 'UBIN', 'IDBI', 'CNRB', 'BKID', 'CORP',
    'IOBA', 'MAHB', 'RMGB', 'CBIN', 'MAHG', 'INDB', 'PPIW',
    'LIMIT', 'LIMITED', 'PVT', 'LTD', 'PRIVATE',
}


def _extract_upi_description(desc: str, ref_number: str = "") -> str:
    """Extract clean payee name from HDFC UPI narration.
    HDFC format: UPI-PAYEENAME-UPIHANDLE@BANK-IFSC-REF-NOTE
    Multi-line continuation joined with spaces."""
    upper = desc.upper()

    # Detect payment method annotations
    via_cred = 'PAIDVIACRED' in upper or 'PAYMENTONCRED' in upper
    is_refund = 'UPIREFUND' in upper or 'REFUND' in upper

    # Find the UPI- prefix and extract everything after it
    upi_start = desc.find('UPI-')
    if upi_start < 0:
        upi_start = desc.find('UPI/')
    if upi_start < 0:
        return f"UPI Transfer #{ref_number[-6:]}" if ref_number else "UPI Transfer"

    rest = desc[upi_start + 4:]  # Text after 'UPI-'

    # Extract payee: first hyphen-separated segment
    first_segment = rest.split('-')[0].strip()

    # If the segment has spaces (from multi-line joining), filter bank code artifacts
    if ' ' in first_segment:
        words = first_segment.split()
        clean_words = []
        for i, w in enumerate(words):
            if w.upper() in _BANK_CODES:
                break
            # Only filter short (<=2 char) trailing words if they're not name prefixes
            if len(w) <= 2 and w.upper() not in ('MR', 'MS', 'DR', 'MO', 'MD'):
                # If it's the first word, keep it (could be a short name)
                if i > 0:
                    break
            clean_words.append(w)
        first_segment = ' '.join(clean_words) if clean_words else words[0]

    payee_raw = first_segment.strip()
    if not payee_raw:
        return f"UPI Transfer #{ref_number[-6:]}" if ref_number else "UPI Transfer"

    # Map to known merchant name
    payee_key = payee_raw.lower().replace(' ', '')
    merchant = _UPI_MERCHANT_MAP.get(payee_key)

    if merchant:
        payee = merchant
    else:
        # Title-case the raw payee name for person names
        payee = payee_raw.title()
        # Truncate overly long names
        if len(payee) > 35:
            payee = payee[:35].rsplit(' ', 1)[0]

    # Build final description with context
    if is_refund:
        return f"UPI Refund - {payee}"

    # For "via Cred" payments: show actual payee, not Cred
    if via_cred and payee_key not in ('cred', 'dreamplugservice', 'dreamplug'):
        return f"UPI - {payee} (via Cred)"

    return f"UPI - {payee}"


def clean_pnb_description(raw_desc: str) -> str:
    """Clean up PNB Bank transaction description.
    PNB narration formats:
      NEFT IN:CODE:COMPANYNAME:BANKCODE:ACCOUNTNO
      NEFT OUT:CODE:PAYEENAME:BANKCODE:
      RTGS From : REF/COMPANYNAME
      RTGS To : REF/PAYEENAME
      Transfer From A/C...NACOMPANYNAME
      TRF COMPANYNAME
      IMPS-IN/ref/phone
      ACH/BD-CompanyName/ref
      Cash Withdrawal At Br : BRANCH
      PMSBY RENEWAL
      INTT. From :date to date
      SMS CHRG FOR:period
      CHQ BK CH:number
      By CLEARING - ref
    """
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    if not desc:
        return "Bank Transaction"

    upper = desc.upper()
    lower_desc = desc.lower()

    # ── SMS charges & reversal ───────────────────────────────────────────
    if 'sms chrg' in lower_desc or 'smsch' in lower_desc:
        if 'rev' in lower_desc:
            return "SMS Charge Reversal"
        return "SMS Charges"

    # ── Interest credit ──────────────────────────────────────────────────
    if upper.startswith('INTT.') or 'INTEREST' in upper:
        return "Interest Credit"

    # ── NEFT IN (credit) — company name at parts[2] ─────────────────────
    if 'NEFT IN' in upper:
        parts = desc.split(':')
        # Format: NEFT IN:CODE:CompanyName:BankCode:AccountNo
        if len(parts) >= 3:
            company = parts[2].strip()
            if company and len(company) > 1 and not company.isdigit():
                return f"NEFT - {company.title()}"
        return "NEFT Inward"

    # ── NEFT OUT (debit) — payee at parts[2] ─────────────────────────────
    if 'NEFT OUT' in upper:
        parts = desc.split(':')
        if len(parts) >= 3:
            payee = parts[2].strip()
            if payee and len(payee) > 1 and not payee.isdigit():
                return f"NEFT - {payee.title()}"
        return "NEFT Outward"

    # ── NEFT Inward Settlement (Transfer From A/C) ───────────────────────
    if desc.startswith('Transfer From'):
        # Format: Transfer From A/C<account>NA<CompanyName> or NEFT INWARD SETTLEMENT
        # Look for company name patterns
        for keyword in ['SHREE', 'SALASAR', 'CRYSTAL', 'DELHIVERY']:
            if keyword in upper:
                idx = upper.find(keyword)
                company = desc[idx:].split('NEFT')[0].split('INWARD')[0].strip()
                if company:
                    return f"NEFT - {company.title()}"
        # Generic fallback
        return "NEFT Inward"

    # ── RTGS ─────────────────────────────────────────────────────────────
    if 'RTGS' in upper:
        parts = desc.split('/')
        if len(parts) >= 2:
            company = parts[-1].strip()
            if company and len(company) > 2 and any(c.isalpha() for c in company):
                if 'TO' in upper:
                    return f"RTGS Out - {company.title()}"
                return f"RTGS - {company.title()}"
        if 'TO' in upper:
            return "RTGS Outward"
        return "RTGS Inward"

    # ── IMPS ─────────────────────────────────────────────────────────────
    if 'IMPS' in upper:
        return "IMPS Transfer"

    # ── Cash Withdrawal ──────────────────────────────────────────────────
    if 'cash withdrawal' in lower_desc:
        return "Cash Withdrawal"

    # ── TRF (cheque transfer) ────────────────────────────────────────────
    if desc.startswith('TRF '):
        name = desc[4:].strip()
        if name:
            return f"Transfer - {name.title()}"
        return "Fund Transfer"

    # ── PMSBY ────────────────────────────────────────────────────────────
    if 'PMSBY' in upper:
        if '- R' in desc or 'REV' in upper:
            return "PMSBY Insurance (Reversal)"
        return "PMSBY Insurance"

    # ── Clearing ─────────────────────────────────────────────────────────
    if 'CLEARING' in upper:
        return "Cheque Clearing"

    # ── ACH / Auto-debit ─────────────────────────────────────────────────
    if desc.startswith('ACH/') or 'ACH/' in desc:
        parts = desc.split('-')
        for part in parts[1:]:
            p = part.strip().split('/')[0].strip()
            if p and len(p) > 2 and p.upper() not in ('BD', 'ACH'):
                return f"Auto-debit - {p.title()}"
        return "Auto-debit"

    # ── LIC ──────────────────────────────────────────────────────────────
    if 'LIC OF INDIA' in upper or upper.startswith('LIC '):
        return "LIC Premium"

    # ── Bajaj Allianz ────────────────────────────────────────────────────
    if 'BAJAJ' in upper and ('ALLIA' in upper or 'ALLINAZ' in upper):
        return "Bajaj Allianz Insurance"

    # ── Cheque book charges ──────────────────────────────────────────────
    if 'CHQ BK CH' in upper or 'CHEQUE BOOK' in upper:
        return "Cheque Book Charges"

    # ── HDFC Bank transfer (cheque) ──────────────────────────────────────
    if 'HDFC BANK LTD' in upper:
        return "Bank Transfer (HDFC)"

    # ── Fallback ─────────────────────────────────────────────────────────
    return desc[:60] if len(desc) > 60 else desc


def clean_idbi_description(raw_desc: str) -> str:
    """Clean up IDBI Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    lower_desc = desc.lower()
    
    # Known merchants
    known_merchants = {
        'phonepe': 'PhonePe',
        'paytm': 'Paytm',
        'amazon': 'Amazon',
        'flipkart': 'Flipkart',
        'swiggy': 'Swiggy',
        'zomato': 'Zomato',
        'uber': 'Uber',
        'bharatpe': 'BharatPe',
    }
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # UPI format: UPI/refno/Name
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        if len(parts) >= 3:
            name = parts[2].strip()
            if name and any(c.isalpha() for c in name):
                return f"UPI - {name.title()}"
        return "UPI Transfer"
    
    # VISA-POS (Card transactions)
    if desc.startswith('VISA-POS/'):
        merchant = desc[9:].split('/')[0].strip()
        return f"Card - {merchant.title()}"
    
    # ATM Withdrawal
    if desc.startswith('ATMWDL') or 'ATM' in desc.upper():
        return "ATM Charges"
    
    # NEFT
    if desc.startswith('NEFT'):
        parts = desc.split('-')
        if len(parts) >= 2:
            name = parts[-1].strip()
            return f"NEFT - {name.title()}"
        return "NEFT Transfer"
    
    # IMPS
    if desc.startswith('IMPS'):
        parts = desc.split('/')
        if len(parts) >= 2:
            name = parts[-1].strip()
            return f"IMPS - {name.title()}"
        return "IMPS Transfer"
    
    # IPAY/ESHP (E-Shop payment)
    if desc.startswith('IPAY/ESHP'):
        return "Online Payment"
    
    # ACH Payment
    if desc.startswith('ACH') or 'achpfm' in lower_desc:
        parts = desc.split('-')
        if len(parts) >= 2:
            purpose = parts[1].strip()
            return f"ACH - {purpose.title()}"
        return "ACH Payment"
    
    # CA Keeping Charges
    if 'ca keeping' in lower_desc or 'keeping chgs' in lower_desc:
        return "Account Maintenance Charges"
    
    # Cash deposit/withdrawal at branch
    if desc.startswith('BN') or desc.startswith('ID064') or desc.startswith('ID130'):
        return "Branch Transaction"
    
    # REF (Refund)
    if desc.startswith('REF\\') or desc.startswith('REF/'):
        return "Refund"
    
    # Interest
    if 'interest' in lower_desc or 'int.' in lower_desc:
        return "Interest Credit"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def clean_canara_description(raw_desc: str) -> str:
    """Clean up Canara Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    lower_desc = desc.lower()
    
    # Cash BNA (Cash Deposit via machine)
    if 'cash-bna' in lower_desc or 'cash bna' in lower_desc:
        return "Cash Deposit (BNA)"
    
    # Cheque Book Issue
    if 'chq bk issue' in lower_desc:
        return "Cheque Book Issue Charges"
    
    # RTGS Credit
    if desc.startswith('RTGS Cr'):
        parts = desc.split('-')
        for part in parts:
            if len(part) > 5 and part.isupper() and ' ' in part:
                return f"RTGS - {part.title()}"
        return "RTGS Inward"
    
    # NEFT Credit
    if desc.startswith('NEFT Cr'):
        parts = desc.split('-')
        for part in parts:
            if len(part) > 5 and any(c.isalpha() for c in part) and not part.startswith('ICIC') and not part.startswith('HDFC'):
                clean_part = part.strip()
                if clean_part and not clean_part.startswith('N0'):
                    return f"NEFT - {clean_part.title()}"
        return "NEFT Inward"
    
    # Funds Transfer Debit
    if 'funds transfer debit' in lower_desc:
        parts = desc.split('-')
        if len(parts) >= 2:
            name = parts[-1].strip()
            return f"Transfer - {name.title()}"
        return "Funds Transfer"
    
    # Self transfer
    if desc.lower().startswith('self'):
        parts = desc.split('-')
        if len(parts) >= 2:
            name = parts[0].replace('self', '').strip()
            if name:
                return f"Self - {name.title()}"
        return "Self Transfer"
    
    # Cheque Return
    if 'chq return' in lower_desc or 'i/w chq return' in lower_desc:
        return "Cheque Return"
    
    # Cheque Return Charges
    if 'chq rtn chg' in lower_desc:
        return "Cheque Return Charges"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def clean_union_description(raw_desc: str) -> str:
    """Clean up Union Bank transaction description.
    Union Bank UPI format:
      UPIAR/ref/DR/PayeeName/BankCode[/upiid] — Debit
      UPIAB/ref/CR/PayeeName/BankCode[/upiid] — Credit
      NEFT/ref/CR_or_DR/PayeeName/BankCode[/purpose]
    """
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    if not desc:
        return "Bank Transaction"

    upper = desc.upper()

    # ── UPI Debit (UPIAR) or Credit (UPIAB) ─────────────────────────────
    if upper.startswith('UPIAR/') or upper.startswith('UPIAB/'):
        return _clean_union_upi(desc)

    # ── NEFT ─────────────────────────────────────────────────────────────
    if upper.startswith('NEFT/') or upper.startswith('NEFT:'):
        return _clean_union_neft(desc)

    # ── Interest ─────────────────────────────────────────────────────────
    if 'INT.PD' in upper or ':INT.' in upper or 'INTEREST' in upper:
        return "Interest Credit"

    # ── SMS Charges ──────────────────────────────────────────────────────
    if 'SMS CHARGES' in upper or 'SMS CHG' in upper:
        return "Bank Charges - SMS"

    # ── General Charges ──────────────────────────────────────────────────
    if 'GENERAL CHARGES' in upper or 'SERVICE CHARGE' in upper:
        return "Service Charges"

    # ── MAND DR (Mandate Debit / Auto-debit) ─────────────────────────────
    if 'MAND DR' in upper or 'MANDATE' in upper:
        return "Auto-debit"

    # ── POS (Card purchase) ──────────────────────────────────────────────
    if upper.startswith('POS:') or upper.startswith('POS/'):
        merchant = desc[4:].split('/')[0].strip()
        return f"Card - {merchant.title()}" if merchant else "Card Purchase"

    # ── ATM ──────────────────────────────────────────────────────────────
    if 'ATM' in upper:
        return "ATM Withdrawal"

    # ── IMPS / MOBFT ─────────────────────────────────────────────────────
    if upper.startswith('MOBFT') or upper.startswith('IMPS'):
        parts = desc.split('/')
        for part in parts[1:]:
            part = part.strip()
            if part and len(part) > 2 and any(c.isalpha() for c in part):
                return f"IMPS - {part.title()}"
        return "IMPS Transfer"

    return desc[:60] if len(desc) > 60 else desc


# Union Bank merchant mapping from UPI IDs
_UNION_UPI_MERCHANTS = {
    'billdesk.elect': 'Bill - Electricity',
    'billdesk.recha': 'Bill - Recharge',
    'billdesk.insur': 'Bill - Insurance',
    'billdesk.broad': 'Bill - Broadband',
    'billdesk': 'BillDesk Payment',
    'paytm-': 'Paytm',
    'phonepe': 'PhonePe',
    'bharatpe': 'BharatPe',
    'euronetgpay': 'Euronet GPay',
    'resident.uidai': 'Aadhaar Payment',
    'amazonpay': 'Amazon Pay',
    'gpay': 'Google Pay',
    '@ybl': None,  # skip bank codes
    '@oki': None,
    '@okhdf': None,
}


def _clean_union_upi(desc: str) -> str:
    """Extract payee from Union Bank UPI narration."""
    parts = desc.split('/')

    # Find DR or CR to locate payee
    payee = None
    upi_id = None
    for i, part in enumerate(parts):
        p = part.strip().upper()
        if p in ('DR', 'CR'):
            if i + 1 < len(parts):
                payee = parts[i + 1].strip()
            if i + 3 < len(parts):
                upi_id = parts[i + 3].strip()
            elif i + 2 < len(parts):
                # Sometimes bank code is merged, check next part
                next_part = parts[i + 2].strip() if i + 2 < len(parts) else ''
                if not next_part.isalpha() or len(next_part) > 5:
                    upi_id = next_part
            break

    if not payee:
        return "UPI Transfer"

    # Check for Aadhaar/DUMMY NAME transactions
    if payee.upper().startswith('DUMMY'):
        return "UPI - Aadhaar Transfer"

    # Check UPI ID for known merchants
    if upi_id:
        upi_lower = upi_id.lower()
        for key, merchant in _UNION_UPI_MERCHANTS.items():
            if key in upi_lower and merchant:
                return f"UPI - {merchant}"

    # Check payee name for known merchants
    payee_lower = payee.lower().replace(' ', '')
    if payee_lower.startswith('billdesk'):
        # Try UPI ID for specific bill type
        if upi_id and 'elect' in upi_id.lower():
            return "UPI - Bill (Electricity)"
        if upi_id and 'recha' in upi_id.lower():
            return "UPI - Bill (Recharge)"
        return "UPI - BillDesk Payment"

    if payee_lower.startswith('euronetg'):
        return "UPI - Euronet GPay"

    if payee_lower.startswith('protean'):
        # Protean is NPCI services, check UPI ID for actual merchant
        if upi_id and 'paytm' in upi_id.lower():
            return "UPI - Paytm"
        return "UPI - Protean"

    # Clean payee name
    # Remove "Mr " / "Mrs " prefix
    clean_name = re.sub(r'^(?:Mr|Mrs|Ms|Dr)\s+', '', payee, flags=re.IGNORECASE).strip()

    # Remove trailing single character (truncation artifact)
    clean_name = re.sub(r'\s+[A-Za-z]$', '', clean_name).strip()

    # Remove trailing digits from UPI handles used as names
    clean_name = re.sub(r'\d+$', '', clean_name).strip()

    if not clean_name:
        clean_name = payee

    return f"UPI - {clean_name.title()}"


def _clean_union_neft(desc: str) -> str:
    """Extract payee from Union Bank NEFT narration.
    Format: NEFT/ref/CR_or_DR/PayeeName/BankCode[/purpose]
    """
    parts = desc.split('/')
    payee = None
    purpose = None

    for i, part in enumerate(parts):
        p = part.strip().upper()
        if p in ('CR', 'DR'):
            if i + 1 < len(parts):
                payee = parts[i + 1].strip()
            # Check for purpose (like "Salary")
            if i + 3 < len(parts):
                purpose = parts[i + 3].strip()
            elif i + 2 < len(parts):
                maybe_purpose = parts[i + 2].strip()
                if maybe_purpose and not maybe_purpose.isdigit() and len(maybe_purpose) > 4:
                    purpose = maybe_purpose
            break

    # Detect salary
    if purpose and 'salary' in purpose.lower():
        return "Salary Credit"
    if payee and 'salary' in payee.lower():
        return "Salary Credit"

    if payee and len(payee) > 2:
        return f"NEFT - {payee.title()}"

    return "NEFT Transfer"


def clean_kotak_description(raw_desc: str) -> str:
    """Clean up Kotak Bank transaction description."""
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    
    lower_desc = desc.lower()
    
    # Known merchants
    known_merchants = {
        'paytm': 'Paytm',
        'phonepe': 'PhonePe',
        'bajaj finance': 'Bajaj Finance',
        'ullu digital': 'Ullu',
        'cashfree': 'Cashfree',
        'razorecom': 'Razorpay',
    }
    
    # Check for known merchants
    for key, name in known_merchants.items():
        if key in lower_desc:
            return f"UPI - {name}"
    
    # UPI format: UPI/Name/refno/Purpose
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        if len(parts) >= 2:
            name = parts[1].strip()
            if name and any(c.isalpha() for c in name):
                return f"UPI - {name.title()}"
        return "UPI Transfer"
    
    # IMPS
    if desc.startswith('IMPS-') or desc.startswith('Recd:IMPS'):
        parts = desc.replace('Recd:IMPS/', '').replace('IMPS-', '').split('/')
        if parts:
            name = parts[0].strip()
            if name and any(c.isalpha() for c in name):
                return f"IMPS - {name.title()}"
        return "IMPS Transfer"
    
    # NEFT
    if 'NEFT' in desc.upper():
        parts = desc.split(' ')
        for part in parts:
            if len(part) > 5 and part.isupper() and part not in ('NEFT', 'NEFTINW'):
                return f"NEFT - {part.title()}"
        return "NEFT Transfer"
    
    # Own Transfer
    if 'own transfer' in lower_desc:
        return "Own Account Transfer"
    
    # Cash Deposit
    if 'cash deposit' in lower_desc:
        return "Cash Deposit"
    
    # OS (Online Services / Payment Gateway)
    if desc.startswith('OS '):
        merchant = desc[3:].split(' ')[0]
        return f"Payment - {merchant.title()}"
    
    # Chrg / Charges
    if desc.startswith('Chrg:') or desc.startswith('Rem Chrgs:'):
        return "Bank Charges"
    
    # Return first 50 chars
    return desc[:50] if len(desc) > 50 else desc


def parse_kotak_pdf(pdf, all_text: str) -> list:
    """
    Parse Kotak Bank PDF statement.
    Supports two formats:
    - Format 1 (Text-based): Date | Narration | Chq/Ref No | Amount(Dr/Cr) | Balance
    - Format 2 (Table-based): # | TRANSACTION | DETAILS | REF | DEBIT | CREDIT | BALANCE
    """
    transactions = []
    
    # Try table-based parsing first (Format 2)
    table_txns = parse_kotak_table_format(pdf)
    if table_txns:
        return table_txns
    
    # Fall back to text-based parsing (Format 1)
    return parse_kotak_text_format(pdf, all_text)


def parse_kotak_table_format(pdf) -> list:
    """Parse Kotak Format 2 (table-based)."""
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Check if this is a transaction table
            first_row = [str(c).lower() if c else "" for c in table[0]]
            if 'transaction' not in ' '.join(first_row):
                continue
            
            for row in table[1:]:
                if not row or len(row) < 6:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header rows
                if cleaned[0] == '#' or not cleaned[0]:
                    continue
                
                # Parse date (column 1 - "DD Mon YYYY HH:MM AM/PM")
                date_str = cleaned[1].split(' ')[0:3]  # Get "DD Mon YYYY"
                date_str = ' '.join(date_str)
                date = parse_date(date_str)
                if not date:
                    continue
                
                # Get description (column 2)
                description = cleaned[2] if len(cleaned) > 2 else ""
                if not description:
                    continue
                
                # Get debit and credit (columns 4 and 5)
                debit_str = cleaned[4] if len(cleaned) > 4 else ""
                credit_str = cleaned[5] if len(cleaned) > 5 else ""
                
                # Kotak uses - prefix for debit and + prefix for credit
                bank_debit = parse_amount(debit_str.replace('-', '').replace('+', ''))
                bank_credit = parse_amount(credit_str.replace('-', '').replace('+', ''))
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_kotak_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_kotak_text_format(pdf, all_text: str) -> list:
    """Parse Kotak text-based formats (both Format 1 and Format 2)."""
    transactions = []
    
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Format 1: Line starts with date DD-MM-YYYY
            if re.match(r'^\d{2}-\d{2}-\d{4}', line):
                date_str = line[:10]
                date = parse_date(date_str)
                
                if date:
                    # Combine multi-line entries
                    full_line = line
                    j = i + 1
                    while j < len(lines) and j < i + 5:
                        next_line = lines[j].strip()
                        if re.match(r'^\d{2}-\d{2}-\d{4}', next_line):
                            break
                        if '(Dr)' in next_line or '(Cr)' in next_line:
                            full_line += ' ' + next_line
                            break
                        full_line += ' ' + next_line
                        j += 1
                    
                    # Extract amount with Dr/Cr
                    amount_match = re.search(r'([\d,]+\.?\d*)\s*\((Dr|Cr)\)', full_line)
                    if amount_match:
                        amount = parse_amount(amount_match.group(1))
                        is_credit = amount_match.group(2) == 'Cr'
                        
                        desc_end = full_line.find(amount_match.group(0))
                        description = full_line[10:desc_end].strip()
                        
                        if amount > 0:
                            transactions.append({
                                'date': date,
                                'description': clean_kotak_description(description),
                                'bank_debit': 0 if is_credit else amount,
                                'bank_credit': amount if is_credit else 0,
                            })
            
            # Format 2: Line starts with serial number then DD Mon YYYY
            elif re.match(r'^\d+\s+\d{2}\s+\w{3}\s+\d{4}', line):
                parts = line.split()
                if len(parts) >= 5:
                    # Date is parts[1:4]
                    date_str = ' '.join(parts[1:4])
                    date = parse_date(date_str)
                    
                    if date:
                        # Find amounts with +/- prefix AND decimal point (to avoid matching ref numbers)
                        # Pattern: +/-number,number.decimal
                        amount_matches = re.findall(r'([+-][\d,]+\.\d{2})\b', line)
                        
                        if amount_matches:
                            # The transaction amount is the one with +/- prefix
                            for amt_str in amount_matches:
                                is_credit = amt_str.startswith('+')
                                amount = parse_amount(amt_str.replace('+', '').replace('-', ''))
                                
                                if amount > 0:
                                    # Get description - between date and first amount
                                    desc_start = line.find(parts[3]) + len(parts[3]) + 1
                                    desc_end = line.find(amt_str)
                                    if desc_end > desc_start:
                                        description = line[desc_start:desc_end].strip()
                                        # Remove reference numbers
                                        description = re.sub(r'\b[A-Z]{2,}-?\d+\b', '', description).strip()
                                        description = re.sub(r'\s+', ' ', description)
                                    else:
                                        description = line[desc_start:].strip()
                                    
                                    transactions.append({
                                        'date': date,
                                        'description': clean_kotak_description(description),
                                        'bank_debit': 0 if is_credit else amount,
                                        'bank_credit': amount if is_credit else 0,
                                    })
                                    break  # Only take first amount per line
            
            i += 1
    
    return transactions



def clean_bob_description(raw_desc: str) -> str:
    """Clean up Bank of Baroda transaction description."""
    desc = raw_desc
    
    # Extract payee from UPI strings
    # Format: UPI/P2A/318262797206/JIVRAYEL /Punjab Na/UPI
    upi_match = re.search(r'UPI/P2[AM]/\d+/([^/]+)', desc)
    if upi_match:
        payee = upi_match.group(1).strip()
        if payee:
            return f"UPI - {payee}"
    
    # Extract from NEFT
    # Format: NEFT/N185232529725945/JOINMAY M/HDFC BANK/NEFT
    neft_match = re.search(r'NEFT/[A-Z0-9]+/([^/]+)', desc)
    if neft_match:
        payee = neft_match.group(1).strip()
        if payee:
            return f"NEFT - {payee}"
    
    # Extract from ACH-DR
    # Format: ACH-DR-TPCapfrst IDFC FIRST-1177262059-UTIB702160
    if 'ACH-DR' in desc:
        ach_match = re.search(r'ACH-DR-([A-Za-z]+)', desc)
        if ach_match:
            return f"ACH Debit - {ach_match.group(1)}"
    
    # Extract from ECS
    # Format: ECS/UTIBDE65064150202305/Bajaj Finance Ltd_SMS OT
    ecs_match = re.search(r'ECS/[A-Z0-9]+/([^/]+)', desc)
    if ecs_match:
        return f"ECS - {ecs_match.group(1).strip()}"
    
    # Interest
    if 'Int.Pd' in desc:
        return "Interest Paid"
    
    # GST
    if 'GST' in desc:
        return desc.strip()
    
    # Consolidated Charges
    if 'Consolidated Charges' in desc:
        return "Bank Charges"
    
    # Clean up whitespace
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc[:100] if len(desc) > 100 else desc


def parse_bob_pdf(pdf, all_text: str) -> list:
    """
    Parse Bank of Baroda PDF statement.
    
    Format:
    - Headers: Txn Date | Transaction | Withdrawals | Deposits | Balance | Other
    - Date format: DD-MM-YYYY
    - Amounts with commas, separate columns for withdrawals and deposits
    
    Uses text-based parsing as primary method for better reliability.
    """
    transactions = []
    
    # First try text-based parsing (more reliable for BOB)
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Match lines starting with date DD-MM-YYYY
            date_match = re.match(r'^(\d{2}-\d{2}-\d{4})\s+(.+)', line)
            if not date_match:
                continue
            
            date = parse_date(date_match.group(1))
            if not date:
                continue
            
            rest = date_match.group(2)
            
            # Skip opening/closing balance lines
            if 'Opening Balance' in rest or 'Closing Balance' in rest:
                continue
            
            # Find all amounts in the line (pattern: digits with optional commas and decimal)
            amount_pattern = r'([\d,]+\.\d{2})'
            amounts = re.findall(amount_pattern, rest)
            
            if len(amounts) < 2:
                continue
            
            # Get description (everything before the first amount)
            desc_end = rest.find(amounts[0])
            description = rest[:desc_end].strip()
            
            if not description:
                continue
            
            # The first amount is the transaction amount, last is usually balance
            transaction_amount = parse_amount(amounts[0])
            
            if transaction_amount <= 0:
                continue
            
            # Determine if this is a credit or debit based on description keywords
            desc_lower = description.lower()
            
            # Credit indicators (money coming IN)
            is_credit = any([
                'upi/p2a/' in desc_lower,  # UPI Pay to Account = receiving money
                'nrp' in desc_lower,       # NRP = incoming transfer
                'neft/' in desc_lower and 'neft -' not in desc_lower,  # NEFT incoming
                'imps/' in desc_lower and 'sent' not in desc_lower,    # IMPS incoming
                'int.pd' in desc_lower,    # Interest paid
                'deposit' in desc_lower,
                'credit' in desc_lower,
                'refund' in desc_lower,
            ])
            
            # Debit indicators (money going OUT)
            is_debit = any([
                'upi/p2m/' in desc_lower,  # UPI Pay to Merchant = payment
                'ach-dr' in desc_lower,    # ACH Debit
                'ecs/' in desc_lower,      # ECS = Electronic Clearing (EMI/auto-debit)
                'gst' in desc_lower,       # GST charges
                'charge' in desc_lower,    # Bank charges
                'withdrawal' in desc_lower,
                'transfer' in desc_lower and 'received' not in desc_lower,
            ])
            
            # If both or neither, use balance comparison if available
            if is_credit and not is_debit:
                withdrawal = 0
                deposit = transaction_amount
            elif is_debit or not is_credit:
                withdrawal = transaction_amount
                deposit = 0
            else:
                # Default to withdrawal (most common case for expense tracking)
                withdrawal = transaction_amount
                deposit = 0
            
            transactions.append({
                'date': date,
                'description': clean_bob_description(description),
                'bank_debit': withdrawal,
                'bank_credit': deposit,
            })
    
    return transactions


def parse_union_pdf(pdf, all_text: str) -> list:
    """
    Parse Union Bank PDF statement.
    Supports both formats:
    - Old format: S.No | Date | Transaction Id | Remarks | Amount(Rs.) | Balance(Rs.)
    - New format: Tran Id | Tran Date | Remarks | Amount (Rs.) | Balance (Rs.)
    
    Amount has (Dr) or (Cr) suffix for debit/credit.
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or len(row) < 4:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header rows and empty rows
                first_col = cleaned[0].lower()
                if 'tran' in first_col or 's.no' in first_col or not cleaned[0]:
                    continue
                if 'scan' in first_col or 'account' in first_col or 'closing' in first_col:
                    continue
                
                # Detect format based on row structure
                # Old format: S.No (number) | Date | Tran Id | Remarks | Amount | Balance
                # New format: Tran Id (alphanumeric) | Date | Remarks | Amount | Balance
                
                date_col = 1  # Default for old format
                remarks_col = 3  # Default for old format
                amount_col = 4  # Default for old format
                
                # Check if first column is a serial number (old format) or transaction ID (new format)
                if cleaned[0].isdigit() and len(cleaned[0]) <= 4:
                    # Old format with S.No
                    date_col = 1
                    remarks_col = 3
                    amount_col = 4
                elif cleaned[0].startswith('S') and len(cleaned[0]) > 4:
                    # New format with Transaction ID
                    date_col = 1
                    remarks_col = 2
                    amount_col = 3
                else:
                    continue
                
                # Parse date
                date = parse_date(cleaned[date_col])
                if not date:
                    continue
                
                # Get description
                description = cleaned[remarks_col] if len(cleaned) > remarks_col else ""
                if not description:
                    continue
                
                # Get amount with Dr/Cr indicator
                amount_str = cleaned[amount_col] if len(cleaned) > amount_col else ""
                if not amount_str:
                    continue
                
                # Parse amount and determine debit/credit
                is_credit = '(cr)' in amount_str.lower()
                is_debit = '(dr)' in amount_str.lower()
                
                # Remove the Dr/Cr indicator before parsing
                amount_clean = amount_str.replace('(Dr)', '').replace('(Cr)', '').replace('(dr)', '').replace('(cr)', '').strip()
                amount = parse_amount(amount_clean)
                
                if amount == 0:
                    continue
                
                if is_credit:
                    bank_credit = amount
                    bank_debit = 0
                else:
                    bank_debit = amount
                    bank_credit = 0
                
                transactions.append({
                    'date': date,
                    'description': clean_union_description(description),
                    'raw_description': description,
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    # Phase 2: Enrich descriptions from text-based continuation lines
    # Union Bank's text has continuation data (like /Salary) after transaction lines
    _enrich_union_descriptions(transactions, all_text)
    
    return transactions


def _enrich_union_descriptions(transactions: list, all_text: str) -> None:
    """Enrich Union Bank transaction descriptions using full text continuation lines."""
    lines = all_text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        # Check for continuation that indicates salary
        if line.startswith('/Salary') or line == 'Salary':
            # Find the transaction that precedes this line
            for txn in reversed(transactions):
                raw = txn.get('raw_description', '')
                if raw.startswith('NEFT') or 'NEFT' in raw:
                    if txn['bank_credit'] > 0:
                        txn['description'] = 'Salary Credit'
                    break


def parse_canara_pdf(pdf, all_text: str) -> list:
    """
    Parse Canara Bank PDF statement.
    Canara format: Txn Date | Value Date | Cheque No. | Description | Branch Code | Debit | Credit | Balance
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Check if this is a transaction table
            first_row = [str(c).lower() if c else "" for c in table[0]]
            is_txn_table = 'txn date' in first_row[0] or 'date' in first_row[0]
            
            start_idx = 1 if is_txn_table else 0
            
            for row in table[start_idx:]:
                if not row or len(row) < 7:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header and page rows
                first_col = cleaned[0].lower()
                if 'txn date' in first_col or 'page' in first_col or not cleaned[0]:
                    continue
                
                # Parse date (DD-MM-YYYY HH:MM:SS format)
                date_str = cleaned[0].split(' ')[0] if ' ' in cleaned[0] else cleaned[0]
                date = parse_date(date_str)
                if not date:
                    continue
                
                # Get description (column 3)
                description = cleaned[3] if len(cleaned) > 3 else ""
                if not description:
                    continue
                
                # Get debit and credit (columns 5 and 6)
                bank_debit = parse_amount(cleaned[5]) if len(cleaned) > 5 else 0
                bank_credit = parse_amount(cleaned[6]) if len(cleaned) > 6 else 0
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_canara_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_idbi_pdf(pdf, all_text: str) -> list:
    """
    Parse IDBI Bank PDF statement.
    IDBI format: Srl | Txn Date | Value Date | Description | Cheque No | CR/DR | CCY | Amount (INR) | Balance (INR)
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or len(row) < 7:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip header rows
                first_col = cleaned[0].lower()
                if 'srl' in first_col or 'txn' in first_col or not cleaned[0]:
                    continue
                
                # Skip if first column is not a serial number
                if not cleaned[0].isdigit():
                    continue
                
                # Parse date (column 1 - Txn Date with timestamp)
                date_str = cleaned[1].split(' ')[0] if ' ' in cleaned[1] else cleaned[1]
                date = parse_date(date_str)
                if not date:
                    continue
                
                # Get description (column 3)
                description = cleaned[3] if len(cleaned) > 3 else ""
                if not description:
                    continue
                
                # Get CR/DR indicator (column 5)
                cr_dr = cleaned[5].lower() if len(cleaned) > 5 else ""
                
                # Get amount (column 7)
                amount = parse_amount(cleaned[7]) if len(cleaned) > 7 else 0
                
                if amount == 0:
                    continue
                
                # Determine debit or credit
                if 'cr' in cr_dr:
                    bank_credit = amount
                    bank_debit = 0
                else:
                    bank_debit = amount
                    bank_credit = 0
                
                transactions.append({
                    'date': date,
                    'description': clean_idbi_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_pnb_pdf(pdf, all_text: str) -> list:
    """
    Parse PNB Bank PDF statement.
    PNB format: Date | Withdrawal | Deposit | Balance | Alpha | CHQ. NO. | Narration
    """
    transactions = []
    
    for page in pdf.pages:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            # Check if this is a transaction table (has Date header)
            first_row = [str(c).lower() if c else "" for c in table[0]]
            if 'date' not in first_row[0]:
                continue
            
            for row in table[1:]:  # Skip header
                if not row or len(row) < 6:
                    continue
                
                # Clean the row
                cleaned = [str(cell).replace('\n', ' ').replace('  ', ' ').strip() if cell else "" for cell in row]
                
                # Skip empty rows and page totals
                first_col = cleaned[0].lower()
                if not cleaned[0] or 'page' in first_col or 'grand' in first_col:
                    continue
                
                # Parse date (DD-MM-YYYY format)
                date = parse_date(cleaned[0])
                if not date:
                    continue
                
                # Get withdrawal and deposit (columns 1 and 2)
                bank_debit = parse_amount(cleaned[1]) if len(cleaned) > 1 else 0
                bank_credit = parse_amount(cleaned[2]) if len(cleaned) > 2 else 0
                
                # Get description (last column - Narration)
                description = cleaned[6] if len(cleaned) > 6 else cleaned[-1]
                if not description:
                    description = "Bank Transaction"
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_pnb_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_hdfc_pdf(pdf, all_text: str) -> list:
    """
    Parse HDFC Bank PDF statement using text extraction.
    HDFC format: Date | Narration | Chq./Ref.No. | ValueDt | WithdrawalAmt. | DepositAmt. | ClosingBalance
    
    Multi-line narrations: HDFC wraps long narrations across 2-3 lines.
    We collect continuation lines and join them with the transaction line.
    """
    transactions = []
    prev_balance = None

    # Collect all lines across all pages, tagging with page boundaries
    all_lines = []
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        for line in text.split('\n'):
            stripped = line.strip()
            if stripped:
                all_lines.append(stripped)

    # Skip header/footer noise patterns
    _SKIP = re.compile(
        r'^(PageNo|Statement|Date\s+Narration|From\s*:|To\s*:|Account|HDFC\s*BANK|'
        r'Opening\s+Balance|Closing\s+Balance|\*\*\*|\*Closing|JOINT|Nomination|'
        r'This is a computer|Contents of this|The details|Generated|'
        r'Customer|RTGS|MICR|Branch|Email|City|State|Currency|'
        r'ODLimit|A/C\s*Open|AccountNo|AccountStatus|AccountType|'
        r'CustID|PhoneNo|Address|HDFCBANKLIMITED|RegisteredOffice|'
        r'StateaccountbranchGSTN|HDFCBankGSTIN|Contentsofthis)', re.IGNORECASE)

    DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{2,4}\s')
    AMOUNT_RE = re.compile(r'([\d,]+\.\d{2})')

    # First pass: group lines into transactions (date line + continuation lines)
    txn_groups = []
    i = 0
    while i < len(all_lines):
        line = all_lines[i]

        if DATE_RE.match(line) and not _SKIP.match(line):
            group = [line]
            j = i + 1
            # Collect continuation lines (non-date, non-header)
            while j < len(all_lines):
                next_line = all_lines[j]
                if DATE_RE.match(next_line):
                    break
                if _SKIP.match(next_line):
                    j += 1
                    continue
                # A continuation line shouldn't contain amounts in the HDFC balance pattern
                # unless it's very short (part of narration)
                amounts_in_next = AMOUNT_RE.findall(next_line)
                # If next line is purely amounts/numbers (like a wrapped balance), skip
                cleaned_next = AMOUNT_RE.sub('', next_line).strip()
                if not cleaned_next and amounts_in_next:
                    j += 1
                    continue
                group.append(next_line)
                j += 1
            txn_groups.append(group)
            i = j
        else:
            i += 1

    # Second pass: parse each transaction group
    for group in txn_groups:
        first_line = group[0]
        continuation = ' '.join(group[1:]) if len(group) > 1 else ''

        # Extract date
        date_str = first_line[:8]
        date = parse_date(date_str)
        if not date:
            continue

        # Extract amounts from the first line only
        amounts = AMOUNT_RE.findall(first_line)
        if len(amounts) < 2:
            continue

        # Last amount is closing balance
        balance = parse_amount(amounts[-1])

        # Extract reference number (long digit sequence, typically 10-20 digits)
        ref_matches = re.findall(r'\b(\d{10,20})\b', first_line)
        ref_number = ref_matches[0] if ref_matches else ''

        # Determine debit/credit by balance change
        bank_debit = 0.0
        bank_credit = 0.0

        if len(amounts) >= 3:
            amt1 = parse_amount(amounts[-3])
            amt2 = parse_amount(amounts[-2])

            if amt1 > 0 and amt2 > 0:
                if prev_balance is not None:
                    change = balance - prev_balance
                    if abs(change) > 0.005:
                        if change > 0:
                            bank_credit = abs(change)
                        else:
                            bank_debit = abs(change)
                    else:
                        bank_debit = amt2
                else:
                    bank_debit = amt2
            elif amt1 > 0:
                bank_debit = amt1
            else:
                bank_debit = amt2
        else:
            amount = parse_amount(amounts[-2])
            if prev_balance is not None:
                change = balance - prev_balance
                if change > 0:
                    bank_credit = amount
                else:
                    bank_debit = amount
            else:
                desc_upper = (first_line + ' ' + continuation).upper()
                if any(kw in desc_upper for kw in ['DEP', 'CREDIT', 'INTEREST', 'CASHDEP', 'REV-']):
                    bank_credit = amount
                else:
                    bank_debit = amount

        # Extract description: between date and value date on first line + continuation
        rest = first_line[9:].strip()
        value_date_match = re.search(r'\d{2}/\d{2}/\d{2}', rest)
        if value_date_match:
            desc_from_line = rest[:value_date_match.start()].strip()
        else:
            desc_from_line = rest[:60]

        # Remove the ref number from description (it's noise for readability)
        if ref_number and ref_number in desc_from_line:
            desc_from_line = desc_from_line.replace(ref_number, '').strip()

        # Build full narration by joining with continuation
        full_narration = desc_from_line
        if continuation:
            full_narration = desc_from_line + ' ' + continuation
        # Clean up extra spaces
        full_narration = re.sub(r'\s+', ' ', full_narration).strip()

        if bank_debit > 0 or bank_credit > 0:
            transactions.append({
                'date': date,
                'description': clean_hdfc_description(full_narration, ref_number),
                'raw_description': full_narration[:120],
                'ref_number': ref_number,
                'bank_debit': bank_debit,
                'bank_credit': bank_credit,
            })

        prev_balance = balance

    return transactions


def parse_sbi_pdf(pdf, all_text: str) -> list:
    """
    Parse SBI Bank PDF statement.
    SBI format: Uses table extraction with columns:
    Txn Date | Value Date | Description | Ref/Cheque | Debit | Credit | Balance
    """
    transactions = []
    
    # SBI uses table extraction
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row or len(row) < 6:
                    continue
                
                # Clean the row
                cleaned = [str(cell).strip().replace('\n', ' ') if cell else "" for cell in row]
                
                # Skip header rows
                if any(h in cleaned[0].lower() for h in ['date', 'txn', 'balance', '']):
                    if 'balance' in ' '.join(cleaned).lower():
                        continue
                
                # Try to parse date from first column
                date = parse_date(cleaned[0])
                if not date:
                    continue
                
                # Get description (usually 3rd column)
                description = cleaned[2] if len(cleaned) > 2 else ""
                if not description:
                    continue
                
                # Get debit and credit (columns 4 and 5 typically)
                # SBI format: col 4 = debit, col 5 = credit (or col 3 = debit, col 4 = credit)
                debit_col = 4 if len(cleaned) > 5 else 3
                credit_col = 5 if len(cleaned) > 5 else 4
                
                bank_debit = parse_amount(cleaned[debit_col]) if len(cleaned) > debit_col else 0
                bank_credit = parse_amount(cleaned[credit_col]) if len(cleaned) > credit_col else 0
                
                if bank_debit == 0 and bank_credit == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': clean_sbi_description(description),
                    'bank_debit': bank_debit,
                    'bank_credit': bank_credit,
                })
    
    return transactions


def parse_pdf_statement(file_bytes: bytes, password: str = None, bank_hint: str = "") -> list:
    """
    Parse a PDF bank statement using pdfplumber.
    Supports password-protected PDFs.
    
    Args:
        file_bytes: PDF file content
        password: Optional password for encrypted PDFs
        bank_hint: User-provided bank name hint for parser selection
    """
    import pdfplumber
    transactions = []
    
    # Try to open PDF, with or without password
    try:
        if password:
            pdf = pdfplumber.open(io.BytesIO(file_bytes), password=password)
        else:
            pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as e:
        error_str = str(e).lower()
        error_type = type(e).__name__
        
        # Check for password-protected PDF
        if 'password' in error_str or 'encrypted' in error_str or 'pdfminer' in error_type.lower():
            if not password:
                raise ValueError("This PDF is password-protected. Please provide the password in the 'PDF Password' field.")
            else:
                raise ValueError("Incorrect PDF password. Please check and try again.")
        raise ValueError(f"Could not open PDF: {str(e) or 'Unknown error'}")
    
    with pdf:
        # Extract all text for bank detection
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"
        
        # Detect bank
        bank = detect_bank(bank_hint, all_text)
        logger.info(f"Detected bank: {bank}")
        
        # Use bank-specific parser
        if bank == "sbi":
            transactions = parse_sbi_pdf(pdf, all_text)
            if transactions:
                logger.info(f"Parsed {len(transactions)} transactions using SBI parser")
                return transactions
        
        elif bank == "icici":
            icici_txns = parse_icici_pdf_text(all_text)
            if icici_txns:
                logger.info(f"Parsed {len(icici_txns)} transactions using ICICI parser")
                return icici_txns
        
        elif bank == "axis":
            axis_txns = parse_axis_pdf(pdf, all_text)
            if axis_txns:
                logger.info(f"Parsed {len(axis_txns)} transactions using Axis parser")
                return axis_txns
        
        elif bank == "indusind":
            indusind_txns = parse_indusind_pdf(pdf, all_text)
            if indusind_txns:
                logger.info(f"Parsed {len(indusind_txns)} transactions using IndusInd parser")
                return indusind_txns
        
        elif bank == "yes":
            yes_txns = parse_yesbank_pdf(pdf, all_text)
            if yes_txns:
                logger.info(f"Parsed {len(yes_txns)} transactions using Yes Bank parser")
                return yes_txns
        
        elif bank == "hdfc":
            hdfc_txns = parse_hdfc_pdf(pdf, all_text)
            if hdfc_txns:
                logger.info(f"Parsed {len(hdfc_txns)} transactions using HDFC parser")
                return hdfc_txns
        
        elif bank == "pnb":
            pnb_txns = parse_pnb_pdf(pdf, all_text)
            if pnb_txns:
                logger.info(f"Parsed {len(pnb_txns)} transactions using PNB parser")
                return pnb_txns
        
        elif bank == "idbi":
            idbi_txns = parse_idbi_pdf(pdf, all_text)
            if idbi_txns:
                logger.info(f"Parsed {len(idbi_txns)} transactions using IDBI parser")
                return idbi_txns
        
        elif bank == "canara":
            canara_txns = parse_canara_pdf(pdf, all_text)
            if canara_txns:
                logger.info(f"Parsed {len(canara_txns)} transactions using Canara parser")
                return canara_txns
        
        elif bank == "union":
            union_txns = parse_union_pdf(pdf, all_text)
            if union_txns:
                logger.info(f"Parsed {len(union_txns)} transactions using Union Bank parser")
                return union_txns
        
        elif bank == "kotak":
            kotak_txns = parse_kotak_pdf(pdf, all_text)
            if kotak_txns:
                logger.info(f"Parsed {len(kotak_txns)} transactions using Kotak parser")
                return kotak_txns
        
        elif bank == "bob":
            bob_txns = parse_bob_pdf(pdf, all_text)
            if bob_txns:
                logger.info(f"Parsed {len(bob_txns)} transactions using Bank of Baroda parser")
                return bob_txns
        
        # Standard table-based parsing for other banks
        all_rows = []
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        cleaned = [str(cell).strip() if cell else "" for cell in row]
                        all_rows.append(cleaned)

        if not all_rows:
            # Try text extraction as fallback
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    for line in text.split("\n"):
                        parts = line.split()
                        if len(parts) >= 3:
                            all_rows.append(parts)

    if not all_rows:
        raise ValueError("Could not extract any data from the PDF. The file may be scanned/image-based.")

    header_idx = 0
    mapping = {}
    for i, row in enumerate(all_rows[:15]):
        test_mapping = detect_header_columns(row)
        if test_mapping["date"] >= 0 and (test_mapping["debit"] >= 0 or test_mapping["credit"] >= 0):
            header_idx = i
            mapping = test_mapping
            break

    if not mapping or mapping["date"] < 0:
        raise ValueError("Could not detect column headers in PDF. The statement format may not be supported.")

    for row in all_rows[header_idx + 1:]:
        if len(row) <= max(v for v in mapping.values() if v >= 0):
            continue

        date_str = row[mapping["date"]] if mapping["date"] >= 0 else ""
        date = parse_date(date_str)
        if not date:
            continue

        description = row[mapping["description"]].strip() if mapping["description"] >= 0 else ""
        if not description:
            continue

        bank_debit = parse_amount(row[mapping["debit"]]) if mapping["debit"] >= 0 else 0
        bank_credit = parse_amount(row[mapping["credit"]]) if mapping["credit"] >= 0 else 0

        if bank_debit == 0 and bank_credit == 0:
            continue

        transactions.append({
            "date": date,
            "description": description,
            "bank_debit": bank_debit,
            "bank_credit": bank_credit,
        })

    return transactions
