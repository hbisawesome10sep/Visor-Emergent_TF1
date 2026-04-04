"""
INDUSIND Bank Statement Parser
Extracted from monolithic pdf_parsers.py for better maintainability.
"""
import re
import logging
from parsers.utils import parse_date, parse_amount

logger = logging.getLogger(__name__)


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


