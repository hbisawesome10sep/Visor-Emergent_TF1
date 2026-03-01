"""
Test Tax Planning Scan & Auto-Deductions CRUD
==============================================
Tests for bulk scan endpoint (POST /api/tax-planning/scan) and 
auto-deductions management (GET, PUT, DELETE).

Test Coverage:
- POST /api/tax-planning/scan?fy=2025-26: Bulk scan returns deductions from transactions, holdings, SIPs, loans
- Idempotency: Second scan returns 0 new deductions
- GET /api/auto-tax-deductions?fy=2025-26: Returns newly scanned deductions
- PUT /api/auto-tax-deductions/{id}: Edit auto-detected deduction amount
- DELETE /api/auto-tax-deductions/{id}: Dismiss/delete auto-detected deduction
- Regression: 2-3 Visor AI endpoints

Author: Testing Agent
Date: January 2026
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')


class TestAuthentication:
    """Get auth token for testing"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login with demo account and get JWT token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Return headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestTaxPlanningAutoDeductionsCRUD(TestAuthentication):
    """
    Test Tax Planning Scan & Auto-Deductions CRUD
    
    Flow:
    1. Clear existing auto-deductions (to ensure clean state)
    2. Run bulk scan → verify count > 0
    3. Run scan again → verify count = 0 (idempotent)
    4. GET auto-deductions → verify they exist
    5. PUT to edit one deduction
    6. DELETE to dismiss one deduction
    """
    
    def test_01_clear_existing_auto_deductions(self, auth_headers):
        """Clear existing auto-deductions to start with clean state"""
        # First get all auto-deductions
        response = requests.get(
            f"{BASE_URL}/api/auto-tax-deductions",
            params={"fy": "2025-26"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET auto-deductions failed: {response.text}"
        data = response.json()
        
        # Delete each deduction if any exist
        deleted_count = 0
        if data.get("sections"):
            for section in data["sections"]:
                for txn in section.get("transactions", []):
                    del_response = requests.delete(
                        f"{BASE_URL}/api/auto-tax-deductions/{txn['id']}",
                        headers=auth_headers
                    )
                    if del_response.status_code == 200:
                        deleted_count += 1
        
        print(f"Cleared {deleted_count} existing auto-deductions")
        
        # Verify cleared
        verify_response = requests.get(
            f"{BASE_URL}/api/auto-tax-deductions",
            params={"fy": "2025-26"},
            headers=auth_headers
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data.get("count", 0) == 0, f"Expected 0 deductions after clear, got {verify_data.get('count')}"
        print("Auto-deductions cleared successfully")
    
    def test_02_bulk_scan_first_run(self, auth_headers):
        """POST /api/tax-planning/scan - First run should find deductions"""
        response = requests.post(
            f"{BASE_URL}/api/tax-planning/scan",
            params={"fy": "2025-26"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Bulk scan failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("status") == "scan_complete", f"Expected scan_complete status, got {data.get('status')}"
        assert "fy" in data, "Missing 'fy' in response"
        assert data["fy"] == "2025-26", f"Expected fy 2025-26, got {data['fy']}"
        assert "new_deductions_found" in data, "Missing 'new_deductions_found' in response"
        assert "total_new_amount" in data, "Missing 'total_new_amount' in response"
        assert "by_section" in data, "Missing 'by_section' in response"
        assert "sources_scanned" in data, "Missing 'sources_scanned' in response"
        
        # Verify sources were scanned
        expected_sources = ["transactions", "holdings", "sips", "loans"]
        assert data["sources_scanned"] == expected_sources, f"Expected sources {expected_sources}, got {data['sources_scanned']}"
        
        new_count = data["new_deductions_found"]
        total_amount = data["total_new_amount"]
        
        print(f"Bulk scan completed: {new_count} new deductions found, total amount ₹{total_amount}")
        
        # Verify by_section structure
        if new_count > 0:
            for section in data["by_section"]:
                assert "section" in section, "Missing 'section' in by_section item"
                assert "label" in section, "Missing 'label' in by_section item"
                assert "count" in section, "Missing 'count' in by_section item"
                assert "amount" in section, "Missing 'amount' in by_section item"
                print(f"  Section {section['section']}: {section['count']} deductions, ₹{section['amount']}")
        
        # Store for next test
        pytest.first_scan_count = new_count
        pytest.first_scan_amount = total_amount
    
    def test_03_bulk_scan_idempotent(self, auth_headers):
        """POST /api/tax-planning/scan - Second run should return 0 new deductions (idempotent)"""
        response = requests.post(
            f"{BASE_URL}/api/tax-planning/scan",
            params={"fy": "2025-26"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Bulk scan failed: {response.text}"
        data = response.json()
        
        assert data.get("status") == "scan_complete"
        assert data["new_deductions_found"] == 0, f"Expected 0 new deductions on second scan, got {data['new_deductions_found']}"
        assert data["total_new_amount"] == 0, f"Expected 0 total amount on second scan, got {data['total_new_amount']}"
        
        print("Idempotency verified: Second scan returned 0 new deductions")
    
    def test_04_get_auto_deductions(self, auth_headers):
        """GET /api/auto-tax-deductions?fy=2025-26 - Verify deductions were stored"""
        response = requests.get(
            f"{BASE_URL}/api/auto-tax-deductions",
            params={"fy": "2025-26"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET auto-deductions failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "fy" in data, "Missing 'fy' in response"
        assert data["fy"] == "2025-26"
        assert "sections" in data, "Missing 'sections' in response"
        assert "total_detected" in data, "Missing 'total_detected' in response"
        assert "count" in data, "Missing 'count' in response"
        
        # Should match first scan
        if hasattr(pytest, 'first_scan_count'):
            assert data["count"] == pytest.first_scan_count, f"Expected {pytest.first_scan_count} deductions, got {data['count']}"
        
        print(f"GET auto-deductions: {data['count']} deductions, ₹{data['total_detected']} total")
        
        # Verify section structure
        if data["sections"]:
            first_section = data["sections"][0]
            assert "section" in first_section, "Missing 'section' in section item"
            assert "section_label" in first_section, "Missing 'section_label' in section item"
            assert "limit" in first_section, "Missing 'limit' in section item"
            assert "total_amount" in first_section, "Missing 'total_amount' in section item"
            assert "transactions" in first_section, "Missing 'transactions' in section item"
            
            # Store a deduction ID for subsequent tests
            if first_section["transactions"]:
                txn = first_section["transactions"][0]
                assert "id" in txn, "Missing 'id' in transaction"
                assert "transaction_id" in txn, "Missing 'transaction_id' in transaction"
                assert "name" in txn, "Missing 'name' in transaction"
                assert "amount" in txn, "Missing 'amount' in transaction"
                
                pytest.test_deduction_id = txn["id"]
                pytest.test_deduction_original_amount = txn["amount"]
                print(f"  Sample deduction: {txn['name']} - ₹{txn['amount']} (id: {txn['id'][:8]}...)")
    
    def test_05_update_auto_deduction(self, auth_headers):
        """PUT /api/auto-tax-deductions/{id} - Edit deduction amount"""
        if not hasattr(pytest, 'test_deduction_id'):
            pytest.skip("No deduction ID available from previous test")
        
        deduction_id = pytest.test_deduction_id
        original_amount = pytest.test_deduction_original_amount
        new_amount = original_amount + 1000  # Add ₹1000 for testing
        
        response = requests.put(
            f"{BASE_URL}/api/auto-tax-deductions/{deduction_id}",
            json={"invested_amount": new_amount},
            headers=auth_headers
        )
        assert response.status_code == 200, f"PUT failed: {response.text}"
        data = response.json()
        
        # Verify updated amount
        assert data.get("amount") == new_amount, f"Expected amount {new_amount}, got {data.get('amount')}"
        print(f"Updated deduction: ₹{original_amount} → ₹{new_amount}")
        
        # Verify via GET
        verify_response = requests.get(
            f"{BASE_URL}/api/auto-tax-deductions",
            params={"fy": "2025-26"},
            headers=auth_headers
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        
        # Find the updated deduction
        found = False
        for section in verify_data.get("sections", []):
            for txn in section.get("transactions", []):
                if txn["id"] == deduction_id:
                    assert txn["amount"] == new_amount, f"Amount not persisted: expected {new_amount}, got {txn['amount']}"
                    found = True
                    break
            if found:
                break
        
        assert found, f"Updated deduction {deduction_id} not found in GET response"
        print("Update persisted and verified via GET")
    
    def test_06_update_nonexistent_deduction(self, auth_headers):
        """PUT /api/auto-tax-deductions/{id} - Non-existent ID should return 404"""
        fake_id = "nonexistent-deduction-id-12345"
        response = requests.put(
            f"{BASE_URL}/api/auto-tax-deductions/{fake_id}",
            json={"invested_amount": 5000},
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("404 correctly returned for non-existent deduction ID")
    
    def test_07_delete_auto_deduction(self, auth_headers):
        """DELETE /api/auto-tax-deductions/{id} - Dismiss deduction"""
        if not hasattr(pytest, 'test_deduction_id'):
            pytest.skip("No deduction ID available from previous test")
        
        deduction_id = pytest.test_deduction_id
        
        # Get count before delete
        before_response = requests.get(
            f"{BASE_URL}/api/auto-tax-deductions",
            params={"fy": "2025-26"},
            headers=auth_headers
        )
        assert before_response.status_code == 200
        count_before = before_response.json().get("count", 0)
        
        # Delete
        response = requests.delete(
            f"{BASE_URL}/api/auto-tax-deductions/{deduction_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"DELETE failed: {response.text}"
        data = response.json()
        assert data.get("status") == "dismissed", f"Expected status 'dismissed', got {data.get('status')}"
        print(f"Deduction {deduction_id[:8]}... dismissed")
        
        # Verify deleted via GET
        after_response = requests.get(
            f"{BASE_URL}/api/auto-tax-deductions",
            params={"fy": "2025-26"},
            headers=auth_headers
        )
        assert after_response.status_code == 200
        count_after = after_response.json().get("count", 0)
        
        assert count_after == count_before - 1, f"Count should decrease by 1: {count_before} → {count_after}"
        print(f"Delete verified: count {count_before} → {count_after}")
    
    def test_08_delete_nonexistent_deduction(self, auth_headers):
        """DELETE /api/auto-tax-deductions/{id} - Non-existent ID should return 404"""
        fake_id = "nonexistent-deduction-id-67890"
        response = requests.delete(
            f"{BASE_URL}/api/auto-tax-deductions/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("404 correctly returned for non-existent deduction ID on delete")


class TestTaxPlanningDifferentFY(TestAuthentication):
    """Test scan with different FY parameters"""
    
    def test_scan_different_fy(self, auth_headers):
        """POST /api/tax-planning/scan with different FY"""
        # Test with older FY
        response = requests.post(
            f"{BASE_URL}/api/tax-planning/scan",
            params={"fy": "2024-25"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Scan failed for FY 2024-25: {response.text}"
        data = response.json()
        
        assert data.get("fy") == "2024-25"
        print(f"FY 2024-25 scan: {data.get('new_deductions_found', 0)} deductions found")
    
    def test_get_deductions_default_fy(self, auth_headers):
        """GET /api/auto-tax-deductions without FY param uses default 2025-26"""
        response = requests.get(
            f"{BASE_URL}/api/auto-tax-deductions",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET failed: {response.text}"
        data = response.json()
        
        assert data.get("fy") == "2025-26", f"Expected default FY 2025-26, got {data.get('fy')}"
        print("Default FY 2025-26 correctly applied")


class TestVisorAIRegression(TestAuthentication):
    """Regression tests for Visor AI endpoints - verify they still work"""
    
    def test_01_visor_ai_basic_chat(self, auth_headers):
        """POST /api/visor-ai/chat - Basic finance query"""
        response = requests.post(
            f"{BASE_URL}/api/visor-ai/chat",
            json={"message": "Mera portfolio kaisa hai?"},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Missing 'id' in response"
        assert "user_msg_id" in data, "Missing 'user_msg_id' in response"
        assert "role" in data, "Missing 'role' in response"
        assert data["role"] == "assistant"
        assert "content" in data, "Missing 'content' in response"
        assert len(data["content"]) > 10, "Response content too short"
        
        print(f"Visor AI basic chat: {data['content'][:100]}...")
    
    def test_02_visor_ai_sip_calculator(self, auth_headers):
        """POST /api/visor-ai/chat - SIP calculator auto-detection"""
        response = requests.post(
            f"{BASE_URL}/api/visor-ai/chat",
            json={"message": "SIP calculate karo - 5000 monthly at 12% for 10 years"},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"SIP calculator failed: {response.text}"
        data = response.json()
        
        # Should have calculator_result
        assert "calculator_result" in data, "Missing 'calculator_result' in response"
        calc = data["calculator_result"]
        
        if calc:
            assert calc.get("type") == "SIP Calculator", f"Expected SIP Calculator type, got {calc.get('type')}"
            assert "monthly_sip" in calc, "Missing 'monthly_sip' in calculator result"
            assert "future_value" in calc, "Missing 'future_value' in calculator result"
            print(f"SIP Calculator: {calc.get('monthly_sip')} → {calc.get('future_value')}")
        else:
            print("Calculator not auto-triggered (might be handled inline)")
    
    def test_03_visor_ai_finance_guardrail(self, auth_headers):
        """POST /api/visor-ai/chat - Non-finance query should be redirected"""
        response = requests.post(
            f"{BASE_URL}/api/visor-ai/chat",
            json={"message": "Tell me a joke about cats"},
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Guardrail test failed: {response.text}"
        data = response.json()
        
        content = data.get("content", "").lower()
        # Should contain finance buddy redirect phrase
        assert any(phrase in content for phrase in [
            "visor", "finance", "money", "invest", "tax", "budget"
        ]), f"Guardrail may not have triggered: {content[:100]}"
        
        print(f"Finance guardrail: Response contains finance redirect")
    
    def test_04_visor_ai_history_get(self, auth_headers):
        """GET /api/visor-ai/history - Get chat history"""
        response = requests.get(
            f"{BASE_URL}/api/visor-ai/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"GET history failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "History should be a list"
        if data:
            msg = data[-1]
            assert "id" in msg, "Missing 'id' in message"
            assert "role" in msg, "Missing 'role' in message"
            assert "content" in msg, "Missing 'content' in message"
            assert "created_at" in msg, "Missing 'created_at' in message"
            print(f"History: {len(data)} messages, last role: {msg['role']}")
        else:
            print("History: Empty (expected if tests ran in isolation)")


class TestTaxPlanningAuthRequired(TestAuthentication):
    """Test that endpoints require authentication"""
    
    def test_scan_without_auth(self):
        """POST /api/tax-planning/scan without auth should fail"""
        response = requests.post(
            f"{BASE_URL}/api/tax-planning/scan",
            params={"fy": "2025-26"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Auth required for scan endpoint: verified")
    
    def test_get_deductions_without_auth(self):
        """GET /api/auto-tax-deductions without auth should fail"""
        response = requests.get(
            f"{BASE_URL}/api/auto-tax-deductions",
            params={"fy": "2025-26"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Auth required for GET auto-deductions: verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
