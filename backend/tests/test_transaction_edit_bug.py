"""
Transaction Edit Bug Fix Tests - Iteration 6
Tests for: PUT /api/transactions/:id (edit transaction functionality)
Bug Context: Transaction edits were previously not saving (showing fake alert instead of calling API)
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

# Use public backend URL for testing
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://enhanced-tax-module.preview.emergentagent.com').rstrip('/')

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture
def demo_user_token(api_client):
    """Login with demo user and return token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "rajesh@visor.demo",
        "password": "Demo@123"
    })
    assert response.status_code == 200, f"Demo login failed: {response.text}"
    data = response.json()
    return data["token"]

@pytest.fixture
def test_user_token(api_client):
    """Create a test user and return token for isolated testing"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    email = f"TEST_edit_{timestamp}@visor.test"
    
    response = api_client.post(f"{BASE_URL}/api/auth/register", json={
        "email": email,
        "password": "Test@1234",
        "full_name": "TEST Edit User",
        "dob": "1995-01-01",
        "pan": "EDITTEST12",
        "aadhaar": "123456789012"
    })
    
    if response.status_code in [200, 201]:
        data = response.json()
        return data["token"]
    else:
        pytest.skip(f"Could not create test user: {response.text}")

# ══════════════════════════════════════
#  PUT /api/transactions/:id TESTS
# ══════════════════════════════════════

class TestTransactionPutEndpoint:
    """Tests for the PUT /api/transactions/:id endpoint - Bug fix verification"""
    
    def test_put_endpoint_exists(self, api_client, test_user_token):
        """Verify PUT endpoint exists and responds (not 404 or 405)"""
        # First create a transaction
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 100,
                "category": "Food",
                "description": "TEST_put_exists",
                "date": "2026-02-15"
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        
        # Test PUT endpoint exists
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 100,
                "category": "Food",
                "description": "TEST_put_exists_updated",
                "date": "2026-02-15"
            }
        )
        # Should NOT be 404 (not found) or 405 (method not allowed)
        assert put_response.status_code not in [404, 405], f"PUT endpoint missing or not allowed: {put_response.status_code}"
        assert put_response.status_code == 200, f"PUT failed: {put_response.status_code} - {put_response.text}"
        print(f"✓ PUT /api/transactions/:id endpoint exists and responds with 200")
    
    def test_update_amount(self, api_client, test_user_token):
        """Test updating transaction amount persists correctly"""
        # Create
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 500.00,
                "category": "Shopping",
                "description": "TEST_amount_update",
                "date": "2026-02-15"
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        original_amount = create_response.json()["amount"]
        
        # Update amount
        new_amount = 750.50
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": new_amount,
                "category": "Shopping",
                "description": "TEST_amount_update",
                "date": "2026-02-15"
            }
        )
        assert put_response.status_code == 200, f"PUT failed: {put_response.text}"
        
        updated_txn = put_response.json()
        assert updated_txn["amount"] == new_amount, f"Amount not updated: expected {new_amount}, got {updated_txn['amount']}"
        
        # Verify persistence via GET
        get_response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert get_response.status_code == 200
        txns = get_response.json()
        found_txn = next((t for t in txns if t["id"] == txn_id), None)
        assert found_txn is not None, "Transaction not found in GET"
        assert found_txn["amount"] == new_amount, f"Amount not persisted: expected {new_amount}, got {found_txn['amount']}"
        
        print(f"✓ Amount updated from {original_amount} to {new_amount} and persisted")
    
    def test_update_description(self, api_client, test_user_token):
        """Test updating transaction description persists correctly"""
        # Create
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 200,
                "category": "Food",
                "description": "TEST_original_description",
                "date": "2026-02-15"
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        
        # Update description
        new_description = "TEST_updated_description_after_edit"
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 200,
                "category": "Food",
                "description": new_description,
                "date": "2026-02-15"
            }
        )
        assert put_response.status_code == 200
        assert put_response.json()["description"] == new_description
        
        # Verify persistence
        get_response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        txns = get_response.json()
        found_txn = next((t for t in txns if t["id"] == txn_id), None)
        assert found_txn["description"] == new_description, "Description not persisted"
        
        print(f"✓ Description updated and persisted")
    
    def test_update_date(self, api_client, test_user_token):
        """Test updating transaction date persists correctly - critical for calendar picker"""
        original_date = "2026-02-10"
        new_date = "2026-02-20"
        
        # Create
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 300,
                "category": "Transport",
                "description": "TEST_date_update",
                "date": original_date
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        assert create_response.json()["date"] == original_date
        
        # Update date
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 300,
                "category": "Transport",
                "description": "TEST_date_update",
                "date": new_date
            }
        )
        assert put_response.status_code == 200
        assert put_response.json()["date"] == new_date, f"Date not updated: expected {new_date}, got {put_response.json()['date']}"
        
        # Verify persistence
        get_response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        txns = get_response.json()
        found_txn = next((t for t in txns if t["id"] == txn_id), None)
        assert found_txn["date"] == new_date, f"Date not persisted: expected {new_date}, got {found_txn['date']}"
        
        print(f"✓ Date updated from {original_date} to {new_date} and persisted")
    
    def test_update_category(self, api_client, test_user_token):
        """Test updating transaction category persists correctly"""
        # Create
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 150,
                "category": "Food",
                "description": "TEST_category_update",
                "date": "2026-02-15"
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        
        # Update category
        new_category = "Entertainment"
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 150,
                "category": new_category,
                "description": "TEST_category_update",
                "date": "2026-02-15"
            }
        )
        assert put_response.status_code == 200
        assert put_response.json()["category"] == new_category
        
        # Verify persistence
        get_response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        txns = get_response.json()
        found_txn = next((t for t in txns if t["id"] == txn_id), None)
        assert found_txn["category"] == new_category, "Category not persisted"
        
        print(f"✓ Category updated and persisted")
    
    def test_update_multiple_fields(self, api_client, test_user_token):
        """Test updating multiple fields at once (amount, description, date)"""
        # Create
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 100,
                "category": "Food",
                "description": "TEST_multi_original",
                "date": "2026-02-01"
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        
        # Update multiple fields
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 999.99,
                "category": "Shopping",
                "description": "TEST_multi_updated",
                "date": "2026-02-28"
            }
        )
        assert put_response.status_code == 200
        updated = put_response.json()
        
        assert updated["amount"] == 999.99, "Amount not updated"
        assert updated["category"] == "Shopping", "Category not updated"
        assert updated["description"] == "TEST_multi_updated", "Description not updated"
        assert updated["date"] == "2026-02-28", "Date not updated"
        
        # Verify all changes persist
        get_response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        txns = get_response.json()
        found_txn = next((t for t in txns if t["id"] == txn_id), None)
        
        assert found_txn["amount"] == 999.99, "Amount not persisted"
        assert found_txn["category"] == "Shopping", "Category not persisted"
        assert found_txn["description"] == "TEST_multi_updated", "Description not persisted"
        assert found_txn["date"] == "2026-02-28", "Date not persisted"
        
        print(f"✓ Multiple fields updated and persisted correctly")
    
    def test_update_nonexistent_transaction(self, api_client, test_user_token):
        """Test PUT on non-existent transaction returns 404"""
        fake_id = "nonexistent-transaction-id-12345"
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{fake_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 100,
                "category": "Food",
                "description": "Should not work",
                "date": "2026-02-15"
            }
        )
        assert put_response.status_code == 404, f"Expected 404, got {put_response.status_code}"
        print(f"✓ PUT on non-existent transaction correctly returns 404")
    
    def test_update_type_change(self, api_client, test_user_token):
        """Test changing transaction type (expense -> income)"""
        # Create expense
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 500,
                "category": "Food",
                "description": "TEST_type_change",
                "date": "2026-02-15"
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        assert create_response.json()["type"] == "expense"
        
        # Change to income
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "income",
                "amount": 500,
                "category": "Salary",
                "description": "TEST_type_change",
                "date": "2026-02-15"
            }
        )
        assert put_response.status_code == 200
        assert put_response.json()["type"] == "income"
        
        print(f"✓ Transaction type changed from expense to income")
    
    def test_update_optional_fields(self, api_client, test_user_token):
        """Test updating optional fields (notes, is_recurring, etc.)"""
        # Create
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 200,
                "category": "Utilities",
                "description": "TEST_optional_fields",
                "date": "2026-02-15",
                "is_recurring": False,
                "notes": None
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        
        # Update with optional fields
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 200,
                "category": "Utilities",
                "description": "TEST_optional_fields",
                "date": "2026-02-15",
                "is_recurring": True,
                "recurring_frequency": "Monthly",
                "notes": "Monthly electricity bill"
            }
        )
        assert put_response.status_code == 200
        updated = put_response.json()
        
        assert updated.get("is_recurring") == True, "is_recurring not updated"
        assert updated.get("recurring_frequency") == "Monthly", "recurring_frequency not updated"
        assert updated.get("notes") == "Monthly electricity bill", "notes not updated"
        
        print(f"✓ Optional fields (is_recurring, notes) updated correctly")

# ══════════════════════════════════════
#  DELETE STILL WORKS TEST
# ══════════════════════════════════════

class TestDeleteStillWorks:
    """Verify delete functionality still works after PUT bug fix"""
    
    def test_delete_after_update(self, api_client, test_user_token):
        """Test that delete works after updating a transaction"""
        # Create
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 100,
                "category": "Other",
                "description": "TEST_delete_after_update",
                "date": "2026-02-15"
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        
        # Update
        put_response = api_client.put(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "type": "expense",
                "amount": 150,
                "category": "Other",
                "description": "TEST_delete_after_update_modified",
                "date": "2026-02-15"
            }
        )
        assert put_response.status_code == 200
        
        # Delete
        delete_response = api_client.delete(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        
        # Verify deletion
        get_response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        txns = get_response.json()
        found_txn = next((t for t in txns if t["id"] == txn_id), None)
        assert found_txn is None, "Transaction still exists after delete"
        
        print(f"✓ Delete still works correctly after update")
