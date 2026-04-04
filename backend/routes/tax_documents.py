"""
Tax Documents Parsers — Phase 2
Form 16 PDF Parser, AIS/Form 26AS Parser, FD Interest Certificate Parser
"""
import io
import re
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
from database import db
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tax")

# ══════════════════════════════════════
#  FORM 16 PARSER
# ══════════════════════════════════════

FORM16_SALARY_PATTERNS = {
    "gross_salary": [
        r"gross\s*salary.*?(\d+[,\d]*)",
        r"total\s*gross\s*salary.*?(\d+[,\d]*)",
        r"1\s*[.\)]\s*gross\s*salary.*?(\d+[,\d]*)",
    ],
    "basic_salary": [
        r"salary\s*as\s*per\s*.*?section\s*17\(1\).*?(\d+[,\d]*)",
        r"basic\s*salary.*?(\d+[,\d]*)",
    ],
    "hra": [
        r"house\s*rent\s*allowance.*?(\d+[,\d]*)",
        r"hra.*?(\d+[,\d]*)",
    ],
    "lta": [
        r"leave\s*travel\s*.*?(\d+[,\d]*)",
        r"lta.*?(\d+[,\d]*)",
    ],
    "perquisites": [
        r"perquisites.*?(\d+[,\d]*)",
        r"value\s*of\s*perquisites.*?17\(2\).*?(\d+[,\d]*)",
    ],
    "profits_in_lieu": [
        r"profits\s*in\s*lieu.*?(\d+[,\d]*)",
        r"section\s*17\(3\).*?(\d+[,\d]*)",
    ],
    "standard_deduction": [
        r"standard\s*deduction.*?(\d+[,\d]*)",
        r"deduction\s*u/s\s*16\(ia\).*?(\d+[,\d]*)",
    ],
    "professional_tax": [
        r"professional\s*tax.*?(\d+[,\d]*)",
        r"tax\s*on\s*employment.*?(\d+[,\d]*)",
    ],
    "total_deductions_16": [
        r"total\s*amount\s*of\s*deductions.*?section\s*16.*?(\d+[,\d]*)",
        r"total\s*deduction\s*u/s\s*16.*?(\d+[,\d]*)",
    ],
    "net_salary": [
        r"income\s*chargeable\s*under.*?salaries.*?(\d+[,\d]*)",
        r"net\s*salary.*?(\d+[,\d]*)",
    ],
}

FORM16_DEDUCTION_PATTERNS = {
    "80C": [
        r"80c.*?(\d+[,\d]*)",
        r"section\s*80c\)?.*?(\d+[,\d]*)",
        r"deduction\s*u/s\s*80c.*?(\d+[,\d]*)",
    ],
    "80CCC": [
        r"80ccc.*?(\d+[,\d]*)",
        r"section\s*80ccc.*?(\d+[,\d]*)",
    ],
    "80CCD1": [
        r"80ccd\(1\).*?(\d+[,\d]*)",
        r"80ccd\s*1.*?(\d+[,\d]*)",
    ],
    "80CCD1B": [
        r"80ccd\(1b\).*?(\d+[,\d]*)",
        r"80ccd\s*1b.*?(\d+[,\d]*)",
        r"additional.*?nps.*?(\d+[,\d]*)",
    ],
    "80CCD2": [
        r"80ccd\(2\).*?(\d+[,\d]*)",
        r"employer.*?nps.*?(\d+[,\d]*)",
    ],
    "80D": [
        r"80d.*?(\d+[,\d]*)",
        r"section\s*80d.*?(\d+[,\d]*)",
        r"health\s*insurance.*?(\d+[,\d]*)",
    ],
    "80E": [
        r"80e.*?(\d+[,\d]*)",
        r"education\s*loan.*?(\d+[,\d]*)",
    ],
    "80G": [
        r"80g.*?(\d+[,\d]*)",
        r"donations.*?(\d+[,\d]*)",
    ],
    "80TTA": [
        r"80tta.*?(\d+[,\d]*)",
        r"savings\s*interest.*?(\d+[,\d]*)",
    ],
    "24b": [
        r"24\(b\).*?(\d+[,\d]*)",
        r"housing\s*loan\s*interest.*?(\d+[,\d]*)",
        r"interest\s*on\s*home\s*loan.*?(\d+[,\d]*)",
    ],
}

