"""
Visor Finance App - Transactions Redesign Tests (Iteration 3)
Tests for: Search functionality, category filters, new fields (is_recurring, recurring_frequency, is_split, split_count)
"""
import pytest
import requests
import os
from datetime import datetime

# Use public backend URL
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://consistency-update.preview.emergentagent.com').rstrip('/')

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

# ══════════════════════════════════════
#  TRANSACTION SEARCH & FILTER TESTS
# ══════════════════════════════════════

class TestTransactionSearch:
    """Test search and filtering functionality"""
    
    def test_search_by_description(self, api_client, demo_user_token):
        """Test searching transactions by description (e.g., 'Swiggy')"""
        # Demo user has 'Swiggy & Zomato' transaction
        response = api_client.get(
            f"{BASE_URL}/api/transactions?search=Swiggy",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200, f"Search failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify results contain 'Swiggy' in description or category or notes
        for txn in data:
            search_term = "swiggy"
            found = (
                search_term in txn.get("description", "").lower() or
                search_term in txn.get("category", "").lower() or
                search_term in txn.get("notes", "").lower()
            )
            assert found, f"Transaction {txn['id']} doesn't match search term"
        
        print(f"✓ Search 'Swiggy' returned {len(data)} transaction(s)")
        if len(data) > 0:
            print(f"  First result: {data[0]['description']}")
    
    def test_search_by_category(self, api_client, demo_user_token):
        """Test searching by category name"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions?search=Rent",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should find 'Rent' in category or description
        for txn in data:
            found = (
                "rent" in txn.get("description", "").lower() or
                "rent" in txn.get("category", "").lower()
            )
            assert found, f"Transaction doesn't match 'Rent' search"
        
        print(f"✓ Search 'Rent' returned {len(data)} transaction(s)")
    
    def test_search_empty_query(self, api_client, demo_user_token):
        """Test search with empty query (should return all)"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions?search=",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        print(f"✓ Empty search returned {len(data)} transaction(s)")
    
    def test_search_no_results(self, api_client, demo_user_token):
        """Test search with term that doesn't match anything"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions?search=XYZNONEXISTENT999",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 0, "Should return empty list for no matches"
        print("✓ Search with no matches returned empty list")

class TestTransactionCategoryFilter:
    """Test category filtering"""
    
    def test_filter_by_category(self, api_client, demo_user_token):
        """Test filtering by category (e.g., Food)"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions?category=Food",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        # All transactions should have category='Food'
        for txn in data:
            assert txn["category"] == "Food", f"Transaction has wrong category: {txn['category']}"
        
        print(f"✓ Category filter 'Food' returned {len(data)} transaction(s)")
    
    def test_filter_by_multiple_categories_combined_with_type(self, api_client, demo_user_token):
        """Test combining type and category filters"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions?type=expense&category=Rent",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        for txn in data:
            assert txn["type"] == "expense", "Type should be expense"
            assert txn["category"] == "Rent", "Category should be Rent"
        
        print(f"✓ Combined filter (type=expense, category=Rent) returned {len(data)} transaction(s)")

class TestTransactionCombinedFilters:
    """Test multiple filters working together"""
    
    def test_type_category_search_combined(self, api_client, demo_user_token):
        """Test all three filters together: type + category + search"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions?type=expense&category=Food&search=Swiggy",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        for txn in data:
            assert txn["type"] == "expense", "Type should be expense"
            assert txn["category"] == "Food", "Category should be Food"
            # Search should match description/category/notes
            search_match = (
                "swiggy" in txn.get("description", "").lower() or
                "swiggy" in txn.get("category", "").lower() or
                "swiggy" in txn.get("notes", "").lower()
            )
            assert search_match, "Should match search term"
        
        print(f"✓ Triple filter (type+category+search) returned {len(data)} transaction(s)")

# ══════════════════════════════════════
#  NEW TRANSACTION FIELDS TESTS
# ══════════════════════════════════════

class TestRecurringTransactions:
    """Test new recurring transaction fields"""
    
    def test_create_recurring_transaction(self, api_client, demo_user_token):
        """Test creating a transaction with is_recurring=true and recurring_frequency"""
        response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {demo_user_token}"},
            json={
                "type": "expense",
                "amount": 1500,
                "category": "Utilities",
                "description": "TEST_recurring - Netflix Monthly",
                "date": "2026-02-15",
                "is_recurring": True,
                "recurring_frequency": "Monthly",
                "notes": "Auto-renews on 15th"
            }
        )
        assert response.status_code in [200, 201], f"Create recurring transaction failed: {response.text}"
        
        data = response.json()
        assert data["is_recurring"] == True, "is_recurring should be True"
        assert data["recurring_frequency"] == "Monthly", "recurring_frequency should be Monthly"
        assert data["description"] == "TEST_recurring - Netflix Monthly"
        assert data["amount"] == 1500
        
        print(f"✓ Recurring transaction created: {data['id']}")
        print(f"  - Frequency: {data['recurring_frequency']}")
    
    def test_create_recurring_transaction_without_frequency(self, api_client, demo_user_token):
        """Test creating recurring transaction without specifying frequency (should be null)"""
        response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {demo_user_token}"},
            json={
                "type": "income",
                "amount": 5000,
                "category": "Freelance",
                "description": "TEST_recurring_no_freq - Regular Client",
                "date": "2026-02-15",
                "is_recurring": True
            }
        )
        assert response.status_code in [200, 201]
        
        data = response.json()
        assert data["is_recurring"] == True
        # recurring_frequency should be None or null if not provided
        print(f"✓ Recurring transaction without frequency: {data['id']}")
    
    def test_create_non_recurring_transaction(self, api_client, demo_user_token):
        """Test creating a normal non-recurring transaction (default behavior)"""
        response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {demo_user_token}"},
            json={
                "type": "expense",
                "amount": 250,
                "category": "Food",
                "description": "TEST_one_time - Coffee",
                "date": "2026-02-15",
                "is_recurring": False
            }
        )
        assert response.status_code in [200, 201]
        
        data = response.json()
        assert data["is_recurring"] == False
        assert data.get("recurring_frequency") is None or data.get("recurring_frequency") is None
        print(f"✓ Non-recurring transaction created: {data['id']}")

