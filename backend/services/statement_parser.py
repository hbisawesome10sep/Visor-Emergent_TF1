"""
Statement Parser — Intelligent XLSX parser for Groww & Zerodha
Handles: Stock holdings, Mutual Fund holdings from various export formats.
"""
import re
import logging
from datetime import datetime, timezone
from typing import Optional
from openpyxl import load_workbook

logger = logging.getLogger(__name__)

# ── Column pattern matching ──────────────────────────────────────────────────
# Each pattern is a tuple: (field_name, list_of_regex_patterns)
_COL_PATTERNS = {
    "name": [
        r"(?:company|stock|scrip|instrument|fund|scheme|security|isin)\s*name",
        r"^name$", r"^instrument$", r"^scrip$", r"^company$", r"^scheme$",
        r"^stock$", r"^security$", r"^fund$",
    ],
    "ticker": [
        r"(?:nse|bse)?\s*(?:symbol|ticker|code|scrip\s*code)",
        r"^symbol$", r"^trading\s*symbol$", r"^nse\s*symbol$",
    ],
    "isin": [r"^isin", r"isin\s*(?:no|number|code)?"],
    "quantity": [
        r"^(?:qty|quantity|units|unit|balance|holding\s*qty|no\.?\s*of\s*shares)",
        r"(?:current|free)\s*balance", r"^shares$", r"^units$",
    ],
    "buy_price": [
        r"(?:avg|average|weighted\s*avg)\.?\s*(?:cost|price|nav|buy\s*price|rate)",
        r"^buy\s*(?:avg|price|rate)$", r"^avg\.?\s*cost$", r"^purchase\s*price$",
        r"^cost\s*price$", r"^avg\.?\s*nav$", r"^invested\s*nav$",
    ],
    "current_price": [
        r"(?:ltp|cmp|current|present|last|mkt|market)[\s_]*(?:price|value|nav|rate)?",
        r"^ltp$", r"^cmp$", r"^nav$", r"^current\s*nav$", r"^closing\s*price$",
    ],
    "invested_value": [
        r"(?:invested?|cost|buy)\s*(?:value|amount|total)",
        r"^invested$", r"^cost\s*value$", r"^investment$",
    ],
    "current_value": [
        r"(?:current|present|market|mkt)\s*(?:value|val|amount)",
        r"^cur\.?\s*val\.?$", r"^present\s*value$",
    ],
    "pnl": [
        r"(?:p\s*&?\s*l|profit|gain|unrealised|unrealized)",
        r"^pnl$", r"^returns?$",
    ],
    "buy_date": [
        r"(?:buy|purchase|trade|transaction)\s*date",
        r"^date$",
    ],
    "folio": [r"folio\s*(?:no|number)?", r"^folio$"],
    "exchange": [r"^exchange$", r"^exch$"],
    "sector": [r"^sector$", r"^industry$"],
}


def _match_col(header: str) -> Optional[str]:
    """Match a column header to a known field name."""
    h = header.strip().lower()
    for field, patterns in _COL_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, h, re.IGNORECASE):
                return field
    return None


def _detect_source(headers: list[str], sheet_name: str) -> str:
    """Detect if the statement is from Groww, Zerodha, or unknown."""
    all_text = " ".join(headers).lower() + " " + sheet_name.lower()
    if "groww" in all_text:
        return "Groww"
    if "zerodha" in all_text or "console" in all_text or "kite" in all_text:
        return "Zerodha"
    return "Unknown"


def _detect_category(name: str, ticker: str, isin: str, sheet_name: str, statement_type: str) -> str:
    """Detect if a holding is Stock or Mutual Fund."""
    if statement_type == "mf_statement":
        return "Mutual Fund"
    if statement_type == "stock_statement":
        return "Stock"
    # Auto-detect from data
    name_lower = name.lower()
    if any(kw in name_lower for kw in ["fund", "scheme", "nifty", "sensex", "index", "growth", "direct", "regular", "flexi", "cap fund", "debt fund", "hybrid"]):
        return "Mutual Fund"
    if isin and isin.startswith("INF"):
        return "Mutual Fund"
    return "Stock"


