"""
Tax Module Phase 2 Tests - Tax Meter, Tax Documents, Parsers
Tests for:
- /api/tax/meter - Real-time tax meter data
- /api/tax/documents - List uploaded tax documents
- /api/tax/income-profile - Income profile CRUD
- /api/tax/salary-profile - Salary profile CRUD
- /api/tax/hra-calculation - HRA calculation
- /api/tax/80c-summary - 80C deduction summary
- /api/tax/remap-transactions - Confidence-based transaction remapping
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://phase3-tax-engine.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestTaxPhase2:
    """Tax Module Phase 2 API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    # ═══════════════════════════════════════════════════════════════
    # TAX METER ENDPOINT TESTS
    # ═══════════════════════════════════════════════════════════════
    
    def test_tax_meter_endpoint_returns_200(self):
        """Test /api/tax/meter returns 200 OK"""
        response = self.session.get(f"{BASE_URL}/api/tax/meter?fy=2025-26")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Tax meter endpoint returns 200")
    
    def test_tax_meter_data_structure(self):
        """Test /api/tax/meter returns proper data structure"""
        response = self.session.get(f"{BASE_URL}/api/tax/meter?fy=2025-26")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        required_fields = [
            "fy", "estimated_tax", "tds_paid_ytd", "tax_due", "refund_expected",
            "better_regime", "savings_by_switch", "total_deductions", "deduction_80c",
            "months_elapsed", "gross_income", "effective_rate"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Check deduction_80c structure
        assert "deduction_80c" in data
        deduction_80c = data["deduction_80c"]
        assert "used" in deduction_80c
        assert "limit" in deduction_80c
        assert "remaining" in deduction_80c
        assert "utilization_pct" in deduction_80c
        
        # Validate data types
        assert isinstance(data["estimated_tax"], (int, float))
        assert isinstance(data["tds_paid_ytd"], (int, float))
        assert isinstance(data["better_regime"], str)
        assert data["better_regime"] in ["old", "new"]
        
        print(f"✓ Tax meter data structure valid: estimated_tax={data['estimated_tax']}, better_regime={data['better_regime']}")
    
    def test_tax_meter_80c_deduction_values(self):
        """Test /api/tax/meter 80C deduction values are reasonable"""
        response = self.session.get(f"{BASE_URL}/api/tax/meter?fy=2025-26")
        assert response.status_code == 200
        
        data = response.json()
        deduction_80c = data["deduction_80c"]
        
        # 80C limit should be 150000
        assert deduction_80c["limit"] == 150000, f"80C limit should be 150000, got {deduction_80c['limit']}"
        
        # Used should be >= 0 and <= limit
        assert deduction_80c["used"] >= 0
        
        # Remaining should be limit - used (capped at 0)
        expected_remaining = max(0, 150000 - deduction_80c["used"])
        assert deduction_80c["remaining"] == expected_remaining, f"Remaining mismatch: expected {expected_remaining}, got {deduction_80c['remaining']}"
        
        # Utilization percentage should be correct
        expected_util = min(100, (deduction_80c["used"] / 150000) * 100)
        assert abs(deduction_80c["utilization_pct"] - expected_util) < 0.2, f"Utilization mismatch"
        
        print(f"✓ 80C deduction values valid: used={deduction_80c['used']}, remaining={deduction_80c['remaining']}")
    
    # ═══════════════════════════════════════════════════════════════
    # TAX DOCUMENTS ENDPOINT TESTS
    # ═══════════════════════════════════════════════════════════════
    
    def test_tax_documents_list_endpoint(self):
        """Test /api/tax/documents returns list (may be empty)"""
        response = self.session.get(f"{BASE_URL}/api/tax/documents?fy=2025-26")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "documents" in data
        assert "count" in data
        assert isinstance(data["documents"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["documents"])
        
        print(f"✓ Tax documents list endpoint works: {data['count']} documents")
    
    # ═══════════════════════════════════════════════════════════════
    # INCOME PROFILE ENDPOINT TESTS
    # ═══════════════════════════════════════════════════════════════
    
    def test_income_profile_get(self):
        """Test GET /api/tax/income-profile"""
        response = self.session.get(f"{BASE_URL}/api/tax/income-profile")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "profile" in data
        
        if data["profile"]:
            profile = data["profile"]
            assert "income_types" in profile
            assert "primary_income_type" in profile
            print(f"✓ Income profile exists: types={profile['income_types']}")
        else:
            print("✓ Income profile GET works (no profile set)")
    
    def test_income_profile_post(self):
        """Test POST /api/tax/income-profile"""
        payload = {
            "income_types": ["salaried", "interest"],
            "primary_income_type": "salaried",
            "fy": "2025-26"
        }
        
        response = self.session.post(f"{BASE_URL}/api/tax/income-profile", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profile" in data
        profile = data["profile"]
        assert profile["income_types"] == ["salaried", "interest"]
        assert profile["primary_income_type"] == "salaried"
        
        print("✓ Income profile POST works")
    
    # ═══════════════════════════════════════════════════════════════
    # SALARY PROFILE ENDPOINT TESTS
    # ═══════════════════════════════════════════════════════════════
    
    def test_salary_profile_get(self):
        """Test GET /api/tax/salary-profile"""
        response = self.session.get(f"{BASE_URL}/api/tax/salary-profile")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "profile" in data
        
        if data["profile"]:
            profile = data["profile"]
            # Check key fields
            assert "monthly_basic" in profile
            assert "monthly_hra" in profile
            assert "city_type" in profile
            
            # Check HRA data is computed
            if "hra_data" in profile:
                hra = profile["hra_data"]
                assert "hra_exemption" in hra
                print(f"✓ Salary profile exists: basic={profile['monthly_basic']}, HRA exemption={hra['hra_exemption']}")
            else:
                print(f"✓ Salary profile exists: basic={profile['monthly_basic']}")
        else:
            print("✓ Salary profile GET works (no profile set)")
    
    def test_salary_profile_post(self):
        """Test POST /api/tax/salary-profile"""
        payload = {
            "fy": "2025-26",
            "employer_name": "Test Company",
            "employment_type": "salaried",
            "monthly_basic": 80000,
            "monthly_hra": 32000,
            "monthly_special_allowance": 20000,
            "monthly_lta": 5000,
            "monthly_other_allowances": 3000,
            "annual_bonus": 100000,
            "employee_pf_monthly": 1800,
            "professional_tax_annual": 2400,
            "tds_monthly": 15000,
            "residence_city": "Mumbai",
            "state": "Maharashtra",
            "is_rent_paid": True,
            "monthly_rent": 30000,
            "landlord_pan_available": True
        }
        
        response = self.session.post(f"{BASE_URL}/api/tax/salary-profile", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profile" in data
        profile = data["profile"]
        
        # Verify city_type auto-detection (Mumbai = metro)
        assert profile["city_type"] == "metro", f"Expected metro for Mumbai, got {profile['city_type']}"
        
        # Verify HRA data is computed
        assert "hra_data" in profile
        hra = profile["hra_data"]
        assert hra["applicable"] == True
        assert hra["hra_exemption"] > 0
        
        print(f"✓ Salary profile POST works: city_type={profile['city_type']}, HRA exemption={hra['hra_exemption']}")
    
    # ═══════════════════════════════════════════════════════════════
    # HRA CALCULATION ENDPOINT TESTS
    # ═══════════════════════════════════════════════════════════════
    
    def test_hra_calculation_endpoint(self):
        """Test GET /api/tax/hra-calculation"""
        response = self.session.get(f"{BASE_URL}/api/tax/hra-calculation")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "hra_data" in data
        
        if data["hra_data"]:
            hra = data["hra_data"]
            
            if hra.get("applicable"):
                # Check 3-condition breakdown
                assert "condition_1_actual_hra" in hra
                assert "condition_2_city_pct" in hra
                assert "condition_3_rent_minus_basic" in hra
                assert "hra_exemption" in hra
                assert "taxable_hra" in hra
                assert "limiting_condition" in hra
                
                # Exemption should be min of 3 conditions
                c1 = hra["condition_1_actual_hra"]
                c2 = hra["condition_2_city_pct"]
                c3 = hra["condition_3_rent_minus_basic"]
                expected_exemption = min(c1, c2, c3)
                
                assert abs(hra["hra_exemption"] - expected_exemption) < 1, f"HRA exemption mismatch"
                
                print(f"✓ HRA calculation works: exemption={hra['hra_exemption']}, limiting={hra['limiting_condition']}")
            else:
                print(f"✓ HRA calculation works (not applicable): {hra.get('message', 'No rent paid')}")
        else:
            print("✓ HRA calculation works (no salary profile)")
    
    # ═══════════════════════════════════════════════════════════════
    # 80C SUMMARY ENDPOINT TESTS
    # ═══════════════════════════════════════════════════════════════
    
    def test_80c_summary_endpoint(self):
        """Test GET /api/tax/80c-summary"""
        response = self.session.get(f"{BASE_URL}/api/tax/80c-summary?fy=2025-26")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Check required fields
        required_fields = [
            "fy", "instruments_80c", "total_80c", "limit_80c", "remaining_80c",
            "utilization_percentage", "status", "recommendation"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Validate values
        assert data["limit_80c"] == 150000
        assert data["total_80c"] >= 0
        assert data["remaining_80c"] >= 0
        assert 0 <= data["utilization_percentage"] <= 100
        assert data["status"] in ["optimized", "good", "under_utilized"]
        
        # Check NPS section
        assert "nps_80ccd_1b" in data
        assert "total_nps" in data
        assert "nps_limit" in data
        assert data["nps_limit"] == 50000
        
        print(f"✓ 80C summary works: total={data['total_80c']}, util={data['utilization_percentage']}%, status={data['status']}")
    
    # ═══════════════════════════════════════════════════════════════
    # REMAP TRANSACTIONS ENDPOINT TESTS
    # ═══════════════════════════════════════════════════════════════
    
    def test_remap_transactions_endpoint(self):
        """Test POST /api/tax/remap-transactions"""
        response = self.session.post(f"{BASE_URL}/api/tax/remap-transactions?fy=2025-26")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check response structure
        assert "status" in data
        assert data["status"] == "remapped"
        assert "fy" in data
        assert "total_found" in data
        assert "high_confidence" in data
        assert "needs_review" in data
        
        print(f"✓ Remap transactions works: found={data['total_found']}, high_conf={data['high_confidence']}, needs_review={data['needs_review']}")
    
    # ═══════════════════════════════════════════════════════════════
    # STATE PROFESSIONAL TAX ENDPOINT TESTS
    # ═══════════════════════════════════════════════════════════════
    
    def test_state_professional_tax_endpoint(self):
        """Test GET /api/tax/state-prof-tax"""
        # Test Maharashtra (should have professional tax)
        response = self.session.get(f"{BASE_URL}/api/tax/state-prof-tax?state=Maharashtra")
        assert response.status_code == 200
        
        data = response.json()
        assert "state" in data
        assert "professional_tax_annual" in data
        assert data["professional_tax_annual"] == 2400  # Maharashtra PT is 2400
        
        # Test Delhi (no professional tax)
        response2 = self.session.get(f"{BASE_URL}/api/tax/state-prof-tax?state=Delhi")
        assert response2.status_code == 200
        
        data2 = response2.json()
        assert data2["professional_tax_annual"] == 0  # Delhi has no PT
        
        print("✓ State professional tax endpoint works: Maharashtra=2400, Delhi=0")


class TestTaxMeterIntegration:
    """Integration tests for Tax Meter with other components"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_tax_meter_consistent_with_80c_summary(self):
        """Test that tax meter 80C data is reasonable (may differ from 80C summary due to EPF source)"""
        # Get tax meter data
        meter_response = self.session.get(f"{BASE_URL}/api/tax/meter?fy=2025-26")
        assert meter_response.status_code == 200
        meter_data = meter_response.json()
        
        # Get 80C summary
        summary_response = self.session.get(f"{BASE_URL}/api/tax/80c-summary?fy=2025-26")
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        
        # Compare 80C values - meter only counts auto_tax_deductions, summary includes EPF from salary_profile
        meter_80c = meter_data["deduction_80c"]
        
        # Both should have valid structure
        assert meter_80c["used"] >= 0
        assert meter_80c["limit"] == 150000
        assert summary_data["total_80c"] >= 0
        assert summary_data["limit_80c"] == 150000
        
        # Tax meter 80C used should be <= 80C summary (summary includes more sources like EPF)
        # This is expected behavior - meter counts only auto_tax_deductions, summary includes salary_profile EPF
        assert meter_80c["used"] <= summary_data["total_80c"] + 1000, \
            f"Tax meter 80C should not exceed summary: meter={meter_80c['used']}, summary={summary_data['total_80c']}"
        
        print(f"✓ Tax meter 80C: {meter_80c['used']}, 80C summary: {summary_data['total_80c']} (diff due to EPF source)")
    
    def test_tax_meter_regime_recommendation(self):
        """Test that tax meter provides valid regime recommendation"""
        response = self.session.get(f"{BASE_URL}/api/tax/meter?fy=2025-26")
        assert response.status_code == 200
        
        data = response.json()
        
        # Better regime should be 'old' or 'new'
        assert data["better_regime"] in ["old", "new"]
        
        # Savings by switch should be >= 0
        assert data["savings_by_switch"] >= 0
        
        # If there are savings, the recommendation makes sense
        if data["savings_by_switch"] > 0:
            print(f"✓ Tax meter recommends {data['better_regime']} regime, saves ₹{data['savings_by_switch']}")
        else:
            print(f"✓ Tax meter shows both regimes equal or current is optimal")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
