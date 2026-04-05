"""
Experience Mode System Tests
Tests for the 3-tier feature gating system (Essential, Plus, Full)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://experience-tier-test.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestExperienceModeAPIs:
    """Test Experience Mode API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GET /api/experience/mode - Get current mode and features
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_get_experience_mode(self):
        """Test GET /api/experience/mode returns correct mode and feature lists"""
        response = self.session.get(f"{BASE_URL}/api/experience/mode")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "current_mode" in data, "Response should contain current_mode"
        assert "mode_info" in data, "Response should contain mode_info"
        assert "available_features" in data, "Response should contain available_features"
        assert "hidden_features" in data, "Response should contain hidden_features"
        
        # Verify mode is one of the valid values
        assert data["current_mode"] in ["essential", "plus", "full"], f"Invalid mode: {data['current_mode']}"
        
        # Verify mode_info structure
        mode_info = data["mode_info"]
        assert "title" in mode_info, "mode_info should contain title"
        assert "color" in mode_info, "mode_info should contain color"
        assert "highlights" in mode_info, "mode_info should contain highlights"
        
        # Verify features are lists
        assert isinstance(data["available_features"], list), "available_features should be a list"
        assert isinstance(data["hidden_features"], list), "hidden_features should be a list"
        
        print(f"✓ Current mode: {data['current_mode']}")
        print(f"✓ Available features count: {len(data['available_features'])}")
        print(f"✓ Hidden features count: {len(data['hidden_features'])}")
    
    def test_get_mode_requires_auth(self):
        """Test GET /api/experience/mode requires authentication"""
        response = requests.get(f"{BASE_URL}/api/experience/mode")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ GET /api/experience/mode correctly requires authentication")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PUT /api/experience/mode - Update user mode
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_update_mode_to_plus(self):
        """Test PUT /api/experience/mode can switch to Plus mode"""
        response = self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "plus", "source": "test"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success", "Response should indicate success"
        assert data.get("mode") == "plus", "Mode should be updated to plus"
        
        print("✓ Successfully switched to Plus mode")
    
    def test_update_mode_to_full(self):
        """Test PUT /api/experience/mode can switch to Full mode"""
        response = self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "full", "source": "test"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success", "Response should indicate success"
        assert data.get("mode") == "full", "Mode should be updated to full"
        
        print("✓ Successfully switched to Full mode")
    
    def test_update_mode_to_essential(self):
        """Test PUT /api/experience/mode can switch to Essential mode"""
        response = self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "essential", "source": "test"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success", "Response should indicate success"
        assert data.get("mode") == "essential", "Mode should be updated to essential"
        
        print("✓ Successfully switched to Essential mode")
    
    def test_update_mode_invalid(self):
        """Test PUT /api/experience/mode rejects invalid mode"""
        response = self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "invalid_mode", "source": "test"}
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid mode, got {response.status_code}"
        print("✓ Invalid mode correctly rejected with 400")
    
    def test_update_mode_requires_auth(self):
        """Test PUT /api/experience/mode requires authentication"""
        response = requests.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "plus", "source": "test"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ PUT /api/experience/mode correctly requires authentication")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GET /api/experience/essential/snapshot - 3-card snapshot
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_essential_snapshot(self):
        """Test GET /api/experience/essential/snapshot returns 3-card snapshot data"""
        response = self.session.get(f"{BASE_URL}/api/experience/essential/snapshot")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify snapshot structure - should have spent, safe_to_spend, saved
        assert "spent" in data or "spent_this_month" in data, "Snapshot should contain spent data"
        assert "safe_to_spend" in data, "Snapshot should contain safe_to_spend data"
        assert "saved" in data or "saved_this_month" in data, "Snapshot should contain saved data"
        
        print(f"✓ Essential snapshot returned successfully")
        print(f"  - Spent: {data.get('spent', data.get('spent_this_month', {}))}")
        print(f"  - Safe to Spend: {data.get('safe_to_spend', {})}")
        print(f"  - Saved: {data.get('saved', data.get('saved_this_month', {}))}")
    
    def test_essential_snapshot_requires_auth(self):
        """Test GET /api/experience/essential/snapshot requires authentication"""
        response = requests.get(f"{BASE_URL}/api/experience/essential/snapshot")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Essential snapshot correctly requires authentication")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GET /api/experience/essential/alerts - Smart alerts
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_essential_alerts(self):
        """Test GET /api/experience/essential/alerts returns smart alerts list"""
        response = self.session.get(f"{BASE_URL}/api/experience/essential/alerts?limit=5")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify alerts structure
        assert "alerts" in data, "Response should contain alerts array"
        assert isinstance(data["alerts"], list), "alerts should be a list"
        
        # If there are alerts, verify their structure
        if len(data["alerts"]) > 0:
            alert = data["alerts"][0]
            assert "title" in alert or "message" in alert, "Alert should have title or message"
        
        print(f"✓ Essential alerts returned: {len(data['alerts'])} alerts")
    
    def test_essential_alerts_requires_auth(self):
        """Test GET /api/experience/essential/alerts requires authentication"""
        response = requests.get(f"{BASE_URL}/api/experience/essential/alerts")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Essential alerts correctly requires authentication")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GET /api/experience/essential/brief - AI morning brief
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_essential_brief(self):
        """Test GET /api/experience/essential/brief returns AI morning brief"""
        response = self.session.get(f"{BASE_URL}/api/experience/essential/brief")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify brief structure - should have message/greeting and snapshot
        assert "message" in data or "greeting" in data, "Brief should contain message or greeting"
        
        print(f"✓ Essential brief returned successfully")
        if "message" in data:
            print(f"  - Message: {data['message'][:100]}...")
    
    def test_essential_brief_requires_auth(self):
        """Test GET /api/experience/essential/brief requires authentication"""
        response = requests.get(f"{BASE_URL}/api/experience/essential/brief")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Essential brief correctly requires authentication")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GET /api/experience/modes - Get all modes info
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_get_all_modes(self):
        """Test GET /api/experience/modes returns all mode information"""
        response = self.session.get(f"{BASE_URL}/api/experience/modes")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify modes structure
        assert "modes" in data, "Response should contain modes array"
        assert len(data["modes"]) == 3, "Should have 3 modes (essential, plus, full)"
        
        # Verify each mode has required fields
        mode_names = []
        for mode in data["modes"]:
            assert "mode" in mode, "Each mode should have mode field"
            assert "title" in mode, "Each mode should have title"
            assert "color" in mode, "Each mode should have color"
            mode_names.append(mode["mode"])
        
        assert "essential" in mode_names, "Should include essential mode"
        assert "plus" in mode_names, "Should include plus mode"
        assert "full" in mode_names, "Should include full mode"
        
        print("✓ All 3 modes returned with correct structure")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Feature Access Tests
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_feature_access_check(self):
        """Test GET /api/experience/features/{feature_id} checks feature access"""
        # Test a feature that should be available in all modes
        response = self.session.get(f"{BASE_URL}/api/experience/features/ai_chat")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "feature_id" in data, "Response should contain feature_id"
        assert "available" in data, "Response should contain available boolean"
        
        print(f"✓ Feature access check works - ai_chat available: {data['available']}")
    
    def test_get_all_features(self):
        """Test GET /api/experience/features returns all features with availability"""
        response = self.session.get(f"{BASE_URL}/api/experience/features")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "features" in data, "Response should contain features array"
        assert "current_mode" in data, "Response should contain current_mode"
        
        print(f"✓ All features returned: {len(data['features'])} features")


