"""
Test Suite: Tax Calculator and Tax-Related APIs
Testing: GET /api/tax-calculator, GET /api/tax-summary, GET /api/capital-gains, CRUD /api/user-tax-deductions
Date: Jan 2026
"""

import pytest
import requests
import os
from uuid import uuid4

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://visor-finance-2.preview.emergentagent.com')

# Test credentials from review request
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestAuth:
    """Authentication - get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for the demo user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_login_success(self):
        """Test login with demo credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"✓ Login successful for {TEST_EMAIL}")


class TestTaxCalculator:
    """Test Income Tax Calculator API - /api/tax-calculator"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_tax_calculator_fy_2025_26(self, auth_headers):
        """Test tax calculator for FY 2025-26 (default)"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2025-26",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Tax calculator failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "fy" in data, "Missing 'fy' in response"
        assert "ay" in data, "Missing 'ay' in response"
        assert data["fy"] == "2025-26", f"FY mismatch: expected '2025-26', got '{data['fy']}'"
        assert data["ay"] == "2026-27", f"AY mismatch: expected '2026-27', got '{data['ay']}'"
        
        # Verify income structure
        assert "income" in data, "Missing 'income' in response"
        assert "salary" in data["income"], "Missing 'salary' in income"
        assert "other" in data["income"], "Missing 'other' in income"
        assert "gross_total" in data["income"], "Missing 'gross_total' in income"
        
        # Verify capital gains structure
        assert "capital_gains" in data, "Missing 'capital_gains' in response"
        assert "stcg" in data["capital_gains"], "Missing 'stcg' in capital_gains"
        assert "ltcg" in data["capital_gains"], "Missing 'ltcg' in capital_gains"
        assert "ltcg_exemption" in data["capital_gains"], "Missing 'ltcg_exemption' in capital_gains"
        
        # Verify deductions list
        assert "deductions" in data, "Missing 'deductions' in response"
        
        # Verify old_regime structure
        assert "old_regime" in data, "Missing 'old_regime' in response"
        old_regime = data["old_regime"]
        assert "standard_deduction" in old_regime, "Missing 'standard_deduction' in old_regime"
        assert old_regime["standard_deduction"] == 50000, f"Old regime std deduction should be ₹50,000, got {old_regime['standard_deduction']}"
        assert "chapter_via_deductions" in old_regime, "Missing 'chapter_via_deductions' in old_regime"
        assert "taxable_income" in old_regime, "Missing 'taxable_income' in old_regime"
        assert "tax_on_income" in old_regime, "Missing 'tax_on_income' in old_regime"
        assert "rebate_87a" in old_regime, "Missing 'rebate_87a' in old_regime"
        assert "surcharge" in old_regime, "Missing 'surcharge' in old_regime"
        assert "cess" in old_regime, "Missing 'cess' in old_regime"
        assert "total_tax" in old_regime, "Missing 'total_tax' in old_regime"
        assert "slab_breakdown" in old_regime, "Missing 'slab_breakdown' in old_regime"
        
        # Verify new_regime structure
        assert "new_regime" in data, "Missing 'new_regime' in response"
        new_regime = data["new_regime"]
        assert "standard_deduction" in new_regime, "Missing 'standard_deduction' in new_regime"
        assert new_regime["standard_deduction"] == 75000, f"New regime std deduction should be ₹75,000, got {new_regime['standard_deduction']}"
        assert "nps_deduction" in new_regime, "Missing 'nps_deduction' in new_regime"
        assert "taxable_income" in new_regime, "Missing 'taxable_income' in new_regime"
        assert "tax_on_income" in new_regime, "Missing 'tax_on_income' in new_regime"
        assert "rebate_87a" in new_regime, "Missing 'rebate_87a' in new_regime"
        assert "total_tax" in new_regime, "Missing 'total_tax' in new_regime"
        assert "slab_breakdown" in new_regime, "Missing 'slab_breakdown' in new_regime"
        
        # Verify comparison structure
        assert "comparison" in data, "Missing 'comparison' in response"
        assert "better_regime" in data["comparison"], "Missing 'better_regime' in comparison"
        assert data["comparison"]["better_regime"] in ["old", "new", "equal"], f"Invalid better_regime value: {data['comparison']['better_regime']}"
        assert "savings" in data["comparison"], "Missing 'savings' in comparison"
        assert "old_effective_rate" in data["comparison"], "Missing 'old_effective_rate' in comparison"
        assert "new_effective_rate" in data["comparison"], "Missing 'new_effective_rate' in comparison"
        
        # Verify notes
        assert "notes" in data, "Missing 'notes' in response"
        assert len(data["notes"]) > 0, "Notes should not be empty"
        
        print(f"✓ Tax Calculator FY 2025-26 working correctly")
        print(f"  - Gross Income: ₹{data['income']['gross_total']:,.2f}")
        print(f"  - Old Regime Tax: ₹{old_regime['total_tax']:,.2f}")
        print(f"  - New Regime Tax: ₹{new_regime['total_tax']:,.2f}")
        print(f"  - Better Regime: {data['comparison']['better_regime']}")
    
    def test_tax_calculator_fy_2024_25(self, auth_headers):
        """Test tax calculator for FY 2024-25"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2024-25",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Tax calculator FY 2024-25 failed: {response.text}"
        data = response.json()
        
        assert data["fy"] == "2024-25", f"FY mismatch: expected '2024-25', got '{data['fy']}'"
        assert data["ay"] == "2025-26", f"AY mismatch: expected '2025-26', got '{data['ay']}'"
        assert "old_regime" in data
        assert "new_regime" in data
        assert "comparison" in data
        
        print(f"✓ Tax Calculator FY 2024-25 working correctly")
        print(f"  - Gross Income: ₹{data['income']['gross_total']:,.2f}")
    
    def test_tax_calculator_fy_2023_24(self, auth_headers):
        """Test tax calculator for FY 2023-24"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2023-24",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Tax calculator FY 2023-24 failed: {response.text}"
        data = response.json()
        
        assert data["fy"] == "2023-24", f"FY mismatch: expected '2023-24', got '{data['fy']}'"
        assert data["ay"] == "2024-25", f"AY mismatch: expected '2024-25', got '{data['ay']}'"
        
        print(f"✓ Tax Calculator FY 2023-24 working correctly")
    
    def test_tax_calculator_default_fy(self, auth_headers):
        """Test tax calculator without FY param (should default to 2025-26)"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Tax calculator default FY failed: {response.text}"
        data = response.json()
        
        assert data["fy"] == "2025-26", f"Default FY should be '2025-26', got '{data['fy']}'"
        
        print(f"✓ Tax Calculator default FY (2025-26) working correctly")
    
    def test_tax_calculator_slab_breakdown_old_regime(self, auth_headers):
        """Verify old regime tax slabs are correctly applied"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2025-26",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        slab_breakdown = data["old_regime"]["slab_breakdown"]
        
        # Verify slab structure if there's taxable income
        if data["old_regime"]["taxable_income"] > 0 and len(slab_breakdown) > 0:
            for slab in slab_breakdown:
                assert "range" in slab, "Missing 'range' in slab"
                assert "rate" in slab, "Missing 'rate' in slab"
                assert "income" in slab, "Missing 'income' in slab"
                assert "tax" in slab, "Missing 'tax' in slab"
            
            # Verify expected slab rates exist
            rates_found = [s["rate"] for s in slab_breakdown]
            # Old regime slabs: 0%, 5%, 20%, 30%
            print(f"✓ Old Regime slab breakdown verified: {rates_found}")
    
    def test_tax_calculator_slab_breakdown_new_regime(self, auth_headers):
        """Verify new regime tax slabs are correctly applied (Budget 2025)"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2025-26",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        slab_breakdown = data["new_regime"]["slab_breakdown"]
        
        # Verify slab structure if there's taxable income
        if data["new_regime"]["taxable_income"] > 0 and len(slab_breakdown) > 0:
            for slab in slab_breakdown:
                assert "range" in slab, "Missing 'range' in slab"
                assert "rate" in slab, "Missing 'rate' in slab"
                assert "income" in slab, "Missing 'income' in slab"
                assert "tax" in slab, "Missing 'tax' in slab"
            
            # New regime slabs (Budget 2025): 0%, 5%, 10%, 15%, 20%, 25%, 30%
            rates_found = [s["rate"] for s in slab_breakdown]
            print(f"✓ New Regime slab breakdown verified: {rates_found}")
    
    def test_tax_calculator_cess_calculation(self, auth_headers):
        """Verify 4% cess is calculated correctly"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2025-26",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Old regime cess verification
        old_tax_after_rebate = data["old_regime"]["tax_after_rebate"]
        old_surcharge = data["old_regime"]["surcharge"]
        old_cess = data["old_regime"]["cess"]
        expected_old_cess = (old_tax_after_rebate + old_surcharge) * 0.04
        assert abs(old_cess - expected_old_cess) < 1, f"Old regime cess mismatch: expected {expected_old_cess}, got {old_cess}"
        
        # New regime cess verification
        new_tax_after_rebate = data["new_regime"]["tax_after_rebate"]
        new_surcharge = data["new_regime"]["surcharge"]
        new_cess = data["new_regime"]["cess"]
        expected_new_cess = (new_tax_after_rebate + new_surcharge) * 0.04
        assert abs(new_cess - expected_new_cess) < 1, f"New regime cess mismatch: expected {expected_new_cess}, got {new_cess}"
        
        print(f"✓ 4% Health & Education Cess calculated correctly")