FORM16_TAX_PATTERNS = {
    "total_taxable_income": [
        r"total\s*taxable\s*income.*?(\d+[,\d]*)",
        r"total\s*income.*?(\d+[,\d]*)",
        r"aggregate\s*of.*?total\s*income.*?(\d+[,\d]*)",
    ],
    "tax_on_income": [
        r"tax\s*on\s*total\s*income.*?(\d+[,\d]*)",
        r"income\s*tax.*?(\d+[,\d]*)",
        r"tax\s*payable.*?(\d+[,\d]*)",
    ],
    "surcharge": [
        r"surcharge.*?(\d+[,\d]*)",
    ],
    "cess": [
        r"cess.*?(\d+[,\d]*)",
        r"health.*?education\s*cess.*?(\d+[,\d]*)",
    ],
    "total_tax": [
        r"total\s*tax\s*payable.*?(\d+[,\d]*)",
        r"tax\s*liability.*?(\d+[,\d]*)",
    ],
    "tds_deducted": [
        r"tax\s*deducted\s*at\s*source.*?(\d+[,\d]*)",
        r"tds\s*deducted.*?(\d+[,\d]*)",
        r"total\s*tds.*?(\d+[,\d]*)",
    ],
}


def parse_amount(text: str) -> float:
    """Extract numeric amount from text, handling Indian formatting."""
    if not text:
        return 0.0
    # Remove commas and spaces
    clean = re.sub(r"[,\s]", "", text)
    try:
        return float(clean)
    except ValueError:
        return 0.0


def extract_with_patterns(text: str, patterns: List[str]) -> Optional[float]:
    """Try multiple regex patterns and return first match."""
    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
        if match:
            amount = parse_amount(match.group(1))
            if amount > 0:
                return amount
    return None


def extract_employer_info(text: str) -> Dict[str, str]:
    """Extract employer details from Form 16."""
    info = {}
    
    # Employer name
    name_match = re.search(r"name\s*(?:and\s*address\s*)?of\s*(?:the\s*)?employer[:\s]*([^\n]+)", text, re.IGNORECASE)
    if name_match:
        info["employer_name"] = name_match.group(1).strip()[:100]
    
    # TAN
    tan_match = re.search(r"tan[:\s]*([A-Z]{4}\d{5}[A-Z])", text, re.IGNORECASE)
    if tan_match:
        info["employer_tan"] = tan_match.group(1).upper()
    
    # Employee PAN
    pan_match = re.search(r"pan\s*(?:of\s*)?(?:the\s*)?(?:employee|deductee)[:\s]*([A-Z]{5}\d{4}[A-Z])", text, re.IGNORECASE)
    if pan_match:
        info["employee_pan"] = pan_match.group(1).upper()
    
    # Financial Year
    fy_match = re.search(r"(?:financial\s*year|assessment\s*year|fy)[:\s]*(\d{4})\s*[-–]\s*(\d{2,4})", text, re.IGNORECASE)
    if fy_match:
        year1 = fy_match.group(1)
        year2 = fy_match.group(2)
        if len(year2) == 2:
            year2 = year1[:2] + year2
        info["financial_year"] = f"{year1}-{year2[-2:]}"
    
    return info


def parse_form16_pdf(text: str) -> Dict[str, Any]:
    """Parse Form 16 PDF text content and extract salary/tax details."""
    result = {
        "document_type": "form16",
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "employer_info": {},
        "salary_components": {},
        "deductions": {},
        "tax_computation": {},
        "raw_text_length": len(text),
    }
    
    # Extract employer info
    result["employer_info"] = extract_employer_info(text)
    
    # Extract salary components
    for component, patterns in FORM16_SALARY_PATTERNS.items():
        amount = extract_with_patterns(text, patterns)
        if amount:
            result["salary_components"][component] = amount
    
    # Extract deductions
    for section, patterns in FORM16_DEDUCTION_PATTERNS.items():
        amount = extract_with_patterns(text, patterns)
        if amount:
            result["deductions"][section] = amount
    
    # Extract tax computation
    for item, patterns in FORM16_TAX_PATTERNS.items():
        amount = extract_with_patterns(text, patterns)
        if amount:
            result["tax_computation"][item] = amount
    
    # Calculate derived values
    if result["salary_components"]:
        result["summary"] = {
            "gross_salary": result["salary_components"].get("gross_salary", 0),
            "total_deductions_claimed": sum(result["deductions"].values()),
            "net_taxable_income": result["tax_computation"].get("total_taxable_income", 0),
            "total_tds": result["tax_computation"].get("tds_deducted", 0),
        }
    
    # Determine parse quality
    has_salary = len(result["salary_components"]) >= 2
    has_tax = len(result["tax_computation"]) >= 2
    result["parse_quality"] = "high" if (has_salary and has_tax) else "medium" if has_salary else "low"
    
    return result


