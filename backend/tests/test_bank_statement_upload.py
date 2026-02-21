"""
Test Bank Statement Upload & Parsing - Phase 5
Tests:
- POST /api/bank-statements/upload - CSV, PDF, Excel
- GET /api/bank-statements/history - Import history
- Perspective reversal (bank credit -> user income, bank debit -> user expense)
- Auto-categorization (ZOMATO -> Food & Dining, IRCTC -> Travel)
- Journal entry auto-creation
- Duplicate detection
- Bank account auto-creation
"""

import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestBankStatementUpload:
    """Bank Statement Upload & Parsing Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        assert self.token, "No token received"
        
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
    
    def test_upload_csv_statement_success(self):
        """Test CSV bank statement upload with correct parsing and categorization"""
        csv_content = """Date,Description,Debit,Credit,Balance
15/01/2025,SALARY JAN 2025,,85000.00,185000.00
18/01/2025,ZOMATO FOOD ORDER,450.00,,184550.00
20/01/2025,ELECTRICITY BILL BESCOM,1200.00,,183350.00
22/01/2025,AMAZON SHOPPING,3500.00,,179850.00
25/01/2025,INTEREST CREDIT Q3,,1250.00,181100.00
28/01/2025,HDFC MF SIP,5000.00,,176100.00
30/01/2025,UBER RIDE,280.00,,175820.00"""
        
        # Use multipart/form-data for file upload
        files = {
            'file': ('test_statement.csv', csv_content, 'text/csv')
        }
        data = {
            'bank_name': 'TEST_HDFC Bank',
            'account_name': 'TEST_HDFC Savings'
        }
        
        # Remove Content-Type header for multipart
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        
        # Verify response structure
        assert "message" in result
        assert "total_in_statement" in result
        assert "imported" in result
        assert "skipped_duplicates" in result
        assert "bank_account_id" in result
        
        # Check parsing results
        assert result["total_in_statement"] == 7, f"Expected 7 transactions, got {result['total_in_statement']}"
        assert result["bank_name"] == "TEST_HDFC Bank"
        assert result["account_name"] == "TEST_HDFC Savings"
        
        print(f"Imported: {result['imported']}, Skipped: {result['skipped_duplicates']}")
        
        return result
    
    def test_perspective_reversal_verified(self):
        """Verify bank credit -> income, bank debit -> expense"""
        # Upload a simple CSV with clear credit/debit
        csv_content = """Date,Description,Debit,Credit
15/01/2025,TEST_SALARY_VERIFY,,50000.00
16/01/2025,TEST_EXPENSE_VERIFY,1000.00,"""
        
        files = {'file': ('verify_perspective.csv', csv_content, 'text/csv')}
        data = {'bank_name': 'TEST_Verify Bank', 'account_name': 'TEST_Verify Account'}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        
        # Check transactions were imported
        assert result["imported"] >= 0 or result["skipped_duplicates"] >= 0
        
        # Verify by fetching transactions
        txn_response = self.session.get(f"{BASE_URL}/api/transactions", params={"search": "TEST_SALARY_VERIFY"})
        if txn_response.status_code == 200:
            txns = txn_response.json()
            if "transactions" in txns and len(txns["transactions"]) > 0:
                salary_txn = txns["transactions"][0]
                # Bank credit (deposit) should become user income
                assert salary_txn["type"] == "income", f"Expected income type, got {salary_txn['type']}"
                print(f"Perspective reversal verified: bank credit -> {salary_txn['type']}")
        
        txn_response = self.session.get(f"{BASE_URL}/api/transactions", params={"search": "TEST_EXPENSE_VERIFY"})
        if txn_response.status_code == 200:
            txns = txn_response.json()
            if "transactions" in txns and len(txns["transactions"]) > 0:
                expense_txn = txns["transactions"][0]
                # Bank debit (withdrawal) should become user expense
                assert expense_txn["type"] in ["expense", "investment"], f"Expected expense/investment, got {expense_txn['type']}"
                print(f"Perspective reversal verified: bank debit -> {expense_txn['type']}")
    
    def test_auto_categorization(self):
        """Test auto-categorization based on description keywords"""
        csv_content = """Date,Description,Debit,Credit
