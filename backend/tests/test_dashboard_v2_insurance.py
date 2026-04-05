"""
Test Suite for Phase 1 Dashboard V2 Endpoints and Insurance CRUD
Endpoints tested:
- GET /api/dashboard/financial-health-v2 (8-dimension score, 0-1000)
- GET /api/dashboard/net-worth (assets vs liabilities)
- GET /api/dashboard/investment-summary (with XIRR)
- GET /api/dashboard/upcoming-dues (CC + Loan dues)
- GET /api/dashboard/ai-insight (AI-generated insight via GPT-4o)
- GET /api/insurance (list policies)
- POST /api/insurance (create policy)
- PUT /api/insurance/{id} (update policy)
- DELETE /api/insurance/{id} (delete policy)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://experience-deploy.preview.emergentagent.com")

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for demo user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    # API returns 'token' not 'access_token'
    assert "token" in data, f"No token in response: {data}"
    return data["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestFinancialHealthV2:
    """Tests for /api/dashboard/financial-health-v2 endpoint"""

    def test_financial_health_v2_returns_200(self, auth_headers):
        """Verify endpoint returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/financial-health-v2",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_financial_health_v2_has_composite_score(self, auth_headers):
        """Verify composite_score is in range 0-1000"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/financial-health-v2",
            headers=auth_headers
        )
        data = response.json()
        assert "composite_score" in data, f"Missing composite_score: {data.keys()}"
        assert 0 <= data["composite_score"] <= 1000, f"Score out of range: {data['composite_score']}"

    def test_financial_health_v2_has_grade(self, auth_headers):
        """Verify grade is one of the expected values"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/financial-health-v2",
            headers=auth_headers
        )
        data = response.json()
        assert "grade" in data, f"Missing grade: {data.keys()}"
        valid_grades = ["Excellent", "Good", "Fair", "Needs Work", "Critical", "No Data"]
        assert data["grade"] in valid_grades, f"Invalid grade: {data['grade']}"

    def test_financial_health_v2_has_8_dimensions(self, auth_headers):
        """Verify all 8 dimensions are present with scores"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/financial-health-v2",
            headers=auth_headers
        )
        data = response.json()
        assert "dimensions" in data, f"Missing dimensions: {data.keys()}"
        
        expected_dimensions = [
            "savings_rate", "debt_load", "investment_rate", "emergency_fund",
            "cc_utilization", "goal_progress", "insurance_cover", "net_worth_growth"
        ]
        for dim in expected_dimensions:
            assert dim in data["dimensions"], f"Missing dimension: {dim}"
            dim_data = data["dimensions"][dim]
            assert "score" in dim_data, f"Missing score in {dim}"
            assert "raw_value" in dim_data, f"Missing raw_value in {dim}"
            # Score should be 0-100 for individual dimensions
            assert 0 <= dim_data["score"] <= 100, f"{dim} score out of range: {dim_data['score']}"

    def test_financial_health_v2_has_improvement_tip(self, auth_headers):
        """Verify improvement tip is present"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/financial-health-v2",
            headers=auth_headers
        )
        data = response.json()
        assert "improvement_tip" in data, f"Missing improvement_tip"
        assert "biggest_drag" in data, f"Missing biggest_drag"


