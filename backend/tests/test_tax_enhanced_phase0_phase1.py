"""
Tax Enhanced Phase 0 + Phase 1 API Tests
Tests: Income Profile (P0), Salary Profile Wizard (1.2), HRA Calculation (1.3), 80C Tracker (1.4)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://enhanced-tax-module.preview.emergentagent.com').rstrip('/')

DEMO_EMAIL = "rajesh@visor.demo"
DEMO_PASSWORD = "Demo@123"


@pytest.fixture(scope="session")
def auth_token():
    """Get auth token for demo user"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD
    })
    assert resp.status_code == 200, f"Auth failed: {resp.text}"
    token = resp.json().get("access_token") or resp.json().get("token")
    assert token, f"No token in response: {resp.json()}"
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ══════════════════════════════════════════
#  Phase 0: INCOME PROFILE Tests
# ══════════════════════════════════════════

class TestIncomeProfile:
    """Tests for GET/POST /api/tax/income-profile"""

    def test_get_income_profile_returns_200(self, auth_headers):
        """GET income profile should return 200 with profile field"""
        resp = requests.get(f"{BASE_URL}/api/tax/income-profile", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "profile" in data, f"'profile' key missing from response: {data}"
        print(f"[PASS] GET /api/tax/income-profile - Status 200, profile={data['profile']}")

    def test_post_income_profile_saves_income_types(self, auth_headers):
        """POST income profile should save income types array"""
        payload = {
            "income_types": ["salaried", "investor"],
            "primary_income_type": "salaried",
            "fy": "2025-26"
        }
        resp = requests.post(f"{BASE_URL}/api/tax/income-profile", json=payload, headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "profile" in data, f"'profile' key missing from response: {data}"
        profile = data["profile"]
        assert profile["income_types"] == ["salaried", "investor"], \
            f"Income types mismatch: {profile['income_types']}"
        assert profile["primary_income_type"] == "salaried", \
            f"Primary income type mismatch: {profile['primary_income_type']}"
        print(f"[PASS] POST /api/tax/income-profile - Saved income_types={profile['income_types']}")

    def test_post_income_profile_persists_to_get(self, auth_headers):
        """After POST, GET should return updated income types"""
        payload = {"income_types": ["salaried"], "primary_income_type": "salaried", "fy": "2025-26"}
        requests.post(f"{BASE_URL}/api/tax/income-profile", json=payload, headers=auth_headers)
        
        resp = requests.get(f"{BASE_URL}/api/tax/income-profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        profile = data.get("profile")
        assert profile is not None, "Profile should exist after POST"
        assert "salaried" in profile.get("income_types", []), \
            f"'salaried' not in income_types: {profile.get('income_types')}"
        print(f"[PASS] GET after POST - income_types={profile.get('income_types')}")

    def test_income_profile_requires_auth(self):
        """Income profile endpoints should require authentication"""
        resp = requests.get(f"{BASE_URL}/api/tax/income-profile")
        assert resp.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {resp.status_code}"
        print(f"[PASS] GET /api/tax/income-profile without auth - Status {resp.status_code}")


# ══════════════════════════════════════════
#  Phase 1.2: SALARY PROFILE Tests
# ══════════════════════════════════════════

class TestSalaryProfile:
    """Tests for GET/POST/DELETE /api/tax/salary-profile"""

    def test_get_salary_profile_returns_200(self, auth_headers):
        """GET salary profile should return 200"""
        resp = requests.get(f"{BASE_URL}/api/tax/salary-profile", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "profile" in data, f"'profile' key missing: {data}"
        print(f"[PASS] GET /api/tax/salary-profile - Status 200, has_profile={data['profile'] is not None}")

    def test_post_salary_profile_metro_city(self, auth_headers):
        """POST salary profile for Mumbai (metro) should auto-detect metro city type"""
        payload = {
            "fy": "2025-26",
            "employer_name": "TEST_Infosys",
            "employment_type": "salaried",
            "monthly_basic": 80000,
            "monthly_hra": 32000,
            "monthly_special_allowance": 15000,
            "monthly_lta": 0,
            "monthly_other_allowances": 0,
            "annual_bonus": 0,
            "employee_pf_monthly": 0,
            "professional_tax_annual": 0,
            "tds_monthly": 5000,
            "residence_city": "Mumbai",
            "state": "maharashtra",
            "is_rent_paid": True,
            "monthly_rent": 30000,
            "landlord_pan_available": False
        }
        resp = requests.post(f"{BASE_URL}/api/tax/salary-profile", json=payload, headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "profile" in data, f"'profile' key missing: {data}"
        profile = data["profile"]
        # Verify city_type is metro for Mumbai
        assert profile.get("city_type") == "metro", \
            f"Expected city_type='metro' for Mumbai, got '{profile.get('city_type')}'"
        # Verify hra_data is included
        assert "hra_data" in profile, f"'hra_data' missing from profile: {profile.keys()}"
        hra_data = profile["hra_data"]
        assert hra_data.get("applicable") == True, \
            f"HRA should be applicable with rent_paid=True: {hra_data}"
        print(f"[PASS] POST salary profile - city_type={profile['city_type']}, hra_exemption={hra_data.get('hra_exemption')}")

    def test_post_salary_profile_auto_calculates_epf(self, auth_headers):
        """POST salary profile with epf=0 should auto-calculate EPF at 12% of basic (capped at 1800)"""
        payload = {
            "fy": "2025-26",
            "employer_name": "TEST_Wipro",
            "monthly_basic": 60000,
            "monthly_hra": 24000,
            "employee_pf_monthly": 0,  # Should be auto-calculated
            "state": "karnataka",
            "residence_city": "Bengaluru",
            "is_rent_paid": False,
            "monthly_rent": 0
        }
        resp = requests.post(f"{BASE_URL}/api/tax/salary-profile", json=payload, headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        profile = resp.json()["profile"]
        # EPF should be auto-calculated: min(60000 * 0.12, 1800) = min(7200, 1800) = 1800
        assert profile.get("employee_pf_monthly") == 1800, \
            f"Expected auto EPF 1800 (capped), got {profile.get('employee_pf_monthly')}"
        print(f"[PASS] EPF auto-calculated: {profile.get('employee_pf_monthly')}")

    def test_post_salary_profile_auto_calculates_prof_tax(self, auth_headers):
        """POST salary profile with state and prof_tax=0 should auto-fill professional tax"""
        payload = {
            "fy": "2025-26",
            "employer_name": "TEST_TCS",
            "monthly_basic": 80000,
            "monthly_hra": 32000,
            "employee_pf_monthly": 1800,
            "professional_tax_annual": 0,  # Should be auto-filled
            "state": "maharashtra",
            "residence_city": "Mumbai",
            "is_rent_paid": False
        }
        resp = requests.post(f"{BASE_URL}/api/tax/salary-profile", json=payload, headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        profile = resp.json()["profile"]
        # Professional tax for Maharashtra = 2400
        assert profile.get("professional_tax_annual") == 2400, \
            f"Expected prof_tax=2400 for Maharashtra, got {profile.get('professional_tax_annual')}"
        print(f"[PASS] Professional tax auto-filled: {profile.get('professional_tax_annual')}")

    def test_salary_profile_hra_data_structure(self, auth_headers):
        """HRA data in salary profile response should have all required fields"""
        payload = {
            "fy": "2025-26",
            "employer_name": "TEST_HRA_Check",
            "monthly_basic": 80000,
            "monthly_hra": 32000,
            "state": "maharashtra",
            "residence_city": "Mumbai",
            "is_rent_paid": True,
            "monthly_rent": 30000
        }
        resp = requests.post(f"{BASE_URL}/api/tax/salary-profile", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        hra_data = resp.json()["profile"]["hra_data"]
        
        required_fields = ["applicable", "hra_exemption", "taxable_hra", "city_type",
                           "condition_1_actual_hra", "condition_2_city_pct", "condition_3_rent_minus_basic",
                           "limiting_condition", "monthly_benefit", "tax_saved_30_slab"]
        for field in required_fields:
            assert field in hra_data, f"Required field '{field}' missing from hra_data: {hra_data.keys()}"
        
        # Verify computation: metro Mumbai
        # c1 = 32000*12 = 384000
        # c2 = 80000*12*0.50 = 480000
        # c3 = 30000*12 - 80000*12*0.10 = 360000 - 96000 = 264000
        # exemption = min(384000, 480000, 264000) = 264000
        assert hra_data["hra_exemption"] == 264000.0, \
            f"HRA exemption computation error: expected 264000, got {hra_data['hra_exemption']}"
        assert hra_data["condition_1_actual_hra"] == 384000.0
        assert hra_data["condition_2_city_pct"] == 480000.0
        assert hra_data["condition_3_rent_minus_basic"] == 264000.0
        assert "Rent Paid" in hra_data["limiting_condition"], \
            f"Limiting condition should mention Rent Paid, got: {hra_data['limiting_condition']}"
        print(f"[PASS] HRA computation correct: exemption={hra_data['hra_exemption']}, limiting={hra_data['limiting_condition']}")

    def test_delete_salary_profile(self, auth_headers):
        """DELETE salary profile should return status:deleted"""
        # First create a profile
        requests.post(f"{BASE_URL}/api/tax/salary-profile", json={
            "employer_name": "TEST_Delete",
            "monthly_basic": 50000,
            "state": "delhi",
            "residence_city": "Delhi"
        }, headers=auth_headers)
        
        # Then delete
        resp = requests.delete(f"{BASE_URL}/api/tax/salary-profile", headers=auth_headers)
        assert resp.status_code == 200, f"DELETE failed: {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "deleted", f"Expected status:deleted, got {data}"
        print(f"[PASS] DELETE /api/tax/salary-profile - {data}")

    def test_salary_profile_after_delete_returns_null(self, auth_headers):
        """After DELETE, GET salary profile should return null"""
        # Delete first
        requests.delete(f"{BASE_URL}/api/tax/salary-profile", headers=auth_headers)
        # Check GET returns null
        resp = requests.get(f"{BASE_URL}/api/tax/salary-profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("profile") is None, \
            f"Expected null profile after delete, got {data.get('profile')}"
        print(f"[PASS] GET after DELETE returns null profile")


# ══════════════════════════════════════════
#  Phase 1.3: HRA CALCULATION Tests
# ══════════════════════════════════════════

class TestHRACalculation:
    """Tests for GET /api/tax/hra-calculation"""

    def test_hra_calculation_no_profile_returns_null(self, auth_headers):
        """With no salary profile, HRA calculation should return null hra_data"""
        # Delete salary profile first
        requests.delete(f"{BASE_URL}/api/tax/salary-profile", headers=auth_headers)
        
        resp = requests.get(f"{BASE_URL}/api/tax/hra-calculation", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("hra_data") is None, \
            f"Expected null hra_data without salary profile, got {data.get('hra_data')}"
        assert "message" in data, f"Expected message key when no profile: {data}"
        print(f"[PASS] GET /api/tax/hra-calculation without profile - hra_data=None, message={data.get('message')}")

    def test_hra_calculation_with_profile(self, auth_headers):
        """With salary profile, HRA calculation should return full breakdown"""
        # Set up salary profile
        requests.post(f"{BASE_URL}/api/tax/salary-profile", json={
            "employer_name": "TEST_TCS_HRA",
            "monthly_basic": 80000,
            "monthly_hra": 32000,
            "state": "maharashtra",
            "residence_city": "Mumbai",
            "is_rent_paid": True,
            "monthly_rent": 30000
        }, headers=auth_headers)
        
        resp = requests.get(f"{BASE_URL}/api/tax/hra-calculation", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        hra_data = data.get("hra_data")
        assert hra_data is not None, f"Expected hra_data, got None. Full response: {data}"
        assert hra_data.get("applicable") == True
        assert hra_data.get("hra_exemption") > 0, f"HRA exemption should be > 0"
        assert hra_data.get("city_type") == "metro"
        print(f"[PASS] GET /api/tax/hra-calculation - exemption={hra_data.get('hra_exemption')}, city={hra_data.get('city_type')}")

    def test_hra_not_applicable_without_rent(self, auth_headers):
        """HRA should not be applicable when is_rent_paid=False"""
        requests.post(f"{BASE_URL}/api/tax/salary-profile", json={
            "employer_name": "TEST_No_Rent",
            "monthly_basic": 80000,
            "monthly_hra": 32000,
            "state": "maharashtra",
            "residence_city": "Mumbai",
            "is_rent_paid": False,
            "monthly_rent": 0
        }, headers=auth_headers)
        
        resp = requests.get(f"{BASE_URL}/api/tax/hra-calculation", headers=auth_headers)
        assert resp.status_code == 200
        hra_data = resp.json().get("hra_data")
        assert hra_data is not None
        assert hra_data.get("applicable") == False, \
            f"HRA should NOT be applicable without rent paid: {hra_data}"
        assert hra_data.get("hra_exemption") == 0
        print(f"[PASS] HRA not applicable without rent - applicable={hra_data.get('applicable')}")

    def test_hra_non_metro_uses_40_percent(self, auth_headers):
        """Non-metro city should use 40% of basic for HRA condition 2"""
        requests.post(f"{BASE_URL}/api/tax/salary-profile", json={
            "employer_name": "TEST_Non_Metro",
            "monthly_basic": 60000,
            "monthly_hra": 24000,
            "state": "karnataka",
            "residence_city": "Mysore",  # Non-metro
            "is_rent_paid": True,
            "monthly_rent": 20000
        }, headers=auth_headers)
        
        resp = requests.get(f"{BASE_URL}/api/tax/hra-calculation", headers=auth_headers)
        assert resp.status_code == 200
        hra_data = resp.json().get("hra_data")
        assert hra_data is not None
        assert hra_data.get("city_type") == "non_metro", \
            f"Expected non_metro for Mysore, got {hra_data.get('city_type')}"
        # c2 should be 40% of basic for non-metro: 60000 * 12 * 0.40 = 288000
        expected_c2 = 60000 * 12 * 0.40
        assert hra_data.get("condition_2_city_pct") == expected_c2, \
            f"Expected condition_2={expected_c2} for non-metro, got {hra_data.get('condition_2_city_pct')}"
        print(f"[PASS] Non-metro HRA uses 40%: condition_2={hra_data.get('condition_2_city_pct')}")


# ══════════════════════════════════════════
#  Phase 1.4: 80C SUMMARY Tests
# ══════════════════════════════════════════

class TestSection80CSummary:
    """Tests for GET /api/tax/80c-summary"""

    def test_80c_summary_returns_200(self, auth_headers):
        """GET 80C summary should return 200 with all required fields"""
        resp = requests.get(f"{BASE_URL}/api/tax/80c-summary?fy=2025-26", headers=auth_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        required_fields = ["fy", "instruments_80c", "total_80c", "limit_80c", "remaining_80c",
                           "utilization_percentage", "status", "recommendation",
                           "nps_80ccd_1b", "total_nps", "nps_limit", "nps_remaining", "nps_utilization_pct"]
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from 80C summary: {data.keys()}"
        print(f"[PASS] GET /api/tax/80c-summary - total_80c={data['total_80c']}, util={data['utilization_percentage']}%")

    def test_80c_summary_limit_is_150000(self, auth_headers):
        """80C limit should be 150000"""
        resp = requests.get(f"{BASE_URL}/api/tax/80c-summary?fy=2025-26", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("limit_80c") == 150000, \
            f"80C limit should be 150000, got {data.get('limit_80c')}"
        print(f"[PASS] 80C limit = {data.get('limit_80c')}")

    def test_80c_summary_nps_limit_is_50000(self, auth_headers):
        """NPS 80CCD(1B) additional limit should be 50000"""
        resp = requests.get(f"{BASE_URL}/api/tax/80c-summary?fy=2025-26", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("nps_limit") == 50000, \
            f"NPS limit should be 50000, got {data.get('nps_limit')}"
        print(f"[PASS] NPS limit = {data.get('nps_limit')}")

    def test_80c_summary_status_valid_values(self, auth_headers):
        """Status should be one of: optimized, good, under_utilized"""
        resp = requests.get(f"{BASE_URL}/api/tax/80c-summary?fy=2025-26", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        valid_statuses = ["optimized", "good", "under_utilized"]
        assert data.get("status") in valid_statuses, \
            f"Status '{data.get('status')}' not in {valid_statuses}"
        print(f"[PASS] Status = {data.get('status')}")

    def test_80c_summary_instruments_list_structure(self, auth_headers):
        """Instruments list should have name and amount fields"""
        resp = requests.get(f"{BASE_URL}/api/tax/80c-summary?fy=2025-26", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        instruments = data.get("instruments_80c", [])
        for inst in instruments:
            assert "name" in inst, f"Instrument missing 'name': {inst}"
            assert "amount" in inst, f"Instrument missing 'amount': {inst}"
            assert isinstance(inst["amount"], (int, float)), \
                f"Instrument amount should be numeric: {inst['amount']}"
        print(f"[PASS] Instruments list ({len(instruments)} items) - all have name+amount")

    def test_80c_includes_epf_from_salary_profile(self, auth_headers):
        """If salary profile has EPF, it should appear in 80C instruments"""
        # Setup salary profile with EPF
        requests.post(f"{BASE_URL}/api/tax/salary-profile", json={
            "employer_name": "TEST_EPF_Check",
            "monthly_basic": 80000,
            "monthly_hra": 32000,
            "employee_pf_monthly": 1800,
            "state": "maharashtra",
            "residence_city": "Mumbai",
            "is_rent_paid": False
        }, headers=auth_headers)
        
        resp = requests.get(f"{BASE_URL}/api/tax/80c-summary?fy=2025-26", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        instruments = data.get("instruments_80c", [])
        instrument_names = [i["name"].lower() for i in instruments]
        has_epf = any("epf" in n or "provident fund" in n for n in instrument_names)
        assert has_epf, f"EPF should appear in 80C instruments when salary profile has EPF. Found: {instrument_names}"
        print(f"[PASS] EPF from salary profile in 80C instruments: {instrument_names}")

    def test_80c_remaining_80c_is_consistent(self, auth_headers):
        """remaining_80c should = limit_80c - total_80c"""
        resp = requests.get(f"{BASE_URL}/api/tax/80c-summary?fy=2025-26", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        expected_remaining = max(0, data["limit_80c"] - data["total_80c"])
        # Allow minor float rounding
        assert abs(data["remaining_80c"] - expected_remaining) < 1.0, \
            f"remaining_80c={data['remaining_80c']} should be ~{expected_remaining}"
        print(f"[PASS] remaining_80c consistency: {data['remaining_80c']} = {data['limit_80c']} - {data['total_80c']}")

    def test_80c_requires_auth(self):
        """80C summary endpoint should require authentication"""
        resp = requests.get(f"{BASE_URL}/api/tax/80c-summary")
        assert resp.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {resp.status_code}"
        print(f"[PASS] 80C summary requires auth - Status {resp.status_code}")


# ══════════════════════════════════════════
#  Phase 1.1: REMAP TRANSACTIONS Test
# ══════════════════════════════════════════

class TestRemapTransactions:
    """Tests for POST /api/tax/remap-transactions"""

    def test_remap_transactions_returns_200(self, auth_headers):
        """POST remap-transactions should return 200 with status:remapped"""
        resp = requests.post(
            f"{BASE_URL}/api/tax/remap-transactions?fy=2025-26",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "remapped", f"Expected status:remapped, got {data.get('status')}"
        assert "fy" in data, "Missing 'fy' in response"
        assert "total_found" in data, "Missing 'total_found' in response"
        assert "high_confidence" in data, "Missing 'high_confidence' in response"
        assert "needs_review" in data, "Missing 'needs_review' in response"
        print(f"[PASS] POST /api/tax/remap-transactions - {data}")


# ══════════════════════════════════════════
#  State Professional Tax API Test
# ══════════════════════════════════════════

class TestStateProfTax:
    """Tests for GET /api/tax/state-prof-tax"""

    def test_maharashtra_prof_tax(self):
        """Maharashtra professional tax should be 2400"""
        resp = requests.get(f"{BASE_URL}/api/tax/state-prof-tax?state=maharashtra")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get("professional_tax_annual") == 2400, \
            f"Maharashtra prof_tax should be 2400, got {data.get('professional_tax_annual')}"
        print(f"[PASS] Maharashtra prof_tax = {data.get('professional_tax_annual')}")

    def test_delhi_no_prof_tax(self):
        """Delhi should have no professional tax"""
        resp = requests.get(f"{BASE_URL}/api/tax/state-prof-tax?state=delhi")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("professional_tax_annual") == 0, \
            f"Delhi prof_tax should be 0, got {data.get('professional_tax_annual')}"
        print(f"[PASS] Delhi prof_tax = 0")

    def test_tamil_nadu_prof_tax(self):
        """Tamil Nadu professional tax should be 1200"""
        resp = requests.get(f"{BASE_URL}/api/tax/state-prof-tax?state=tamil%20nadu")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("professional_tax_annual") == 1200, \
            f"Tamil Nadu prof_tax should be 1200, got {data.get('professional_tax_annual')}"
        print(f"[PASS] Tamil Nadu prof_tax = {data.get('professional_tax_annual')}")


# ══════════════════════════════════════════
#  Health Check
# ══════════════════════════════════════════

def test_health_check():
    """Backend health check"""
    resp = requests.get(f"{BASE_URL}/api/health")
    assert resp.status_code == 200
    print(f"[PASS] Health check OK: {resp.json()}")


# Restore salary profile for subsequent UI tests
@pytest.fixture(autouse=True, scope="session")
def restore_salary_profile(auth_token):
    """After all tests, restore the original salary profile"""
    yield
    # Restore demo salary profile (Tata Consultancy, Mumbai)
    headers = {"Authorization": f"Bearer {auth_token}"}
    requests.post(f"{BASE_URL}/api/tax/salary-profile", json={
        "fy": "2025-26",
        "employer_name": "Tata Consultancy",
        "employment_type": "salaried",
        "monthly_basic": 80000,
        "monthly_hra": 32000,
        "monthly_special_allowance": 0,
        "annual_bonus": 0,
        "employee_pf_monthly": 1800,
        "professional_tax_annual": 2400,
        "tds_monthly": 0,
        "residence_city": "Mumbai",
        "state": "maharashtra",
        "city_type": "metro",
        "is_rent_paid": True,
        "monthly_rent": 30000,
        "landlord_pan_available": False
    }, headers=headers)
    # Restore income profile
    requests.post(f"{BASE_URL}/api/tax/income-profile", json={
        "income_types": ["salaried"],
        "primary_income_type": "salaried",
        "fy": "2025-26"
    }, headers=headers)
    print("[RESTORE] Demo salary + income profile restored")
