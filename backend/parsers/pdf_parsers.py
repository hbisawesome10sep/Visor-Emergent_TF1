"""
Bank Statement PDF Parser - Main Entry Point
Refactored for maintainability: Bank-specific logic is in parsers/banks/
"""
import io
import logging
from parsers.utils import detect_bank, parse_date, parse_amount, detect_header_columns
from parsers.banks import (
    parse_icici_pdf_text,
    parse_sbi_pdf,
    parse_axis_pdf,
    parse_indusind_pdf,
    parse_yesbank_pdf,
    parse_kotak_pdf,
    parse_bob_pdf,
    parse_union_pdf,
    parse_canara_pdf,
    parse_idbi_pdf,
    parse_pnb_pdf,
    parse_hdfc_pdf,
)

logger = logging.getLogger(__name__)


def parse_pdf_statement(file_bytes: bytes, password: str = None, bank_hint: str = "") -> list:
    """
    Parse a PDF bank statement using pdfplumber.
    Supports password-protected PDFs and 12+ Indian banks.
    
    Args:
        file_bytes: PDF file content
        password: Optional password for encrypted PDFs
        bank_hint: User-provided bank name hint for parser selection
    
    Returns:
        List of transaction dictionaries with date, description, bank_debit, bank_credit
    """
    import pdfplumber
    transactions = []
    
    # Try to open PDF, with or without password
    try:
        if password:
            pdf = pdfplumber.open(io.BytesIO(file_bytes), password=password)
        else:
            pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as e:
        error_str = str(e).lower()
        error_type = type(e).__name__
        
        # Check for password-protected PDF
        if 'password' in error_str or 'encrypted' in error_str or 'pdfminer' in error_type.lower():
            if not password:
                raise ValueError("This PDF is password-protected. Please provide the password in the 'PDF Password' field.")
            else:
                raise ValueError("Incorrect PDF password. Please check and try again.")
        raise ValueError(f"Could not open PDF: {str(e) or 'Unknown error'}")
    
    with pdf:
        # Extract all text for bank detection
        all_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"
        
        # Detect bank
        bank = detect_bank(bank_hint, all_text)
        logger.info(f"Detected bank: {bank}")
        
        # Use bank-specific parser
        if bank == "sbi":
            transactions = parse_sbi_pdf(pdf, all_text)
            if transactions:
                logger.info(f"Parsed {len(transactions)} transactions using SBI parser")
                return transactions
        
        elif bank == "icici":
            icici_txns = parse_icici_pdf_text(all_text)
            if icici_txns:
                logger.info(f"Parsed {len(icici_txns)} transactions using ICICI parser")
                return icici_txns
        
        elif bank == "axis":
            axis_txns = parse_axis_pdf(pdf, all_text)
            if axis_txns:
                logger.info(f"Parsed {len(axis_txns)} transactions using Axis parser")
                return axis_txns
        
        elif bank == "indusind":
            indusind_txns = parse_indusind_pdf(pdf, all_text)
            if indusind_txns:
                logger.info(f"Parsed {len(indusind_txns)} transactions using IndusInd parser")
                return indusind_txns
        
        elif bank == "yes":
            yes_txns = parse_yesbank_pdf(pdf, all_text)
            if yes_txns:
                logger.info(f"Parsed {len(yes_txns)} transactions using Yes Bank parser")
                return yes_txns
        
        elif bank == "hdfc":
            hdfc_txns = parse_hdfc_pdf(pdf, all_text)
            if hdfc_txns:
                logger.info(f"Parsed {len(hdfc_txns)} transactions using HDFC parser")
                return hdfc_txns
        
        elif bank == "pnb":
            pnb_txns = parse_pnb_pdf(pdf, all_text)
            if pnb_txns:
                logger.info(f"Parsed {len(pnb_txns)} transactions using PNB parser")
                return pnb_txns
        
        elif bank == "idbi":
            idbi_txns = parse_idbi_pdf(pdf, all_text)
            if idbi_txns:
                logger.info(f"Parsed {len(idbi_txns)} transactions using IDBI parser")
                return idbi_txns
        
        elif bank == "canara":
            canara_txns = parse_canara_pdf(pdf, all_text)
            if canara_txns:
                logger.info(f"Parsed {len(canara_txns)} transactions using Canara parser")
                return canara_txns
        
        elif bank == "union":
            union_txns = parse_union_pdf(pdf, all_text)
            if union_txns:
                logger.info(f"Parsed {len(union_txns)} transactions using Union Bank parser")
                return union_txns
        
        elif bank == "kotak":
            kotak_txns = parse_kotak_pdf(pdf, all_text)
            if kotak_txns:
                logger.info(f"Parsed {len(kotak_txns)} transactions using Kotak parser")
                return kotak_txns
        
        elif bank == "bob":
            bob_txns = parse_bob_pdf(pdf, all_text)
            if bob_txns:
                logger.info(f"Parsed {len(bob_txns)} transactions using Bank of Baroda parser")
                return bob_txns
        
        # Standard table-based parsing for other banks
        all_rows = []
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        cleaned = [str(cell).strip() if cell else "" for cell in row]
                        all_rows.append(cleaned)

        if not all_rows:
            # Try text extraction as fallback
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    for line in text.split("\n"):
                        parts = line.split()
                        if len(parts) >= 3:
                            all_rows.append(parts)

    if not all_rows:
        raise ValueError("Could not extract any data from the PDF. The file may be scanned/image-based.")

    header_idx = 0
    mapping = {}
    for i, row in enumerate(all_rows[:15]):
        test_mapping = detect_header_columns(row)
        if test_mapping["date"] >= 0 and (test_mapping["debit"] >= 0 or test_mapping["credit"] >= 0):
            header_idx = i
            mapping = test_mapping
            break

    if not mapping or mapping["date"] < 0:
        raise ValueError("Could not detect column headers in PDF. The statement format may not be supported.")

    for row in all_rows[header_idx + 1:]:
        if len(row) <= max(v for v in mapping.values() if v >= 0):
            continue

        date_str = row[mapping["date"]] if mapping["date"] >= 0 else ""
        date = parse_date(date_str)
        if not date:
            continue

        description = row[mapping["description"]].strip() if mapping["description"] >= 0 else ""
        if not description:
            continue

        bank_debit = parse_amount(row[mapping["debit"]]) if mapping["debit"] >= 0 else 0
        bank_credit = parse_amount(row[mapping["credit"]]) if mapping["credit"] >= 0 else 0

        if bank_debit == 0 and bank_credit == 0:
            continue

        transactions.append({
            "date": date,
            "description": description,
            "bank_debit": bank_debit,
            "bank_credit": bank_credit,
        })

    return transactions