class TestNetWorth:
    """Tests for /api/dashboard/net-worth endpoint"""

    def test_net_worth_returns_200(self, auth_headers):
        """Verify endpoint returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/net-worth",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_net_worth_has_required_fields(self, auth_headers):
        """Verify net_worth, total_assets, total_liabilities are present"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/net-worth",
            headers=auth_headers
        )
        data = response.json()
        
        assert "net_worth" in data, f"Missing net_worth"
        assert "total_assets" in data, f"Missing total_assets"
        assert "total_liabilities" in data, f"Missing total_liabilities"
        
        # Net worth should equal assets minus liabilities
        expected_net = data["total_assets"] - data["total_liabilities"]
        assert abs(data["net_worth"] - expected_net) < 0.01, f"Net worth calculation mismatch"

    def test_net_worth_has_breakdown(self, auth_headers):
        """Verify breakdown includes assets and liabilities details"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/net-worth",
            headers=auth_headers
        )
        data = response.json()
        
        assert "breakdown" in data, f"Missing breakdown"
        assert "assets" in data["breakdown"], f"Missing assets breakdown"
        assert "liabilities" in data["breakdown"], f"Missing liabilities breakdown"
        
        # Check assets breakdown
        assets = data["breakdown"]["assets"]
        assert "bank_balance" in assets, f"Missing bank_balance in assets"
        assert "investments" in assets, f"Missing investments in assets"
        
        # Check liabilities breakdown
        liabilities = data["breakdown"]["liabilities"]
        assert "loans" in liabilities, f"Missing loans in liabilities"
        assert "credit_cards" in liabilities, f"Missing credit_cards in liabilities"


class TestInvestmentSummary:
    """Tests for /api/dashboard/investment-summary endpoint"""

    def test_investment_summary_returns_200(self, auth_headers):
        """Verify endpoint returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/investment-summary",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_investment_summary_has_required_fields(self, auth_headers):
        """Verify required fields are present"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/investment-summary",
            headers=auth_headers
        )
        data = response.json()
        
        required_fields = [
            "total_invested", "current_value", "absolute_gain",
            "absolute_return_pct", "xirr", "holdings_count"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_investment_summary_xirr_valid_or_null(self, auth_headers):
        """Verify XIRR is either a number or null"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/investment-summary",
            headers=auth_headers
        )
        data = response.json()
        
        xirr = data["xirr"]
        if xirr is not None:
            assert isinstance(xirr, (int, float)), f"XIRR should be a number, got {type(xirr)}"
            # XIRR should be between -99% and 1000%
            assert -99 <= xirr <= 1000, f"XIRR out of reasonable range: {xirr}"

    def test_investment_summary_values_consistent(self, auth_headers):
        """Verify absolute_gain = current_value - total_invested"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/investment-summary",
            headers=auth_headers
        )
        data = response.json()
        
        expected_gain = data["current_value"] - data["total_invested"]
        assert abs(data["absolute_gain"] - expected_gain) < 0.01, f"Absolute gain calculation mismatch"


class TestUpcomingDues:
    """Tests for /api/dashboard/upcoming-dues endpoint"""

    def test_upcoming_dues_returns_200(self, auth_headers):
        """Verify endpoint returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/upcoming-dues",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_upcoming_dues_has_dues_array(self, auth_headers):
        """Verify dues array is present"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/upcoming-dues",
            headers=auth_headers
        )
        data = response.json()
        
        assert "dues" in data, f"Missing dues array"
        assert isinstance(data["dues"], list), f"dues should be a list"

    def test_upcoming_dues_item_structure(self, auth_headers):
        """Verify each due item has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/upcoming-dues",
            headers=auth_headers
        )
        data = response.json()
        
        if len(data["dues"]) > 0:
            due = data["dues"][0]
            required_fields = ["id", "name", "type", "amount", "due_date", "days_until", "urgency", "icon"]
            for field in required_fields:
                assert field in due, f"Missing field in due item: {field}"
            
            # Verify type is credit_card or loan
            assert due["type"] in ["credit_card", "loan"], f"Invalid type: {due['type']}"
            
            # Verify urgency is valid
            valid_urgencies = ["critical", "warning", "upcoming", "normal"]
            assert due["urgency"] in valid_urgencies, f"Invalid urgency: {due['urgency']}"

    def test_upcoming_dues_sorted_by_days(self, auth_headers):
        """Verify dues are sorted by days_until (ascending)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/upcoming-dues",
            headers=auth_headers
        )
        data = response.json()
        
        dues = data["dues"]
        if len(dues) > 1:
            days_list = [d["days_until"] for d in dues]
            assert days_list == sorted(days_list), f"Dues not sorted by days_until: {days_list}"


class TestAIInsight:
    """Tests for /api/dashboard/ai-insight endpoint"""

    def test_ai_insight_returns_200(self, auth_headers):
        """Verify endpoint returns 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/ai-insight",
            headers=auth_headers,
            timeout=30  # AI generation can take time
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_ai_insight_has_required_fields(self, auth_headers):
        """Verify insight and generated_at are present"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/ai-insight",
            headers=auth_headers,
            timeout=30
        )
        data = response.json()
        
        assert "insight" in data, f"Missing insight"
        assert "generated_at" in data, f"Missing generated_at"
        assert "data_points_used" in data, f"Missing data_points_used"

    def test_ai_insight_is_non_empty(self, auth_headers):
        """Verify insight text is non-empty"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/ai-insight",
            headers=auth_headers,
            timeout=30
        )
        data = response.json()
        
        insight = data["insight"]
        assert isinstance(insight, str), f"Insight should be a string"
        assert len(insight) > 20, f"Insight too short: {insight}"


