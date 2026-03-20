"""
Test iteration 39: Live Price Refresh and SIP Suggestions endpoints
Tests:
1. POST /api/holdings/refresh-prices - Refresh stock/MF prices via yfinance and mfapi.in
2. GET /api/holdings/live - Holdings with updated values
3. GET /api/sip-suggestions - Pending SIP suggestions
4. POST /api/sip-suggestions/{id}/approve - Approve a suggestion
5. DELETE /api/sip-suggestions/{id} - Decline/delete a suggestion
6. GET /api/portfolio-overview - Updated portfolio values after refresh
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

class TestAuthAndSetup:
    """Setup: Authenticate and get token for subsequent tests"""
    
    token = None
    user_id = None
    
    @pytest.fixture(scope="class", autouse=True)
    def auth_setup(self, request):
        """Authenticate once for all tests in this class"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        request.cls.token = data["token"]
        request.cls.user_id = data.get("user", {}).get("id")
        print(f"Authenticated successfully. User ID: {request.cls.user_id}")


class TestLivePriceRefresh(TestAuthAndSetup):
    """Test live price refresh endpoint for stocks and mutual funds"""
    
    def test_01_get_holdings_before_refresh(self):
        """GET /api/holdings/live - Verify holdings exist before refresh"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{BASE_URL}/api/holdings/live", headers=headers)
        
        assert response.status_code == 200, f"Holdings API failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "holdings" in data, "Missing 'holdings' key"
        assert "summary" in data, "Missing 'summary' key"
        
        holdings = data["holdings"]
        print(f"Found {len(holdings)} holdings before refresh")
        
        # Store holdings count for later comparison
        TestLivePriceRefresh.holdings_count = len(holdings)
        TestLivePriceRefresh.initial_holdings = holdings
        
        # Verify at least some holdings exist (from iteration 38)
        if holdings:
            # Check each holding has expected fields
            sample = holdings[0]
            required_fields = ["id", "name", "category", "quantity"]
            for field in required_fields:
                assert field in sample, f"Missing field '{field}' in holding"
    
    def test_02_refresh_prices_endpoint(self):
        """POST /api/holdings/refresh-prices - Refresh live prices for all holdings"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # This endpoint makes external API calls, may take 10-15 seconds
        response = requests.post(
            f"{BASE_URL}/api/holdings/refresh-prices", 
            headers=headers,
            timeout=60  # Long timeout for external API calls
        )
        
        assert response.status_code == 200, f"Refresh prices failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "updated" in data, "Missing 'updated' count"
        assert "total" in data, "Missing 'total' count"
        
        # Verify additional fields if holdings were updated
        if data.get("total", 0) > 0:
            assert "stocks_updated" in data, "Missing 'stocks_updated' count"
            assert "mfs_updated" in data, "Missing 'mfs_updated' count"
            assert "message" in data, "Missing 'message' field"
        
        print(f"Refresh result: {data}")
        TestLivePriceRefresh.refresh_result = data
    
    def test_03_get_holdings_after_refresh(self):
        """GET /api/holdings/live - Verify holdings have updated values after refresh"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{BASE_URL}/api/holdings/live", headers=headers)
        
        assert response.status_code == 200, f"Holdings API failed: {response.text}"
        data = response.json()
        holdings = data["holdings"]
        
        # Verify holdings now have value fields
        for h in holdings:
            assert "current_value" in h, f"Missing current_value for {h.get('name')}"
            assert "gain_loss" in h, f"Missing gain_loss for {h.get('name')}"
            assert "gain_loss_pct" in h, f"Missing gain_loss_pct for {h.get('name')}"
            assert "invested_value" in h, f"Missing invested_value for {h.get('name')}"
            
            print(f"Holding: {h.get('name')[:30]} | Category: {h.get('category')} | "
                  f"Invested: {h.get('invested_value')} | Current: {h.get('current_value')} | "
                  f"Gain: {h.get('gain_loss')} ({h.get('gain_loss_pct')}%)")
        
        # Verify summary reflects total values
        summary = data["summary"]
        assert summary.get("total_invested", 0) >= 0, "Invalid total_invested"
        assert summary.get("total_current_value", 0) >= 0, "Invalid total_current_value"
        print(f"Summary: Invested={summary.get('total_invested')}, "
              f"Current={summary.get('total_current_value')}, "
              f"Gain={summary.get('total_gain_loss')}")
    
    def test_04_portfolio_overview_reflects_updated_values(self):
        """GET /api/portfolio-overview - Verify portfolio overview shows updated values"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{BASE_URL}/api/portfolio-overview", headers=headers)
        
        assert response.status_code == 200, f"Portfolio overview failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total_invested" in data, "Missing total_invested"
        assert "total_current_value" in data, "Missing total_current_value"
        assert "total_gain_loss" in data, "Missing total_gain_loss"
        assert "total_gain_loss_pct" in data, "Missing total_gain_loss_pct"
        
        print(f"Portfolio Overview: Invested={data.get('total_invested')}, "
              f"Current={data.get('total_current_value')}, "
              f"Gain/Loss={data.get('total_gain_loss')} ({data.get('total_gain_loss_pct')}%)")
        
        # Verify categories breakdown if present
        if "categories" in data:
            for cat in data["categories"]:
                print(f"  Category: {cat.get('category')} - "
                      f"Invested: {cat.get('invested_value')}, "
                      f"Current: {cat.get('current_value')}")


