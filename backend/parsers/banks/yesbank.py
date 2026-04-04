"""
Yes Bank Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


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
    """Clean up Canara Bank transaction description.
    Canara Bank patterns:
      RTGS Cr-<REF>-<BANKCODE>-<COMPANY>--/<PRIORITY>/
      RTGS Dr-<REF>-<BANKCODE>-<PAYEE>-/<PURPOSE>/
      NEFT Cr-<REF>-<BANKCODE>-<COMPANY>--/<PURPOSE>/
      Funds Transfer Debit - <NAME>
      self-<name> - <BRANCH>   or   self - <BRANCH>
      IB-IMPS-DR//<BANK>/**<LAST4>//<DATE> <TIME>
      IB ITG <ref> <acctno> Online Transaction <purpose>
      Chq Paid-MICR Inward Clearing-<PAYEE>-<BANK>-<BANK>
      I/W Chq return- Funds Insufficient- for payee -<PAYEE>--
      By Clg:<CLEARING_HOUSE>-<BANK>, <PAYEE>
    """
    import re
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    if not desc:
        return "Bank Transaction"

    upper = desc.upper()
    lower = desc.lower()

    # ── Cash BNA (Cash Deposit via machine) ──────────────────────────────
    if 'cash-bna' in lower or 'cash bna' in lower:
        return "Cash Deposit (BNA)"

    # ── Cash Deposit at branch ───────────────────────────────────────────
    if lower.startswith('cash deposit'):
        return "Cash Deposit"

    # ── Cheque Book Issue ────────────────────────────────────────────────
    if 'chq bk issue' in lower:
        return "Cheque Book Issue Charges"

    # ── RTGS Cr / RTGS Dr ────────────────────────────────────────────────
    # Format: RTGS Cr-<REF>-<IFSC>-<COMPANY_NAME>--/URGENT/
    if upper.startswith('RTGS CR') or upper.startswith('RTGS DR'):
        is_debit = upper.startswith('RTGS DR')
        # IFSC code pattern: 4 alpha + 0 + 6 alphanumeric (e.g., ICIC0000011, BARB0MOUNTR)
        ifsc_match = re.search(r'[A-Z]{4}0[A-Z0-9]{6}', upper)
        if ifsc_match:
            after_ifsc = desc[ifsc_match.end():]
            after_ifsc = re.sub(r'^[\s\-]+', '', after_ifsc)
            name = re.split(r'--+|/URGENT|/NONE|/\s*$', after_ifsc)[0].strip()
            name = name.rstrip('-/ ')
            if name and len(name) > 1 and any(c.isalpha() for c in name):
                label = "RTGS Out" if is_debit else "RTGS"
                return f"{label} - {name.title()}"
        return "RTGS Outward" if is_debit else "RTGS Inward"

    # ── RTGS Service Charges ─────────────────────────────────────────────
    if upper.startswith('RTGS') and ('SC' in upper or 'SERVICE' in upper or 'UPTO' in upper):
        return "RTGS Service Charges"

    # ── NEFT Cr ──────────────────────────────────────────────────────────
    # Format: NEFT Cr-<REF>-<IFSC>-<COMPANY>--/<PURPOSE>
    if upper.startswith('NEFT CR'):
        ifsc_match = re.search(r'[A-Z]{4}0[A-Z0-9]{6}', upper)
        if ifsc_match:
            after_ifsc = desc[ifsc_match.end():]
            after_ifsc = re.sub(r'^[\s\-]+', '', after_ifsc)
            name = re.split(r'--+|/NEFT|/\s*$', after_ifsc)[0].strip()
            name = name.rstrip('-/ ')
            if name and len(name) > 1 and any(c.isalpha() for c in name):
                return f"NEFT - {name.title()}"
        return "NEFT Inward"

    # ── Funds Transfer Debit ─────────────────────────────────────────────
    if 'funds transfer debit' in lower:
        parts = desc.split('-')
        if len(parts) >= 2:
            name = parts[-1].strip()
            if name:
                return f"Transfer - {name.title()}"
        return "Funds Transfer"

    # ── Self transfer ────────────────────────────────────────────────────
    # Format: self-<name> - <BRANCH>  or  self - <BRANCH>
    if lower.startswith('self'):
        # Remove 'self' prefix and any separator
        rest = re.sub(r'^self[\s\-]*', '', desc, flags=re.IGNORECASE).strip()
        # Split on ' - ' to separate name from branch
        parts = rest.split(' - ')
        name_part = parts[0].strip() if parts else ""
        if name_part and len(name_part) > 1 and not name_part.upper().startswith('DELHI') and not name_part.upper().startswith('MUMBAI'):
            return f"Self - {name_part.title()}"
        return "Self Transfer"

    # ── I/W Cheque Return (with payee) ───────────────────────────────────
    if 'chq return' in lower or 'i/w chq return' in lower:
        # Extract payee from 'for payee -<NAME>--'
        payee_match = re.search(r'for payee\s*[\-\s]+(.+?)--', desc, re.IGNORECASE)
        if payee_match:
            payee = payee_match.group(1).strip()
            if payee:
                return f"Cheque Return - {payee.title()}"
        return "Cheque Return"

    # ── INW CHQ RTN CHG (Cheque Return Charges) ─────────────────────────
    if 'chq rtn chg' in lower or 'inw chq rtn' in lower:
        return "Cheque Return Charges"

    # ── IB-IMPS-DR (Internet Banking IMPS Debit) ────────────────────────
    # Format: IB-IMPS-DR//<BANK>/**<LAST4>//<DATE> <TIME>
    if upper.startswith('IB-IMPS'):
        bank_match = re.search(r'//([A-Z]+)/\*\*(\d+)//', desc)
        if bank_match:
            bank = bank_match.group(1)
            last4 = bank_match.group(2)
            return f"IMPS Transfer ({bank} **{last4})"
        return "IMPS Transfer"

    # ── ATM / IMPS Charges ───────────────────────────────────────────────
    if 'atm txn' in lower and 'imps charges' in lower:
        return "IMPS Charges"

    # ── IB ITG (Internet Banking Internal Transfer) ──────────────────────
    # Format: IB ITG <ref> <acctno> Online Transaction <purpose>
    if upper.startswith('IB ITG'):
        purpose_match = re.search(r'Online Transaction\s+(.+)', desc, re.IGNORECASE)
        if purpose_match:
            purpose = purpose_match.group(1).strip()
            # Clean up purpose (OTH-site expnse => Site Expense)
            purpose = re.sub(r'^OTH[\-\s]*', '', purpose).strip()
            if purpose:
                return f"Online Transfer - {purpose.title()}"
        return "Online Transfer"

    # ── Chq Paid-MICR (Cheque Clearing Debit) ───────────────────────────
    # Format: Chq Paid-MICR Inward Clearing-<PAYEE>-<BANK>-<BANK>
    if 'chq paid' in lower and 'micr' in lower:
        # Extract payee after 'Clearing-' or 'Clearing '
        clearing_match = re.search(r'Clearing[\-\s]+(.+)', desc, re.IGNORECASE)
        if clearing_match:
            rest = clearing_match.group(1).strip()
            # Payee is the first segment before a bank name
            bank_pattern = r'\-\s*(HDFC|ICICI|SBI|AXIS|CANARA|CENTRAL|CITI|KOTAK|BOB|PNB|IDBI|YES|INDUSIND)'
            parts = re.split(bank_pattern, rest, flags=re.IGNORECASE)
            payee = parts[0].strip().rstrip('- ')
            if payee:
                return f"Cheque - {payee.title()}"
        return "Cheque Payment"

    # ── By Clg (Clearing Credit) ─────────────────────────────────────────
    # Format: By Clg:<CLEARING_HOUSE>-<BANK>, <PAYEE>
    if lower.startswith('by clg'):
        # Try to extract payee after comma
        comma_idx = desc.find(',')
        if comma_idx > 0:
            payee = desc[comma_idx + 1:].strip()
            if payee and len(payee) > 1:
                return f"Clearing Credit - {payee.title()}"
        # Try to extract bank name
        parts = desc.split('-')
        if len(parts) >= 2:
            bank_part = parts[-1].strip()
            if bank_part:
                return f"Clearing Credit ({bank_part.title()})"
        return "Clearing Credit"

    # ── Service Charges ──────────────────────────────────────────────────
    if lower.startswith('service charge'):
        return "Service Charges"

    # ── SMS Charges ──────────────────────────────────────────────────────
    if 'sms charge' in lower:
        return "SMS Charges"

    # ── Fallback: return first 60 chars ──────────────────────────────────
    return desc[:60] if len(desc) > 60 else desc


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
    """Clean up Kotak Bank transaction description.
    Kotak patterns:
      UPI/<Payee>/<ref>/<Purpose>
      IMPS-<Company>
      Recd:IMPS/<ref>/<Payee>
      NEFT-<ref>-<Payee>
      OS <Merchant>  (Online Services)
      Chrg: / Rem Chrgs:
    """
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    if not desc:
        return "Bank Transaction"

    lower = desc.lower()

    # ── Known payment gateways to bypass for payee ───────────────────────
    gateway_names = {
        'credclub': 'Cred', 'cred ': 'Cred',
    }

    # ── UPI format: UPI/<Payee>/<ref>/<Purpose> ──────────────────────────
    if desc.startswith('UPI/'):
        parts = desc.split('/')
        if len(parts) >= 2:
            payee = parts[1].strip()
            # Check if payee is a gateway
            for gw_key, gw_name in gateway_names.items():
                if gw_key in payee.lower():
                    return f"UPI - {gw_name}"
            # Clean up payee: remove trailing spaces/numbers
            payee = re.sub(r'\d{5,}.*', '', payee).strip()
            if payee and len(payee) > 1 and any(c.isalpha() for c in payee):
                return f"UPI - {payee.title()}"
        return "UPI Transfer"

    # ── IMPS incoming: Recd:IMPS/<ref>/<Payee> ───────────────────────────
    if lower.startswith('recd:imps') or lower.startswith('recd: imps'):
        parts = desc.split('/')
        if len(parts) >= 3:
            payee = parts[2].strip()
            payee = re.sub(r'\d{5,}.*', '', payee).strip()
            if payee and any(c.isalpha() for c in payee):
                return f"IMPS - {payee.title()}"
        return "IMPS Inward"

    # ── IMPS outgoing: IMPS-<Company> ────────────────────────────────────
    if desc.startswith('IMPS-') or desc.startswith('IMPS '):
        rest = re.sub(r'^IMPS[\-\s]+', '', desc).strip()
        # Remove trailing ref numbers
        rest = re.sub(r'\s+\d{6,}.*', '', rest).strip()
        if rest and any(c.isalpha() for c in rest):
            return f"IMPS - {rest.title()}"
        return "IMPS Transfer"

    # ── NEFT ─────────────────────────────────────────────────────────────
    if 'NEFT' in desc.upper():
        neft_match = re.search(r'NEFT[\-/]\s*(?:[A-Z0-9]+[\-/])?\s*([A-Za-z][\w\s]+)', desc)
        if neft_match:
            payee = neft_match.group(1).strip()
            if payee:
                return f"NEFT - {payee.title()}"
        return "NEFT Transfer"

    # ── Own Transfer ─────────────────────────────────────────────────────
    if 'own transfer' in lower:
        return "Own Account Transfer"

    # ── Cash Deposit ─────────────────────────────────────────────────────
    if 'cash deposit' in lower:
        return "Cash Deposit"

    # ── OS (Online Services / Payment Gateway) ───────────────────────────
    if desc.startswith('OS '):
        merchant = desc[3:].split(' ')[0]
        return f"Payment - {merchant.title()}"

    # ── Charges ──────────────────────────────────────────────────────────
    if desc.startswith('Chrg:') or desc.startswith('Rem Chrgs:') or 'consolidated chrg' in lower:
        return "Bank Charges"

    # ── Interest ─────────────────────────────────────────────────────────
    if 'interest' in lower or 'int.pd' in lower or 'int.cr' in lower:
        return "Interest Credit"

    # ── Fallback ─────────────────────────────────────────────────────────
    desc_clean = re.sub(r'\s+', ' ', desc).strip()
    return desc_clean[:80] if len(desc_clean) > 80 else desc_clean


