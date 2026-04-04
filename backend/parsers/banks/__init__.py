"""
Bank-specific PDF parsers module.
Each bank has its own file for better maintainability.
"""
from parsers.banks.icici import parse_icici_pdf_text
from parsers.banks.sbi import parse_sbi_pdf
from parsers.banks.axis import parse_axis_pdf
from parsers.banks.indusind import parse_indusind_pdf
from parsers.banks.yesbank import parse_yesbank_pdf
from parsers.banks.kotak import parse_kotak_pdf
from parsers.banks.bob import parse_bob_pdf
from parsers.banks.union import parse_union_pdf
from parsers.banks.canara import parse_canara_pdf
from parsers.banks.idbi import parse_idbi_pdf
from parsers.banks.pnb import parse_pnb_pdf
from parsers.banks.hdfc import parse_hdfc_pdf

__all__ = [
    'parse_icici_pdf_text',
    'parse_sbi_pdf',
    'parse_axis_pdf',
    'parse_indusind_pdf',
    'parse_yesbank_pdf',
    'parse_kotak_pdf',
    'parse_bob_pdf',
    'parse_union_pdf',
    'parse_canara_pdf',
    'parse_idbi_pdf',
    'parse_pnb_pdf',
    'parse_hdfc_pdf',
]