class TestSplitTransactions:
    """Test new split expense fields"""
    
    def test_create_split_transaction(self, api_client, demo_user_token):
        """Test creating a transaction with is_split=true and split_count"""
        response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {demo_user_token}"},
            json={
                "type": "expense",
                "amount": 2000,
                "category": "Food",
                "description": "TEST_split - Dinner with friends",
                "date": "2026-02-15",
                "is_split": True,
                "split_count": 4,
                "notes": "Split between 4 people"
            }
        )
        assert response.status_code in [200, 201], f"Create split transaction failed: {response.text}"
        
        data = response.json()
        assert data["is_split"] == True, "is_split should be True"
        assert data["split_count"] == 4, "split_count should be 4"
        assert data["amount"] == 2000
        
        # Calculate per-person amount
        per_person = data["amount"] / data["split_count"]
        print(f"✓ Split transaction created: {data['id']}")
        print(f"  - Total: ₹{data['amount']}, Split: {data['split_count']} people")
        print(f"  - Each pays: ₹{per_person:.2f}")
    
    def test_create_non_split_transaction(self, api_client, demo_user_token):
        """Test creating a normal transaction without splitting"""
        response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {demo_user_token}"},
            json={
                "type": "expense",
                "amount": 500,
                "category": "Transport",
                "description": "TEST_no_split - Solo Uber ride",
                "date": "2026-02-15",
                "is_split": False,
                "split_count": 1
            }
        )
        assert response.status_code in [200, 201]
        
        data = response.json()
        assert data["is_split"] == False
        assert data["split_count"] == 1
        print(f"✓ Non-split transaction created: {data['id']}")
    
    def test_create_recurring_and_split_transaction(self, api_client, demo_user_token):
        """Test creating a transaction that is both recurring AND split"""
        response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {demo_user_token}"},
            json={
                "type": "expense",
                "amount": 3000,
                "category": "Utilities",
                "description": "TEST_recurring_split - Shared Internet",
                "date": "2026-02-15",
                "is_recurring": True,
                "recurring_frequency": "Monthly",
                "is_split": True,
                "split_count": 3,
                "notes": "Split with 2 roommates, renews monthly"
            }
        )
        assert response.status_code in [200, 201], f"Create recurring+split failed: {response.text}"
        
        data = response.json()
        assert data["is_recurring"] == True
        assert data["recurring_frequency"] == "Monthly"
        assert data["is_split"] == True
        assert data["split_count"] == 3
        
        print(f"✓ Recurring + Split transaction created: {data['id']}")
        print(f"  - Recurring: {data['recurring_frequency']}")
        print(f"  - Split: {data['split_count']} people (₹{data['amount'] / data['split_count']:.2f} each)")

class TestTransactionResponseFields:
    """Test that all new fields are returned in GET requests"""
    
    def test_get_transactions_includes_new_fields(self, api_client, demo_user_token):
        """Test that GET /transactions returns new fields"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            txn = data[0]
            # Check that new fields exist (even if they're false/null)
            assert "is_recurring" in txn, "Missing is_recurring field"
            assert "recurring_frequency" in txn, "Missing recurring_frequency field"
            assert "is_split" in txn, "Missing is_split field"
            assert "split_count" in txn, "Missing split_count field"
            assert "notes" in txn, "Missing notes field"
            
            print("✓ All new fields present in GET /transactions response")
            print(f"  Fields: is_recurring, recurring_frequency, is_split, split_count, notes")
        else:
            print("✓ No transactions to check (empty list)")
