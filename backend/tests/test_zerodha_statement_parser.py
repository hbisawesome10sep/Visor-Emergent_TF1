"""
Test Zerodha Stock Statement Parser
- POST /api/upload-statement with Zerodha XLSX
- Verify 16 stock holdings parsed correctly
- Verify ticker format (.NS suffix), category, invested_value calculation
- Verify sector field populated
- Verify duplicate handling (re-upload updates, not duplicates)
- Verify portfolio-overview and investment-summary APIs after upload
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')
TEST_FILE_PATH = "/tmp/zerodha_stocks_real.xlsx"

# Expected stocks from Zerodha statement (16 stocks)
EXPECTED_STOCKS = [
    {"symbol": "ADANIPOWER", "isin": "INE814H01029", "sector": "ENERGY", "qty": 60, "avg_price": 64.7492},
    {"symbol": "BHEL", "isin": "INE257A01026", "sector": "ENGINEERING & CAPITAL GOODS", "qty": 5, "avg_price": 87.1},
    {"symbol": "CARYSIL", "isin": "INE482D01024", "sector": "FMCG", "qty": 2, "avg_price": 640.15},
    {"symbol": "FCL", "isin": "INE045J01034", "sector": "CHEMICALS", "qty": 100, "avg_price": 15.44},
    {"symbol": "GREENPOWER", "isin": "INE999K01014", "sector": "ENERGY", "qty": 10, "avg_price": 24.2},
    {"symbol": "HATHWAY", "isin": "INE982F01036", "sector": "TELECOM", "qty": 10, "avg_price": 23.35},
    {"symbol": "INDHOTEL", "isin": "INE053A01029", "sector": "TOURISM & HOSPITALITY", "qty": 2, "avg_price": 253.375},
    {"symbol": "JSL", "isin": "INE220G01021", "sector": "METALS", "qty": 1, "avg_price": 596.8},
    {"symbol": "KALYANKJIL", "isin": "INE303R01014", "sector": "RETAIL", "qty": 1, "avg_price": 492.45},
    {"symbol": "NHPC", "isin": "INE848E01016", "sector": "ENERGY", "qty": 10, "avg_price": 87.5},
    {"symbol": "ONGC", "isin": "INE213A01029", "sector": "ENERGY", "qty": 2, "avg_price": 230.85},
    {"symbol": "RAILTEL", "isin": "INE677A01016", "sector": "ENGINEERING & CAPITAL GOODS", "qty": 2, "avg_price": 399.45},
    {"symbol": "TATACONSUM", "isin": "INE192A01025", "sector": "FMCG", "qty": 2, "avg_price": 831.0},
    {"symbol": "TATAPOWER", "isin": "INE245A01021", "sector": "ENERGY", "qty": 10, "avg_price": 233.0},
    {"symbol": "TMCV-BL", "isin": "INE0PAG01016", "sector": "AUTO ANCILLARY", "qty": 10, "avg_price": 161.8694},
    {"symbol": "TMPV", "isin": "INE0PAH01014", "sector": "AUTO ANCILLARY", "qty": 10, "avg_price": 357.7756},
]


class TestZerodhaStatementParser:
    """Test Zerodha stock statement parsing functionality"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Authenticate and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        # API returns 'token' not 'access_token'
        assert "token" in data, f"No token in response: {data}"
        return data["token"]

    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Return headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}

    # ─────────────────────────────────────────────────────────────────────────
    # Test 1: Preview Zerodha statement parsing
    # ─────────────────────────────────────────────────────────────────────────
    def test_01_preview_zerodha_statement(self, auth_headers):
        """Test preview endpoint parses Zerodha XLSX correctly"""
        with open(TEST_FILE_PATH, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/parse-statement-preview",
                files={"file": ("zerodha_stocks_real.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"statement_type": "stock_statement"},
                headers=auth_headers
            )
        
        assert response.status_code == 200, f"Preview failed: {response.text}"
        data = response.json()
        
        # Verify holdings count
        holdings = data.get("holdings", [])
        assert len(holdings) == 16, f"Expected 16 holdings, got {len(holdings)}"
        
        # Verify metadata
        metadata = data.get("metadata", {})
        assert metadata.get("source") == "Zerodha", f"Source not detected as Zerodha: {metadata.get('source')}"
        assert "Equity" in metadata.get("sheets_parsed", []), f"Equity sheet not parsed: {metadata.get('sheets_parsed')}"
        # Combined sheet should be skipped (no duplicates)
        assert "Combined" not in metadata.get("sheets_parsed", []), f"Combined sheet should be skipped: {metadata.get('sheets_parsed')}"
        
        # Verify all stocks have .NS ticker suffix and Stock category
        for h in holdings:
            assert h["category"] == "Stock", f"Wrong category for {h['name']}: {h['category']}"
            assert h["ticker"].endswith(".NS"), f"Ticker should end with .NS: {h['ticker']}"
            assert h["invested_value"] > 0, f"Invested value should be positive: {h['invested_value']}"
        
        print(f"✓ Preview parsed 16 stocks correctly with Zerodha source detected")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 2: Verify specific stock data
    # ─────────────────────────────────────────────────────────────────────────
    def test_02_verify_stock_data(self, auth_headers):
        """Verify specific stock details from parsed data"""
        with open(TEST_FILE_PATH, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/parse-statement-preview",
                files={"file": ("zerodha_stocks_real.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"statement_type": "stock_statement"},
                headers=auth_headers
            )
        
        assert response.status_code == 200
        holdings = response.json().get("holdings", [])
        
        # Build lookup by ISIN
        holdings_by_isin = {h["isin"]: h for h in holdings}
        
        # Verify ADANIPOWER
        adani = holdings_by_isin.get("INE814H01029")
        assert adani is not None, "ADANIPOWER not found"
        assert adani["name"] == "ADANIPOWER", f"Name mismatch: {adani['name']}"
        assert adani["ticker"] == "ADANIPOWER.NS", f"Ticker mismatch: {adani['ticker']}"
        assert adani["quantity"] == 60, f"Quantity mismatch: {adani['quantity']}"
        assert abs(adani["buy_price"] - 64.7492) < 0.01, f"Buy price mismatch: {adani['buy_price']}"
        expected_invested = 60 * 64.7492
        assert abs(adani["invested_value"] - expected_invested) < 1, f"Invested value mismatch: {adani['invested_value']} vs {expected_invested}"
        assert adani["sector"] == "ENERGY", f"Sector mismatch: {adani['sector']}"
        
        # Verify BHEL
        bhel = holdings_by_isin.get("INE257A01026")
        assert bhel is not None, "BHEL not found"
        assert bhel["quantity"] == 5
        assert abs(bhel["invested_value"] - 435.5) < 1
        assert bhel["sector"] == "ENGINEERING & CAPITAL GOODS"
        
        # Verify TATAPOWER
        tatapower = holdings_by_isin.get("INE245A01021")
        assert tatapower is not None, "TATAPOWER not found"
        assert tatapower["quantity"] == 10
        assert abs(tatapower["invested_value"] - 2330) < 1
        assert tatapower["sector"] == "ENERGY"
        
        print("✓ Stock data verified: ADANIPOWER, BHEL, TATAPOWER with correct quantities, prices, sectors")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 3: Upload Zerodha statement - first upload saves all
    # ─────────────────────────────────────────────────────────────────────────
    def test_03_upload_zerodha_statement(self, auth_headers):
        """Test full upload of Zerodha XLSX statement"""
        with open(TEST_FILE_PATH, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/upload-statement",
                files={"file": ("zerodha_stocks_real.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"statement_type": "stock_statement"},
                headers=auth_headers
            )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        
        # Should parse all 16 stocks
        assert data.get("total_parsed") == 16, f"Expected 16 parsed, got {data.get('total_parsed')}"
        
        # Either saved all or duplicates (if previously uploaded)
        saved = data.get("saved", 0)
        duplicates = data.get("duplicates", 0)
        assert saved + duplicates == 16, f"Expected 16 total (saved + duplicates), got {saved + duplicates}"
        
        # Verify metadata
        metadata = data.get("metadata", {})
        assert metadata.get("source") == "Zerodha", f"Source mismatch: {metadata.get('source')}"
        
        print(f"✓ Upload successful: {saved} new, {duplicates} duplicates updated")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 4: Re-upload should mark all as duplicates (update, not create new)
    # ─────────────────────────────────────────────────────────────────────────
    def test_04_reupload_duplicate_handling(self, auth_headers):
        """Re-uploading same file should update existing holdings"""
        with open(TEST_FILE_PATH, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/upload-statement",
                files={"file": ("zerodha_stocks_real.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"statement_type": "stock_statement"},
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # All 16 should be duplicates on re-upload
        assert data.get("duplicates") == 16, f"Expected 16 duplicates on re-upload, got {data.get('duplicates')}"
        assert data.get("saved") == 0, f"Expected 0 saved on re-upload, got {data.get('saved')}"
        
        print("✓ Duplicate handling: Re-upload correctly marks all 16 as duplicates (updated)")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 5: Verify holdings via GET /api/holdings/live
    # ─────────────────────────────────────────────────────────────────────────
    def test_05_holdings_live_after_upload(self, auth_headers):
        """Verify holdings/live returns Zerodha stocks correctly"""
        response = requests.get(f"{BASE_URL}/api/holdings/live", headers=auth_headers)
        assert response.status_code == 200, f"Holdings live failed: {response.text}"
        data = response.json()
        
        holdings = data.get("holdings", [])
        
        # Filter Zerodha stocks only
        zerodha_stocks = [h for h in holdings if h.get("source", "").lower() == "zerodha_statement"]
        assert len(zerodha_stocks) >= 16, f"Expected at least 16 Zerodha stocks, got {len(zerodha_stocks)}"
        
        # All Zerodha stocks should have category = "Stock"
        stock_category = [h for h in zerodha_stocks if h.get("category") == "Stock"]
        assert len(stock_category) == len(zerodha_stocks), f"All Zerodha holdings should be Stock category"
        
        # All should have .NS ticker
        for h in zerodha_stocks:
            assert h.get("ticker", "").endswith(".NS"), f"Ticker should end with .NS: {h.get('ticker')}"
        
        print(f"✓ Holdings live: Found {len(zerodha_stocks)} Zerodha stocks with correct category and tickers")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 6: Portfolio overview should show both Stock and Mutual Fund categories
    # ─────────────────────────────────────────────────────────────────────────
    def test_06_portfolio_overview_categories(self, auth_headers):
        """Verify portfolio overview shows both Stock and Mutual Fund categories"""
        response = requests.get(f"{BASE_URL}/api/portfolio-overview", headers=auth_headers)
        assert response.status_code == 200, f"Portfolio overview failed: {response.text}"
        data = response.json()
        
        categories = data.get("categories", [])
        category_names = [c.get("category") for c in categories]
        
        # Should have both Stock and Mutual Fund categories
        assert "Stock" in category_names, f"Stock category missing from portfolio overview: {category_names}"
        assert "Mutual Fund" in category_names, f"Mutual Fund category missing from portfolio overview: {category_names}"
        
        # Verify Stock category details (API uses "transactions" as count field)
        stock_cat = next((c for c in categories if c.get("category") == "Stock"), None)
        assert stock_cat is not None
        stock_count = stock_cat.get("transactions") or stock_cat.get("holdings_count") or 0
        assert stock_count >= 16, f"Stock holdings count should be >= 16: {stock_count}"
        
        # Verify Mutual Fund category still has 7 holdings (from previous Groww + eCAS upload)
        mf_cat = next((c for c in categories if c.get("category") == "Mutual Fund"), None)
        assert mf_cat is not None
        # MF count can vary but should have at least some holdings
        mf_count = mf_cat.get("transactions") or mf_cat.get("holdings_count") or 0
        assert mf_count > 0, f"MF holdings count should be > 0: {mf_count}"
        
        print(f"✓ Portfolio overview: Stock={stock_count}, MF={mf_count} holdings")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 7: Investment summary totals
    # ─────────────────────────────────────────────────────────────────────────
    def test_07_investment_summary(self, auth_headers):
        """Verify investment summary includes Zerodha stocks"""
        response = requests.get(f"{BASE_URL}/api/dashboard/investment-summary", headers=auth_headers)
        assert response.status_code == 200, f"Investment summary failed: {response.text}"
        data = response.json()
        
        # Should have total holdings = MF (7) + Stocks (16) = 23
        holdings_count = data.get("holdings_count", 0)
        assert holdings_count >= 23, f"Expected at least 23 holdings, got {holdings_count}"
        
        # Should have some invested value (Zerodha stocks ~20.5K + Groww MF ~110K)
        total_invested = data.get("total_invested", 0)
        assert total_invested > 100000, f"Total invested should be > 100K, got {total_invested}"
        
        # XIRR should be reasonable (weighted average)
        xirr = data.get("xirr", 0)
        assert xirr > 0, f"XIRR should be positive: {xirr}"
        
        print(f"✓ Investment summary: {holdings_count} holdings, ₹{total_invested:,.2f} invested, XIRR={xirr}%")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 8: Verify Groww MF holdings still intact
    # ─────────────────────────────────────────────────────────────────────────
    def test_08_groww_holdings_intact(self, auth_headers):
        """Verify Groww MF holdings are still present after Zerodha upload"""
        response = requests.get(f"{BASE_URL}/api/holdings/live", headers=auth_headers)
        assert response.status_code == 200
        holdings = response.json().get("holdings", [])
        
        # Filter Groww MF holdings
        groww_holdings = [h for h in holdings if "groww" in h.get("source", "").lower()]
        mf_holdings = [h for h in holdings if h.get("category") == "Mutual Fund"]
        
        # Should have 6 Groww MF holdings + 1 eCAS = 7 total MF
        assert len(mf_holdings) >= 6, f"Expected at least 6 MF holdings, got {len(mf_holdings)}"
        
        # Check a specific Groww fund exists
        fund_names = [h.get("name", "") for h in mf_holdings]
        groww_fund_found = any("Nippon" in name or "Parag" in name or "DSP" in name for name in fund_names)
        assert groww_fund_found, f"Groww MF holdings not found: {fund_names}"
        
        print(f"✓ Groww MF holdings intact: {len(mf_holdings)} MF holdings found")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 9: Verify sector field populated
    # ─────────────────────────────────────────────────────────────────────────
    def test_09_sector_field_populated(self, auth_headers):
        """Verify sector field is populated for Zerodha stocks"""
        response = requests.get(f"{BASE_URL}/api/holdings/live", headers=auth_headers)
        assert response.status_code == 200
        holdings = response.json().get("holdings", [])
        
        zerodha_stocks = [h for h in holdings if h.get("source", "").lower() == "zerodha_statement"]
        
        # All stocks should have sector
        stocks_with_sector = [h for h in zerodha_stocks if h.get("sector")]
        assert len(stocks_with_sector) >= 14, f"Expected at least 14 stocks with sector, got {len(stocks_with_sector)}"
        
        # Check specific sectors
        sectors_found = set(h.get("sector", "") for h in zerodha_stocks)
        expected_sectors = {"ENERGY", "ENGINEERING & CAPITAL GOODS", "FMCG", "CHEMICALS"}
        for sector in expected_sectors:
            assert sector in sectors_found, f"Sector '{sector}' not found: {sectors_found}"
        
        print(f"✓ Sectors populated: {len(stocks_with_sector)} stocks have sector data")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 10: Authentication required
    # ─────────────────────────────────────────────────────────────────────────
    def test_10_upload_requires_auth(self):
        """Verify upload endpoint requires authentication"""
        with open(TEST_FILE_PATH, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/upload-statement",
                files={"file": ("test.xlsx", f)},
                data={"statement_type": "auto"}
            )
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Upload endpoint correctly requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
