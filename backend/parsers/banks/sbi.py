"""
SBI Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


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


