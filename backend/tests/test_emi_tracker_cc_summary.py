"""
Tests for EMI Tracker Dashboard API and Credit Card Summary in Dashboard Stats
Tests the new features: EMI Tracker card + Credit Card Summary on Dashboard
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# Demo credentials
DEMO_EMAIL = "rajesh@visor.demo"
DEMO_PASSWORD = "Demo@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for demo user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        token = data.get("token") or data.get("access_token")
        if token:
            return token
    pytest.skip(f"Authentication failed with status {response.status_code}: {response.text[:200]}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers for requests"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestEMITrackerDashboard:
    """Tests for /api/emi-tracker/dashboard endpoint"""

    def test_emi_tracker_dashboard_requires_auth(self):
        """EMI tracker dashboard should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/emi-tracker/dashboard")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: EMI tracker requires authentication")

    def test_emi_tracker_dashboard_success(self, auth_headers):
        """EMI tracker dashboard should return 200 with valid auth"""
        response = requests.get(f"{BASE_URL}/api/emi-tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:300]}"
        print("PASS: EMI tracker dashboard returns 200")

    def test_emi_tracker_dashboard_structure(self, auth_headers):
        """EMI tracker dashboard response should have correct structure"""
        response = requests.get(f"{BASE_URL}/api/emi-tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()

        # Check top-level keys
        assert "summary" in data, f"Missing 'summary' key in response: {list(data.keys())}"
        assert "active_emis" in data, f"Missing 'active_emis' key in response: {list(data.keys())}"
        assert "upcoming_payments" in data, f"Missing 'upcoming_payments' key in response: {list(data.keys())}"

        print(f"PASS: EMI tracker dashboard has correct structure with keys: {list(data.keys())}")

    def test_emi_tracker_summary_fields(self, auth_headers):
        """EMI tracker summary should have all required fields"""
        response = requests.get(f"{BASE_URL}/api/emi-tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        summary = data["summary"]

        required_summary_fields = [
            "total_monthly_emi",
            "total_outstanding",
            "total_principal",
            "total_paid",
            "active_count",
            "overall_progress"
        ]

        for field in required_summary_fields:
            assert field in summary, f"Missing field '{field}' in summary: {list(summary.keys())}"

        print(f"PASS: EMI tracker summary has all required fields")
        print(f"  Summary: monthly_emi={summary['total_monthly_emi']}, outstanding={summary['total_outstanding']}, active_count={summary['active_count']}")

    def test_emi_tracker_active_emis_structure(self, auth_headers):
        """Active EMIs should have the correct structure if any exist"""
        response = requests.get(f"{BASE_URL}/api/emi-tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        active_emis = data["active_emis"]

        assert isinstance(active_emis, list), f"active_emis should be a list, got {type(active_emis)}"

        if len(active_emis) > 0:
            emi = active_emis[0]
            required_emi_fields = [
                "id", "name", "loan_type", "lender",
                "principal_amount", "interest_rate", "tenure_months",
                "emi_amount", "outstanding", "total_paid",
                "principal_paid", "interest_paid",
                "remaining_emis", "paid_emis", "progress",
                "start_date", "next_emi_date", "source"
            ]
            for field in required_emi_fields:
                assert field in emi, f"Missing field '{field}' in active EMI: {list(emi.keys())}"
            print(f"PASS: Active EMI has all required fields. Found {len(active_emis)} active EMIs")
        else:
            print(f"INFO: No active EMIs found for demo user (empty list is valid)")

    def test_emi_tracker_upcoming_payments_structure(self, auth_headers):
        """Upcoming payments should have the correct structure if any exist"""
        response = requests.get(f"{BASE_URL}/api/emi-tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        upcoming = data["upcoming_payments"]

        assert isinstance(upcoming, list), f"upcoming_payments should be a list, got {type(upcoming)}"

        if len(upcoming) > 0:
            payment = upcoming[0]
            required_payment_fields = [
                "loan_id", "loan_name", "amount", "due_date",
                "principal", "interest", "status"
            ]
            for field in required_payment_fields:
                assert field in payment, f"Missing field '{field}' in upcoming payment: {list(payment.keys())}"
            print(f"PASS: Upcoming payments have correct structure. Found {len(upcoming)} upcoming payments")
        else:
            print("INFO: No upcoming payments for demo user (empty list is valid)")

    def test_emi_tracker_no_mongo_id(self, auth_headers):
        """Response should not contain MongoDB _id fields"""
        response = requests.get(f"{BASE_URL}/api/emi-tracker/dashboard", headers=auth_headers)
        assert response.status_code == 200

        response_text = response.text
        assert '"_id"' not in response_text, "Response contains MongoDB _id field which should be excluded"
        print("PASS: No MongoDB _id in EMI tracker response")


class TestDashboardCreditCardSummary:
    """Tests for credit_card_summary in /api/dashboard/stats response"""

    def test_dashboard_stats_requires_auth(self):
        """Dashboard stats should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Dashboard stats requires authentication")

    def test_dashboard_stats_success(self, auth_headers):
        """Dashboard stats should return 200 with valid auth"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:300]}"
        print("PASS: Dashboard stats returns 200")

    def test_dashboard_stats_has_credit_card_summary(self, auth_headers):
        """Dashboard stats should include credit_card_summary section"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "credit_card_summary" in data, f"Missing 'credit_card_summary' in dashboard stats response: {list(data.keys())}"

        print(f"PASS: Dashboard stats has credit_card_summary section")

    def test_credit_card_summary_fields(self, auth_headers):
        """Credit card summary should have all required fields"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        cc_summary = data["credit_card_summary"]

        required_fields = [
            "total_outstanding",
            "total_limit",
            "utilization",
            "total_expenses",
            "total_payments",
            "monthly_expenses",
            "cards_count"
        ]

        for field in required_fields:
            assert field in cc_summary, f"Missing field '{field}' in credit_card_summary: {list(cc_summary.keys())}"

        print(f"PASS: Credit card summary has all required fields")
        print(f"  CC Summary: cards_count={cc_summary['cards_count']}, outstanding={cc_summary['total_outstanding']}, utilization={cc_summary['utilization']}%")

    def test_credit_card_summary_numeric_fields(self, auth_headers):
        """Credit card summary numeric fields should be valid numbers"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        cc_summary = data["credit_card_summary"]

        numeric_fields = ["total_outstanding", "total_limit", "utilization", "cards_count"]
        for field in numeric_fields:
            val = cc_summary[field]
            assert isinstance(val, (int, float)), f"Field '{field}' should be numeric, got {type(val)}: {val}"
            assert val >= 0, f"Field '{field}' should be non-negative, got {val}"

        print("PASS: Credit card summary numeric fields are valid")

    def test_credit_card_summary_utilization_range(self, auth_headers):
        """Credit card utilization should be between 0 and 100"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        utilization = data["credit_card_summary"]["utilization"]

        assert 0 <= utilization <= 100, f"Utilization should be 0-100%, got {utilization}"
        print(f"PASS: Utilization is {utilization}% (valid range 0-100)")

    def test_dashboard_stats_core_fields(self, auth_headers):
        """Dashboard stats should still have core fields (regression check)"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        core_fields = ["total_income", "total_expenses", "total_investments", "health_score"]

        for field in core_fields:
            assert field in data, f"Missing core field '{field}' in dashboard stats: {list(data.keys())}"

        print(f"PASS: Dashboard stats has all core fields")

    def test_dashboard_no_mongo_id(self, auth_headers):
        """Dashboard response should not contain MongoDB _id fields"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200

        response_text = response.text
        assert '"_id"' not in response_text, "Response contains MongoDB _id field which should be excluded"
        print("PASS: No MongoDB _id in dashboard stats response")


class TestCreditCardsAPI:
    """Verify credit cards API for adding/listing CCs (needed for CC summary to show)"""

    def test_list_credit_cards(self, auth_headers):
        """Should be able to list credit cards"""
        response = requests.get(f"{BASE_URL}/api/credit-cards", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"PASS: Listed credit cards. Count: {len(data)}")
        return data

    def test_credit_cards_no_mongo_id(self, auth_headers):
        """Credit cards response should not contain MongoDB _id"""
        response = requests.get(f"{BASE_URL}/api/credit-cards", headers=auth_headers)
        assert response.status_code == 200
        assert '"_id"' not in response.text, "Response contains MongoDB _id"
        print("PASS: No MongoDB _id in credit cards response")