# ══════════════════════════════════════
#  AIS / FORM 26AS PARSER
# ══════════════════════════════════════

def parse_ais_json(data: Dict) -> Dict[str, Any]:
    """Parse Annual Information Statement (AIS) JSON data."""
    result = {
        "document_type": "ais",
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "tds_details": [],
        "sft_details": [],  # Specified Financial Transactions
        "interest_income": [],
        "dividend_income": [],
        "capital_gains": [],
        "summary": {
            "total_tds": 0,
            "total_interest": 0,
            "total_dividends": 0,
            "total_capital_gains": 0,
        },
    }
    
    # Process TDS entries
    if "tdsDetails" in data or "TDS_Details" in data:
        tds_list = data.get("tdsDetails") or data.get("TDS_Details") or []
        for entry in tds_list:
            tds_entry = {
                "deductor_name": entry.get("deductorName", entry.get("name", "")),
                "deductor_tan": entry.get("deductorTan", entry.get("tan", "")),
                "amount_paid": parse_amount(str(entry.get("amountPaid", entry.get("amount_paid", 0)))),
                "tds_deducted": parse_amount(str(entry.get("tdsDeducted", entry.get("tds", 0)))),
                "section": entry.get("section", ""),
                "transaction_date": entry.get("transactionDate", entry.get("date", "")),
            }
            result["tds_details"].append(tds_entry)
            result["summary"]["total_tds"] += tds_entry["tds_deducted"]
    
    # Process SFT (Specified Financial Transactions)
    if "sftDetails" in data or "SFT_Details" in data:
        sft_list = data.get("sftDetails") or data.get("SFT_Details") or []
        for entry in sft_list:
            result["sft_details"].append({
                "transaction_type": entry.get("transactionType", entry.get("type", "")),
                "amount": parse_amount(str(entry.get("amount", 0))),
                "reporting_entity": entry.get("reportingEntity", entry.get("entity", "")),
                "date": entry.get("date", ""),
            })
    
    # Process interest income
    if "interestIncome" in data or "Interest_Income" in data:
        interest_list = data.get("interestIncome") or data.get("Interest_Income") or []
        for entry in interest_list:
            amount = parse_amount(str(entry.get("amount", entry.get("interest", 0))))
            result["interest_income"].append({
                "payer": entry.get("payer", entry.get("bankName", "")),
                "amount": amount,
                "tds": parse_amount(str(entry.get("tds", 0))),
            })
            result["summary"]["total_interest"] += amount
    
    # Process dividend income
    if "dividendIncome" in data or "Dividend_Income" in data:
        div_list = data.get("dividendIncome") or data.get("Dividend_Income") or []
        for entry in div_list:
            amount = parse_amount(str(entry.get("amount", entry.get("dividend", 0))))
            result["dividend_income"].append({
                "company": entry.get("company", entry.get("companyName", "")),
                "amount": amount,
                "tds": parse_amount(str(entry.get("tds", 0))),
            })
            result["summary"]["total_dividends"] += amount
    
    return result


def parse_form26as_pdf(text: str) -> Dict[str, Any]:
    """Parse Form 26AS PDF text content."""
    result = {
        "document_type": "form26as",
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "tds_details": [],
        "tcs_details": [],
        "advance_tax": [],
        "self_assessment_tax": [],
        "summary": {
            "total_tds": 0,
            "total_tcs": 0,
            "total_advance_tax": 0,
            "total_self_assessment": 0,
        },
    }
    
    # Extract TDS entries (Part A)
    tds_pattern = r"([A-Z]{4}\d{5}[A-Z])\s+(.+?)\s+(\d+)\s+(\d+[,\d]*\.?\d*)\s+(\d+[,\d]*\.?\d*)"
    tds_matches = re.findall(tds_pattern, text)
    for match in tds_matches:
        tan, name, section, amount_paid, tds = match
        tds_entry = {
            "deductor_tan": tan,
            "deductor_name": name.strip()[:50],
            "section": section,
            "amount_paid": parse_amount(amount_paid),
            "tds_deducted": parse_amount(tds),
        }
        result["tds_details"].append(tds_entry)
        result["summary"]["total_tds"] += tds_entry["tds_deducted"]
    
    # Extract advance tax (Part C)
    advance_pattern = r"advance\s*tax.*?(\d+[,\d]*)"
    advance_matches = re.findall(advance_pattern, text, re.IGNORECASE)
    for match in advance_matches:
        amount = parse_amount(match)
        if amount > 0:
            result["advance_tax"].append({"amount": amount})
            result["summary"]["total_advance_tax"] += amount
    
    # Extract self-assessment tax (Part D)
    sat_pattern = r"self[\s-]*assessment\s*tax.*?(\d+[,\d]*)"
    sat_matches = re.findall(sat_pattern, text, re.IGNORECASE)
    for match in sat_matches:
        amount = parse_amount(match)
        if amount > 0:
            result["self_assessment_tax"].append({"amount": amount})
            result["summary"]["total_self_assessment"] += amount
    
    return result