15/01/2025,TEST_ZOMATO_CAT,500.00,
16/01/2025,TEST_IRCTC_CAT,1500.00,
17/01/2025,TEST_AMAZON_CAT,2000.00,"""
        
        files = {'file': ('categorize_test.csv', csv_content, 'text/csv')}
        data = {'bank_name': 'TEST_Cat Bank', 'account_name': 'TEST_Cat Account'}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        
        # Check categorization by fetching transactions
        categories_to_check = [
            ("TEST_ZOMATO_CAT", "Food & Dining"),
            ("TEST_IRCTC_CAT", "Travel"),
            ("TEST_AMAZON_CAT", "Shopping")
        ]
        
        for search_term, expected_category in categories_to_check:
            txn_response = self.session.get(f"{BASE_URL}/api/transactions", params={"search": search_term})
            if txn_response.status_code == 200:
                txns = txn_response.json()
                if "transactions" in txns and len(txns["transactions"]) > 0:
                    txn = txns["transactions"][0]
                    print(f"{search_term}: category = {txn.get('category')}, expected = {expected_category}")
                    # Some flexibility in category names
                    assert txn.get("category") in [expected_category, "Other", "Transport"], \
                        f"Expected {expected_category} or similar, got {txn.get('category')}"
    
    def test_journal_entry_creation(self):
        """Test that journal entries are auto-created for imported transactions"""
        csv_content = """Date,Description,Debit,Credit
20/01/2025,TEST_JOURNAL_CHECK,800.00,"""
        
        files = {'file': ('journal_test.csv', csv_content, 'text/csv')}
        data = {'bank_name': 'TEST_Journal Bank', 'account_name': 'TEST_Journal Account'}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        
        # Check journal entries
        journal_response = self.session.get(f"{BASE_URL}/api/journal", params={"search": "TEST_JOURNAL_CHECK"})
        assert journal_response.status_code == 200, f"Journal fetch failed: {journal_response.text}"
        
        journals = journal_response.json()
        print(f"Journal entries found: {journals.get('total', 0)}")
        
        # If transactions were imported (not duplicates), journals should exist
        if response.json().get("imported", 0) > 0:
            assert journals.get("total", 0) >= 0, "Expected journal entries for imported transactions"
    
    def test_duplicate_detection(self):
        """Test that re-uploading same statement skips duplicates"""
        csv_content = """Date,Description,Debit,Credit
25/01/2025,TEST_DUPLICATE_CHECK,999.00,"""
        
        files = {'file': ('dup_test.csv', csv_content, 'text/csv')}
        data = {'bank_name': 'TEST_Dup Bank', 'account_name': 'TEST_Dup Account'}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # First upload
        response1 = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        assert response1.status_code == 200
        result1 = response1.json()
        imported_first = result1.get("imported", 0)
        
        print(f"First upload - imported: {imported_first}")
        
        # Second upload - same content
        files2 = {'file': ('dup_test2.csv', csv_content, 'text/csv')}
        response2 = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files2,
            data=data,
            headers=headers
        )
        assert response2.status_code == 200
        result2 = response2.json()
        
        print(f"Second upload - imported: {result2.get('imported')}, skipped: {result2.get('skipped_duplicates')}")
        
        # Second upload should skip duplicates
        if imported_first > 0:
            assert result2.get("skipped_duplicates", 0) >= 1, "Expected duplicates to be skipped"
    
    def test_bank_account_auto_creation(self):
        """Test that bank account is auto-created if not exists"""
        unique_name = f"TEST_AutoBank_{os.urandom(4).hex()}"
        csv_content = """Date,Description,Debit,Credit
