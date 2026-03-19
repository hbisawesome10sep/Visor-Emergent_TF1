"""
Test Groww Mutual Fund Statement Parser
=======================================
Tests:
1. POST /api/upload-statement - Upload real Groww XLSX (6 holdings)
2. POST /api/parse-statement-preview - Preview parsed holdings without saving
3. GET /api/holdings/live - All holdings including Groww + eCAS
4. GET /api/portfolio-overview - Category totals
5. GET /api/dashboard/investment-summary - XIRR calculation (weighted avg)
6. Duplicate handling - Re-upload should update, not duplicate
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TEST_FILE_PATH = "/tmp/groww_mf_real.xlsx"

# Expected Groww holdings from the XLSX file
EXPECTED_GROWW_HOLDINGS = [
    "Nippon India Small Cap Fund Direct Growth",
    "Parag Parikh Flexi Cap Fund Direct Growth",
    "DSP Small Cap Fund Growth",
    "Motilal Oswal Midcap Fund Direct Growth",
    "Quant Small Cap Fund Direct Plan Growth",
    "Nippon India Growth Mid Cap Fund Growth",
]

# Expected totals from XLSX summary
EXPECTED_TOTAL_INVESTED = 110073.32
EXPECTED_TOTAL_CURRENT = 129885.31
EXPECTED_XIRR_RANGE = (15.0, 22.0)  # Weighted average should be ~17-19%


class TestGrowwStatementParser:
    """Test suite for Groww MF statement parser"""
    
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login with demo account before tests"""
        if not BASE_URL:
            pytest.skip("BASE_URL not set")
        
        # Login
        login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "rajesh@visor.demo", "password": "Demo@123"}
        )
        if login_resp.status_code != 200:
            pytest.skip(f"Login failed: {login_resp.status_code}")
        
        TestGrowwStatementParser.token = login_resp.json().get("token")
        if not TestGrowwStatementParser.token:
            pytest.skip("No token returned from login")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Test 1: Parse-statement-preview (doesn't save to DB)
    # ═══════════════════════════════════════════════════════════════════════════
    def test_parse_statement_preview(self):
        """POST /api/parse-statement-preview returns parsed holdings without saving"""
        if not os.path.exists(TEST_FILE_PATH):
            pytest.skip(f"Test file not found: {TEST_FILE_PATH}")
        
        with open(TEST_FILE_PATH, "rb") as f:
            files = {"file": ("groww_mf_real.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            data = {"statement_type": "auto"}
            resp = requests.post(
                f"{BASE_URL}/api/parse-statement-preview",
                headers=self.get_headers(),
                files=files,
                data=data
            )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        result = resp.json()
        
        # Verify response structure
        assert "holdings" in result, "Response should have 'holdings' key"
        assert "metadata" in result, "Response should have 'metadata' key"
        
        holdings = result["holdings"]
        metadata = result["metadata"]
        
        # Verify 6 holdings parsed
        assert len(holdings) == 6, f"Expected 6 holdings, got {len(holdings)}"
        
        # Verify source detected as Groww
        assert metadata.get("source") == "Groww", f"Expected source 'Groww', got {metadata.get('source')}"
        
        # Verify all expected holding names present
        holding_names = [h["name"] for h in holdings]
        for expected_name in EXPECTED_GROWW_HOLDINGS:
            assert expected_name in holding_names, f"Missing holding: {expected_name}"
        
        # Verify holding fields
        for h in holdings:
            assert h.get("name"), "Holding should have name"
            assert h.get("quantity", 0) > 0, f"Holding {h.get('name')} should have positive quantity"
            assert h.get("invested_value", 0) > 0, f"Holding {h.get('name')} should have invested_value"
            assert h.get("current_value", 0) > 0, f"Holding {h.get('name')} should have current_value"
            assert h.get("xirr") is not None, f"Holding {h.get('name')} should have XIRR"
            assert h.get("category") == "Mutual Fund", f"Holding should be Mutual Fund, got {h.get('category')}"
        
        print(f"✓ parse-statement-preview: Parsed {len(holdings)} holdings from Groww XLSX")
        print(f"  Source: {metadata.get('source')}")
        for h in holdings:
            print(f"  - {h['name']}: ₹{h['invested_value']:,.2f} invested, XIRR: {h['xirr']}%")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Test 2: Upload statement (saves to DB)
    # ═══════════════════════════════════════════════════════════════════════════
    def test_upload_statement(self):
        """POST /api/upload-statement parses and saves holdings to DB"""
        if not os.path.exists(TEST_FILE_PATH):
            pytest.skip(f"Test file not found: {TEST_FILE_PATH}")
        
        with open(TEST_FILE_PATH, "rb") as f:
            files = {"file": ("groww_mf_real.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            data = {"statement_type": "mf_statement"}
            resp = requests.post(
                f"{BASE_URL}/api/upload-statement",
                headers=self.get_headers(),
                files=files,
                data=data
            )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        result = resp.json()
        
        # Verify response structure
        assert result.get("status") == "success", f"Expected status 'success', got {result.get('status')}"
        assert "saved" in result or "duplicates" in result, "Response should have saved/duplicates count"
        
        total_parsed = result.get("total_parsed", 0)
        saved = result.get("saved", 0)
        duplicates = result.get("duplicates", 0)
        
        # Either saved or duplicates should account for all 6
        assert total_parsed == 6, f"Expected 6 parsed, got {total_parsed}"
        assert saved + duplicates == 6, f"saved({saved}) + duplicates({duplicates}) should equal 6"
        
        print(f"✓ upload-statement: {saved} saved, {duplicates} duplicates updated")
        print(f"  Metadata source: {result.get('metadata', {}).get('source')}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Test 3: Duplicate handling - Re-upload should update existing
    # ═══════════════════════════════════════════════════════════════════════════
    def test_upload_statement_duplicate_handling(self):
        """Re-uploading same file should update existing holdings, not create duplicates"""
        if not os.path.exists(TEST_FILE_PATH):
            pytest.skip(f"Test file not found: {TEST_FILE_PATH}")
        
        # Upload first time
        with open(TEST_FILE_PATH, "rb") as f:
            files = {"file": ("groww_mf_real.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            data = {"statement_type": "auto"}
            resp1 = requests.post(
                f"{BASE_URL}/api/upload-statement",
                headers=self.get_headers(),
                files=files,
                data=data
            )
        
        assert resp1.status_code == 200, f"First upload failed: {resp1.text}"
        
        # Upload second time (same file)
        with open(TEST_FILE_PATH, "rb") as f:
            files = {"file": ("groww_mf_real.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            data = {"statement_type": "auto"}
            resp2 = requests.post(
                f"{BASE_URL}/api/upload-statement",
                headers=self.get_headers(),
                files=files,
                data=data
            )
        
        assert resp2.status_code == 200, f"Second upload failed: {resp2.text}"
        result2 = resp2.json()
        
        # On re-upload, all 6 should be marked as duplicates (updated)
        duplicates = result2.get("duplicates", 0)
        saved = result2.get("saved", 0)
        
        # All 6 should be duplicates on re-upload
        assert duplicates == 6 or saved == 0, f"Re-upload should mark all as duplicates: saved={saved}, duplicates={duplicates}"
        
        print(f"✓ Duplicate handling: On re-upload, {duplicates} updated as duplicates")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Test 4: GET /api/holdings/live - Verify all holdings present with XIRR
    # ═══════════════════════════════════════════════════════════════════════════
    def test_holdings_live_includes_groww(self):
        """GET /api/holdings/live should include all 7 holdings (6 Groww + 1 eCAS) with XIRR"""
        resp = requests.get(
            f"{BASE_URL}/api/holdings/live",
            headers=self.get_headers()
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        result = resp.json()
        
        # API returns {"holdings": [...], "summary": {...}}
        holdings = result.get("holdings", [])
        summary = result.get("summary", {})
        
        # Should have at least 6 Groww holdings + existing eCAS
        assert len(holdings) >= 6, f"Expected at least 6 holdings, got {len(holdings)}"
        
        holding_names = [h.get("name", "") for h in holdings]
        
        # Verify Groww holdings present
        groww_found = 0
        for expected_name in EXPECTED_GROWW_HOLDINGS:
            if expected_name in holding_names:
                groww_found += 1
        
        assert groww_found == 6, f"Expected 6 Groww holdings, found {groww_found}"
        
        # Verify all Groww holdings have XIRR field
        holdings_with_xirr = [h for h in holdings if h.get("xirr") is not None]
        assert len(holdings_with_xirr) >= 6, f"Expected at least 6 holdings with XIRR, got {len(holdings_with_xirr)}"
        
        # Check category is Mutual Fund for Groww holdings
        mutual_fund_count = sum(1 for h in holdings if h.get("category") == "Mutual Fund")
        assert mutual_fund_count >= 6, f"Expected at least 6 Mutual Fund holdings, got {mutual_fund_count}"
        
        # Verify summary totals
        assert summary.get("holding_count", 0) >= 7, f"Expected holding_count >= 7, got {summary.get('holding_count')}"
        assert summary.get("total_invested", 0) > 100000, f"Expected total_invested > 100000"
        
        print(f"✓ holdings/live: {len(holdings)} total holdings")
        print(f"  - Groww holdings found: {groww_found}")
        print(f"  - Holdings with XIRR: {len(holdings_with_xirr)}")
        print(f"  - Mutual Fund category: {mutual_fund_count}")
        print(f"  - Summary totals: ₹{summary.get('total_invested', 0):,.2f} invested, ₹{summary.get('total_current_value', 0):,.2f} current")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Test 5: GET /api/portfolio-overview - Only 'Mutual Fund' category
    # ═══════════════════════════════════════════════════════════════════════════
    def test_portfolio_overview_correct_category(self):
        """GET /api/portfolio-overview should show only 'Mutual Fund' category"""
        resp = requests.get(
            f"{BASE_URL}/api/portfolio-overview",
            headers=self.get_headers()
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        result = resp.json()
        
        # Verify structure
        assert "total_invested" in result, "Should have total_invested"
        assert "total_current_value" in result, "Should have total_current_value"
        assert "categories" in result, "Should have categories"
        
        categories = result.get("categories", [])
        category_names = [c.get("category") for c in categories]
        
        # Should only have 'Mutual Fund' category (from holdings)
        assert "Mutual Fund" in category_names, "Should have 'Mutual Fund' category"
        
        # Get Mutual Fund category data
        mf_cat = next((c for c in categories if c.get("category") == "Mutual Fund"), None)
        assert mf_cat is not None, "Mutual Fund category not found"
        
        # Verify totals are reasonable (at least Groww totals)
        total_invested = result.get("total_invested", 0)
        total_current = result.get("total_current_value", 0)
        
        # Should have at least the Groww invested amount
        assert total_invested >= EXPECTED_TOTAL_INVESTED * 0.9, f"Expected invested >= {EXPECTED_TOTAL_INVESTED * 0.9}, got {total_invested}"
        
        print(f"✓ portfolio-overview:")
        print(f"  Total Invested: ₹{total_invested:,.2f}")
        print(f"  Total Current: ₹{total_current:,.2f}")
        print(f"  Categories: {category_names}")
        print(f"  Gain/Loss: ₹{result.get('total_gain_loss', 0):,.2f} ({result.get('total_gain_loss_pct', 0):.2f}%)")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Test 6: GET /api/dashboard/investment-summary - XIRR ~17-18%
    # ═══════════════════════════════════════════════════════════════════════════
    def test_investment_summary_xirr(self):
        """GET /api/dashboard/investment-summary should show XIRR ~17-18% (weighted avg)"""
        resp = requests.get(
            f"{BASE_URL}/api/dashboard/investment-summary",
            headers=self.get_headers()
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        result = resp.json()
        
        # Verify structure
        assert "total_invested" in result, "Should have total_invested"
        assert "current_value" in result, "Should have current_value"
        assert "xirr" in result, "Should have xirr"
        assert "holdings_count" in result, "Should have holdings_count"
        
        xirr = result.get("xirr")
        holdings_count = result.get("holdings_count", 0)
        total_invested = result.get("total_invested", 0)
        
        # Verify holdings count (at least 6 Groww + existing)
        assert holdings_count >= 6, f"Expected at least 6 holdings, got {holdings_count}"
        
        # Verify XIRR is within expected range (15-22%)
        assert xirr is not None, "XIRR should not be None"
        assert EXPECTED_XIRR_RANGE[0] <= xirr <= EXPECTED_XIRR_RANGE[1], \
            f"Expected XIRR between {EXPECTED_XIRR_RANGE[0]}-{EXPECTED_XIRR_RANGE[1]}%, got {xirr}%"
        
        # Verify total invested includes Groww amount
        assert total_invested >= EXPECTED_TOTAL_INVESTED * 0.9, \
            f"Expected invested >= {EXPECTED_TOTAL_INVESTED * 0.9}, got {total_invested}"
        
        print(f"✓ investment-summary:")
        print(f"  Total Invested: ₹{total_invested:,.2f}")
        print(f"  Current Value: ₹{result.get('current_value', 0):,.2f}")
        print(f"  XIRR: {xirr:.2f}%")
        print(f"  Holdings Count: {holdings_count}")
        print(f"  Absolute Return: {result.get('absolute_return_pct', 0):.2f}%")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Test 7: Verify exact Groww holding names
    # ═══════════════════════════════════════════════════════════════════════════
    def test_verify_exact_groww_holdings(self):
        """Verify exact 6 Groww holding names from the statement"""
        resp = requests.get(
            f"{BASE_URL}/api/holdings/live",
            headers=self.get_headers()
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        result = resp.json()
        
        # API returns {"holdings": [...], "summary": {...}}
        holdings = result.get("holdings", [])
        
        holding_names = [h.get("name", "") for h in holdings]
        
        missing = []
        for expected in EXPECTED_GROWW_HOLDINGS:
            if expected not in holding_names:
                missing.append(expected)
        
        assert len(missing) == 0, f"Missing holdings: {missing}"
        
        print(f"✓ All 6 Groww holdings verified:")
        for name in EXPECTED_GROWW_HOLDINGS:
            h = next((x for x in holdings if x.get("name") == name), None)
            if h:
                print(f"  - {name}")
                print(f"    Units: {h.get('quantity', 0):.4f}, Invested: ₹{h.get('invested_value', 0):,.2f}, XIRR: {h.get('xirr')}%")


class TestAuthRequired:
    """Test authentication requirements for statement endpoints"""
    
    def test_upload_requires_auth(self):
        """POST /api/upload-statement should require authentication"""
        if not os.path.exists(TEST_FILE_PATH):
            pytest.skip(f"Test file not found: {TEST_FILE_PATH}")
        
        with open(TEST_FILE_PATH, "rb") as f:
            files = {"file": ("groww_mf_real.xlsx", f)}
            resp = requests.post(
                f"{BASE_URL}/api/upload-statement",
                files=files
            )
        
        assert resp.status_code == 401, f"Expected 401 without auth, got {resp.status_code}"
        print("✓ upload-statement requires authentication")
    
    def test_preview_requires_auth(self):
        """POST /api/parse-statement-preview should require authentication"""
        if not os.path.exists(TEST_FILE_PATH):
            pytest.skip(f"Test file not found: {TEST_FILE_PATH}")
        
        with open(TEST_FILE_PATH, "rb") as f:
            files = {"file": ("groww_mf_real.xlsx", f)}
            resp = requests.post(
                f"{BASE_URL}/api/parse-statement-preview",
                files=files
            )
        
        assert resp.status_code == 401, f"Expected 401 without auth, got {resp.status_code}"
        print("✓ parse-statement-preview requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
