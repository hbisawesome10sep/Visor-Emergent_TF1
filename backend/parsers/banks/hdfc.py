"""
HDFC Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


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


