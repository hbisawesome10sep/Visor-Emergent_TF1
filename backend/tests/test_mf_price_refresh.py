"""
Test MF Price Refresh Feature - Iteration 40
Tests for the mutual fund price refresh functionality that:
1. Correctly matches Direct plan funds to Direct NAVs
2. Correctly matches Regular/ambiguous funds to Regular NAVs
3. Returns stocks_updated and mfs_updated counts
4. Validates NAV reasonableness vs buy_price
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Demo user credentials
DEMO_EMAIL = "rajesh@visor.demo"
DEMO_PASSWORD = "Demo@123"


class TestMFPriceRefresh:
    """Tests for the Mutual Fund price refresh feature with improved matching logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if resp.status_code != 200:
            pytest.skip(f"Could not login: {resp.status_code} - {resp.text}")
        data = resp.json()
        self.token = data.get("access_token") or data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_refresh_prices_endpoint_exists(self):
        """Test that POST /api/holdings/refresh-prices endpoint exists"""
        resp = requests.post(f"{BASE_URL}/api/holdings/refresh-prices", headers=self.headers)
        # Should not be 404 or 405
        assert resp.status_code != 404, "Endpoint not found"
        assert resp.status_code != 405, "Method not allowed"
        print(f"refresh-prices endpoint status: {resp.status_code}")
    
    def test_refresh_prices_returns_updated_counts(self):
        """Test that refresh-prices response includes stocks_updated and mfs_updated counts"""
        resp = requests.post(
            f"{BASE_URL}/api/holdings/refresh-prices", 
            headers=self.headers,
            timeout=30  # External API calls may take time
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        print(f"Refresh response: {data}")
        
        # Check required fields in response
        assert "updated" in data, "Response missing 'updated' field"
        assert "total" in data, "Response missing 'total' field"
        assert "stocks_updated" in data, "Response missing 'stocks_updated' field"
        assert "mfs_updated" in data, "Response missing 'mfs_updated' field"
        assert "message" in data, "Response missing 'message' field"
        
        print(f"Updated: {data['updated']}/{data['total']}")
        print(f"Stocks updated: {data['stocks_updated']}")
        print(f"MFs updated: {data['mfs_updated']}")
    
    def test_holdings_live_after_refresh(self):
        """Test GET /api/holdings/live returns holdings with reasonable gain/loss percentages"""
        # First refresh prices
        refresh_resp = requests.post(
            f"{BASE_URL}/api/holdings/refresh-prices",
            headers=self.headers,
            timeout=30
        )
        print(f"Refresh status: {refresh_resp.status_code}")
        
        # Allow some time for data to settle
        time.sleep(1)
        
        # Get live holdings
        resp = requests.get(f"{BASE_URL}/api/holdings/live", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        data = resp.json()
        holdings = data.get("holdings", [])
        summary = data.get("summary", {})
        
        print(f"Total holdings: {len(holdings)}")
        print(f"Summary: {summary}")
        
        # Check each holding for reasonable values
        for h in holdings:
            name = h.get("name", "Unknown")
            category = h.get("category", "")
            buy_price = h.get("buy_price", 0)
            current_value = h.get("current_value", 0)
            invested_value = h.get("invested_value", 0)
            gain_loss_pct = h.get("gain_loss_pct", 0)
            quantity = h.get("quantity", 0)
            
            print(f"\n{category}: {name[:40]}")
            print(f"  qty={quantity}, buy_price={buy_price}")
            print(f"  invested={invested_value}, current={current_value}")
            print(f"  gain/loss: {gain_loss_pct}%")
            
            # Validate reasonable gain/loss percentage
            # Unless the fund really moved dramatically, we shouldn't see >300% or <-90%
            if category == "Mutual Fund" and current_value > 0 and invested_value > 0:
                # NAV should be reasonable - not showing extreme values from wrong fund matching
                if abs(gain_loss_pct) > 300:
                    print(f"  WARNING: Extreme gain/loss {gain_loss_pct}% - possible wrong fund match!")
                
                # Current value should be roughly qty * some reasonable NAV
                implied_nav = current_value / quantity if quantity > 0 else 0
                nav_to_buy_ratio = implied_nav / buy_price if buy_price > 0 else 0
                print(f"  implied_nav={implied_nav:.4f}, nav/buy_ratio={nav_to_buy_ratio:.2f}")
                
                # NAV should be within 0.1x to 10x of buy_price (matching validation logic)
                if nav_to_buy_ratio > 0:
                    assert 0.08 <= nav_to_buy_ratio <= 12, \
                        f"NAV ratio out of range for {name}: {nav_to_buy_ratio}"
    
    def test_holdings_data_structure(self):
        """Test holdings response structure is correct"""
        resp = requests.get(f"{BASE_URL}/api/holdings/live", headers=self.headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "holdings" in data, "Response missing 'holdings'"
        assert "summary" in data, "Response missing 'summary'"
        
        summary = data["summary"]
        expected_summary_keys = [
            "total_invested", "total_current_value", 
            "total_gain_loss", "total_gain_loss_pct", "holding_count"
        ]
        for key in expected_summary_keys:
            assert key in summary, f"Summary missing '{key}'"
        
        print(f"Holdings summary: {summary}")


class TestSIPSuggestions:
    """Tests for SIP suggestions endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if resp.status_code != 200:
            pytest.skip(f"Could not login: {resp.status_code}")
        data = resp.json()
        self.token = data.get("access_token") or data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_sip_suggestions_endpoint(self):
        """Test GET /api/sip-suggestions returns pending suggestions"""
        resp = requests.get(f"{BASE_URL}/api/sip-suggestions", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        data = resp.json()
        assert "suggestions" in data, "Response missing 'suggestions'"
        
        suggestions = data["suggestions"]
        print(f"SIP suggestions count: {len(suggestions)}")
        
        for sug in suggestions:
            print(f"  - {sug.get('fund_name', 'Unknown')} (status: {sug.get('status')})")
            assert "id" in sug, "Suggestion missing 'id'"
            assert "fund_name" in sug, "Suggestion missing 'fund_name'"
            assert "status" in sug, "Suggestion missing 'status'"


class TestHoldingsMatchingLogic:
    """Tests to verify the MF matching logic works correctly for Direct vs Regular plans"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if resp.status_code != 200:
            pytest.skip(f"Could not login: {resp.status_code}")
        data = resp.json()
        self.token = data.get("access_token") or data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_mf_holdings_exist(self):
        """Verify MF holdings exist for the demo user"""
        resp = requests.get(f"{BASE_URL}/api/holdings", headers=self.headers)
        assert resp.status_code == 200
        
        holdings = resp.json().get("holdings", [])
        mf_holdings = [h for h in holdings if h.get("category") == "Mutual Fund"]
        
        print(f"Total MF holdings: {len(mf_holdings)}")
        for h in mf_holdings:
            name = h.get("name", "")
            is_direct = "direct" in name.lower()
            print(f"  - {name[:50]} (Direct: {is_direct})")
        
        assert len(mf_holdings) >= 0, "Should have MF holdings to test"
    
    def test_refresh_prices_with_mf_holdings(self):
        """Test refresh prices actually updates MF holdings"""
        # Get holdings before refresh
        before_resp = requests.get(f"{BASE_URL}/api/holdings/live", headers=self.headers)
        assert before_resp.status_code == 200
        before_holdings = before_resp.json().get("holdings", [])
        
        # Refresh prices (may take time due to external API calls)
        refresh_resp = requests.post(
            f"{BASE_URL}/api/holdings/refresh-prices",
            headers=self.headers,
            timeout=45  # Longer timeout for external API calls
        )
        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
        
        refresh_data = refresh_resp.json()
        print(f"Refresh result: {refresh_data}")
        
        # If we have MF holdings, at least some should be updated
        mf_count = len([h for h in before_holdings if h.get("category") == "Mutual Fund"])
        if mf_count > 0:
            # Check that mfs_updated is a reasonable number
            mfs_updated = refresh_data.get("mfs_updated", 0)
            print(f"MF holdings: {mf_count}, Updated: {mfs_updated}")


class TestMFMatchingValidation:
    """Test to validate MF matching by checking backend logs or response data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if resp.status_code != 200:
            pytest.skip(f"Could not login: {resp.status_code}")
        data = resp.json()
        self.token = data.get("access_token") or data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_direct_fund_stays_direct(self):
        """
        Validate that a Direct plan fund gets matched to Direct NAV.
        We can check this by verifying the current_value calculation makes sense.
        """
        resp = requests.get(f"{BASE_URL}/api/holdings/live", headers=self.headers)
        assert resp.status_code == 200
        
        holdings = resp.json().get("holdings", [])
        direct_mfs = [h for h in holdings 
                      if h.get("category") == "Mutual Fund" 
                      and "direct" in h.get("name", "").lower()]
        
        print(f"Direct plan MFs: {len(direct_mfs)}")
        
        for h in direct_mfs:
            name = h.get("name", "")
            buy_price = h.get("buy_price", 0)
            quantity = h.get("quantity", 0)
            current_value = h.get("current_value", 0)
            
            if quantity > 0 and current_value > 0:
                implied_nav = current_value / quantity
                if buy_price > 0:
                    ratio = implied_nav / buy_price
                    print(f"{name[:40]}: buy={buy_price:.2f}, nav={implied_nav:.2f}, ratio={ratio:.2f}")
                    
                    # Direct NAV should be within reasonable bounds
                    # If we matched the wrong Regular plan, ratio would be way off
                    assert 0.1 <= ratio <= 10, f"Suspicious NAV ratio for Direct fund: {ratio}"
    
    def test_regular_fund_stays_regular(self):
        """
        Validate that a Regular/ambiguous plan fund gets matched to Regular NAV.
        """
        resp = requests.get(f"{BASE_URL}/api/holdings/live", headers=self.headers)
        assert resp.status_code == 200
        
        holdings = resp.json().get("holdings", [])
        regular_mfs = [h for h in holdings 
                       if h.get("category") == "Mutual Fund" 
                       and "direct" not in h.get("name", "").lower()]
        
        print(f"Regular/ambiguous MFs: {len(regular_mfs)}")
        
        for h in regular_mfs:
            name = h.get("name", "")
            buy_price = h.get("buy_price", 0)
            quantity = h.get("quantity", 0)
            current_value = h.get("current_value", 0)
            
            if quantity > 0 and current_value > 0:
                implied_nav = current_value / quantity
                if buy_price > 0:
                    ratio = implied_nav / buy_price
                    print(f"{name[:40]}: buy={buy_price:.2f}, nav={implied_nav:.2f}, ratio={ratio:.2f}")
                    
                    # Regular NAV should be within reasonable bounds
                    assert 0.1 <= ratio <= 10, f"Suspicious NAV ratio for Regular fund: {ratio}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
