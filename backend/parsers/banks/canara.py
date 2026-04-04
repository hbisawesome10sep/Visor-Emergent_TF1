"""
CANARA Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


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


