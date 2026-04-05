"""
Tax Documents Parsers — Phase 2
Form 16 PDF Parser, AIS/Form 26AS Parser, FD Interest Certificate Parser
With LLM-powered fallback for low-quality regex parsing.
"""
import io
import re
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
from database import db
from auth import get_current_user
from config import EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tax")

# ══════════════════════════════════════
#  FORM 16 PARSER
# ══════════════════════════════════════

FORM16_SALARY_PATTERNS = {
    "gross_salary": [
        r"gross\s*salary",
        r"total\s*gross\s*salary",
        r"1\s*[.\)]\s*gross\s*salary",
    ],
    "basic_salary": [
        r"salary\s*as\s*per\s*.*?section\s*17\(1\)",
        r"basic\s*salary",
    ],
    "hra": [
        r"house\s*rent\s*allowance\s*.*?10\(13A?\)",
    ],
    "lta": [
        r"leave\s*travel\s*(?:concession|allowance|assistance)",
        r"travel\s*concession\s*or\s*assistance",
    ],
    "perquisites": [
        r"value\s*of\s*perquisites.*?17\(2\)",
    ],
    "profits_in_lieu": [
        r"profits\s*in\s*lieu.*?17\(3\)",
    ],
    "standard_deduction": [
        r"standard\s*deduction\s*.*?16\(ia\)",
    ],
    "professional_tax": [
        r"tax\s*on\s*employment\s*.*?16\(iii\)",
        r"professional\s*tax",
    ],
    "total_deductions_16": [
        r"total\s*amount\s*of\s*deductions.*?section\s*16",
        r"total\s*deduction\s*u/s\s*16",
    ],
    "net_salary": [
        r"income\s*chargeable\s*under.*?head.*?salaries",
        r"net\s*salary",
    ],
    "exemption_section_10": [
        r"total\s*amount\s*of\s*exemption\s*claimed\s*under\s*section\s*10",
    ],
    "salary_after_exemption": [
        r"total\s*amount\s*of\s*salary\s*received\s*from\s*current\s*employer",
    ],
    "gross_total_income": [
        r"gross\s*total\s*income",
    ],
}

FORM16_DEDUCTION_PATTERNS = {
    "80C": [
        r"(?:life\s*insurance|provident\s*fund).*?section\s*80c\b",
        r"deduction\s*.*?section\s*80c\b",
    ],
    "80CCC": [
        r"(?:contribution\s*to\s*certain\s*pension|section\s*80ccc)\b",
    ],
    "80CCD1": [
        r"(?:contribution\s*by\s*taxpayer|section\s*80ccd\s*\(?1\)?)\b",
    ],
    "80CCD1B": [
        r"(?:notified\s*pension\s*scheme|section\s*80ccd\s*\(?1b?\)?)",
    ],
    "80CCD2": [
        r"(?:contribution\s*by\s*employer.*?pension|section\s*80ccd\s*\(?2\)?)",
    ],
    "80D": [
        r"(?:health\s*insurance\s*premia|section\s*80d)\b",
    ],
    "80E": [
        r"(?:interest\s*on\s*loan.*?higher\s*education|section\s*80e)\b",
    ],
    "80G": [
        r"(?:donations\s*to\s*certain\s*funds|section\s*80g)\b",
    ],
    "80TTA": [
        r"(?:interest\s*on\s*deposits\s*in\s*savings|section\s*80tta)\b",
    ],
    "24b": [
        r"(?:section\s*24\s*\(?b\)?|housing\s*loan\s*interest|interest\s*on\s*home\s*loan|loss\s*from\s*house\s*property)",
    ],
}

