"""
UNION Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


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


