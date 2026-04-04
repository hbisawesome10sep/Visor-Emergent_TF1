"""
BOB Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


def parse_bob_pdf(pdf, all_text: str) -> list:
    """
    Parse Bank of Baroda PDF statement.
    
    Uses TABLE extraction as primary method — the table has separate
    Withdrawals and Deposits columns giving us ground truth for debit/credit.
    
    Page 1 table has 7 cols: [date, empty, description, withdrawals, deposits, balance, other]
    Page 2+ tables have 6 cols: [date, description, withdrawals, deposits, balance, other]
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

                cleaned = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]

                # Determine column layout (7-col vs 6-col)
                if len(cleaned) >= 7:
                    date_str = cleaned[0]
                    desc = cleaned[2]
                    withdrawal_str = cleaned[3]
                    deposit_str = cleaned[4]
                elif len(cleaned) >= 6:
                    date_str = cleaned[0]
                    desc = cleaned[1]
                    withdrawal_str = cleaned[2]
                    deposit_str = cleaned[3]
                else:
                    continue

                # Parse date
                date_str_clean = date_str.split(' ')[0] if ' ' in date_str else date_str
                date = parse_date(date_str_clean)
                if not date:
                    continue

                # Skip Opening/Closing Balance
                if 'opening balance' in desc.lower() or 'closing balance' in desc.lower():
                    continue

                # Skip empty descriptions
                if not desc:
                    continue

                withdrawal = parse_amount(withdrawal_str)
                deposit = parse_amount(deposit_str)

                if withdrawal == 0 and deposit == 0:
                    continue

                transactions.append({
                    'date': date,
                    'description': clean_bob_description(desc),
                    'bank_debit': withdrawal,
                    'bank_credit': deposit,
                })

    # ── Gap-filling: catch entries missed by table extraction (page boundaries) ──
    captured = set()
    for t in transactions:
        amt = t['bank_debit'] if t['bank_debit'] > 0 else t['bank_credit']
        captured.add((t['date'], amt))

    prev_balance = None
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        for line in text.split('\n'):
            line = line.strip()
            date_match = re.match(r'^(\d{2}-\d{2}-\d{4})\s+(.+)', line)
            if not date_match:
                continue
            date = parse_date(date_match.group(1))
            if not date:
                continue
            rest = date_match.group(2)
            if 'Opening Balance' in rest or 'Closing Balance' in rest:
                amounts = re.findall(r'([\d,]+\.\d{2})', rest)
                if amounts:
                    prev_balance = parse_amount(amounts[-1])
                continue

            amounts = re.findall(r'([\d,]+\.\d{2})', rest)
            if len(amounts) < 2:
                continue

            txn_amount = parse_amount(amounts[0])
            new_balance = parse_amount(amounts[-1])

            if txn_amount <= 0:
                prev_balance = new_balance
                continue

            if (date, txn_amount) in captured:
                prev_balance = new_balance
                continue

            desc_end = rest.find(amounts[0])
            description = rest[:desc_end].strip()
            if not description:
                prev_balance = new_balance
                continue

            if prev_balance is not None and new_balance > prev_balance:
                withdrawal, deposit = 0, txn_amount
            else:
                withdrawal, deposit = txn_amount, 0

            transactions.append({
                'date': date,
                'description': clean_bob_description(description),
                'bank_debit': withdrawal,
                'bank_credit': deposit,
            })
            captured.add((date, txn_amount))
            prev_balance = new_balance

    transactions.sort(key=lambda t: t['date'])
    return transactions