class TestInsuranceCRUD:
    """Tests for Insurance CRUD endpoints"""

    def test_get_insurance_returns_200(self, auth_headers):
        """Verify GET /api/insurance returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/insurance",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert isinstance(response.json(), list), "Response should be a list"

    def test_create_insurance_policy(self, auth_headers):
        """Test POST /api/insurance creates a new policy"""
        policy_data = {
            "policy_name": "TEST_HDFC Life Term Plan",
            "policy_type": "term_life",
            "provider": "HDFC Life",
            "cover_amount": 10000000,  # 1 Crore
            "premium_amount": 15000,
            "premium_frequency": "yearly",
            "start_date": "2024-01-01",
            "end_date": "2054-01-01",
            "policy_number": "TEST123456",
            "nominees": "Spouse"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/insurance",
            headers=auth_headers,
            json=policy_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have id"
        assert data["policy_name"] == policy_data["policy_name"]
        assert data["cover_amount"] == policy_data["cover_amount"]
        
        # Store id for later tests
        TestInsuranceCRUD.created_policy_id = data["id"]
        return data["id"]

    def test_read_created_policy(self, auth_headers):
        """Verify created policy appears in list"""
        response = requests.get(
            f"{BASE_URL}/api/insurance",
            headers=auth_headers
        )
        data = response.json()
        
        policy_id = getattr(TestInsuranceCRUD, "created_policy_id", None)
        if policy_id:
            found = any(p["id"] == policy_id for p in data)
            assert found, f"Created policy {policy_id} not found in list"

    def test_update_insurance_policy(self, auth_headers):
        """Test PUT /api/insurance/{id} updates a policy"""
        policy_id = getattr(TestInsuranceCRUD, "created_policy_id", None)
        if not policy_id:
            pytest.skip("No policy created to update")
        
        update_data = {
            "policy_name": "TEST_HDFC Life Term Plan Updated",
            "premium_amount": 16000
        }
        
        response = requests.put(
            f"{BASE_URL}/api/insurance/{policy_id}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["policy_name"] == update_data["policy_name"]
        assert data["premium_amount"] == update_data["premium_amount"]

    def test_verify_update_persisted(self, auth_headers):
        """Verify update was persisted"""
        policy_id = getattr(TestInsuranceCRUD, "created_policy_id", None)
        if not policy_id:
            pytest.skip("No policy created")
        
        response = requests.get(
            f"{BASE_URL}/api/insurance",
            headers=auth_headers
        )
        data = response.json()
        
        policy = next((p for p in data if p["id"] == policy_id), None)
        assert policy is not None, f"Policy {policy_id} not found"
        assert policy["policy_name"] == "TEST_HDFC Life Term Plan Updated"
        assert policy["premium_amount"] == 16000

    def test_delete_insurance_policy(self, auth_headers):
        """Test DELETE /api/insurance/{id} deletes a policy"""
        policy_id = getattr(TestInsuranceCRUD, "created_policy_id", None)
        if not policy_id:
            pytest.skip("No policy created to delete")
        
        response = requests.delete(
            f"{BASE_URL}/api/insurance/{policy_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("message") == "Policy deleted" or "deleted" in str(data).lower()

    def test_verify_delete_worked(self, auth_headers):
        """Verify deleted policy no longer exists"""
        policy_id = getattr(TestInsuranceCRUD, "created_policy_id", None)
        if not policy_id:
            pytest.skip("No policy created")
        
        response = requests.get(
            f"{BASE_URL}/api/insurance",
            headers=auth_headers
        )
        data = response.json()
        
        found = any(p["id"] == policy_id for p in data)
        assert not found, f"Deleted policy {policy_id} still exists"

    def test_update_nonexistent_policy(self, auth_headers):
        """Test updating non-existent policy returns error"""
        response = requests.put(
            f"{BASE_URL}/api/insurance/nonexistent-id-12345",
            headers=auth_headers,
            json={"policy_name": "Test"}
        )
        # Should either return 404 or error message
        data = response.json()
        if response.status_code != 404:
            assert "error" in data or "Policy not found" in str(data)

    def test_delete_nonexistent_policy(self, auth_headers):
        """Test deleting non-existent policy returns error"""
        response = requests.delete(
            f"{BASE_URL}/api/insurance/nonexistent-id-12345",
            headers=auth_headers
        )
        data = response.json()
        if response.status_code != 404:
            assert "error" in data or "not found" in str(data).lower()


class TestAuthRequired:
    """Tests to verify endpoints require authentication"""

    def test_financial_health_v2_requires_auth(self):
        """Verify endpoint rejects unauthenticated requests"""
        response = requests.get(f"{BASE_URL}/api/dashboard/financial-health-v2")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"

    def test_net_worth_requires_auth(self):
        """Verify endpoint rejects unauthenticated requests"""
        response = requests.get(f"{BASE_URL}/api/dashboard/net-worth")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"

    def test_insurance_requires_auth(self):
        """Verify endpoint rejects unauthenticated requests"""
        response = requests.get(f"{BASE_URL}/api/insurance")
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
