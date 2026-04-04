"""
KOTAK Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


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
    """Parse Kotak text-based format using word positions for column detection.
    
    Uses balance-delta approach: the balance column (rightmost) is ground truth.
    Amount and debit/credit are computed from balance differences because
    pdfplumber's (Dr)/(Cr) suffixes are unreliable for Kotak's multi-line layout.
    
    Column layout (from word x-positions):
      x ~30:  Date
      x ~94:  Narration
      x ~277: Chq/Ref No (excluded)
      x ~400: Amount (Dr/Cr)
      x ~500: Balance (Cr)
    """
    transactions = []
    BALANCE_X_THRESHOLD = 470  # Words at x >= 470 are in the Balance column
    AMOUNT_X_THRESHOLD = 380   # Words at x >= 380 are in Amount or Balance columns
    NARRATION_X_MAX = 270      # Words at x < 270 are narration (excludes Ref No at ~277)
    DATE_PATTERN = re.compile(r'^\d{2}-\d{2}-\d{4}$')
    AMOUNT_DRCR = re.compile(r'([\d,]+\.\d{2})\s*\((Cr|Dr)\)')

    prev_balance = None

    for page in pdf.pages:
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if not words:
            continue

        # Group words by approximate y-position (2px bands for tight grouping)
        from collections import defaultdict
        y_lines = defaultdict(list)
        for w in words:
            y_key = round(w['top'] / 3) * 3
            y_lines[y_key].append(w)

        # Merge lines that are very close vertically into visual rows
        sorted_ys = sorted(y_lines.keys())
        merged_lines = []
        for y in sorted_ys:
            if merged_lines and abs(y - merged_lines[-1][0]) < 8:
                merged_lines[-1][1].extend(y_lines[y])
            else:
                merged_lines.append([y, list(y_lines[y])])

        # Build transaction entries: group lines between date-starting rows
        entries = []
        current_entry = None

        for _, line_words in merged_lines:
            line_words.sort(key=lambda w: w['x0'])
            first_word = line_words[0]['text'] if line_words else ""

            # Check if this line starts a new entry (has date at x ~30)
            if DATE_PATTERN.match(first_word) and line_words[0]['x0'] < 80:
                if current_entry:
                    entries.append(current_entry)
                current_entry = {
                    'date_str': first_word,
                    'narration_words': [],
                    'amount_words': [],
                    'balance_words': [],
                }

            if current_entry is None:
                continue

            # Classify each word into columns by x-position
            for w in line_words:
                text = w['text']
                x = w['x0']
                if DATE_PATTERN.match(text) and x < 80:
                    continue  # Skip the date word itself
                if x >= BALANCE_X_THRESHOLD:
                    current_entry['balance_words'].append(text)
                elif x >= AMOUNT_X_THRESHOLD:
                    current_entry['amount_words'].append(text)
                elif x < NARRATION_X_MAX:
                    current_entry['narration_words'].append(text)
                # Words between NARRATION_X_MAX and AMOUNT_X_THRESHOLD (Ref column) are excluded

        if current_entry:
            entries.append(current_entry)

        # Process each entry using balance-delta
        for entry in entries:
            date = parse_date(entry['date_str'])
            if not date:
                continue

            # Build narration text (strip summary artifacts)
            narration = ' '.join(entry['narration_words']).strip()
            narration = re.sub(r'\s*Statement Summary.*$', '', narration, flags=re.IGNORECASE).strip()
            if not narration:
                continue

            # Skip summary/balance lines
            narration_lower = narration.lower()
            if any(kw in narration_lower for kw in ['opening balance', 'closing balance', 'total withdrawal', 'total deposit']):
                continue

            # Extract balance from balance_words
            balance_text = ' '.join(entry['balance_words'])
            amt_text = ' '.join(entry['amount_words'])
            all_text_combined = amt_text + ' ' + balance_text
            balance_match = AMOUNT_DRCR.search(balance_text)
            if not balance_match:
                all_amounts = AMOUNT_DRCR.findall(all_text_combined)
                if len(all_amounts) >= 2:
                    balance_val = parse_amount(all_amounts[-1][0])
                elif len(all_amounts) == 1:
                    balance_val = parse_amount(all_amounts[0][0])
                else:
                    continue
            else:
                balance_val = parse_amount(balance_match.group(1))

            if balance_val is None or balance_val < 0:
                continue

            if prev_balance is not None:
                delta = round(balance_val - prev_balance, 2)
                amount = abs(delta)
                if amount < 0.01:
                    prev_balance = balance_val
                    continue
                is_credit = delta > 0
            else:
                # First entry: extract amount from amount_words text
                first_amt_match = AMOUNT_DRCR.search(amt_text)
                if first_amt_match:
                    amount = parse_amount(first_amt_match.group(1))
                    # Infer direction: opening_balance = balance - amount (if Cr) or balance + amount (if Dr)
                    # The first entry amount is usually correct in the first row
                    is_credit = first_amt_match.group(2) == 'Cr'
                else:
                    prev_balance = balance_val
                    continue

            if amount > 0:
                transactions.append({
                    'date': date,
                    'description': clean_kotak_description(narration),
                    'bank_debit': 0 if is_credit else amount,
                    'bank_credit': amount if is_credit else 0,
                })

            prev_balance = balance_val

    return transactions



def clean_bob_description(raw_desc: str) -> str:
    """Clean up Bank of Baroda transaction description.
    BOB patterns:
      UPI/P2A/<ref>/<PAYEE>/<BANK>/<purpose>   (Person-to-Account)
      UPI/P2M/<ref>/<PAYEE>/<BANK>/<purpose>   (Person-to-Merchant)
      NEFT/<ref>/<PAYEE>/<BANK>/NEFT
      ACH-DR-<Company> <Bank>-<ref>-<code>
      ECS/<ref>/<Company_purpose>
      NRP<ref><PayeePurpose>
      920...:Int.Pd:<date_range>
      GST @18% on Charge
      Consolidated Charges for A/c
    """
    desc = raw_desc.replace('\n', ' ').replace('  ', ' ').strip()
    if not desc:
        return "Bank Transaction"

    upper = desc.upper()

    # ── Known payment gateways to bypass for actual payee ────────────────
    gateway_names = {
        'credclub': 'Cred',
    }

    # ── UPI (P2A / P2M) ─────────────────────────────────────────────────
    # Format: UPI/P2A/ref/PAYEE/Bank/purpose or UPI/P2M/ref/PAYEE/Bank/purpose
    if upper.startswith('UPI/'):
        parts = desc.split('/')
        # parts: ['UPI', 'P2A', 'ref', 'PAYEE', 'BankName', 'purpose']
        if len(parts) >= 4:
            payee = parts[3].strip()
            # Check if payee is a known gateway
            payee_lower = payee.lower().replace(' ', '')
            for gw_key, gw_name in gateway_names.items():
                if gw_key in payee_lower:
                    return f"UPI - {gw_name}"
            if payee and len(payee) > 1:
                # Capitalize properly
                return f"UPI - {payee.title()}"
        return "UPI Transfer"

    # ── NEFT ─────────────────────────────────────────────────────────────
    # Format: NEFT/ref/PAYEE/BANK/NEFT
    if upper.startswith('NEFT/'):
        parts = desc.split('/')
        if len(parts) >= 3:
            payee = parts[2].strip()
            if payee and len(payee) > 1:
                return f"NEFT - {payee.title()}"
        return "NEFT Transfer"

    # ── ACH-DR (Auto Clearing House Debit) ───────────────────────────────
    # Format: ACH-DR-TPCapfrst IDFC FIRST-ref-code
    if 'ACH-DR' in upper:
        rest = re.sub(r'^ACH-DR-', '', desc, flags=re.IGNORECASE).strip()
        # Take the company name part (before the ref number dash)
        parts = rest.split('-')
        if parts:
            company = parts[0].strip()
            if company:
                return f"Auto-Debit - {company.title()}"
        return "Auto-Debit"

    # ── ECS (Electronic Clearing) ────────────────────────────────────────
    # Format: ECS/ref/Company_purpose
    if upper.startswith('ECS/'):
        parts = desc.split('/')
        if len(parts) >= 3:
            purpose = parts[2].strip()
            # Clean up: "Bajaj Finance Ltd_SMS OT" → "Bajaj Finance Ltd"
            purpose = re.split(r'_', purpose)[0].strip()
            if purpose:
                return f"ECS - {purpose.title()}"
        return "ECS Debit"

    # ── NRP (NEFT Remittance Payment / incoming transfer) ────────────────
    # Format: NRP<digits><PayeePurpose> e.g. NRP21555713RatanshahaniJulyRen
    if upper.startswith('NRP'):
        # Strip NRP and leading digits
        rest = re.sub(r'^NRP\d+', '', desc).strip()
        if rest:
            # CamelCase split: insert space before uppercase letters
            spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', rest)
            return f"NRP - {spaced.title()}"
        return "NRP Inward"

    # ── IMPS ─────────────────────────────────────────────────────────────
    if upper.startswith('IMPS/'):
        parts = desc.split('/')
        if len(parts) >= 3:
            payee = parts[2].strip()
            if payee and len(payee) > 1:
                return f"IMPS - {payee.title()}"
        return "IMPS Transfer"

    # ── Interest Paid ────────────────────────────────────────────────────
    if 'INT.PD' in upper or 'INT.CR' in upper or 'INTEREST' in upper:
        return "Interest Credit"

    # ── GST ──────────────────────────────────────────────────────────────
    if upper.startswith('GST'):
        return "GST Charges"

    # ── Consolidated Charges ─────────────────────────────────────────────
    if 'CONSOLIDATED CHARGE' in upper:
        return "Bank Charges"

    # ── SMS Charges ──────────────────────────────────────────────────────
    if 'SMS' in upper and 'CHARGE' in upper:
        return "SMS Charges"

    # ── Fallback ─────────────────────────────────────────────────────────
    desc_clean = re.sub(r'\s+', ' ', desc).strip()
    return desc_clean[:80] if len(desc_clean) > 80 else desc_clean