class TestModeSwitchingFlow:
    """Test the complete mode switching flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_mode_switch_essential_to_plus_to_full(self):
        """Test switching modes: Essential -> Plus -> Full"""
        # First set to Essential
        response = self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "essential", "source": "test"}
        )
        assert response.status_code == 200
        
        # Verify Essential mode
        response = self.session.get(f"{BASE_URL}/api/experience/mode")
        assert response.json()["current_mode"] == "essential"
        print("✓ Set to Essential mode")
        
        # Switch to Plus
        response = self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "plus", "source": "test"}
        )
        assert response.status_code == 200
        
        # Verify Plus mode
        response = self.session.get(f"{BASE_URL}/api/experience/mode")
        assert response.json()["current_mode"] == "plus"
        print("✓ Switched to Plus mode")
        
        # Switch to Full
        response = self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "full", "source": "test"}
        )
        assert response.status_code == 200
        
        # Verify Full mode
        response = self.session.get(f"{BASE_URL}/api/experience/mode")
        assert response.json()["current_mode"] == "full"
        print("✓ Switched to Full mode")
    
    def test_feature_availability_changes_with_mode(self):
        """Test that feature availability changes when mode changes"""
        # Set to Essential mode
        self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "essential", "source": "test"}
        )
        
        # Check tax_basic feature (should NOT be available in Essential)
        response = self.session.get(f"{BASE_URL}/api/experience/features/tax_basic")
        essential_tax = response.json()
        
        # Set to Plus mode
        self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "plus", "source": "test"}
        )
        
        # Check tax_basic feature again (should be available in Plus)
        response = self.session.get(f"{BASE_URL}/api/experience/features/tax_basic")
        plus_tax = response.json()
        
        # Verify the change
        assert essential_tax["available"] == False, "tax_basic should NOT be available in Essential"
        assert plus_tax["available"] == True, "tax_basic should be available in Plus"
        
        print("✓ Feature availability correctly changes with mode")
        print(f"  - tax_basic in Essential: {essential_tax['available']}")
        print(f"  - tax_basic in Plus: {plus_tax['available']}")
    
    def test_bookkeeping_only_in_full_mode(self):
        """Test that bookkeeping features are only available in Full mode"""
        # Set to Plus mode
        self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "plus", "source": "test"}
        )
        
        # Check bookkeeping_journal feature (should NOT be available in Plus)
        response = self.session.get(f"{BASE_URL}/api/experience/features/bookkeeping_journal")
        plus_bookkeeping = response.json()
        
        # Set to Full mode
        self.session.put(
            f"{BASE_URL}/api/experience/mode",
            json={"mode": "full", "source": "test"}
        )
        
        # Check bookkeeping_journal feature again (should be available in Full)
        response = self.session.get(f"{BASE_URL}/api/experience/features/bookkeeping_journal")
        full_bookkeeping = response.json()
        
        # Verify the change
        assert plus_bookkeeping["available"] == False, "bookkeeping_journal should NOT be available in Plus"
        assert full_bookkeeping["available"] == True, "bookkeeping_journal should be available in Full"
        
        print("✓ Bookkeeping correctly gated to Full mode only")
        print(f"  - bookkeeping_journal in Plus: {plus_bookkeeping['available']}")
        print(f"  - bookkeeping_journal in Full: {full_bookkeeping['available']}")


class TestEssentialModeFeatures:
    """Test Essential mode specific features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token and set to Essential mode"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token") or data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            
            # Set to Essential mode for these tests
            self.session.put(
                f"{BASE_URL}/api/experience/mode",
                json={"mode": "essential", "source": "test"}
            )
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_essential_mode_has_ai_chat(self):
        """Test that Essential mode has AI chat access"""
        response = self.session.get(f"{BASE_URL}/api/experience/features/ai_chat")
        data = response.json()
        
        assert data["available"] == True, "ai_chat should be available in Essential mode"
        print("✓ AI chat is available in Essential mode")
    
    def test_essential_mode_has_bank_import(self):
        """Test that Essential mode has auto bank import"""
        response = self.session.get(f"{BASE_URL}/api/experience/features/bank_import_auto")
        data = response.json()
        
        assert data["available"] == True, "bank_import_auto should be available in Essential mode"
        print("✓ Auto bank import is available in Essential mode")
    
    def test_essential_mode_no_tax_module(self):
        """Test that Essential mode does NOT have tax module"""
        response = self.session.get(f"{BASE_URL}/api/experience/features/tax_basic")
        data = response.json()
        
        assert data["available"] == False, "tax_basic should NOT be available in Essential mode"
        print("✓ Tax module correctly hidden in Essential mode")
    
    def test_essential_mode_no_bookkeeping(self):
        """Test that Essential mode does NOT have bookkeeping"""
        response = self.session.get(f"{BASE_URL}/api/experience/features/bookkeeping_journal")
        data = response.json()
        
        assert data["available"] == False, "bookkeeping_journal should NOT be available in Essential mode"
        print("✓ Bookkeeping correctly hidden in Essential mode")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