def _to_float(val) -> float:
    """Safely convert a cell value to float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("₹", "").replace("Rs", "").replace("INR", "").strip()
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def _to_str(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _build_ticker(name: str, ticker: str, isin: str, category: str) -> str:
    """Build a Yahoo Finance compatible ticker."""
    if ticker:
        t = ticker.strip().upper().replace(" ", "")
        if not t.endswith(".NS") and not t.endswith(".BO") and category == "Stock":
            t = f"{t}.NS"
        return t
    # Try to extract from name
    if category == "Mutual Fund" and isin:
        return isin
    return ""


def parse_holdings_xlsx(file_bytes: bytes, statement_type: str = "auto", filename: str = "") -> dict:
    """
    Parse an XLSX file and extract holdings.
    
    Args:
        file_bytes: Raw bytes of the XLSX file
        statement_type: 'stock_statement', 'mf_statement', or 'auto'
        filename: Original filename for source detection
    
    Returns:
        dict with 'holdings' list and 'metadata'
    """
    import io
    wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    
    all_holdings = []
    metadata = {
        "source": "Unknown",
        "sheets_parsed": [],
        "total_rows_scanned": 0,
        "parse_errors": [],
    }
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        
        # Find header row (scan first 20 rows)
        header_row_idx = None
        col_map = {}
        
        for i, row in enumerate(rows[:20]):
            if not row:
                continue
            headers = [_to_str(c) for c in row]
            temp_map = {}
            for j, h in enumerate(headers):
                if not h:
                    continue
                field = _match_col(h)
                if field and field not in temp_map:
                    temp_map[field] = j
            
            # Need at least 'name' or 'isin' + one of quantity/invested_value
            has_identifier = "name" in temp_map or "isin" in temp_map
            has_value = "quantity" in temp_map or "invested_value" in temp_map or "current_value" in temp_map
            if has_identifier and has_value:
                header_row_idx = i
                col_map = temp_map
                source = _detect_source(headers, sheet_name)
                if source != "Unknown":
                    metadata["source"] = source
                break
        
        if header_row_idx is None:
            # Try scanning for "ISIN" pattern in cells
            for i, row in enumerate(rows[:20]):
                for j, cell in enumerate(row or []):
                    if cell and "isin" in str(cell).lower():
                        # This might be a merged header — try next row
                        pass
            continue
        
        metadata["sheets_parsed"].append(sheet_name)
        
        # Parse data rows
        for row in rows[header_row_idx + 1:]:
            if not row:
                continue
            metadata["total_rows_scanned"] += 1
            
            def get(field):
                idx = col_map.get(field)
                return row[idx] if idx is not None and idx < len(row) else None
            
            name = _to_str(get("name"))
            isin = _to_str(get("isin"))
            ticker = _to_str(get("ticker"))
            quantity = _to_float(get("quantity"))
            buy_price = _to_float(get("buy_price"))
            current_price = _to_float(get("current_price"))
            invested_value = _to_float(get("invested_value"))
            current_value = _to_float(get("current_value"))
            buy_date_raw = get("buy_date")
            
            # Skip empty/invalid rows
            if not name and not isin:
                continue
            if quantity <= 0 and invested_value <= 0:
                continue
            
            # Determine category
            category = _detect_category(name, ticker, isin, sheet_name, statement_type)
            
            # Build ticker
            final_ticker = _build_ticker(name, ticker, isin, category)
            
            # Calculate missing values
            if invested_value <= 0 and quantity > 0 and buy_price > 0:
                invested_value = round(quantity * buy_price, 2)
            if buy_price <= 0 and invested_value > 0 and quantity > 0:
                buy_price = round(invested_value / quantity, 2)
            if current_value <= 0 and quantity > 0 and current_price > 0:
                current_value = round(quantity * current_price, 2)
            
            # Handle buy date
            buy_date_str = ""
            if buy_date_raw:
                if isinstance(buy_date_raw, datetime):
                    buy_date_str = buy_date_raw.strftime("%Y-%m-%d")
                else:
                    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%d %b %Y"]:
                        try:
                            buy_date_str = datetime.strptime(str(buy_date_raw).strip(), fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
            
            holding = {
                "name": name or isin,
                "ticker": final_ticker,
                "isin": isin,
                "category": category,
                "quantity": round(quantity, 4),
                "buy_price": round(buy_price, 2),
                "buy_date": buy_date_str,
                "invested_value": round(invested_value, 2),
                "current_price": round(current_price, 2) if current_price > 0 else None,
                "current_value": round(current_value, 2) if current_value > 0 else None,
            }
            all_holdings.append(holding)
    
    wb.close()
    
    # Detect source from filename if not found in sheet
    if metadata["source"] == "Unknown":
        fn = filename.lower()
        if "groww" in fn:
            metadata["source"] = "Groww"
        elif "zerodha" in fn or "console" in fn or "kite" in fn:
            metadata["source"] = "Zerodha"
    
    metadata["holdings_found"] = len(all_holdings)
    
    logger.info(f"Parsed {filename}: source={metadata['source']}, "
                f"sheets={metadata['sheets_parsed']}, "
                f"holdings={len(all_holdings)}, "
                f"rows_scanned={metadata['total_rows_scanned']}")
    
    return {"holdings": all_holdings, "metadata": metadata}
