"""
IDBI Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


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


