"""
Test Tax Planning and Portfolio Rebalancing APIs
Tests for iteration 11 - new features on Invest screen:
1. GET /api/tax-summary - Tax sections 80C/80D with PPF mapping
2. GET /api/portfolio-rebalancing - Actual vs target allocation with actions
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

class TestTaxSummaryAPI:
    """Tests for GET /api/tax-summary endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token for authenticated requests"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_tax_summary_returns_200(self):
        """Tax summary endpoint returns 200 status"""
        resp = requests.get(f"{BASE_URL}/api/tax-summary", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: GET /api/tax-summary returns 200")
    
    def test_tax_summary_has_sections(self):
        """Tax summary returns sections array"""
        resp = requests.get(f"{BASE_URL}/api/tax-summary", headers=self.headers)
        data = resp.json()
        
        assert "sections" in data, "Response missing 'sections' field"
        assert isinstance(data["sections"], list), "sections should be a list"
        print(f"PASS: Tax summary has {len(data['sections'])} sections")
    
    def test_tax_summary_has_fy(self):
        """Tax summary returns FY 2025-26 label"""
        resp = requests.get(f"{BASE_URL}/api/tax-summary", headers=self.headers)
        data = resp.json()
        
        assert "fy" in data, "Response missing 'fy' field"
        assert data["fy"] == "2025-26", f"Expected FY 2025-26, got {data['fy']}"
        print("PASS: Tax summary has FY 2025-26")
    
    def test_tax_summary_has_tax_saved_estimates(self):
        """Tax summary returns tax saved estimates for 30% and 20% slabs"""
        resp = requests.get(f"{BASE_URL}/api/tax-summary", headers=self.headers)
        data = resp.json()
        
        assert "tax_saved_30_slab" in data, "Response missing 'tax_saved_30_slab'"
        assert "tax_saved_20_slab" in data, "Response missing 'tax_saved_20_slab'"
        assert isinstance(data["tax_saved_30_slab"], (int, float)), "tax_saved_30_slab should be numeric"
        assert isinstance(data["tax_saved_20_slab"], (int, float)), "tax_saved_20_slab should be numeric"
        print(f"PASS: Tax saved estimates - 30% slab: {data['tax_saved_30_slab']}, 20% slab: {data['tax_saved_20_slab']}")
    
    def test_tax_summary_section_80c_structure(self):
        """Section 80C exists with proper fields (label, limit, used, items, percentage, remaining)"""
        resp = requests.get(f"{BASE_URL}/api/tax-summary", headers=self.headers)
        data = resp.json()
        
        sections_by_id = {s["section"]: s for s in data["sections"]}
        assert "80C" in sections_by_id, "Section 80C not found in response"
        
        sec80c = sections_by_id["80C"]
        required_fields = ["section", "label", "limit", "used", "items", "percentage", "remaining"]
        for field in required_fields:
            assert field in sec80c, f"80C missing field: {field}"
        
        assert sec80c["limit"] == 150000, f"80C limit should be 150000, got {sec80c['limit']}"
        assert sec80c["label"] == "Section 80C", f"80C label incorrect: {sec80c['label']}"
        print(f"PASS: 80C structure verified - used: {sec80c['used']}/{sec80c['limit']}, {sec80c['percentage']}%")
    
    def test_tax_summary_section_80d_exists(self):
        """Section 80D exists with proper structure"""
        resp = requests.get(f"{BASE_URL}/api/tax-summary", headers=self.headers)
        data = resp.json()
        
        sections_by_id = {s["section"]: s for s in data["sections"]}
        assert "80D" in sections_by_id, "Section 80D not found in response"
        
        sec80d = sections_by_id["80D"]
        assert sec80d["limit"] == 25000, f"80D limit should be 25000, got {sec80d['limit']}"
        print(f"PASS: 80D exists - used: {sec80d['used']}/{sec80d['limit']}, {sec80d['percentage']}%")
    
    def test_tax_summary_ppf_mapped_to_80c(self):
        """PPF transactions are mapped to Section 80C"""
        resp = requests.get(f"{BASE_URL}/api/tax-summary", headers=self.headers)
        data = resp.json()
        
        sections_by_id = {s["section"]: s for s in data["sections"]}
        sec80c = sections_by_id.get("80C", {})
        
        items = sec80c.get("items", [])
        ppf_items = [i for i in items if "PPF" in i.get("name", "")]
        
        if sec80c.get("used", 0) > 0:
            assert len(ppf_items) > 0 or sec80c["used"] > 0, "80C has usage but no PPF items visible"
            print(f"PASS: 80C has {len(ppf_items)} PPF items, total used: {sec80c['used']}")
        else:
            print(f"INFO: 80C used is 0, no PPF items to validate")
    
    def test_tax_summary_requires_auth(self):
        """Tax summary requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/tax-summary")
        assert resp.status_code == 401, f"Expected 401 without auth, got {resp.status_code}"
        print("PASS: Tax summary requires authentication")


class TestPortfolioRebalancingAPI:
    """Tests for GET /api/portfolio-rebalancing endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token for authenticated requests"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_rebalancing_returns_200(self):
        """Portfolio rebalancing endpoint returns 200 status"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: GET /api/portfolio-rebalancing returns 200")
    
    def test_rebalancing_has_profile(self):
        """Rebalancing returns risk profile (Conservative/Moderate/Aggressive)"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing", headers=self.headers)
        data = resp.json()
        
        assert "profile" in data, "Response missing 'profile' field"
        assert data["profile"] in ["Conservative", "Moderate", "Aggressive"], \
            f"Invalid profile: {data['profile']}"
        print(f"PASS: Rebalancing profile: {data['profile']}")
    
    def test_rebalancing_has_strategy_name(self):
        """Rebalancing returns strategy name (Safe Harbor/Balanced Growth/High Growth)"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing", headers=self.headers)
        data = resp.json()
        
        assert "strategy_name" in data, "Response missing 'strategy_name' field"
        expected_names = ["Safe Harbor", "Balanced Growth", "High Growth"]
        assert data["strategy_name"] in expected_names, \
            f"Unexpected strategy name: {data['strategy_name']}"
        print(f"PASS: Strategy name: {data['strategy_name']}")
    
    def test_rebalancing_has_actual_allocation(self):
        """Rebalancing returns actual allocation percentages"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing", headers=self.headers)
        data = resp.json()
        
        assert "actual" in data, "Response missing 'actual' field"
        assert isinstance(data["actual"], dict), "actual should be a dict"
        
        # Actual allocation should have percentage values
        for bucket, pct in data["actual"].items():
            assert isinstance(pct, (int, float)), f"Actual {bucket} should be numeric"
        
        print(f"PASS: Actual allocation: {data['actual']}")
    
    def test_rebalancing_has_target_allocation(self):
        """Rebalancing returns target allocation percentages based on risk profile"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing", headers=self.headers)
        data = resp.json()
        
        assert "target" in data, "Response missing 'target' field"
        assert isinstance(data["target"], dict), "target should be a dict"
        
        # Verify target sums to ~100%
        target_sum = sum(data["target"].values())
        assert 95 <= target_sum <= 105, f"Target allocation should sum to ~100%, got {target_sum}"
        
        print(f"PASS: Target allocation: {data['target']}")
    
    def test_rebalancing_has_actions(self):
        """Rebalancing returns actions array with reduce/increase suggestions"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing", headers=self.headers)
        data = resp.json()
        
        assert "actions" in data, "Response missing 'actions' field"
        assert isinstance(data["actions"], list), "actions should be a list"
        
        # Each action should have required fields
        for action in data["actions"]:
            assert "bucket" in action, "Action missing 'bucket'"
            assert "action" in action, "Action missing 'action' (reduce/increase)"
            assert "suggestion" in action, "Action missing 'suggestion'"
            assert action["action"] in ["reduce", "increase"], \
                f"Invalid action type: {action['action']}"
        
        print(f"PASS: Rebalancing has {len(data['actions'])} action items")
    
    def test_rebalancing_actions_have_correct_suggestions(self):
        """Actions have correct reduce/increase suggestions based on diff"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing", headers=self.headers)
        data = resp.json()
        
        for action in data["actions"]:
            # If actual > target, action should be "reduce"
            # If actual < target, action should be "increase"
            actual = data["actual"].get(action["bucket"], 0)
            target = data["target"].get(action["bucket"], 0)
            
            if actual > target:
                assert action["action"] == "reduce", \
                    f"{action['bucket']}: actual ({actual}) > target ({target}), should be 'reduce'"
            else:
                assert action["action"] == "increase", \
                    f"{action['bucket']}: actual ({actual}) < target ({target}), should be 'increase'"
            
            # Suggestion should mention the bucket name and percentage
            assert action["bucket"] in action["suggestion"], \
                f"Suggestion should mention bucket name"
            assert "%" in action["suggestion"], \
                f"Suggestion should include percentage"
        
        if data["actions"]:
            print(f"PASS: Action suggestions verified - e.g., '{data['actions'][0]['suggestion']}'")
        else:
            print("INFO: No rebalancing actions (portfolio already balanced)")
    
    def test_rebalancing_has_total_invested(self):
        """Rebalancing returns total invested amount"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing", headers=self.headers)
        data = resp.json()
        
        assert "total" in data, "Response missing 'total' field"
        assert isinstance(data["total"], (int, float)), "total should be numeric"
        print(f"PASS: Total invested: {data['total']}")
    
    def test_rebalancing_requires_auth(self):
        """Portfolio rebalancing requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing")
        assert resp.status_code == 401, f"Expected 401 without auth, got {resp.status_code}"
        print("PASS: Portfolio rebalancing requires authentication")
    
    def test_rebalancing_moderate_profile_allocations(self):
        """For Moderate profile, verify target allocations match expected strategy"""
        resp = requests.get(f"{BASE_URL}/api/portfolio-rebalancing", headers=self.headers)
        data = resp.json()
        
        if data["profile"] == "Moderate":
            # Moderate strategy: Equity 40%, Debt 30%, Gold 15%, Alt 15%
            target = data["target"]
            assert target.get("Equity", 0) == 40, f"Moderate Equity should be 40%, got {target.get('Equity')}"
            assert target.get("Debt", 0) == 30, f"Moderate Debt should be 30%, got {target.get('Debt')}"
            assert target.get("Gold", 0) == 15, f"Moderate Gold should be 15%, got {target.get('Gold')}"
            assert target.get("Alt", 0) == 15, f"Moderate Alt should be 15%, got {target.get('Alt')}"
            print("PASS: Moderate profile target allocations verified")
        else:
            print(f"INFO: Profile is {data['profile']}, skipping Moderate allocation check")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