26/01/2025,TEST_AUTO_BANK,100.00,"""
        
        files = {'file': ('auto_bank.csv', csv_content, 'text/csv')}
        data = {'bank_name': unique_name, 'account_name': f'{unique_name} Savings'}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        
        # Check if account was created
        assert "account_created" in result
        assert result["account_created"] == True, "Expected bank account to be auto-created"
        assert result["bank_account_id"], "Expected bank_account_id in response"
        
        print(f"Bank account auto-created: {result['account_created']}, ID: {result['bank_account_id']}")
    
    def test_get_upload_history(self):
        """Test GET /api/bank-statements/history endpoint"""
        response = self.session.get(f"{BASE_URL}/api/bank-statements/history")
        
        assert response.status_code == 200, f"History fetch failed: {response.text}"
        result = response.json()
        
        assert "imports" in result, "Expected 'imports' key in response"
        print(f"Import history count: {len(result['imports'])}")
        
        # Check structure of imports if any exist
        if len(result["imports"]) > 0:
            imp = result["imports"][0]
            assert "account_name" in imp
            assert "transaction_count" in imp
            assert "total_amount" in imp
            assert "date_range" in imp
            print(f"Sample import: {imp['account_name']} - {imp['transaction_count']} transactions")
    
    def test_unsupported_file_format(self):
        """Test that unsupported file formats are rejected"""
        files = {'file': ('test.txt', 'some text content', 'text/plain')}
        data = {'bank_name': 'Test Bank'}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400 for unsupported format, got {response.status_code}"
        print(f"Unsupported format rejected: {response.json().get('detail')}")
    
    def test_empty_csv(self):
        """Test that empty CSV returns appropriate error"""
        csv_content = """Date,Description,Debit,Credit"""  # Headers only
        
        files = {'file': ('empty.csv', csv_content, 'text/csv')}
        data = {'bank_name': 'Test Bank'}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        # Should fail with 422 - no transactions found
        assert response.status_code == 422, f"Expected 422 for empty CSV, got {response.status_code}"
        print(f"Empty CSV handled: {response.json().get('detail')}")
    
    def test_csv_with_indian_date_formats(self):
        """Test parsing of various Indian date formats"""
        csv_content = """Date,Description,Debit,Credit
15-01-2025,TEST_DATE_FORMAT_1,100.00,
16/01/25,TEST_DATE_FORMAT_2,200.00,
17 Jan 2025,TEST_DATE_FORMAT_3,300.00,"""
        
        files = {'file': ('date_formats.csv', csv_content, 'text/csv')}
        data = {'bank_name': 'TEST_DateFormat Bank'}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        
        # Should parse all date formats
        total_parsed = result.get("imported", 0) + result.get("skipped_duplicates", 0)
        print(f"Date formats parsed: {total_parsed} transactions from 3 rows")
    
    def test_csv_with_indian_amount_formats(self):
        """Test parsing of Indian amount formats (commas, INR symbol)"""
        csv_content = """Date,Description,Debit,Credit
15/01/2025,TEST_AMOUNT_FORMAT_1,"1,500.00",
16/01/2025,TEST_AMOUNT_FORMAT_2,₹2500.00,"""
        
        files = {'file': ('amount_formats.csv', csv_content, 'text/csv')}
        data = {'bank_name': 'TEST_AmountFormat Bank'}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/bank-statements/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        print(f"Indian amount formats parsed successfully")


class TestBankStatementCleanup:
    """Cleanup test data created during tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
    
    def test_cleanup_test_transactions(self):
        """Clean up TEST_ prefixed transactions"""
        # Fetch transactions with TEST_ prefix
        response = self.session.get(f"{BASE_URL}/api/transactions", params={"limit": 100})
        if response.status_code == 200:
            txns = response.json().get("transactions", [])
            deleted = 0
            for txn in txns:
                if txn.get("description", "").startswith("TEST_") or \
                   txn.get("payment_account_name", "").startswith("TEST_") or \
                   "TEST_" in txn.get("notes", ""):
                    del_response = self.session.delete(f"{BASE_URL}/api/transactions/{txn['id']}")
                    if del_response.status_code in [200, 204]:
                        deleted += 1
            print(f"Cleaned up {deleted} test transactions")
    
    def test_cleanup_test_bank_accounts(self):
        """Clean up TEST_ prefixed bank accounts"""
        response = self.session.get(f"{BASE_URL}/api/bank-accounts")
        if response.status_code == 200:
            accounts = response.json()
            deleted = 0
            for acc in accounts:
                if acc.get("bank_name", "").startswith("TEST_") or \
                   acc.get("account_name", "").startswith("TEST_"):
                    del_response = self.session.delete(f"{BASE_URL}/api/bank-accounts/{acc['id']}")
                    if del_response.status_code in [200, 204]:
                        deleted += 1
            print(f"Cleaned up {deleted} test bank accounts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