# ══════════════════════════════════════
#  FD INTEREST CERTIFICATE PARSER
# ══════════════════════════════════════

FD_PATTERNS = {
    "bank_name": [
        r"(?:from|bank)[:\s]*([A-Za-z\s]+(?:bank|ltd|limited))",
        r"^([A-Za-z\s]+(?:bank|ltd|limited))",
    ],
    "fd_account": [
        r"(?:fd|fixed\s*deposit|account)\s*(?:no|number|#)[:\s]*([A-Z0-9]+)",
        r"deposit\s*(?:no|number)[:\s]*([A-Z0-9]+)",
    ],
    "principal": [
        r"(?:principal|deposit)\s*(?:amount)?[:\s]*(?:rs\.?\s*)?(\d+[,\d]*)",
        r"amount\s*(?:deposited|of\s*fd)[:\s]*(?:rs\.?\s*)?(\d+[,\d]*)",
    ],
    "interest_earned": [
        r"(?:interest|int)\s*(?:earned|credited|paid)[:\s]*(?:rs\.?\s*)?(\d+[,\d]*\.?\d*)",
        r"gross\s*interest[:\s]*(?:rs\.?\s*)?(\d+[,\d]*\.?\d*)",
        r"total\s*interest[:\s]*(?:rs\.?\s*)?(\d+[,\d]*\.?\d*)",
    ],
    "tds_deducted": [
        r"(?:tds|tax)\s*(?:deducted|withheld)[:\s]*(?:rs\.?\s*)?(\d+[,\d]*\.?\d*)",
        r"income\s*tax\s*deducted[:\s]*(?:rs\.?\s*)?(\d+[,\d]*\.?\d*)",
    ],
    "interest_rate": [
        r"(?:rate|roi|interest\s*rate)[:\s]*(\d+\.?\d*)\s*%",
        r"@\s*(\d+\.?\d*)\s*%",
    ],
    "maturity_date": [
        r"(?:maturity|due)\s*date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    ],
}


def parse_fd_certificate(text: str) -> Dict[str, Any]:
    """Parse Fixed Deposit Interest Certificate."""
    result = {
        "document_type": "fd_interest_certificate",
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "fd_details": [],
        "summary": {
            "total_interest": 0,
            "total_tds": 0,
            "total_principal": 0,
        },
    }
    
    fd_entry = {}
    
    for field, patterns in FD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                if field in ("principal", "interest_earned", "tds_deducted"):
                    fd_entry[field] = parse_amount(match.group(1))
                elif field == "interest_rate":
                    fd_entry[field] = float(match.group(1))
                else:
                    fd_entry[field] = match.group(1).strip()
                break
    
    # Extract financial year
    fy_match = re.search(r"(?:fy|financial\s*year|assessment\s*year)[:\s]*(\d{4})\s*[-–]\s*(\d{2,4})", text, re.IGNORECASE)
    if fy_match:
        year1 = fy_match.group(1)
        year2 = fy_match.group(2)
        if len(year2) == 2:
            year2 = year1[:2] + year2
        fd_entry["financial_year"] = f"{year1}-{year2[-2:]}"
    
    if fd_entry.get("interest_earned", 0) > 0:
        result["fd_details"].append(fd_entry)
        result["summary"]["total_interest"] = fd_entry.get("interest_earned", 0)
        result["summary"]["total_tds"] = fd_entry.get("tds_deducted", 0)
        result["summary"]["total_principal"] = fd_entry.get("principal", 0)
    
    # Try to find multiple FDs in the document
    # Pattern for tabular FD data
    table_pattern = r"(\d+[,\d]*\.?\d*)\s+(\d+\.?\d*)\s*%\s+(\d+[,\d]*\.?\d*)\s+(\d+[,\d]*\.?\d*)"
    table_matches = re.findall(table_pattern, text)
    for match in table_matches:
        principal, rate, interest, tds = match
        entry = {
            "principal": parse_amount(principal),
            "interest_rate": float(rate),
            "interest_earned": parse_amount(interest),
            "tds_deducted": parse_amount(tds),
        }
        if entry["interest_earned"] > 0 and entry not in result["fd_details"]:
            result["fd_details"].append(entry)
            result["summary"]["total_interest"] += entry["interest_earned"]
            result["summary"]["total_tds"] += entry["tds_deducted"]
            result["summary"]["total_principal"] += entry["principal"]
    
    return result


# ══════════════════════════════════════
#  API ENDPOINTS
# ══════════════════════════════════════

@router.post("/upload/form16")
async def upload_form16(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload and parse Form 16 PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        import pdfplumber
        content = await file.read()
        
        # Extract text from PDF
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Parse Form 16
        parsed = parse_form16_pdf(text)
        
        # Store in database
        doc = {
            "id": str(uuid4()),
            "user_id": user["id"],
            "document_type": "form16",
            "filename": file.filename,
            "financial_year": parsed["employer_info"].get("financial_year", ""),
            "employer_name": parsed["employer_info"].get("employer_name", ""),
            "parsed_data": parsed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.tax_documents.insert_one(doc)
        del doc["_id"]
        
        return {
            "status": "success",
            "document_id": doc["id"],
            "parse_quality": parsed["parse_quality"],
            "summary": parsed.get("summary", {}),
            "salary_components": parsed["salary_components"],
            "deductions": parsed["deductions"],
            "tax_computation": parsed["tax_computation"],
            "employer_info": parsed["employer_info"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Form 16 parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse Form 16: {str(e)}")


@router.post("/upload/ais")
async def upload_ais(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload and parse AIS (Annual Information Statement) - JSON or PDF."""
    filename_lower = file.filename.lower()
    
    try:
        content = await file.read()
        
        if filename_lower.endswith(".json"):
            import json
            data = json.loads(content.decode("utf-8"))
            parsed = parse_ais_json(data)
        elif filename_lower.endswith(".pdf"):
            import pdfplumber
            text = ""
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            parsed = parse_form26as_pdf(text)  # AIS PDF is similar to Form 26AS
        else:
            raise HTTPException(status_code=400, detail="Only JSON or PDF files are supported")
        
        # Store in database
        doc = {
            "id": str(uuid4()),
            "user_id": user["id"],
            "document_type": parsed["document_type"],
            "filename": file.filename,
            "parsed_data": parsed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.tax_documents.insert_one(doc)
        del doc["_id"]
        
        return {
            "status": "success",
            "document_id": doc["id"],
            "document_type": parsed["document_type"],
            "summary": parsed["summary"],
            "tds_entries_count": len(parsed.get("tds_details", [])),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AIS parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse AIS: {str(e)}")


@router.post("/upload/form26as")
async def upload_form26as(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload and parse Form 26AS PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        import pdfplumber
        content = await file.read()
        
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        parsed = parse_form26as_pdf(text)
        
        # Store in database
        doc = {
            "id": str(uuid4()),
            "user_id": user["id"],
            "document_type": "form26as",
            "filename": file.filename,
            "parsed_data": parsed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.tax_documents.insert_one(doc)
        del doc["_id"]
        
        return {
            "status": "success",
            "document_id": doc["id"],
            "summary": parsed["summary"],
            "tds_entries_count": len(parsed.get("tds_details", [])),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Form 26AS parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse Form 26AS: {str(e)}")


@router.post("/upload/fd-certificate")
async def upload_fd_certificate(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload and parse FD Interest Certificate PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        import pdfplumber
        content = await file.read()
        
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        parsed = parse_fd_certificate(text)
        
        # Store in database
        doc = {
            "id": str(uuid4()),
            "user_id": user["id"],
            "document_type": "fd_interest_certificate",
            "filename": file.filename,
            "parsed_data": parsed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.tax_documents.insert_one(doc)
        del doc["_id"]
        
        # Auto-create deduction entry for 80TTA (interest income up to 10K)
        if parsed["summary"]["total_interest"] > 0:
            interest = parsed["summary"]["total_interest"]
            tds = parsed["summary"]["total_tds"]
            
            # Add to auto-deductions for tracking
            auto_doc = {
                "id": str(uuid4()),
                "user_id": user["id"],
                "transaction_id": f"fd_{doc['id']}",
                "section": "80TTA",
                "section_label": "Section 80TTA",
                "name": f"FD Interest (TDS: ₹{tds:,.0f})",
                "amount": min(interest, 10000),  # 80TTA limit
                "limit": 10000,
                "fy": "2025-26",
                "detected_from": "fd_certificate",
                "source_category": "FD Interest",
                "source_description": file.filename,
                "source_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.auto_tax_deductions.insert_one(auto_doc)
        
        return {
            "status": "success",
            "document_id": doc["id"],
            "summary": parsed["summary"],
            "fd_count": len(parsed.get("fd_details", [])),
            "fd_details": parsed.get("fd_details", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FD Certificate parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse FD Certificate: {str(e)}")


@router.get("/documents")
async def get_tax_documents(user=Depends(get_current_user), fy: str = "2025-26"):
    """Get all uploaded tax documents for the user."""
    docs = await db.tax_documents.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return {
        "documents": docs,
        "count": len(docs),
    }


@router.delete("/documents/{document_id}")
async def delete_tax_document(document_id: str, user=Depends(get_current_user)):
    """Delete an uploaded tax document."""
    result = await db.tax_documents.delete_one({
        "id": document_id,
        "user_id": user["id"],
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted"}


# ══════════════════════════════════════
#  TAX METER / QUICK SUMMARY ENDPOINT
# ══════════════════════════════════════

@router.get("/meter")
async def get_tax_meter(user=Depends(get_current_user), fy: str = "2025-26"):
    """
    Get real-time tax meter data for dashboard widget.
    Returns: estimated tax liability, TDS paid, tax savings, and comparison.
    """
    from routes.tax import get_tax_summary, income_tax_calculator
    
    # Get tax calculation
    tax_calc = await income_tax_calculator(user, fy)
    
    # Get salary profile for more accurate estimates
    salary_profile = await db.salary_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    
    # Get auto-detected deductions total
    auto_deds = await db.auto_tax_deductions.find(
        {"user_id": user["id"], "fy": fy},
        {"_id": 0, "amount": 1, "section": 1}
    ).to_list(500)
    
    total_auto_deductions = sum(d.get("amount", 0) for d in auto_deds)
    
    # Calculate monthly TDS expected
    monthly_tds = salary_profile.get("tds_monthly", 0) if salary_profile else 0
    months_elapsed = min(12, max(1, datetime.now().month - 3 if datetime.now().month >= 4 else datetime.now().month + 9))
    tds_paid_ytd = monthly_tds * months_elapsed
    
    # Recommended regime
    better_regime = tax_calc["comparison"]["better_regime"]
    savings_by_switch = tax_calc["comparison"]["savings"]
    
    # Tax due/refund estimate
    if better_regime == "new":
        estimated_tax = tax_calc["new_regime"]["total_tax"]
    else:
        estimated_tax = tax_calc["old_regime"]["total_tax"]
    
    tax_due = max(0, estimated_tax - tds_paid_ytd)
    refund_expected = max(0, tds_paid_ytd - estimated_tax)
    
    # Deduction utilization
    total_80c = sum(d.get("amount", 0) for d in auto_deds if d.get("section") in ("80C", "80CCC", "80CCD1"))
    remaining_80c = max(0, 150000 - total_80c)
    
    return {
        "fy": fy,
        "estimated_tax": round(estimated_tax, 0),
        "tds_paid_ytd": round(tds_paid_ytd, 0),
        "tax_due": round(tax_due, 0),
        "refund_expected": round(refund_expected, 0),
        "better_regime": better_regime,
        "savings_by_switch": round(savings_by_switch, 0),
        "total_deductions": round(total_auto_deductions, 0),
        "deduction_80c": {
            "used": round(total_80c, 0),
            "limit": 150000,
            "remaining": round(remaining_80c, 0),
            "utilization_pct": round(min(100, total_80c / 150000 * 100), 1),
        },
        "months_elapsed": months_elapsed,
        "gross_income": round(tax_calc["income"]["gross_total"], 0),
        "effective_rate": tax_calc["comparison"]["new_effective_rate"] if better_regime == "new" else tax_calc["comparison"]["old_effective_rate"],
    }