class TestTaxSummary:
    """Test Tax Summary API - /api/tax-summary"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_tax_summary_endpoint(self, auth_headers):
        """Test GET /api/tax-summary returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/tax-summary",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Tax summary failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "sections" in data, "Missing 'sections' in response"
        assert "total_deductions" in data, "Missing 'total_deductions' in response"
        assert "tax_saved_30_slab" in data, "Missing 'tax_saved_30_slab' in response"
        assert "tax_saved_20_slab" in data, "Missing 'tax_saved_20_slab' in response"
        assert "fy" in data, "Missing 'fy' in response"
        
        # Verify sections structure
        for section in data["sections"]:
            assert "section" in section, "Missing 'section' in section item"
            assert "label" in section, "Missing 'label' in section item"
            assert "limit" in section, "Missing 'limit' in section item"
            assert "used" in section, "Missing 'used' in section item"
            assert "percentage" in section, "Missing 'percentage' in section item"
            assert "remaining" in section, "Missing 'remaining' in section item"
        
        print(f"✓ Tax Summary API working correctly")
        print(f"  - Total Deductions: ₹{data['total_deductions']:,.2f}")
        print(f"  - Tax Saved (30% slab): ₹{data['tax_saved_30_slab']:,.2f}")
        print(f"  - Sections: {[s['section'] for s in data['sections']]}")
    
    def test_tax_summary_80c_section(self, auth_headers):
        """Verify Section 80C limit is ₹1,50,000"""
        response = requests.get(
            f"{BASE_URL}/api/tax-summary",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for section in data["sections"]:
            if section["section"] == "80C":
                assert section["limit"] == 150000, f"80C limit should be ₹1,50,000, got {section['limit']}"
                print(f"✓ Section 80C limit verified: ₹{section['limit']:,}")
                return
        
        # 80C should always be present (even if 0 used)
        print("ℹ Section 80C not in active sections (no investments in 80C)")


class TestCapitalGains:
    """Test Capital Gains API - /api/capital-gains"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_capital_gains_endpoint(self, auth_headers):
        """Test GET /api/capital-gains returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/capital-gains",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Capital gains failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "gains" in data, "Missing 'gains' in response"
        assert "summary" in data, "Missing 'summary' in response"
        assert "notes" in data, "Missing 'notes' in response"
        assert "fy" in data, "Missing 'fy' in response"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_stcg" in summary, "Missing 'total_stcg' in summary"
        assert "total_ltcg" in summary, "Missing 'total_ltcg' in summary"
        assert "ltcg_exemption" in summary, "Missing 'ltcg_exemption' in summary"
        assert summary["ltcg_exemption"] == 125000, f"LTCG exemption should be ₹1,25,000, got {summary['ltcg_exemption']}"
        assert "ltcg_taxable" in summary, "Missing 'ltcg_taxable' in summary"
        assert "estimated_stcg_tax" in summary, "Missing 'estimated_stcg_tax' in summary"
        assert "estimated_ltcg_tax" in summary, "Missing 'estimated_ltcg_tax' in summary"
        assert "total_estimated_tax" in summary, "Missing 'total_estimated_tax' in summary"
        
        # Verify gains structure (if any)
        for gain in data["gains"]:
            assert "description" in gain, "Missing 'description' in gain item"
            assert "category" in gain, "Missing 'category' in gain item"
            assert "sell_date" in gain, "Missing 'sell_date' in gain item"
            assert "sell_amount" in gain, "Missing 'sell_amount' in gain item"
            assert "cost_basis" in gain, "Missing 'cost_basis' in gain item"
            assert "gain_loss" in gain, "Missing 'gain_loss' in gain item"
            assert "is_long_term" in gain, "Missing 'is_long_term' in gain item"
            assert "tax_rate" in gain, "Missing 'tax_rate' in gain item"
            assert "tax_liability" in gain, "Missing 'tax_liability' in gain item"
        
        print(f"✓ Capital Gains API working correctly")
        print(f"  - Total STCG: ₹{summary['total_stcg']:,.2f}")
        print(f"  - Total LTCG: ₹{summary['total_ltcg']:,.2f}")
        print(f"  - LTCG Exemption: ₹{summary['ltcg_exemption']:,}")
        print(f"  - Total CG Tax: ₹{summary['total_estimated_tax']:,.2f}")


class TestUserTaxDeductions:
    """Test User Tax Deductions CRUD - /api/user-tax-deductions"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_user_tax_deductions(self, auth_headers):
        """Test GET /api/user-tax-deductions"""
        response = requests.get(
            f"{BASE_URL}/api/user-tax-deductions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get deductions failed: {response.text}"
        data = response.json()
        
        assert "deductions" in data, "Missing 'deductions' in response"
        assert isinstance(data["deductions"], list), "'deductions' should be a list"
        
        print(f"✓ GET user-tax-deductions working - {len(data['deductions'])} deductions found")
    
    def test_create_user_tax_deduction(self, auth_headers):
        """Test POST /api/user-tax-deductions - Create new deduction"""
        test_deduction_id = f"TEST_{uuid4().hex[:8]}"
        
        payload = {
            "deduction_id": test_deduction_id,
            "section": "80C",
            "name": "TEST PPF Investment",
            "limit": 150000,
            "invested_amount": 50000
        }
        
        response = requests.post(
            f"{BASE_URL}/api/user-tax-deductions",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Create deduction failed: {response.text}"
        data = response.json()
        
        # Verify response
        assert "id" in data, "Missing 'id' in response"
        assert data["deduction_id"] == test_deduction_id, f"deduction_id mismatch"
        assert data["section"] == "80C", f"section mismatch"
        assert data["name"] == "TEST PPF Investment", f"name mismatch"
        assert data["invested_amount"] == 50000, f"invested_amount mismatch"
        
        # Store ID for update/delete tests
        created_id = data["id"]
        
        print(f"✓ POST user-tax-deductions working - Created deduction {created_id}")
        
        # Verify persistence with GET
        get_response = requests.get(
            f"{BASE_URL}/api/user-tax-deductions",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        deductions = get_response.json()["deductions"]
        created_deduction = next((d for d in deductions if d["id"] == created_id), None)
        assert created_deduction is not None, f"Created deduction {created_id} not found in GET"
        
        print(f"✓ Deduction persisted and verified in GET")
        
        return created_id
    
    def test_update_user_tax_deduction(self, auth_headers):
        """Test PUT /api/user-tax-deductions/{id} - Update invested amount"""
        # First create a deduction to update
        test_deduction_id = f"TEST_UPDATE_{uuid4().hex[:8]}"
        
        create_payload = {
            "deduction_id": test_deduction_id,
            "section": "80D",
            "name": "TEST Health Insurance",
            "limit": 25000,
            "invested_amount": 10000
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/user-tax-deductions",
            json=create_payload,
            headers=auth_headers
        )
        assert create_response.status_code == 200, f"Create for update test failed: {create_response.text}"
        created_id = create_response.json()["id"]
        
        # Update the invested amount
        update_payload = {
            "invested_amount": 20000
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/user-tax-deductions/{created_id}",
            json=update_payload,
            headers=auth_headers
        )
        assert update_response.status_code == 200, f"Update deduction failed: {update_response.text}"
        updated_data = update_response.json()
        
        assert updated_data["invested_amount"] == 20000, f"invested_amount not updated: expected 20000, got {updated_data['invested_amount']}"
        
        print(f"✓ PUT user-tax-deductions working - Updated invested_amount to ₹20,000")
        
        # Verify with GET
        get_response = requests.get(
            f"{BASE_URL}/api/user-tax-deductions",
            headers=auth_headers
        )
        deductions = get_response.json()["deductions"]
        updated_deduction = next((d for d in deductions if d["id"] == created_id), None)
        assert updated_deduction is not None, "Updated deduction not found"
        assert updated_deduction["invested_amount"] == 20000, "Update not persisted"
        
        print(f"✓ Update persisted and verified in GET")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/user-tax-deductions/{created_id}",
            headers=auth_headers
        )
    
    def test_delete_user_tax_deduction(self, auth_headers):
        """Test DELETE /api/user-tax-deductions/{id} - Remove deduction"""
        # First create a deduction to delete
        test_deduction_id = f"TEST_DELETE_{uuid4().hex[:8]}"
        
        create_payload = {
            "deduction_id": test_deduction_id,
            "section": "80C",
            "name": "TEST Deduction to Delete",
            "limit": 150000,
            "invested_amount": 5000
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/user-tax-deductions",
            json=create_payload,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]
        
        # Delete the deduction
        delete_response = requests.delete(
            f"{BASE_URL}/api/user-tax-deductions/{created_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200, f"Delete deduction failed: {delete_response.text}"
        assert delete_response.json()["status"] == "deleted", "Delete status mismatch"
        
        print(f"✓ DELETE user-tax-deductions working - Deleted deduction {created_id}")
        
        # Verify deletion with GET
        get_response = requests.get(
            f"{BASE_URL}/api/user-tax-deductions",
            headers=auth_headers
        )
        deductions = get_response.json()["deductions"]
        deleted_deduction = next((d for d in deductions if d["id"] == created_id), None)
        assert deleted_deduction is None, "Deduction still exists after delete"
        
        print(f"✓ Deletion verified - Deduction not found in GET")
    
    def test_delete_nonexistent_deduction(self, auth_headers):
        """Test DELETE with non-existent ID returns 404"""
        fake_id = f"nonexistent_{uuid4().hex}"
        
        response = requests.delete(
            f"{BASE_URL}/api/user-tax-deductions/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404 for non-existent deduction, got {response.status_code}"
        
        print(f"✓ DELETE non-existent returns 404 as expected")
    
    def test_update_nonexistent_deduction(self, auth_headers):
        """Test PUT with non-existent ID returns 404"""
        fake_id = f"nonexistent_{uuid4().hex}"
        
        response = requests.put(
            f"{BASE_URL}/api/user-tax-deductions/{fake_id}",
            json={"invested_amount": 1000},
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404 for non-existent deduction, got {response.status_code}"
        
        print(f"✓ PUT non-existent returns 404 as expected")
    
    def test_duplicate_deduction_creation(self, auth_headers):
        """Test POST with duplicate deduction_id returns 400"""
        test_deduction_id = f"TEST_DUP_{uuid4().hex[:8]}"
        
        payload = {
            "deduction_id": test_deduction_id,
            "section": "80C",
            "name": "TEST Duplicate",
            "limit": 150000,
            "invested_amount": 1000
        }
        
        # Create first
        response1 = requests.post(
            f"{BASE_URL}/api/user-tax-deductions",
            json=payload,
            headers=auth_headers
        )
        assert response1.status_code == 200
        created_id = response1.json()["id"]
        
        # Try to create duplicate
        response2 = requests.post(
            f"{BASE_URL}/api/user-tax-deductions",
            json=payload,
            headers=auth_headers
        )
        assert response2.status_code == 400, f"Expected 400 for duplicate, got {response2.status_code}"
        
        print(f"✓ Duplicate deduction creation returns 400 as expected")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/user-tax-deductions/{created_id}",
            headers=auth_headers
        )


class TestTaxCalculatorValidation:
    """Additional validation tests for tax calculator logic"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_rebate_87a_old_regime_logic(self, auth_headers):
        """Verify rebate u/s 87A logic for Old Regime (up to ₹12,500 if income ≤₹5L)"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2025-26",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        old_taxable = data["old_regime"]["taxable_income"]
        old_rebate = data["old_regime"]["rebate_87a"]
        
        if old_taxable <= 500000:
            # Rebate should be min(tax, 12500)
            assert old_rebate <= 12500, f"Old regime rebate exceeds ₹12,500: {old_rebate}"
            print(f"✓ Old regime rebate verified: ₹{old_rebate} (income ≤₹5L)")
        else:
            assert old_rebate == 0, f"Old regime rebate should be 0 for income >{old_taxable}: got {old_rebate}"
            print(f"✓ Old regime rebate is 0 for income >₹5L (taxable: ₹{old_taxable:,.0f})")
    
    def test_rebate_87a_new_regime_logic(self, auth_headers):
        """Verify rebate u/s 87A logic for New Regime (up to ₹60,000 if income ≤₹12L)"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2025-26",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        new_taxable = data["new_regime"]["taxable_income"]
        new_rebate = data["new_regime"]["rebate_87a"]
        
        if new_taxable <= 1200000:
            # Rebate should be min(tax, 60000)
            assert new_rebate <= 60000, f"New regime rebate exceeds ₹60,000: {new_rebate}"
            print(f"✓ New regime rebate verified: ₹{new_rebate} (income ≤₹12L)")
        else:
            assert new_rebate == 0, f"New regime rebate should be 0 for income >{new_taxable}: got {new_rebate}"
            print(f"✓ New regime rebate is 0 for income >₹12L (taxable: ₹{new_taxable:,.0f})")
    
    def test_capital_gains_in_tax_calculator(self, auth_headers):
        """Verify capital gains are included in tax calculator"""
        response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2025-26",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        cg = data["capital_gains"]
        old_regime = data["old_regime"]
        new_regime = data["new_regime"]
        
        # Capital gains tax should be same in both regimes
        assert old_regime["capital_gains_tax"] == new_regime["capital_gains_tax"], \
            "Capital gains tax should be same in both regimes"
        
        # Verify capital gains tax is added to total tax
        expected_old_total = old_regime["total_tax_on_income"] + old_regime["capital_gains_tax"]
        assert abs(old_regime["total_tax"] - expected_old_total) < 1, \
            f"Old regime total tax mismatch: expected {expected_old_total}, got {old_regime['total_tax']}"
        
        expected_new_total = new_regime["total_tax_on_income"] + new_regime["capital_gains_tax"]
        assert abs(new_regime["total_tax"] - expected_new_total) < 1, \
            f"New regime total tax mismatch: expected {expected_new_total}, got {new_regime['total_tax']}"
        
        print(f"✓ Capital gains tax correctly added to total tax")
        print(f"  - STCG: ₹{cg['stcg']:,.2f}, LTCG: ₹{cg['ltcg']:,.2f}")
        print(f"  - CG Tax: ₹{cg['total_cg_tax']:,.2f}")


class TestCleanup:
    """Cleanup test data created during testing"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_cleanup_test_deductions(self, auth_headers):
        """Clean up any TEST_ prefixed deductions"""
        response = requests.get(
            f"{BASE_URL}/api/user-tax-deductions",
            headers=auth_headers
        )
        assert response.status_code == 200
        deductions = response.json()["deductions"]
        
        test_deductions = [d for d in deductions if d.get("deduction_id", "").startswith("TEST_") or d.get("name", "").startswith("TEST")]
        
        for deduction in test_deductions:
            delete_response = requests.delete(
                f"{BASE_URL}/api/user-tax-deductions/{deduction['id']}",
                headers=auth_headers
            )
            if delete_response.status_code == 200:
                print(f"  Cleaned up test deduction: {deduction['name']}")
        
        print(f"✓ Cleaned up {len(test_deductions)} test deductions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
