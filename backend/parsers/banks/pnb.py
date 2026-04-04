"""
PNB Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


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