class TestSIPSuggestions(TestAuthAndSetup):
    """Test SIP suggestions endpoints - auto-created from MF statement uploads"""
    
    test_suggestion_id = None
    
    def test_05_get_sip_suggestions(self):
        """GET /api/sip-suggestions - Get pending SIP suggestions"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{BASE_URL}/api/sip-suggestions", headers=headers)
        
        assert response.status_code == 200, f"SIP suggestions API failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "suggestions" in data, "Missing 'suggestions' key"
        
        suggestions = data["suggestions"]
        print(f"Found {len(suggestions)} pending SIP suggestions")
        
        if suggestions:
            # Verify each suggestion has required fields
            for sug in suggestions:
                assert "id" in sug, "Missing 'id' in suggestion"
                assert "fund_name" in sug, "Missing 'fund_name' in suggestion"
                assert "status" in sug, "Missing 'status' in suggestion"
                print(f"  SIP Suggestion: {sug.get('fund_name')[:50]} | ISIN: {sug.get('isin')} | Status: {sug.get('status')}")
            
            # Store first suggestion ID for approval/decline tests
            TestSIPSuggestions.test_suggestion_id = suggestions[0]["id"]
            TestSIPSuggestions.original_suggestions_count = len(suggestions)
    
    def test_06_approve_sip_suggestion(self):
        """POST /api/sip-suggestions/{id}/approve - Mark suggestion as approved"""
        if not self.test_suggestion_id:
            pytest.skip("No SIP suggestions available to approve")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{BASE_URL}/api/sip-suggestions/{self.test_suggestion_id}/approve",
            headers=headers
        )
        
        assert response.status_code == 200, f"Approve suggestion failed: {response.text}"
        data = response.json()
        assert "message" in data, "Missing message in response"
        print(f"Approval result: {data}")
    
    def test_07_verify_approved_suggestion_removed_from_pending(self):
        """GET /api/sip-suggestions - Approved suggestion should not appear in pending list"""
        if not self.test_suggestion_id:
            pytest.skip("No SIP suggestions available")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{BASE_URL}/api/sip-suggestions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        suggestions = data["suggestions"]
        
        # Approved suggestion should be removed from pending list
        approved_ids = [s["id"] for s in suggestions]
        # The approved one may still appear but with status changed, or removed entirely
        # Based on code, approved status != pending, so it won't appear
        print(f"Remaining suggestions after approval: {len(suggestions)}")
        
        # If we had multiple suggestions, count should be reduced
        if hasattr(TestSIPSuggestions, 'original_suggestions_count'):
            if TestSIPSuggestions.original_suggestions_count > 0:
                assert len(suggestions) < TestSIPSuggestions.original_suggestions_count, \
                    "Approved suggestion should be removed from pending list"
    
    def test_08_decline_sip_suggestion(self):
        """DELETE /api/sip-suggestions/{id} - Decline/delete a suggestion"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # First get current suggestions
        response = requests.get(f"{BASE_URL}/api/sip-suggestions", headers=headers)
        assert response.status_code == 200
        suggestions = response.json()["suggestions"]
        
        if not suggestions:
            pytest.skip("No more SIP suggestions to decline")
        
        suggestion_to_decline = suggestions[0]["id"]
        suggestion_name = suggestions[0]["fund_name"]
        initial_count = len(suggestions)
        
        # Decline/delete the suggestion
        response = requests.delete(
            f"{BASE_URL}/api/sip-suggestions/{suggestion_to_decline}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Decline suggestion failed: {response.text}"
        data = response.json()
        assert "message" in data, "Missing message in response"
        print(f"Declined suggestion: {suggestion_name}")
        
        # Verify it's removed
        response = requests.get(f"{BASE_URL}/api/sip-suggestions", headers=headers)
        new_suggestions = response.json()["suggestions"]
        assert len(new_suggestions) == initial_count - 1, "Declined suggestion should be removed"
    
    def test_09_decline_nonexistent_suggestion_returns_404(self):
        """DELETE /api/sip-suggestions/{id} - Nonexistent ID should return 404"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        fake_id = "000000000000000000000000"  # Valid ObjectId format but doesn't exist
        response = requests.delete(
            f"{BASE_URL}/api/sip-suggestions/{fake_id}",
            headers=headers
        )
        
        assert response.status_code == 404, f"Expected 404 for nonexistent suggestion, got {response.status_code}"


class TestEdgeCases(TestAuthAndSetup):
    """Edge case tests"""
    
    def test_10_refresh_prices_unauthenticated(self):
        """POST /api/holdings/refresh-prices without auth should fail"""
        response = requests.post(f"{BASE_URL}/api/holdings/refresh-prices", timeout=10)
        assert response.status_code in [401, 403, 422], \
            f"Unauthenticated request should fail, got {response.status_code}"
    
    def test_11_sip_suggestions_unauthenticated(self):
        """GET /api/sip-suggestions without auth should fail"""
        response = requests.get(f"{BASE_URL}/api/sip-suggestions")
        assert response.status_code in [401, 403, 422], \
            f"Unauthenticated request should fail, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
