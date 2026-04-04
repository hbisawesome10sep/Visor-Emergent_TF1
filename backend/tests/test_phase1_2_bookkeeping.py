"""
Test suite for Phase 1+2: Bank Accounts CRUD, Journal Entries, Double-Entry System
Tests: bank_accounts.py, journal.py, updated transactions.py, bookkeeping.py

Features Tested:
- Bank Accounts CRUD (30 Indian banks list, create/update/delete/set-default)
- Transaction payment_mode and payment_account_name fields
- Auto-created Journal Entries from transactions (double-entry)
- Individual Account Ledgers with running balance
- Updated P&L and Balance Sheet from journal entries
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://enhanced-tax-module.preview.emergentagent.com')
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestAuth:
    """Get auth token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login and return token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        return data["token"]
    
    def test_login(self, auth_token):
        """Verify login works"""
        assert auth_token is not None
        assert len(auth_token) > 20
        print(f"✓ Login successful, token obtained")


class TestBankAccountsAPI:
    """Bank Accounts CRUD tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_banks_list(self):
        """GET /api/bank-accounts/banks-list - should return 30 Indian banks"""
        response = requests.get(f"{BASE_URL}/api/bank-accounts/banks-list")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "banks" in data
        assert len(data["banks"]) == 30, f"Expected 30 banks, got {len(data['banks'])}"
        # Check some known banks
        banks = data["banks"]
        assert any("SBI" in b for b in banks), "SBI not found"
        assert any("HDFC" in b for b in banks), "HDFC not found"
        assert any("ICICI" in b for b in banks), "ICICI not found"
        print(f"✓ Banks list returned {len(banks)} Indian banks")
    
    def test_create_bank_account(self, auth_token):
        """POST /api/bank-accounts - create a bank account"""
        response = requests.post(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "bank_name": "HDFC Bank",
                "account_name": "TEST_HDFC Savings",
                "account_number": "50100123456789",
                "ifsc_code": "HDFC0001234",
                "is_default": False
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["bank_name"] == "HDFC Bank"
        assert data["account_name"] == "TEST_HDFC Savings"
        assert "id" in data
        print(f"✓ Created bank account: {data['account_name']}")
        return data["id"]
    
    def test_get_bank_accounts(self, auth_token):
        """GET /api/bank-accounts - list user bank accounts"""
        response = requests.get(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} bank accounts")
    
    def test_update_bank_account(self, auth_token):
        """PUT /api/bank-accounts/{id} - update bank account"""
        # First create one
        create_resp = requests.post(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"bank_name": "Axis Bank", "account_name": "TEST_Update Account"}
        )
        account_id = create_resp.json()["id"]
        
        # Update it
        response = requests.put(
            f"{BASE_URL}/api/bank-accounts/{account_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"account_name": "TEST_Updated Savings Account", "ifsc_code": "UTIB0000123"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["account_name"] == "TEST_Updated Savings Account"
        assert data["ifsc_code"] == "UTIB0000123"
        print(f"✓ Updated bank account successfully")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/bank-accounts/{account_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_set_default_bank_account(self, auth_token):
        """PUT /api/bank-accounts/{id}/set-default - set as default"""
        # Create two accounts
        acc1 = requests.post(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"bank_name": "SBI", "account_name": "TEST_Primary Account", "is_default": True}
        ).json()
        
        acc2 = requests.post(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"bank_name": "ICICI", "account_name": "TEST_Secondary Account"}
        ).json()
        
        # Set second as default
        response = requests.put(
            f"{BASE_URL}/api/bank-accounts/{acc2['id']}/set-default",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify
        accounts = requests.get(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        
        for acc in accounts:
            if acc["id"] == acc2["id"]:
                assert acc["is_default"] == True, "New default not set"
        
        print(f"✓ Set default bank account successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bank-accounts/{acc1['id']}", headers={"Authorization": f"Bearer {auth_token}"})
        requests.delete(f"{BASE_URL}/api/bank-accounts/{acc2['id']}", headers={"Authorization": f"Bearer {auth_token}"})
    
    def test_delete_bank_account(self, auth_token):
        """DELETE /api/bank-accounts/{id} - delete specific bank account"""
        # Create
        acc = requests.post(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"bank_name": "Yes Bank", "account_name": "TEST_Delete Me"}
        ).json()
        
        # Delete
        response = requests.delete(
            f"{BASE_URL}/api/bank-accounts/{acc['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify deleted
        get_resp = requests.get(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        accounts = get_resp.json()
        assert not any(a["id"] == acc["id"] for a in accounts), "Account not deleted"
        print(f"✓ Deleted bank account successfully")


class TestTransactionsWithPaymentMode:
    """Test transactions with payment_mode and auto-journal creation"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_create_transaction_default_payment_mode(self, auth_token):
        """POST /api/transactions - payment_mode defaults to 'cash'"""
        response = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "expense",
                "amount": 150.0,
                "category": "Groceries",
                "description": "TEST_Default payment mode",
                "date": "2026-01-15"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["payment_mode"] == "cash", f"Expected 'cash', got {data['payment_mode']}"
        assert data["payment_account_name"] == "Cash", f"Expected 'Cash', got {data['payment_account_name']}"
        print(f"✓ Transaction created with default payment_mode='cash'")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/transactions/{data['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_create_income_with_bank_payment(self, auth_token):
        """POST /api/transactions - income with bank payment creates journal: Dr. Bank, Cr. Category"""
        response = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "income",
                "amount": 50000.0,
                "category": "Salary",
                "description": "TEST_Jan Salary",
                "date": "2026-01-10",
                "payment_mode": "bank",
                "payment_account_name": "HDFC Savings"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        txn_id = data["id"]
        
        # Verify journal entry was created
        time.sleep(0.5)  # Allow async journal creation
        journal_resp = requests.get(
            f"{BASE_URL}/api/journal?search=salary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert journal_resp.status_code == 200
        journal_data = journal_resp.json()
        
        # Check if journal entry exists for this transaction
        found = False
        for entry in journal_data.get("entries", []):
            if entry.get("reference_id") == txn_id:
                found = True
                # Verify double-entry: Dr. Bank, Cr. Salary
                entries = entry.get("entries", [])
                dr_entry = next((e for e in entries if e["debit"] > 0), None)
                cr_entry = next((e for e in entries if e["credit"] > 0), None)
                
                assert dr_entry is not None, "No debit entry found"
                assert cr_entry is not None, "No credit entry found"
                assert "HDFC" in dr_entry["account_name"], f"Debit should be Bank, got {dr_entry['account_name']}"
                assert "Salary" in cr_entry["account_name"], f"Credit should be Salary, got {cr_entry['account_name']}"
                print(f"✓ Income journal: Dr. {dr_entry['account_name']} {dr_entry['debit']}, Cr. {cr_entry['account_name']} {cr_entry['credit']}")
                break
        
        assert found, "Journal entry for income transaction not found"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_create_expense_with_cash_payment(self, auth_token):
        """POST /api/transactions - expense creates journal: Dr. Category, Cr. Cash"""
        response = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "expense",
                "amount": 2500.0,
                "category": "Electricity",
                "description": "TEST_Electricity Bill",
                "date": "2026-01-12",
                "payment_mode": "cash",
                "payment_account_name": "Cash"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        txn_id = response.json()["id"]
        
        time.sleep(0.5)
        journal_resp = requests.get(
            f"{BASE_URL}/api/journal?search=Electricity",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        journal_data = journal_resp.json()
        
        for entry in journal_data.get("entries", []):
            if entry.get("reference_id") == txn_id:
                entries = entry.get("entries", [])
                dr_entry = next((e for e in entries if e["debit"] > 0), None)
                cr_entry = next((e for e in entries if e["credit"] > 0), None)
                
                assert "Electricity" in dr_entry["account_name"], f"Debit should be Electricity, got {dr_entry['account_name']}"
                assert "Cash" in cr_entry["account_name"], f"Credit should be Cash, got {cr_entry['account_name']}"
                print(f"✓ Expense journal: Dr. {dr_entry['account_name']} {dr_entry['debit']}, Cr. {cr_entry['account_name']} {cr_entry['credit']}")
                break
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_create_investment_transaction(self, auth_token):
        """POST /api/transactions - investment creates journal: Dr. Asset, Cr. Cash/Bank"""
        response = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "investment",
                "amount": 10000.0,
                "category": "Mutual Funds",
                "description": "TEST_SIP Axis Bluechip",
                "date": "2026-01-05",
                "payment_mode": "bank",
                "payment_account_name": "ICICI Savings"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        txn_id = response.json()["id"]
        
        time.sleep(0.5)
        journal_resp = requests.get(
            f"{BASE_URL}/api/journal?search=Mutual",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        journal_data = journal_resp.json()
        
        for entry in journal_data.get("entries", []):
            if entry.get("reference_id") == txn_id:
                entries = entry.get("entries", [])
                dr_entry = next((e for e in entries if e["debit"] > 0), None)
                cr_entry = next((e for e in entries if e["credit"] > 0), None)
                
                # Investment: Dr. Asset (Mutual Funds), Cr. Bank
                assert dr_entry["account_type"] == "Real", f"Debit should be Real account, got {dr_entry['account_type']}"
                assert "ICICI" in cr_entry["account_name"], f"Credit should be Bank, got {cr_entry['account_name']}"
                print(f"✓ Investment journal: Dr. {dr_entry['account_name']} ({dr_entry['account_type']}), Cr. {cr_entry['account_name']}")
                break
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_search_transactions(self, auth_token):
        """GET /api/transactions?search= - search by description, category, payment_account_name"""
        # Create a transaction to search for
        create_resp = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "expense",
                "amount": 999.0,
                "category": "Shopping",
                "description": "TEST_SearchableItem12345",
                "date": "2026-01-15"
            }
        )
        txn_id = create_resp.json()["id"]
        
        # Search
        search_resp = requests.get(
            f"{BASE_URL}/api/transactions?search=SearchableItem12345",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert search_resp.status_code == 200
        results = search_resp.json()
        assert len(results) >= 1, "Search did not find the transaction"
        assert any(t["description"] == "TEST_SearchableItem12345" for t in results)
        print(f"✓ Transaction search works")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_delete_transaction_deletes_journal(self, auth_token):
        """DELETE /api/transactions/{id} - should also delete linked journal entry"""
        # Create
        create_resp = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "expense",
                "amount": 777.0,
                "category": "Transport",
                "description": "TEST_DeleteJournalTest",
                "date": "2026-01-15"
            }
        )
        txn_id = create_resp.json()["id"]
        
        time.sleep(0.5)
        
        # Verify journal exists
        journal_before = requests.get(
            f"{BASE_URL}/api/journal?search=DeleteJournalTest",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        
        has_journal = any(e.get("reference_id") == txn_id for e in journal_before.get("entries", []))
        assert has_journal, "Journal entry should exist before deletion"
        
        # Delete transaction
        del_resp = requests.delete(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert del_resp.status_code == 200
        
        time.sleep(0.5)
        
        # Verify journal deleted
        journal_after = requests.get(
            f"{BASE_URL}/api/journal?search=DeleteJournalTest",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        
        has_journal_after = any(e.get("reference_id") == txn_id for e in journal_after.get("entries", []))
        assert not has_journal_after, "Journal entry should be deleted with transaction"
        print(f"✓ Deleting transaction also deleted journal entry")


class TestJournalAPI:
    """Test Journal Entries API"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_journal_entries(self, auth_token):
        """GET /api/journal - list journal entries with pagination"""
        response = requests.get(
            f"{BASE_URL}/api/journal",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert "page" in data
        print(f"✓ Got {len(data['entries'])} journal entries, total: {data['total']}")
    
    def test_get_journal_with_search(self, auth_token):
        """GET /api/journal?search=keyword - search by narration and account_name"""
        response = requests.get(
            f"{BASE_URL}/api/journal?search=Salary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Journal search returned {len(data.get('entries', []))} entries")
    
    def test_get_journal_with_date_filter(self, auth_token):
        """GET /api/journal with start_date and end_date"""
        response = requests.get(
            f"{BASE_URL}/api/journal?start_date=2026-01-01&end_date=2026-01-31",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Journal date filter returned {len(data.get('entries', []))} entries for Jan 2026")
    
    def test_get_journal_accounts(self, auth_token):
        """GET /api/journal/accounts - list all unique accounts with totals"""
        response = requests.get(
            f"{BASE_URL}/api/journal/accounts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "accounts" in data
        
        if data["accounts"]:
            acc = data["accounts"][0]
            assert "name" in acc
            assert "account_type" in acc
            assert "total_debit" in acc
            assert "total_credit" in acc
            assert "balance" in acc
        print(f"✓ Got {len(data['accounts'])} unique accounts from journal")
    
    def test_get_journal_accounts_with_search(self, auth_token):
        """GET /api/journal/accounts?search=Electricity - search accounts"""
        response = requests.get(
            f"{BASE_URL}/api/journal/accounts?search=Cash",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Account search returned {len(data.get('accounts', []))} accounts")
    
    def test_get_individual_ledger(self, auth_token):
        """GET /api/journal/ledger/{account_name} - individual ledger with running balance"""
        # First get an account name
        accounts_resp = requests.get(
            f"{BASE_URL}/api/journal/accounts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        accounts = accounts_resp.json().get("accounts", [])
        
        if accounts:
            account_name = accounts[0]["name"]
            response = requests.get(
                f"{BASE_URL}/api/journal/ledger/{account_name}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert response.status_code == 200, f"Failed: {response.text}"
            data = response.json()
            
            assert "account_name" in data
            assert "account_type" in data
            assert "entries" in data
            assert "total_debit" in data
            assert "total_credit" in data
            assert "closing_balance" in data
            
            # Verify running balance in entries
            if data["entries"]:
                assert "balance" in data["entries"][0], "Running balance missing in entry"
            
            print(f"✓ Individual ledger for '{account_name}': {len(data['entries'])} entries, balance: {data['closing_balance']}")
        else:
            pytest.skip("No accounts found to test individual ledger")


class TestBooksAPI:
    """Test P&L and Balance Sheet from journal entries"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_pnl(self, auth_token):
        """GET /api/books/pnl - P&L based on journal entries"""
        response = requests.get(
            f"{BASE_URL}/api/books/pnl",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "income_sections" in data
        assert "expense_sections" in data
        assert "total_income" in data
        assert "total_expenses" in data
        assert "surplus_deficit" in data
        
        print(f"✓ P&L: Income={data['total_income']}, Expenses={data['total_expenses']}, Surplus={data['surplus_deficit']}")
    
    def test_get_balance_sheet(self, auth_token):
        """GET /api/books/balance-sheet - Balance Sheet based on journal entries"""
        response = requests.get(
            f"{BASE_URL}/api/books/balance-sheet",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "assets" in data
        assert "liabilities" in data
        assert "net_worth" in data
        assert "is_balanced" in data
        
        print(f"✓ Balance Sheet: Assets={data['assets']['total']}, Liabilities={data['liabilities']['total']}, Net Worth={data['net_worth']['closing']}, Balanced={data['is_balanced']}")
    
    def test_get_ledger(self, auth_token):
        """GET /api/books/ledger - General ledger from journal entries"""
        response = requests.get(
            f"{BASE_URL}/api/books/ledger",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "accounts" in data
        assert "entry_count" in data
        assert "account_count" in data
        
        print(f"✓ General Ledger: {data['account_count']} accounts, {data['entry_count']} entries")
    
    def test_get_ledger_with_search(self, auth_token):
        """GET /api/books/ledger?search= - search in ledger"""
        response = requests.get(
            f"{BASE_URL}/api/books/ledger?search=Cash",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Ledger search returned {data.get('account_count', 0)} matching accounts")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_cleanup_test_bank_accounts(self, auth_token):
        """Remove TEST_ prefixed bank accounts"""
        accounts = requests.get(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        
        deleted = 0
        for acc in accounts:
            if acc.get("account_name", "").startswith("TEST_"):
                requests.delete(
                    f"{BASE_URL}/api/bank-accounts/{acc['id']}",
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                deleted += 1
        
        print(f"✓ Cleaned up {deleted} TEST_ bank accounts")
    
    def test_cleanup_test_transactions(self, auth_token):
        """Remove TEST_ prefixed transactions"""
        txns = requests.get(
            f"{BASE_URL}/api/transactions?search=TEST_",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        
        deleted = 0
        for txn in txns:
            if txn.get("description", "").startswith("TEST_"):
                requests.delete(
                    f"{BASE_URL}/api/transactions/{txn['id']}",
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                deleted += 1
        
        print(f"✓ Cleaned up {deleted} TEST_ transactions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