FORM16_TAX_PATTERNS = {
    "total_taxable_income": [
        r"total\s*taxable\s*income",
        r"12\.\s*total\s*taxable\s*income",
    ],
    "tax_on_income": [
        r"tax\s*on\s*total\s*income",
        r"13\.\s*tax\s*on\s*total\s*income",
    ],
    "rebate_87a": [
        r"rebate\s*under\s*section\s*87a",
        r"rebate\s*u/s\s*87a",
    ],
    "surcharge": [
        r"surcharge",
    ],
    "cess": [
        r"health\s*and\s*education\s*cess",
        r"education\s*cess",
    ],
    "total_tax": [
        r"tax\s*payable\s*\(13",
        r"17\.\s*tax\s*payable",
        r"net\s*tax\s*payable",
    ],
    "tds_deducted": [
        r"total\s*\(rs\.\)\s*.*\s+(\d[\d,.]+)\s+(\d[\d,.]+)\s*$",
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


def extract_line_amount(line: str) -> Optional[float]:
    """Extract the last monetary amount from a line of text.
    Monetary amounts are numbers >= 100 or with decimal (.00).
    Returns the rightmost valid amount on the line."""
    # Find all numbers that look like money (with optional decimals)
    amounts = re.findall(r'(\d[\d,]*(?:\.\d{1,2})?)', line)
    if not amounts:
        return None
    # Walk backwards to find the last valid monetary amount
    for amt_str in reversed(amounts):
        val = parse_amount(amt_str)
        # Accept if it's >= 100 OR has decimal (like 0.00)
        if val >= 100 or '.00' in amt_str or '.0' in amt_str:
            return val
    return None


def extract_with_patterns(text: str, patterns: List[str]) -> Optional[float]:
    """Find label lines matching patterns, then extract the last monetary amount."""
    lines = text.split('\n')
    text_lower = text.lower()

    for pattern in patterns:
        # Special handling for TDS pattern that has its own capture groups
        if r'\s+(\d[\d,.]+)\s+(\d[\d,.]+)\s*$' in pattern:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            if match:
                # Get the last group (TDS deposited amount)
                try:
                    amount = parse_amount(match.group(match.lastindex))
                    if amount >= 100:
                        return amount
                except (IndexError, AttributeError):
                    pass
            continue

        # For regular patterns: find matching lines, extract last amount
        for line in lines:
            if re.search(pattern, line.lower(), re.IGNORECASE):
                amount = extract_line_amount(line)
                if amount is not None and amount > 0:
                    return amount
                # Also check the next line (amounts sometimes wrap)
                line_idx = lines.index(line)
                if line_idx + 1 < len(lines):
                    next_line = lines[line_idx + 1].strip()
                    if next_line and re.match(r'^[\d,.\s]+$', next_line):
                        amount = extract_line_amount(next_line)
                        if amount is not None and amount > 0:
                            return amount
    return None


def extract_employer_info(text: str) -> Dict[str, str]:
    """Extract employer details from Form 16."""
    info = {}
    lines = text.split('\n')

    # Find employer name from lines near "Name and address of the Employer"
    for i, line in enumerate(lines):
        if re.search(r'name\s*and\s*address\s*of\s*the\s*employer', line, re.IGNORECASE):
            # Employer name is often on the NEXT line(s)
            for j in range(i + 1, min(i + 5, len(lines))):
                candidate = lines[j].strip()
                # Skip empty lines and lines that look like address/phone
                if candidate and len(candidate) > 5 and not re.match(r'^[\d+\(\)\-\s]+$', candidate):
                    if not re.search(r'pan\s*of|tan\s*of|employee|deductee|citizen', candidate, re.IGNORECASE):
                        # Clean up garbled text (overlapping columns)
                        info["employer_name"] = candidate[:100]
                        break
            break

    # TAN — look for proper TAN format
    tan_match = re.search(r'([A-Z]{4}\d{5}[A-Z])', text)
    if tan_match:
        info["employer_tan"] = tan_match.group(1)

    # Employee PAN
    pan_matches = re.findall(r'([A-Z]{5}\d{4}[A-Z])', text)
    if len(pan_matches) >= 2:
        info["employee_pan"] = pan_matches[1]  # Second PAN is usually the employee
    elif pan_matches:
        info["employee_pan"] = pan_matches[0]

    # Assessment Year and Financial Year
    ay_match = re.search(r'assessment\s*year[:\s]*(\d{4})\s*[-–]\s*(\d{2,4})', text, re.IGNORECASE)
    if ay_match:
        ay_year1 = ay_match.group(1)
        ay_year2 = ay_match.group(2)
        if len(ay_year2) == 2:
            ay_year2 = ay_year1[:2] + ay_year2
        fy_start = int(ay_year1) - 1
        fy_end = int(ay_year2) - 1
        info["financial_year"] = f"{fy_start}-{str(fy_end)[-2:]}"
        info["assessment_year"] = f"{ay_year1}-{ay_year2[-2:]}"
    else:
        fy_match = re.search(r'financial\s*year[:\s]*(\d{4})\s*[-–]\s*(\d{2,4})', text, re.IGNORECASE)
        if fy_match:
            year1 = fy_match.group(1)
            year2 = fy_match.group(2)
            if len(year2) == 2:
                year2 = year1[:2] + year2
            info["financial_year"] = f"{year1}-{year2[-2:]}"

    # Extract Total TDS from Part A summary row
    tds_match = re.search(r'total\s*\(rs\.?\)\s+(\d[\d,.]+)\s+(\d[\d,.]+)\s+(\d[\d,.]+)', text, re.IGNORECASE)
    if tds_match:
        info["_total_tds_part_a"] = parse_amount(tds_match.group(3))
        info["_total_salary_part_a"] = parse_amount(tds_match.group(1))

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

    # Extract employer info (also extracts TDS from Part A)
    result["employer_info"] = extract_employer_info(text)

    # Extract salary components
    for component, patterns in FORM16_SALARY_PATTERNS.items():
        amount = extract_with_patterns(text, patterns)
        if amount:
            result["salary_components"][component] = amount

    # Use Part A totals as fallback for gross salary
    part_a_salary = result["employer_info"].pop("_total_salary_part_a", 0)
    part_a_tds = result["employer_info"].pop("_total_tds_part_a", 0)

    if not result["salary_components"].get("gross_salary") and part_a_salary:
        result["salary_components"]["gross_salary"] = part_a_salary
    if not result["salary_components"].get("basic_salary") and result["salary_components"].get("gross_salary"):
        result["salary_components"]["basic_salary"] = result["salary_components"]["gross_salary"]

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

    # Use Part A TDS as fallback
    if not result["tax_computation"].get("tds_deducted") and part_a_tds:
        result["tax_computation"]["tds_deducted"] = part_a_tds

    # Calculate derived values
    gross = result["salary_components"].get("gross_salary", 0)
    total_deds = sum(result["deductions"].values())
    taxable = result["tax_computation"].get("total_taxable_income", 0)
    tds = result["tax_computation"].get("tds_deducted", 0)

    result["summary"] = {
        "gross_salary": gross,
        "total_deductions_claimed": total_deds,
        "net_taxable_income": taxable,
        "total_tds": tds,
    }

    # Determine parse quality based on VALUE validation
    has_salary = gross >= 100 or result["salary_components"].get("basic_salary", 0) >= 100
    has_deductions = total_deds > 0
    has_tax = taxable >= 100 or result["tax_computation"].get("tax_on_income", 0) >= 100
    has_tds = tds >= 100

    if has_salary and has_tax and has_tds:
        result["parse_quality"] = "high"
    elif has_salary and (has_tax or has_deductions):
        result["parse_quality"] = "medium"
    else:
        result["parse_quality"] = "low"
    
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
#  LLM-POWERED FALLBACK PARSER
# ══════════════════════════════════════

LLM_FORM16_PROMPT = """You are an expert Indian tax document parser. Extract structured data from this Form 16 PDF text.
Return ONLY a valid JSON object (no markdown, no explanation) with these exact keys:
{
  "employer_info": {"employer_name": "", "employer_tan": "", "employee_pan": "", "financial_year": ""},
  "salary_components": {"gross_salary": 0, "basic_salary": 0, "hra": 0, "lta": 0, "perquisites": 0, "standard_deduction": 0, "professional_tax": 0, "net_salary": 0},
  "deductions": {"80C": 0, "80CCC": 0, "80CCD1": 0, "80CCD1B": 0, "80CCD2": 0, "80D": 0, "80E": 0, "80G": 0, "80TTA": 0, "24b": 0},
  "tax_computation": {"total_taxable_income": 0, "tax_on_income": 0, "surcharge": 0, "cess": 0, "total_tax": 0, "tds_deducted": 0}
}
Only include non-zero values. All amounts should be numbers (no commas, no rupee symbols).
If you cannot find a value, omit it rather than guessing.

PDF TEXT:
"""

LLM_AIS_PROMPT = """You are an expert Indian tax document parser. Extract structured data from this AIS/Form 26AS PDF text.
Return ONLY a valid JSON object (no markdown, no explanation) with these exact keys:
{
  "tds_details": [{"deductor_name": "", "deductor_tan": "", "amount_paid": 0, "tds_deducted": 0, "section": ""}],
  "interest_income": [{"payer": "", "amount": 0, "tds": 0}],
  "dividend_income": [{"company": "", "amount": 0, "tds": 0}],
  "advance_tax": [{"amount": 0}],
  "self_assessment_tax": [{"amount": 0}],
  "summary": {"total_tds": 0, "total_interest": 0, "total_dividends": 0}
}
Only include entries you can actually find in the text. All amounts should be numbers.

PDF TEXT:
"""

LLM_FD_PROMPT = """You are an expert Indian tax document parser. Extract structured data from this FD Interest Certificate PDF text.
Return ONLY a valid JSON object (no markdown, no explanation) with these exact keys:
{
  "fd_details": [{"bank_name": "", "fd_account": "", "principal": 0, "interest_earned": 0, "tds_deducted": 0, "interest_rate": 0, "financial_year": ""}],
  "summary": {"total_interest": 0, "total_tds": 0, "total_principal": 0}
}
Only include entries with actual values. All amounts should be numbers.

PDF TEXT:
"""


async def llm_parse_document(text: str, doc_type: str) -> Optional[Dict[str, Any]]:
    """Use GPT-5.2 to extract structured data from document text when regex fails."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        prompts = {
            "form16": LLM_FORM16_PROMPT,
            "form26as": LLM_AIS_PROMPT,
            "ais": LLM_AIS_PROMPT,
            "fd_interest_certificate": LLM_FD_PROMPT,
        }
        prompt = prompts.get(doc_type)
        if not prompt:
            return None

        # Truncate text to avoid token limits (keep first ~8000 chars)
        truncated = text[:8000]

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"tax-parser-{doc_type}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            system_message="You are a precise JSON data extractor for Indian tax documents. Return ONLY valid JSON.",
        )
        chat.with_model("openai", "gpt-5.2")

        response = await chat.send_message(UserMessage(text=f"{prompt}{truncated}"))

        # Clean response - strip markdown code blocks if present
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        if clean.startswith("json"):
            clean = clean[4:].strip()

        parsed = json.loads(clean)
        logger.info(f"LLM parsed {doc_type} successfully with {len(str(parsed))} chars")
        return parsed
    except Exception as e:
        logger.warning(f"LLM parse fallback failed for {doc_type}: {e}")
        return None


async def ocr_pdf_with_llm(pdf_bytes: bytes, doc_type: str) -> Optional[Dict[str, Any]]:
    """Convert image-based PDF pages to images and use GPT vision for OCR + parsing."""
    try:
        import base64
        from pdf2image import convert_from_bytes
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

        prompts = {
            "form16": LLM_FORM16_PROMPT.replace("PDF TEXT:", "Analyze this Form 16 document image and extract the data:"),
            "form26as": LLM_AIS_PROMPT.replace("PDF TEXT:", "Analyze this Form 26AS / AIS document image and extract the data:"),
            "ais": LLM_AIS_PROMPT.replace("PDF TEXT:", "Analyze this AIS document image and extract the data:"),
            "fd_interest_certificate": LLM_FD_PROMPT.replace("PDF TEXT:", "Analyze this FD certificate image and extract the data:"),
        }
        prompt = prompts.get(doc_type)
        if not prompt:
            return None

        # Convert first 3 pages to images (enough for most tax docs)
        images = convert_from_bytes(pdf_bytes, first_page=1, last_page=3, dpi=150)
        if not images:
            logger.warning("No images extracted from PDF")
            return None

        logger.info(f"OCR: Converted {len(images)} pages to images for {doc_type}")

        # Convert first page to base64 PNG
        buf = io.BytesIO()
        images[0].save(buf, format="PNG", optimize=True)
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"tax-ocr-{doc_type}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            system_message="You are a precise document OCR and data extractor for Indian tax documents. Analyze the image carefully and return ONLY valid JSON.",
        )
        chat.with_model("openai", "gpt-5.2")

        # Send image using ImageContent with base64
        image_content = ImageContent(image_base64=img_b64)
        response = await chat.send_message(
            UserMessage(text=prompt, file_contents=[image_content])
        )

        # Clean response
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        if clean.startswith("json"):
            clean = clean[4:].strip()

        parsed = json.loads(clean)
        logger.info(f"OCR+LLM parsed {doc_type} from image with {len(str(parsed))} chars")
        return parsed
    except ImportError:
        logger.warning("pdf2image not available for OCR")
        return None
    except Exception as e:
        logger.warning(f"OCR+LLM failed for {doc_type}: {e}")
        return None


def merge_llm_into_regex_result(regex_result: Dict, llm_result: Dict, doc_type: str) -> Dict:
    """Merge LLM-extracted data into regex result, filling gaps only."""
    if not llm_result:
        return regex_result

    if doc_type == "form16":
        # Fill missing salary components
        for key, val in llm_result.get("salary_components", {}).items():
            if key not in regex_result.get("salary_components", {}) and val and val > 0:
                regex_result.setdefault("salary_components", {})[key] = val

        # Fill missing deductions
        for key, val in llm_result.get("deductions", {}).items():
            if key not in regex_result.get("deductions", {}) and val and val > 0:
                regex_result.setdefault("deductions", {})[key] = val

        # Fill missing tax computation
        for key, val in llm_result.get("tax_computation", {}).items():
            if key not in regex_result.get("tax_computation", {}) and val and val > 0:
                regex_result.setdefault("tax_computation", {})[key] = val

        # Fill employer info gaps
        for key, val in llm_result.get("employer_info", {}).items():
            if key not in regex_result.get("employer_info", {}) and val:
                regex_result.setdefault("employer_info", {})[key] = val

        # Recalculate summary
        if regex_result.get("salary_components"):
            regex_result["summary"] = {
                "gross_salary": regex_result["salary_components"].get("gross_salary", 0),
                "total_deductions_claimed": sum(regex_result.get("deductions", {}).values()),
                "net_taxable_income": regex_result.get("tax_computation", {}).get("total_taxable_income", 0),
                "total_tds": regex_result.get("tax_computation", {}).get("tds_deducted", 0),
            }

        # Re-evaluate quality
        has_salary = len(regex_result.get("salary_components", {})) >= 2
        has_tax = len(regex_result.get("tax_computation", {})) >= 2
        regex_result["parse_quality"] = "high" if (has_salary and has_tax) else "medium" if has_salary else "low"
        regex_result["llm_enhanced"] = True

    elif doc_type in ("form26as", "ais"):
        # Add TDS entries found by LLM but not regex
        existing_tans = {t.get("deductor_tan", "") for t in regex_result.get("tds_details", [])}
        for entry in llm_result.get("tds_details", []):
            if entry.get("deductor_tan") and entry["deductor_tan"] not in existing_tans:
                regex_result.setdefault("tds_details", []).append(entry)

        # Update summary totals
        if llm_result.get("summary"):
            for key in ("total_tds", "total_interest", "total_dividends"):
                llm_val = llm_result["summary"].get(key, 0)
                regex_val = regex_result.get("summary", {}).get(key, 0)
                if llm_val > regex_val:
                    regex_result.setdefault("summary", {})[key] = llm_val
        regex_result["llm_enhanced"] = True

    elif doc_type == "fd_interest_certificate":
        # Add FD entries from LLM if regex found none
        if not regex_result.get("fd_details") and llm_result.get("fd_details"):
            regex_result["fd_details"] = llm_result["fd_details"]
            regex_result["summary"] = llm_result.get("summary", regex_result.get("summary", {}))
            regex_result["llm_enhanced"] = True

    return regex_result


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
            # Try OCR for image-based PDFs
            logger.info("Form 16 has no extractable text, attempting OCR via LLM vision...")
            ocr_result = await ocr_pdf_with_llm(content, "form16")
            if ocr_result:
                parsed = {
                    "document_type": "form16",
                    "parsed_at": datetime.now(timezone.utc).isoformat(),
                    "employer_info": ocr_result.get("employer_info", {}),
                    "salary_components": ocr_result.get("salary_components", {}),
                    "deductions": ocr_result.get("deductions", {}),
                    "tax_computation": ocr_result.get("tax_computation", {}),
                    "raw_text_length": 0,
                    "ocr_extracted": True,
                    "parse_quality": "medium",
                    "summary": {
                        "gross_salary": ocr_result.get("salary_components", {}).get("gross_salary", 0),
                        "total_deductions_claimed": sum(ocr_result.get("deductions", {}).values()),
                        "net_taxable_income": ocr_result.get("tax_computation", {}).get("total_taxable_income", 0),
                        "total_tds": ocr_result.get("tax_computation", {}).get("tds_deducted", 0),
                    },
                }
            else:
                raise HTTPException(status_code=400, detail="Could not extract text from PDF. The PDF may be scanned/image-based and OCR failed.")
        else:
            # Parse Form 16 with regex
            parsed = parse_form16_pdf(text)
        
        # If parse quality is low, try LLM-powered extraction
        if parsed["parse_quality"] == "low":
            logger.info("Form 16 regex parse quality is low, attempting LLM fallback...")
            llm_result = await llm_parse_document(text, "form16")
            if llm_result:
                parsed = merge_llm_into_regex_result(parsed, llm_result, "form16")
                logger.info(f"LLM enhanced Form 16 parse quality to: {parsed['parse_quality']}")
        
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
            
            if not text.strip() or len(text.strip()) < 50:
                # Image-based PDF — use OCR via LLM vision
                logger.info("AIS/26AS has no extractable text, attempting OCR via LLM vision...")
                ocr_result = await ocr_pdf_with_llm(content, "ais")
                if ocr_result:
                    parsed = {
                        "document_type": "form26as",
                        "parsed_at": datetime.now(timezone.utc).isoformat(),
                        "tds_details": ocr_result.get("tds_details", []),
                        "interest_income": ocr_result.get("interest_income", []),
                        "dividend_income": ocr_result.get("dividend_income", []),
                        "summary": ocr_result.get("summary", {"total_tds": 0}),
                        "ocr_extracted": True,
                    }
                else:
                    parsed = parse_form26as_pdf(text)
            else:
                parsed = parse_form26as_pdf(text)
                # Try LLM enhancement if few entries found
                if len(parsed.get("tds_details", [])) == 0:
                    logger.info("AIS PDF regex found 0 TDS entries, attempting LLM fallback...")
                    llm_result = await llm_parse_document(text, "ais")
                    if llm_result:
                        parsed = merge_llm_into_regex_result(parsed, llm_result, "ais")
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
        
        if not text.strip() or len(text.strip()) < 50:
            # Image-based PDF — use OCR via LLM vision
            logger.info("Form 26AS has no extractable text, attempting OCR via LLM vision...")
            ocr_result = await ocr_pdf_with_llm(content, "form26as")
            if ocr_result:
                parsed = {
                    "document_type": "form26as",
                    "parsed_at": datetime.now(timezone.utc).isoformat(),
                    "tds_details": ocr_result.get("tds_details", []),
                    "interest_income": ocr_result.get("interest_income", []),
                    "dividend_income": ocr_result.get("dividend_income", []),
                    "summary": ocr_result.get("summary", {"total_tds": 0}),
                    "ocr_extracted": True,
                }
            else:
                parsed = parse_form26as_pdf(text)
        else:
            parsed = parse_form26as_pdf(text)
            
            # LLM enhancement if regex found no entries
            if len(parsed.get("tds_details", [])) == 0:
                logger.info("Form 26AS regex found 0 TDS entries, attempting LLM fallback...")
                llm_result = await llm_parse_document(text, "form26as")
                if llm_result:
                    parsed = merge_llm_into_regex_result(parsed, llm_result, "form26as")
        
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
            raise HTTPException(status_code=400, detail="Could not extract text from PDF. The PDF may be scanned/image-based.")
        
        parsed = parse_fd_certificate(text)
        
        # LLM enhancement if regex found no FD entries
        if not parsed.get("fd_details"):
            logger.info("FD cert regex found no entries, attempting LLM fallback...")
            llm_result = await llm_parse_document(text, "fd_interest_certificate")
            if llm_result:
                parsed = merge_llm_into_regex_result(parsed, llm_result, "fd_interest_certificate")
        
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


@router.post("/documents/{document_id}/reparse")
async def reparse_document(document_id: str, user=Depends(get_current_user)):
    """Re-parse an existing document using LLM-powered extraction for better accuracy."""
    doc = await db.tax_documents.find_one(
        {"id": document_id, "user_id": user["id"]},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    parsed = doc.get("parsed_data", {})
    doc_type = doc.get("document_type", "")
    raw_text_len = parsed.get("raw_text_length", 0)  # noqa: F841

    if not doc_type:
        raise HTTPException(status_code=400, detail="Document type unknown, cannot reparse")

    # We need the original text — re-extract is not possible without stored text
    # Instead, use LLM to enhance the already-parsed data
    # Build a text representation from parsed data for LLM to verify/enhance
    text_repr = json.dumps(parsed, indent=2, default=str)

    llm_result = await llm_parse_document(text_repr, doc_type)
    if not llm_result:
        return {
            "status": "no_improvement",
            "message": "LLM could not extract additional data from this document.",
            "document_id": document_id,
        }

    enhanced = merge_llm_into_regex_result(parsed, llm_result, doc_type)

    # Update in database
    await db.tax_documents.update_one(
        {"id": document_id, "user_id": user["id"]},
        {"$set": {
            "parsed_data": enhanced,
            "reparsed_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    return {
        "status": "enhanced",
        "document_id": document_id,
        "llm_enhanced": enhanced.get("llm_enhanced", False),
        "parse_quality": enhanced.get("parse_quality", "unknown"),
        "summary": enhanced.get("summary", {}),
    }


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
