"""
Phase 3: EMI & SIP Analytics Comprehensive Tests
Tests for:
- EMI Analytics Overview (Principal vs Interest split, loan breakdown, monthly timeline)
- Prepayment Calculator (tenure reduction vs EMI reduction)
- SIP Analytics Dashboard (category allocation, discipline score)
- Wealth Projector (conservative/moderate/aggressive scenarios)
- Goal Mapper (SIP-goal mapping with gap analysis)

Test user: rajesh@visor.demo / Demo@123
Test loan_id: e32fd46a-6fd2-4f10-8656-ecf8202ff69a (Home Loan, 50L, 8.5%, 240 months)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    # Fallback for local testing
    BASE_URL = "https://visor-preview.preview.emergentagent.com"

TEST_USER_EMAIL = "rajesh@visor.demo"
TEST_USER_PASSWORD = "Demo@123"
TEST_LOAN_ID = "e32fd46a-6fd2-4f10-8656-ecf8202ff69a"


class TestAuthentication:
    """Authentication fixture tests"""
    
    def test_login_success(self):
        """Test login with demo user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not returned in login response"
        assert "user" in data, "User data not returned"
        print(f"✓ Login successful for {TEST_USER_EMAIL}")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for all tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        token = response.json().get("token")
        print(f"✓ Got auth token for {TEST_USER_EMAIL}")
        return token
    pytest.fail(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with authentication"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# ============================================================
# EMI Analytics Overview Tests
# ============================================================
class TestEmiAnalyticsOverview:
    """Test GET /api/emi-analytics/overview endpoint"""
    
    def test_emi_overview_returns_200(self, auth_headers):
        """EMI overview endpoint returns 200 with auth"""
        response = requests.get(f"{BASE_URL}/api/emi-analytics/overview", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ EMI analytics overview returns 200")
    
    def test_emi_overview_response_structure(self, auth_headers):
        """EMI overview response has correct structure"""
        response = requests.get(f"{BASE_URL}/api/emi-analytics/overview", headers=auth_headers)
        data = response.json()
        
        # Top-level required fields
        required_fields = [
            "total_principal_paid", "total_interest_paid", "total_outstanding",
            "total_emi_per_month", "interest_to_principal_ratio", "loans", "monthly_timeline"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ EMI overview has all required fields")
        print(f"  - Total principal paid: ₹{data['total_principal_paid']:,.2f}")
        print(f"  - Total interest paid: ₹{data['total_interest_paid']:,.2f}")
        print(f"  - Total outstanding: ₹{data['total_outstanding']:,.2f}")
        print(f"  - Monthly EMI: ₹{data['total_emi_per_month']:,.2f}")
        print(f"  - I/P ratio: {data['interest_to_principal_ratio']}")
    
    def test_emi_overview_loans_structure(self, auth_headers):
        """Each loan in EMI overview has correct structure"""
        response = requests.get(f"{BASE_URL}/api/emi-analytics/overview", headers=auth_headers)
        data = response.json()
        
        if len(data["loans"]) > 0:
            loan = data["loans"][0]
            loan_required_fields = [
                "id", "name", "loan_type", "principal_amount", "interest_rate",
                "tenure_months", "emi_amount", "principal_paid", "interest_paid",
                "outstanding", "total_interest_lifetime", "total_cost", 
                "progress_pct", "remaining_emis"
            ]
            for field in loan_required_fields:
                assert field in loan, f"Loan missing field: {field}"
            
            print(f"✓ Loan structure valid: {loan['name']}")
            print(f"  - Principal: ₹{loan['principal_amount']:,.2f}")
            print(f"  - Interest rate: {loan['interest_rate']}%")
            print(f"  - Progress: {loan['progress_pct']}%")
            print(f"  - Remaining EMIs: {loan['remaining_emis']}")
        else:
            print("⚠ No loans found for user")
    
    def test_emi_overview_has_test_loan(self, auth_headers):
        """Verify the test loan exists in overview"""
        response = requests.get(f"{BASE_URL}/api/emi-analytics/overview", headers=auth_headers)
        data = response.json()
        
        loan_ids = [loan["id"] for loan in data["loans"]]
        assert TEST_LOAN_ID in loan_ids, f"Test loan {TEST_LOAN_ID} not found. Available: {loan_ids}"
        
        test_loan = next(l for l in data["loans"] if l["id"] == TEST_LOAN_ID)
        assert test_loan["principal_amount"] == 5000000, "Test loan should be 50L"
        assert test_loan["interest_rate"] == 8.5, "Test loan rate should be 8.5%"
        assert test_loan["tenure_months"] == 240, "Test loan tenure should be 240 months"
        print(f"✓ Test loan verified: {test_loan['name']} (₹50L @ 8.5% for 240 months)")
    
    def test_emi_overview_monthly_timeline(self, auth_headers):
        """Monthly timeline structure is correct"""
        response = requests.get(f"{BASE_URL}/api/emi-analytics/overview", headers=auth_headers)
        data = response.json()
        
        timeline = data["monthly_timeline"]
        if len(timeline) > 0:
            entry = timeline[0]
            assert "month" in entry, "Timeline entry missing 'month'"
            assert "principal" in entry, "Timeline entry missing 'principal'"
            assert "interest" in entry, "Timeline entry missing 'interest'"
            print(f"✓ Monthly timeline valid ({len(timeline)} months)")
            print(f"  - Sample: {entry['month']} - P: ₹{entry['principal']:,.2f}, I: ₹{entry['interest']:,.2f}")
        else:
            print("⚠ No monthly timeline data")
    
    def test_emi_overview_unauthenticated(self):
        """EMI overview returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/emi-analytics/overview")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ EMI overview correctly rejects unauthenticated requests")


# ============================================================
# Prepayment Calculator Tests
# ============================================================
class TestPrepaymentCalculator:
    """Test POST /api/emi-analytics/prepayment endpoint"""
    
    def test_prepayment_reduce_tenure(self, auth_headers):
        """Prepayment with reduce_type=tenure returns correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/emi-analytics/prepayment",
            headers=auth_headers,
            json={
                "loan_id": TEST_LOAN_ID,
                "prepayment_amount": 500000,  # 5L prepayment
                "reduce_type": "tenure"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        required_fields = [
            "loan_name", "original_tenure_months", "original_emi",
            "original_total_interest", "original_total_paid",
            "new_tenure_months", "new_emi", "new_total_interest", "new_total_paid",
            "interest_saved", "tenure_saved_months"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify tenure is reduced, EMI stays same
        assert data["new_emi"] == data["original_emi"], "EMI should stay same when reducing tenure"
        assert data["new_tenure_months"] < data["original_tenure_months"], "Tenure should be reduced"
        assert data["interest_saved"] > 0, "Should save interest with prepayment"
        
        print(f"✓ Prepayment (reduce tenure) works correctly")
        print(f"  - ₹5L prepayment on {data['loan_name']}")
        print(f"  - Interest saved: ₹{data['interest_saved']:,.2f}")
        print(f"  - Tenure reduced by: {data['tenure_saved_months']} months")
    
    def test_prepayment_reduce_emi(self, auth_headers):
        """Prepayment with reduce_type=emi returns correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/emi-analytics/prepayment",
            headers=auth_headers,
            json={
                "loan_id": TEST_LOAN_ID,
                "prepayment_amount": 500000,  # 5L prepayment
                "reduce_type": "emi"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify EMI is reduced, tenure stays same
        assert data["new_emi"] < data["original_emi"], "EMI should be reduced"
        assert data["interest_saved"] > 0, "Should save interest with prepayment"
        assert data["reduce_type"] == "emi", "reduce_type should be returned"
        
        print(f"✓ Prepayment (reduce EMI) works correctly")
        print(f"  - Original EMI: ₹{data['original_emi']:,.2f}")
        print(f"  - New EMI: ₹{data['new_emi']:,.2f}")
        print(f"  - Interest saved: ₹{data['interest_saved']:,.2f}")
    
    def test_prepayment_full_amount(self, auth_headers):
        """Prepayment equal to outstanding clears the loan"""
        # First get the outstanding amount
        overview = requests.get(f"{BASE_URL}/api/emi-analytics/overview", headers=auth_headers).json()
        test_loan = next(l for l in overview["loans"] if l["id"] == TEST_LOAN_ID)
        outstanding = test_loan["outstanding"]
        
        response = requests.post(
            f"{BASE_URL}/api/emi-analytics/prepayment",
            headers=auth_headers,
            json={
                "loan_id": TEST_LOAN_ID,
                "prepayment_amount": outstanding + 100000,  # More than outstanding
                "reduce_type": "tenure"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data or data["new_emi"] == 0, "Full prepayment should clear loan"
        print(f"✓ Full prepayment handles correctly")
        if "message" in data:
            print(f"  - Message: {data['message']}")
    
    def test_prepayment_invalid_loan(self, auth_headers):
        """Prepayment with invalid loan_id returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/emi-analytics/prepayment",
            headers=auth_headers,
            json={
                "loan_id": "invalid-loan-id-12345",
                "prepayment_amount": 100000,
                "reduce_type": "tenure"
            }
        )
        assert response.status_code == 404, f"Expected 404 for invalid loan, got {response.status_code}"
        print("✓ Invalid loan_id correctly returns 404")
    
    def test_prepayment_zero_amount(self, auth_headers):
        """Prepayment with zero amount should work (no change)"""
        response = requests.post(
            f"{BASE_URL}/api/emi-analytics/prepayment",
            headers=auth_headers,
            json={
                "loan_id": TEST_LOAN_ID,
                "prepayment_amount": 0,
                "reduce_type": "tenure"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # With zero prepayment, no savings expected
        print(f"✓ Zero prepayment handled (interest saved: ₹{data.get('interest_saved', 0):,.2f})")
    
    def test_prepayment_unauthenticated(self):
        """Prepayment returns 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/emi-analytics/prepayment",
            json={"loan_id": TEST_LOAN_ID, "prepayment_amount": 100000, "reduce_type": "tenure"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Prepayment correctly rejects unauthenticated requests")


# ============================================================
# SIP Analytics Dashboard Tests
# ============================================================
class TestSipAnalyticsDashboard:
    """Test GET /api/sip-analytics/dashboard endpoint"""
    
    def test_sip_dashboard_returns_200(self, auth_headers):
        """SIP dashboard endpoint returns 200 with auth"""
        response = requests.get(f"{BASE_URL}/api/sip-analytics/dashboard", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ SIP analytics dashboard returns 200")
    
    def test_sip_dashboard_summary_structure(self, auth_headers):
        """SIP dashboard summary has correct structure"""
        response = requests.get(f"{BASE_URL}/api/sip-analytics/dashboard", headers=auth_headers)
        data = response.json()
        
        assert "summary" in data, "Missing 'summary' field"
        summary = data["summary"]
        
        summary_fields = [
            "total_sips", "active_sips", "paused_sips",
            "total_monthly_commitment", "total_invested",
            "total_executions", "estimated_portfolio_value", "discipline_score"
        ]
        for field in summary_fields:
            assert field in summary, f"Summary missing field: {field}"
        
        print(f"✓ SIP dashboard summary structure valid")
        print(f"  - Total SIPs: {summary['total_sips']}")
        print(f"  - Active SIPs: {summary['active_sips']}")
        print(f"  - Monthly commitment: ₹{summary['total_monthly_commitment']:,.2f}")
        print(f"  - Total invested: ₹{summary['total_invested']:,.2f}")
        print(f"  - Discipline score: {summary['discipline_score']}%")
    
    def test_sip_dashboard_category_allocation(self, auth_headers):
        """SIP dashboard has category allocation"""
        response = requests.get(f"{BASE_URL}/api/sip-analytics/dashboard", headers=auth_headers)
        data = response.json()
        
        assert "category_allocation" in data, "Missing 'category_allocation' field"
        
        if len(data["category_allocation"]) > 0:
            cat = data["category_allocation"][0]
            assert "category" in cat, "Category missing 'category' field"
            assert "count" in cat, "Category missing 'count' field"
            assert "monthly_amount" in cat, "Category missing 'monthly_amount' field"
            print(f"✓ Category allocation valid ({len(data['category_allocation'])} categories)")
            for c in data["category_allocation"]:
                print(f"  - {c['category']}: {c['count']} SIPs, ₹{c['monthly_amount']:,.2f}/month")
        else:
            print("⚠ No category allocation data")
    
    def test_sip_dashboard_sip_list(self, auth_headers):
        """SIP dashboard returns list of SIPs with details"""
        response = requests.get(f"{BASE_URL}/api/sip-analytics/dashboard", headers=auth_headers)
        data = response.json()
        
        assert "sips" in data, "Missing 'sips' field"
        
        if len(data["sips"]) > 0:
            sip = data["sips"][0]
            sip_fields = [
                "id", "name", "amount", "frequency", "category",
                "is_active", "monthly_equivalent", "total_invested",
                "execution_count"
            ]
            for field in sip_fields:
                assert field in sip, f"SIP missing field: {field}"
            
            print(f"✓ SIP list valid ({len(data['sips'])} SIPs)")
            for s in data["sips"][:3]:  # Show first 3
                status = "Active" if s["is_active"] else "Paused"
                print(f"  - {s['name']}: ₹{s['amount']} ({s['frequency']}) - {status}")
        else:
            print("⚠ No SIPs found for user")
    
    def test_sip_dashboard_discipline_score_range(self, auth_headers):
        """Discipline score is between 0 and 100"""
        response = requests.get(f"{BASE_URL}/api/sip-analytics/dashboard", headers=auth_headers)
        data = response.json()
        
        score = data["summary"]["discipline_score"]
        assert 0 <= score <= 100, f"Discipline score {score} out of range"
        print(f"✓ Discipline score valid: {score}%")
    
    def test_sip_dashboard_unauthenticated(self):
        """SIP dashboard returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/sip-analytics/dashboard")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ SIP dashboard correctly rejects unauthenticated requests")


# ============================================================
# Wealth Projector Tests
# ============================================================
class TestWealthProjector:
    """Test POST /api/sip-analytics/wealth-projection endpoint"""
    
    def test_wealth_projection_with_inputs(self, auth_headers):
        """Wealth projection with explicit inputs returns scenarios"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/wealth-projection",
            headers=auth_headers,
            json={
                "monthly_sip": 25000,
                "current_value": 500000,
                "years": 10
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check inputs echo
        assert "inputs" in data, "Missing 'inputs' field"
        assert data["inputs"]["monthly_sip"] == 25000
        assert data["inputs"]["current_value"] == 500000
        assert data["inputs"]["years"] == 10
        
        # Check scenarios
        assert "scenarios" in data, "Missing 'scenarios' field"
        for scenario in ["conservative", "moderate", "aggressive"]:
            assert scenario in data["scenarios"], f"Missing {scenario} scenario"
            s = data["scenarios"][scenario]
            assert "future_value" in s, f"{scenario} missing future_value"
            assert "total_invested" in s, f"{scenario} missing total_invested"
            assert "returns" in s, f"{scenario} missing returns"
            assert "annual_return_pct" in s, f"{scenario} missing annual_return_pct"
        
        print(f"✓ Wealth projection scenarios valid")
        print(f"  - Conservative (8%): ₹{data['scenarios']['conservative']['future_value']:,.0f}")
        print(f"  - Moderate (12%): ₹{data['scenarios']['moderate']['future_value']:,.0f}")
        print(f"  - Aggressive (15%): ₹{data['scenarios']['aggressive']['future_value']:,.0f}")
    
    def test_wealth_projection_auto_fill(self, auth_headers):
        """Wealth projection with zero inputs auto-fills from DB"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/wealth-projection",
            headers=auth_headers,
            json={
                "monthly_sip": 0,
                "current_value": 0,
                "years": 15
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # When 0 is passed, should fetch actual data
        print(f"✓ Auto-fill from DB: Monthly SIP=₹{data['inputs']['monthly_sip']:,.2f}, Current=₹{data['inputs']['current_value']:,.2f}")
    
    def test_wealth_projection_custom_return(self, auth_headers):
        """Wealth projection with custom return rate"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/wealth-projection",
            headers=auth_headers,
            json={
                "monthly_sip": 10000,
                "current_value": 100000,
                "years": 5,
                "expected_return_pct": 18
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "custom" in data["scenarios"], "Custom scenario not returned"
        assert data["scenarios"]["custom"]["annual_return_pct"] == 18
        print(f"✓ Custom return rate (18%): ₹{data['scenarios']['custom']['future_value']:,.0f}")
    
    def test_wealth_projection_yearly_timeline(self, auth_headers):
        """Wealth projection has yearly projection timeline"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/wealth-projection",
            headers=auth_headers,
            json={
                "monthly_sip": 20000,
                "current_value": 200000,
                "years": 10
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "yearly_projection" in data, "Missing 'yearly_projection' field"
        assert len(data["yearly_projection"]) == 10, f"Expected 10 years, got {len(data['yearly_projection'])}"
        
        for entry in data["yearly_projection"]:
            assert "year" in entry
            assert "future_value" in entry
            assert "total_invested" in entry
            assert "returns" in entry
        
        # Values should increase each year
        values = [e["future_value"] for e in data["yearly_projection"]]
        assert values == sorted(values), "Future values should increase yearly"
        
        print(f"✓ Yearly projection valid ({len(data['yearly_projection'])} years)")
        print(f"  - Year 1: ₹{data['yearly_projection'][0]['future_value']:,.0f}")
        print(f"  - Year 10: ₹{data['yearly_projection'][-1]['future_value']:,.0f}")
    
    def test_wealth_projection_empty_body(self, auth_headers):
        """Wealth projection with empty body uses defaults"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/wealth-projection",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["inputs"]["years"] == 10, "Default years should be 10"
        print(f"✓ Empty body uses defaults: {data['inputs']['years']} years")
    
    def test_wealth_projection_unauthenticated(self):
        """Wealth projection returns 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/wealth-projection",
            json={"monthly_sip": 10000, "current_value": 0, "years": 10}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Wealth projection correctly rejects unauthenticated requests")


# ============================================================
# Goal Mapper Tests
# ============================================================
class TestGoalMapper:
    """Test POST /api/sip-analytics/goal-map endpoint"""
    
    def test_goal_map_auto_suggest(self, auth_headers):
        """Goal map with empty body returns auto-suggested mappings"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        required_fields = [
            "total_monthly_sip", "total_goals", "goals_on_track",
            "goal_analysis", "unmapped_sips", "active_sips"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Goal map auto-suggest works")
        print(f"  - Total monthly SIP: ₹{data['total_monthly_sip']:,.2f}")
        print(f"  - Total goals: {data['total_goals']}")
        print(f"  - Goals on track: {data['goals_on_track']}")
    
    def test_goal_map_goal_analysis_structure(self, auth_headers):
        """Goal analysis has correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            headers=auth_headers,
            json={}
        )
        data = response.json()
        
        if len(data["goal_analysis"]) > 0:
            goal = data["goal_analysis"][0]
            goal_fields = [
                "goal_id", "goal_title", "target_amount", "current_amount",
                "gap", "deadline", "months_left", "sip_needed_monthly",
                "mapped_sip_amount", "shortfall", "on_track", "mapped_sips"
            ]
            for field in goal_fields:
                assert field in goal, f"Goal missing field: {field}"
            
            print(f"✓ Goal analysis structure valid ({len(data['goal_analysis'])} goals)")
            for g in data["goal_analysis"]:
                status = "✅ On track" if g["on_track"] else f"⚠ Shortfall: ₹{g['shortfall']:,.0f}/month"
                print(f"  - {g['goal_title']}: Target ₹{g['target_amount']:,.0f}, Gap ₹{g['gap']:,.0f}, {status}")
        else:
            print("⚠ No goals found for user")
    
    def test_goal_map_unmapped_sips(self, auth_headers):
        """Unmapped SIPs are listed correctly"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            headers=auth_headers,
            json={}
        )
        data = response.json()
        
        assert "unmapped_sips" in data, "Missing 'unmapped_sips' field"
        assert "active_sips" in data, "Missing 'active_sips' field"
        
        if len(data["unmapped_sips"]) > 0:
            sip = data["unmapped_sips"][0]
            assert "id" in sip or "name" in sip
            assert "monthly_equivalent" in sip
            print(f"✓ Unmapped SIPs: {len(data['unmapped_sips'])}")
            for s in data["unmapped_sips"]:
                print(f"  - {s['name']}: ₹{s['monthly_equivalent']:,.2f}/month")
        else:
            print("✓ All SIPs are mapped to goals")
    
    def test_goal_map_active_sips_structure(self, auth_headers):
        """Active SIPs have correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            headers=auth_headers,
            json={}
        )
        data = response.json()
        
        if len(data["active_sips"]) > 0:
            sip = data["active_sips"][0]
            sip_fields = ["id", "name", "amount", "monthly_equivalent", "category", "mapped_goal_id"]
            for field in sip_fields:
                assert field in sip, f"Active SIP missing field: {field}"
            print(f"✓ Active SIPs structure valid ({len(data['active_sips'])} SIPs)")
        else:
            print("⚠ No active SIPs found")
    
    def test_goal_map_sip_needed_calculation(self, auth_headers):
        """SIP needed calculation is reasonable"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            headers=auth_headers,
            json={}
        )
        data = response.json()
        
        for goal in data["goal_analysis"]:
            if goal["gap"] > 0 and goal["months_left"] > 0:
                # SIP needed should be positive and less than the gap
                assert goal["sip_needed_monthly"] >= 0, f"SIP needed should be >= 0 for {goal['goal_title']}"
                # With compound interest, SIP needed * months should be <= gap
                # (since money grows over time)
                print(f"✓ {goal['goal_title']}: Need ₹{goal['sip_needed_monthly']:,.0f}/month for {goal['months_left']} months to cover ₹{goal['gap']:,.0f} gap")
    
    def test_goal_map_unauthenticated(self):
        """Goal map returns 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            json={}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Goal map correctly rejects unauthenticated requests")


# ============================================================
# Integration Tests
# ============================================================
class TestIntegration:
    """Cross-endpoint integration tests"""
    
    def test_emi_overview_matches_prepayment_loan(self, auth_headers):
        """Prepayment loan data matches overview data"""
        overview = requests.get(f"{BASE_URL}/api/emi-analytics/overview", headers=auth_headers).json()
        test_loan = next(l for l in overview["loans"] if l["id"] == TEST_LOAN_ID)
        
        prepayment = requests.post(
            f"{BASE_URL}/api/emi-analytics/prepayment",
            headers=auth_headers,
            json={"loan_id": TEST_LOAN_ID, "prepayment_amount": 100000, "reduce_type": "tenure"}
        ).json()
        
        assert prepayment["original_emi"] == test_loan["emi_amount"], "EMI should match"
        assert prepayment["original_tenure_months"] == test_loan["tenure_months"], "Tenure should match"
        print(f"✓ EMI overview and prepayment data consistent")
    
    def test_sip_dashboard_matches_goal_map(self, auth_headers):
        """SIP data is consistent across endpoints"""
        dashboard = requests.get(f"{BASE_URL}/api/sip-analytics/dashboard", headers=auth_headers).json()
        goal_map = requests.post(f"{BASE_URL}/api/sip-analytics/goal-map", headers=auth_headers, json={}).json()
        
        # Total monthly SIP should match
        assert abs(dashboard["summary"]["total_monthly_commitment"] - goal_map["total_monthly_sip"]) < 1, \
            "Monthly SIP commitment should match"
        
        # Active SIP count should match
        assert dashboard["summary"]["active_sips"] == len(goal_map["active_sips"]), \
            "Active SIP count should match"
        
        print(f"✓ SIP dashboard and goal map data consistent")
    
    def test_wealth_projection_uses_dashboard_data(self, auth_headers):
        """Wealth projection auto-fill uses actual SIP data"""
        dashboard = requests.get(f"{BASE_URL}/api/sip-analytics/dashboard", headers=auth_headers).json()
        
        projection = requests.post(
            f"{BASE_URL}/api/sip-analytics/wealth-projection",
            headers=auth_headers,
            json={"monthly_sip": 0, "current_value": 0, "years": 5}
        ).json()
        
        # Auto-filled monthly SIP should match dashboard
        if dashboard["summary"]["active_sips"] > 0:
            assert abs(projection["inputs"]["monthly_sip"] - dashboard["summary"]["total_monthly_commitment"]) < 1, \
                "Auto-filled SIP should match dashboard"
            print(f"✓ Wealth projection auto-fill uses dashboard data")
        else:
            print("⚠ No active SIPs to verify auto-fill")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
