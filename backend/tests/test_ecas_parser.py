"""Tests for eCAS parser invested_value calculation."""
import pytest
from routes.holdings import _parse_cas_text


ECAS_TEXT_SIMPLE = """
AMC Name : HDFC Mutual Fund
Scheme Name : HDFC Flexi Cap Fund - Direct Plan - Growth Option Scheme Code : 02T
ISIN : INF179K01UT0 UCC : MFHDFC0019 RTA : CAMS

HDFC Mutual Fund
02T - HDFC Flexi Cap Fund - Direct Plan - Growth Option
ISIN : INF179K01UT0 UCC : MFHDFC0019
Opening Balance 7.166
SIP Purchase-BSE -
Instalment No - 3/999 -
29-12-2025 999.95 2251.607 2251.607 .444 .05 0 0
Closing Balance 7.61
"""

ECAS_TEXT_MULTI_TXN = """
AMC Name : SBI Mutual Fund
Scheme Name : SBI Small Cap Fund - Direct Plan - Growth Scheme Code : SC1
ISIN : INF200K01RQ0 UCC : MFSBI0023 RTA : CAMS

SBI Mutual Fund
SC1 - SBI Small Cap Fund - Direct Plan - Growth
ISIN : INF200K01RQ0 UCC : MFSBI0023
Opening Balance 0.0
Purchase -
15-11-2025 5000.00 126.200 126.200 39.620 .25 0 0
SIP Purchase-BSE -
Instalment No - 2/999 -
15-12-2025 5000.00 130.500 130.500 38.314 .25 0 0
Closing Balance 77.934
"""

ECAS_TEXT_NO_OPENING = """
AMC Name : Axis Mutual Fund
Scheme Name : Axis Bluechip Fund - Direct Plan - Growth Scheme Code : AX1
ISIN : INF846K01DP8 UCC : MFAXIS001 RTA : CAMS

Axis Mutual Fund
AX1 - Axis Bluechip Fund - Direct Plan - Growth
ISIN : INF846K01DP8 UCC : MFAXIS001
Purchase -
01-10-2025 10000.00 55.500 55.500 180.180 .50 0 0
Closing Balance 180.18
"""


def test_invested_value_with_opening_balance():
    """Opening balance units valued at first NAV + purchase amount."""
    holdings, sips = _parse_cas_text(ECAS_TEXT_SIMPLE)
    assert len(holdings) == 1
    h = holdings[0]
    assert h["isin"] == "INF179K01UT0"
    assert h["quantity"] == 7.61
    expected_opening_cost = round(7.166 * 2251.607, 2)
    expected_invested = round(999.95 + expected_opening_cost, 2)
    assert h["invested_value"] == expected_invested
    assert h["invested_value"] != h["current_value"]


def test_invested_value_multiple_purchases():
    """Multiple purchases with no opening balance should sum amounts."""
    holdings, sips = _parse_cas_text(ECAS_TEXT_MULTI_TXN)
    assert len(holdings) == 1
    h = holdings[0]
    assert h["isin"] == "INF200K01RQ0"
    assert h["invested_value"] == 10000.0
    assert h["current_value"] == round(77.934 * 130.5, 2)
    assert h["invested_value"] != h["current_value"]


def test_invested_value_no_opening_balance():
    """Single purchase with no opening balance."""
    holdings, _ = _parse_cas_text(ECAS_TEXT_NO_OPENING)
    assert len(holdings) == 1
    h = holdings[0]
    assert h["invested_value"] == 10000.0
    assert h["current_value"] == round(180.18 * 55.5, 2)
    assert h["invested_value"] != h["current_value"]


def test_sip_detection():
    """SIP keywords should flag funds correctly."""
    holdings, sips = _parse_cas_text(ECAS_TEXT_SIMPLE)
    assert len(sips) == 1
    assert "HDFC Flexi Cap" in sips[0]
    assert holdings[0]["is_sip"] is True


def test_empty_text():
    """Empty or invalid text returns no holdings."""
    holdings, sips = _parse_cas_text("")
    assert len(holdings) == 0
    assert len(sips) == 0
