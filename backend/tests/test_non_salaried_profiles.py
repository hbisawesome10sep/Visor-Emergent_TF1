"""
Non-Salaried Tax Profiles API Tests - Phase 3b
Tests for Freelancer (44ADA), Business (44AD), Investor (F&O), Rental (HP) profiles
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://experience-deploy.preview.emergentagent.com')

# Test credentials from test_credentials.md
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ══════════════════════════════════════
#  HELPER ENDPOINTS TESTS
# ══════════════════════════════════════

class TestHelperEndpoints:
    """Test professions and business types list endpoints (no auth required)."""
    
    def test_professions_list_returns_44ada_professions(self, api_client):
        """GET /api/tax/professions-list returns eligible 44ADA professions."""
        response = api_client.get(f"{BASE_URL}/api/tax/professions-list")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "professions" in data, "Response should contain 'professions' key"
        assert isinstance(data["professions"], list), "Professions should be a list"
        assert len(data["professions"]) > 0, "Should have at least one profession"
        
        # Verify structure of profession items
        first_profession = data["professions"][0]
        assert "id" in first_profession, "Profession should have 'id'"
        assert "label" in first_profession, "Profession should have 'label'"
        
        # Verify expected professions exist
        profession_ids = [p["id"] for p in data["professions"]]
        expected_professions = ["freelance_developer", "consultant", "doctor", "lawyer", "chartered_accountant"]
        for expected in expected_professions:
            assert expected in profession_ids, f"Expected profession '{expected}' not found"
        
        print(f"✓ Professions list returned {len(data['professions'])} professions")
    
    def test_business_types_list_returns_44ad_businesses(self, api_client):
        """GET /api/tax/business-types-list returns eligible 44AD business types."""
        response = api_client.get(f"{BASE_URL}/api/tax/business-types-list")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "business_types" in data, "Response should contain 'business_types' key"
        assert isinstance(data["business_types"], list), "Business types should be a list"
        assert len(data["business_types"]) > 0, "Should have at least one business type"
        
        # Verify structure
        first_business = data["business_types"][0]
        assert "id" in first_business, "Business type should have 'id'"
        assert "label" in first_business, "Business type should have 'label'"
        
        # Verify expected business types exist
        business_ids = [b["id"] for b in data["business_types"]]
        expected_businesses = ["retail_trade", "wholesale_trade", "manufacturing", "contractor"]
        for expected in expected_businesses:
            assert expected in business_ids, f"Expected business type '{expected}' not found"
        
        print(f"✓ Business types list returned {len(data['business_types'])} types")


# ══════════════════════════════════════
#  FREELANCER PROFILE TESTS (44ADA)
# ══════════════════════════════════════

class TestFreelancerProfile:
    """Test Freelancer profile endpoints (Section 44ADA)."""
    
    def test_save_freelancer_profile_presumptive(self, authenticated_client):
        """POST /api/tax/freelancer-profile saves profile with 44ADA presumptive computation."""
        payload = {
            "profession": "freelance_developer",
            "gross_receipts": 2500000,  # ₹25 Lakhs
            "use_presumptive": True,
            "gst_registered": False,
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/freelancer-profile",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "saved", "Status should be 'saved'"
        assert "profile" in data, "Response should contain 'profile'"
        
        profile = data["profile"]
        assert profile["profession"] == "freelance_developer"
        assert profile["gross_receipts"] == 2500000
        assert profile["use_presumptive"] == True
        
        # Verify computation
        assert "computation" in profile, "Profile should have computation"
        computation = profile["computation"]
        
        assert computation["method"] == "presumptive_44ada", "Method should be presumptive_44ada"
        assert computation["gross_receipts"] == 2500000
        assert computation["taxable_income"] == 1250000, "50% of 25L = 12.5L taxable"
        assert computation["deemed_expenses"] == 1250000, "50% deemed expenses"
        assert computation["eligible_for_44ada"] == True
        assert computation["itr_form"] == "ITR-4 (Sugam)"
        assert "notes" in computation and len(computation["notes"]) > 0
        
        print(f"✓ Freelancer profile saved with taxable income: ₹{computation['taxable_income']:,.0f}")
    
    def test_get_freelancer_profile_with_computation(self, authenticated_client):
        """GET /api/tax/freelancer-profile retrieves profile with computation."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/tax/freelancer-profile?fy=2025-26"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profile" in data, "Response should contain 'profile'"
        
        if data["profile"]:
            profile = data["profile"]
            assert "computation" in profile, "Profile should have computation"
            assert profile["computation"]["method"] in ["presumptive_44ada", "actual"]
            assert "taxable_income" in profile["computation"]
            assert "itr_form" in profile["computation"]
            print(f"✓ Freelancer profile retrieved with taxable: ₹{profile['computation']['taxable_income']:,.0f}")
        else:
            print("✓ Freelancer profile GET returned null (no profile exists)")
    
    def test_save_freelancer_profile_actual_method(self, authenticated_client):
        """POST /api/tax/freelancer-profile with actual expenses method."""
        payload = {
            "profession": "consultant",
            "gross_receipts": 3000000,  # ₹30 Lakhs
            "use_presumptive": False,
            "expenses_claimed": 1800000,  # ₹18 Lakhs expenses
            "gst_registered": True,
            "gst_number": "27AAAAA0000A1Z5",
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/freelancer-profile",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        profile = data["profile"]
        computation = profile["computation"]
        
        assert computation["method"] == "actual", "Method should be 'actual'"
        assert computation["taxable_income"] == 1200000, "30L - 18L = 12L taxable"
        # Audit required since profit (12L) < 50% of gross (15L)
        assert computation["audit_required"] == True, "Audit should be required"
        
        print(f"✓ Freelancer profile (actual method) saved with taxable: ₹{computation['taxable_income']:,.0f}")


# ══════════════════════════════════════
#  BUSINESS PROFILE TESTS (44AD)
# ══════════════════════════════════════

class TestBusinessProfile:
    """Test Business Owner profile endpoints (Section 44AD)."""
    
    def test_save_business_profile_presumptive(self, authenticated_client):
        """POST /api/tax/business-profile saves profile with 44AD computation."""
        payload = {
            "business_type": "retail_trade",
            "business_name": "Test Retail Store",
            "gross_turnover": 10000000,  # ₹1 Crore
            "digital_receipts_pct": 70.0,  # 70% digital
            "use_presumptive": True,
            "gst_registered": True,
            "gst_number": "27BBBBB0000B1Z5",
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/business-profile",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "saved", "Status should be 'saved'"
        
        profile = data["profile"]
        assert profile["business_type"] == "retail_trade"
        assert profile["gross_turnover"] == 10000000
        
        # Verify computation
        computation = profile["computation"]
        assert computation["method"] == "presumptive_44ad"
        assert computation["gross_turnover"] == 10000000
        assert computation["digital_pct"] == 70.0
        
        # 70% digital (6%) + 30% cash (8%)
        # Digital: 70L * 6% = 4.2L
        # Cash: 30L * 8% = 2.4L
        # Total: 6.6L
        expected_digital_profit = 7000000 * 0.06  # 420000
        expected_cash_profit = 3000000 * 0.08  # 240000
        expected_total = expected_digital_profit + expected_cash_profit  # 660000
        
        assert computation["taxable_income"] == expected_total, f"Expected {expected_total}, got {computation['taxable_income']}"
        assert computation["eligible_for_44ad"] == True
        assert computation["itr_form"] == "ITR-4 (Sugam)"
        
        print(f"✓ Business profile saved with taxable income: ₹{computation['taxable_income']:,.0f}")
    
    def test_get_business_profile(self, authenticated_client):
        """GET /api/tax/business-profile retrieves profile."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/tax/business-profile?fy=2025-26"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profile" in data
        
        if data["profile"]:
            profile = data["profile"]
            assert "computation" in profile
            assert "taxable_income" in profile["computation"]
            print(f"✓ Business profile retrieved with taxable: ₹{profile['computation']['taxable_income']:,.0f}")
        else:
            print("✓ Business profile GET returned null (no profile exists)")


# ══════════════════════════════════════
#  INVESTOR PROFILE TESTS (F&O/Crypto)
# ══════════════════════════════════════

class TestInvestorProfile:
    """Test Investor/Trader profile endpoints (F&O, Crypto)."""
    
    def test_save_investor_profile_with_fo(self, authenticated_client):
        """POST /api/tax/investor-profile saves profile with F&O computation."""
        payload = {
            "has_equity_delivery": True,
            "equity_delivery_turnover": 500000,
            "equity_delivery_profit": 75000,
            "has_intraday": True,
            "intraday_turnover": 2000000,
            "intraday_profit": -25000,  # Loss
            "has_futures": True,
            "futures_turnover": 5000000,
            "futures_profit": 150000,
            "has_options": True,
            "options_turnover": 3000000,
            "options_profit": -50000,  # Loss
            "has_crypto": True,
            "crypto_profit": 100000,
            "demat_broker": "Zerodha",
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/investor-profile",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "saved"
        
        profile = data["profile"]
        computation = profile["computation"]
        
        # Verify equity delivery
        assert computation["equity_delivery"]["profit_loss"] == 75000
        assert computation["equity_delivery"]["tax_type"] == "Capital Gains (STCG 20% / LTCG 12.5%)"
        
        # Verify intraday (speculative)
        assert computation["intraday"]["profit_loss"] == -25000
        assert "Speculative" in computation["intraday"]["tax_type"]
        
        # Verify F&O
        assert computation["futures_options"]["total_profit_loss"] == 100000  # 150K - 50K
        assert computation["futures_options"]["total_turnover"] == 8000000  # 5M + 3M
        assert computation["futures_options"]["audit_required"] == False  # Under 1Cr
        
        # Verify crypto
        assert computation["crypto"]["profit_loss"] == 100000
        assert computation["crypto"]["estimated_tax"] == 30000  # 30% of 100K
        
        # ITR form should be ITR-3 due to F&O
        assert computation["itr_form"] == "ITR-3"
        
        print(f"✓ Investor profile saved with F&O profit: ₹{computation['futures_options']['total_profit_loss']:,.0f}")
    
    def test_get_investor_profile(self, authenticated_client):
        """GET /api/tax/investor-profile retrieves profile."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/tax/investor-profile?fy=2025-26"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profile" in data
        
        if data["profile"]:
            profile = data["profile"]
            assert "computation" in profile
            assert "futures_options" in profile["computation"]
            assert "crypto" in profile["computation"]
            print(f"✓ Investor profile retrieved")
        else:
            print("✓ Investor profile GET returned null (no profile exists)")
    
    def test_investor_profile_audit_threshold(self, authenticated_client):
        """Test F&O audit requirement when turnover > 1 Crore."""
        payload = {
            "has_futures": True,
            "futures_turnover": 15000000,  # ₹1.5 Crore - above audit limit
            "futures_profit": 500000,
            "has_options": False,
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/investor-profile",
            json=payload
        )
        
        assert response.status_code == 200
        
        data = response.json()
        computation = data["profile"]["computation"]
        
        # Audit should be required for turnover > 1 Crore
        assert computation["futures_options"]["audit_required"] == True
        assert computation["futures_options"]["audit_limit"] == 10000000
        
        print(f"✓ Investor profile correctly flags audit requirement for high turnover")


# ══════════════════════════════════════
#  RENTAL PROFILE TESTS (House Property)
# ══════════════════════════════════════

class TestRentalProfile:
    """Test Rental Income profile endpoints (House Property)."""
    
    def test_save_rental_profile_with_properties(self, authenticated_client):
        """POST /api/tax/rental-profile saves rental properties with HP computation."""
        payload = {
            "properties": [
                {
                    "property_name": "Flat in Mumbai",
                    "property_type": "residential",
                    "gross_annual_rent": 360000,  # ₹30K/month
                    "municipal_taxes_paid": 12000,
                    "home_loan_interest": 180000,
                    "is_self_occupied": False,
                    "fy": "2025-26"
                },
                {
                    "property_name": "Self-Occupied Home",
                    "property_type": "residential",
                    "gross_annual_rent": 0,
                    "municipal_taxes_paid": 0,
                    "home_loan_interest": 250000,  # Will be capped at 2L
                    "is_self_occupied": True,
                    "fy": "2025-26"
                }
            ],
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/rental-profile",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "saved"
        
        profile = data["profile"]
        computation = profile["computation"]
        
        # Verify properties
        assert len(computation["properties"]) == 2
        
        # Let-out property computation
        let_out = computation["properties"][0]
        assert let_out["property_name"] == "Flat in Mumbai"
        assert let_out["gross_annual_rent"] == 360000
        assert let_out["municipal_taxes"] == 12000
        nav = 360000 - 12000  # 348000
        assert let_out["net_annual_value"] == nav
        standard_ded = nav * 0.30  # 104400
        assert let_out["standard_deduction_30pct"] == standard_ded
        # Taxable = NAV - 30% - Interest = 348000 - 104400 - 180000 = 63600
        expected_taxable = nav - standard_ded - 180000
        assert let_out["taxable_income"] == expected_taxable
        
        # Self-occupied property computation
        self_occ = computation["properties"][1]
        assert self_occ["is_self_occupied"] == True
        assert self_occ["net_annual_value"] == 0
        assert self_occ["home_loan_interest_24b"] == 200000  # Capped at 2L
        assert self_occ["taxable_income"] == -200000  # Loss from self-occupied
        
        # Summary
        summary = computation["summary"]
        assert summary["total_properties"] == 2
        assert "total_taxable_income" in summary
        
        print(f"✓ Rental profile saved with total taxable: ₹{summary['total_taxable_income']:,.0f}")
    
    def test_get_rental_profile(self, authenticated_client):
        """GET /api/tax/rental-profile retrieves properties with HP computation."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/tax/rental-profile?fy=2025-26"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "profile" in data
        
        if data["profile"]:
            profile = data["profile"]
            assert "computation" in profile
            assert "properties" in profile["computation"]
            assert "summary" in profile["computation"]
            print(f"✓ Rental profile retrieved with {len(profile['computation']['properties'])} properties")
        else:
            print("✓ Rental profile GET returned null (no profile exists)")
    
    def test_add_rental_property(self, authenticated_client):
        """POST /api/tax/rental-profile/add-property adds new property."""
        payload = {
            "property_name": "Commercial Shop",
            "property_type": "commercial",
            "gross_annual_rent": 600000,  # ₹50K/month
            "municipal_taxes_paid": 24000,
            "home_loan_interest": 0,
            "is_self_occupied": False,
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/rental-profile/add-property",
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "added"
        
        profile = data["profile"]
        computation = profile["computation"]
        
        # Should have the new property
        property_names = [p["property_name"] for p in computation["properties"]]
        assert "Commercial Shop" in property_names
        
        # Verify commercial property computation
        commercial = next(p for p in computation["properties"] if p["property_name"] == "Commercial Shop")
        assert commercial["property_type"] == "commercial"
        nav = 600000 - 24000  # 576000
        assert commercial["net_annual_value"] == nav
        
        print(f"✓ Rental property added, total properties: {computation['summary']['total_properties']}")


# ══════════════════════════════════════
#  CONSOLIDATED INCOME TESTS
# ══════════════════════════════════════

class TestConsolidatedIncome:
    """Test consolidated income endpoint combining all sources."""
    
    def test_get_consolidated_income(self, authenticated_client):
        """GET /api/tax/consolidated-income combines all income sources."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/tax/consolidated-income?fy=2025-26"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "fy" in data
        assert data["fy"] == "2025-26"
        assert "income_sources" in data
        assert "total_taxable_income" in data
        assert "recommended_itr_form" in data
        assert "profiles_available" in data
        
        # Verify profiles_available structure
        profiles = data["profiles_available"]
        assert "salary" in profiles
        assert "freelancer" in profiles
        assert "business" in profiles
        assert "investor" in profiles
        assert "rental" in profiles
        
        # Verify income_sources has proper structure for available profiles
        sources = data["income_sources"]
        for source_type, source_data in sources.items():
            assert "taxable" in source_data or source_type == "investor", f"Source {source_type} should have 'taxable'"
        
        # Verify ITR form recommendation
        itr_form = data["recommended_itr_form"]
        assert itr_form in ["ITR-1 (Sahaj)", "ITR-2", "ITR-3", "ITR-4 (Sugam)"]
        
        print(f"✓ Consolidated income: ₹{data['total_taxable_income']:,.0f}, ITR: {itr_form}")
        print(f"  Profiles available: {[k for k, v in profiles.items() if v]}")
    
    def test_consolidated_income_itr_form_logic(self, authenticated_client):
        """Verify ITR form recommendation logic based on income sources."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/tax/consolidated-income?fy=2025-26"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        sources = data["income_sources"]
        itr_form = data["recommended_itr_form"]
        
        # ITR-3 if F&O income exists
        if "investor" in sources and sources["investor"].get("fo_income", 0) != 0:
            assert itr_form == "ITR-3", "Should recommend ITR-3 for F&O income"
        # ITR-4 if business/freelancer with presumptive
        elif "business" in sources or "freelancer" in sources:
            assert itr_form == "ITR-4 (Sugam)", "Should recommend ITR-4 for presumptive income"
        # ITR-2 if rental/investor without F&O
        elif "rental" in sources or "investor" in sources:
            assert itr_form == "ITR-2", "Should recommend ITR-2 for rental/capital gains"
        
        print(f"✓ ITR form logic verified: {itr_form}")


# ══════════════════════════════════════
#  EDGE CASES AND VALIDATION TESTS
# ══════════════════════════════════════

class TestEdgeCases:
    """Test edge cases and validation."""
    
    def test_freelancer_above_44ada_limit(self, authenticated_client):
        """Test freelancer with gross receipts above 44ADA limit (₹75L)."""
        payload = {
            "profession": "consultant",
            "gross_receipts": 80000000,  # ₹80 Lakhs - above limit
            "use_presumptive": True,
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/freelancer-profile",
            json=payload
        )
        
        assert response.status_code == 200
        
        data = response.json()
        computation = data["profile"]["computation"]
        
        # Should not be eligible for 44ADA
        assert computation["eligible_for_44ada"] == False
        assert computation["audit_required"] == True
        
        print(f"✓ Freelancer above 44ADA limit correctly flagged")
    
    def test_business_high_digital_percentage(self, authenticated_client):
        """Test business with 100% digital receipts (6% rate)."""
        payload = {
            "business_type": "retail_trade",
            "gross_turnover": 5000000,  # ₹50 Lakhs
            "digital_receipts_pct": 100.0,  # 100% digital
            "use_presumptive": True,
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/business-profile",
            json=payload
        )
        
        assert response.status_code == 200
        
        data = response.json()
        computation = data["profile"]["computation"]
        
        # 100% digital at 6% = 3L taxable
        assert computation["taxable_income"] == 300000
        assert computation["blended_rate"] == 6.0
        
        print(f"✓ Business with 100% digital correctly computed at 6%")
    
    def test_rental_loss_setoff_limit(self, authenticated_client):
        """Test rental loss setoff limit (max ₹2L per year)."""
        payload = {
            "properties": [
                {
                    "property_name": "High Interest Property",
                    "property_type": "residential",
                    "gross_annual_rent": 120000,  # ₹10K/month
                    "municipal_taxes_paid": 0,
                    "home_loan_interest": 500000,  # High interest causing loss
                    "is_self_occupied": False,
                    "fy": "2025-26"
                }
            ],
            "fy": "2025-26"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/tax/rental-profile",
            json=payload
        )
        
        assert response.status_code == 200
        
        data = response.json()
        computation = data["profile"]["computation"]
        summary = computation["summary"]
        
        # NAV = 120000, Standard Ded = 36000, Interest = 500000
        # Taxable = 120000 - 36000 - 500000 = -416000 (loss)
        assert summary["total_taxable_income"] < 0, "Should have loss"
        
        # Loss setoff should be capped at 2L
        if summary["total_taxable_income"] < -200000:
            assert summary["loss_setoff_allowed"] == 200000, "Loss setoff should be capped at 2L"
            assert summary["carry_forward_loss"] > 0, "Excess loss should be carried forward"
        
        print(f"✓ Rental loss setoff limit correctly applied")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
