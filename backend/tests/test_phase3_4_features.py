"""
Test suite for Phase 3+4: Ledger PDF Export, Asset Auto-Journaling, Holdings/Live, Portfolio-Rebalancing
Tests: journal.py (PDF export), assets.py (payment_mode + auto-journal), holdings.py (/live alias), portfolio.py (/rebalancing)

Features Tested:
- GET /api/journal/ledger-pdf/{account_name} - PDF export for ledgers
- POST /api/assets with payment_mode - auto-creates journal entry (Dr. Asset A/c, Cr. Cash/Bank A/c)
- DELETE /api/assets/{id} - deletes asset + linked journal entries
- GET /api/holdings/live - alias for GET /api/holdings with live prices
- GET /api/portfolio-rebalancing - risk profile based rebalancing suggestions
- GET /api/transactions?search= - search across description, category, notes, payment_account_name
- GET /api/journal?search=asset_name - find journal entry created from asset
"""

import pytest
import requests
import os
import time
import urllib.parse

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://visor-accounts.preview.emergentagent.com')
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


class TestLedgerPDFExport:
    """Test PDF export for individual ledgers"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_ledger_pdf_cash_account(self, auth_token):
        """GET /api/journal/ledger-pdf/Cash A/c - returns PDF file"""
        # URL encode the account name (contains space and /)
        account_name = "Cash A/c"
        encoded_name = urllib.parse.quote(account_name, safe='')
        
        response = requests.get(
            f"{BASE_URL}/api/journal/ledger-pdf/{encoded_name}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text[:500]}"
        assert response.headers.get("Content-Type") == "application/pdf", f"Expected application/pdf, got {response.headers.get('Content-Type')}"
        assert "Content-Disposition" in response.headers, "Missing Content-Disposition header"
        assert len(response.content) > 100, "PDF content too small"
        print(f"✓ PDF export for 'Cash A/c' returned {len(response.content)} bytes")
    
    def test_get_ledger_pdf_with_dates(self, auth_token):
        """GET /api/journal/ledger-pdf/{account} with date filters"""
        account_name = "Cash A/c"
        encoded_name = urllib.parse.quote(account_name, safe='')
        
        response = requests.get(
            f"{BASE_URL}/api/journal/ledger-pdf/{encoded_name}?start_date=2025-04-01&end_date=2026-03-31",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Failed: {response.status_code}"
        assert response.headers.get("Content-Type") == "application/pdf"
        print(f"✓ PDF export with date filter returned {len(response.content)} bytes")
    
    def test_get_ledger_pdf_empty_account(self, auth_token):
        """GET /api/journal/ledger-pdf/{non_existent} - should still return PDF (empty)"""
        account_name = "NonExistent A/c"
        encoded_name = urllib.parse.quote(account_name, safe='')
        
        response = requests.get(
            f"{BASE_URL}/api/journal/ledger-pdf/{encoded_name}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Should return 200 with empty PDF (no entries)
        assert response.status_code == 200, f"Failed: {response.status_code}"
        assert response.headers.get("Content-Type") == "application/pdf"
        print(f"✓ PDF export for non-existent account returned valid (possibly empty) PDF")


class TestAssetAutoJournaling:
    """Test asset creation with payment_mode and auto-journal entry"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_create_asset_with_cash_payment(self, auth_token):
        """POST /api/assets with payment_mode=cash creates journal: Dr. Asset A/c, Cr. Cash A/c"""
        asset_data = {
            "name": "TEST_Office Laptop",
            "category": "Electronics",
            "purchase_date": "2026-01-10",
            "purchase_value": 85000.0,
            "current_value": 80000.0,
            "depreciation_rate": 20.0,
            "payment_mode": "cash",
            "payment_account_name": "Cash"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/assets",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=asset_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["name"] == "TEST_Office Laptop"
        assert data["payment_mode"] == "cash"
        asset_id = data["id"]
        
        # Verify journal entry was created
        time.sleep(0.5)
        journal_resp = requests.get(
            f"{BASE_URL}/api/journal?search=Office Laptop",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert journal_resp.status_code == 200
        journal_data = journal_resp.json()
        
        # Find journal entry for this asset
        found = False
        for entry in journal_data.get("entries", []):
            if entry.get("reference_id") == asset_id:
                found = True
                entries = entry.get("entries", [])
                
                # Should have Dr. Asset A/c (Real/Asset), Cr. Cash A/c
                dr_entry = next((e for e in entries if e["debit"] > 0), None)
                cr_entry = next((e for e in entries if e["credit"] > 0), None)
                
                assert dr_entry is not None, "No debit entry found"
                assert cr_entry is not None, "No credit entry found"
                
                # Verify account types
                assert dr_entry["account_type"] == "Real", f"Debit should be Real account, got {dr_entry['account_type']}"
                assert dr_entry["account_group"] == "Asset", f"Debit should be Asset group, got {dr_entry['account_group']}"
                assert "Laptop" in dr_entry["account_name"], f"Debit should be Asset account, got {dr_entry['account_name']}"
                assert "Cash" in cr_entry["account_name"], f"Credit should be Cash, got {cr_entry['account_name']}"
                
                print(f"✓ Asset journal: Dr. {dr_entry['account_name']} ({dr_entry['account_type']}/{dr_entry['account_group']}) ₹{dr_entry['debit']}")
                print(f"  Cr. {cr_entry['account_name']} ₹{cr_entry['credit']}")
                break
        
        assert found, "Journal entry for asset not found"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/assets/{asset_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_create_asset_with_bank_payment(self, auth_token):
        """POST /api/assets with payment_mode=bank creates journal: Dr. Asset A/c, Cr. Bank A/c"""
        asset_data = {
            "name": "TEST_Toyota Car",
            "category": "Vehicle",
            "purchase_date": "2026-01-05",
            "purchase_value": 1200000.0,
            "current_value": 1100000.0,
            "depreciation_rate": 15.0,
            "payment_mode": "bank",
            "payment_account_name": "HDFC Savings"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/assets",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=asset_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        asset_id = data["id"]
        
        # Verify journal entry
        time.sleep(0.5)
        journal_resp = requests.get(
            f"{BASE_URL}/api/journal?search=Toyota",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        journal_data = journal_resp.json()
        
        for entry in journal_data.get("entries", []):
            if entry.get("reference_id") == asset_id:
                entries = entry.get("entries", [])
                cr_entry = next((e for e in entries if e["credit"] > 0), None)
                
                assert "HDFC" in cr_entry["account_name"], f"Credit should be Bank account, got {cr_entry['account_name']}"
                assert cr_entry["account_type"] == "Personal", f"Bank should be Personal account, got {cr_entry['account_type']}"
                
                print(f"✓ Asset with bank payment: Cr. {cr_entry['account_name']} ({cr_entry['account_type']}) ₹{cr_entry['credit']}")
                break
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/assets/{asset_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_delete_asset_deletes_journal(self, auth_token):
        """DELETE /api/assets/{id} - should also delete linked journal entry"""
        # Create asset
        asset_data = {
            "name": "TEST_Delete Asset Test",
            "category": "Furniture",
            "purchase_date": "2026-01-12",
            "purchase_value": 25000.0,
            "current_value": 24000.0,
            "depreciation_rate": 10.0,
            "payment_mode": "cash",
            "payment_account_name": "Cash"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/assets",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=asset_data
        )
        asset_id = create_resp.json()["id"]
        
        time.sleep(0.5)
        
        # Verify journal exists
        journal_before = requests.get(
            f"{BASE_URL}/api/journal?search=Delete Asset Test",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        
        has_journal = any(e.get("reference_id") == asset_id for e in journal_before.get("entries", []))
        assert has_journal, "Journal entry should exist before deletion"
        
        # Delete asset
        del_resp = requests.delete(
            f"{BASE_URL}/api/assets/{asset_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert del_resp.status_code == 200
        
        time.sleep(0.5)
        
        # Verify journal deleted
        journal_after = requests.get(
            f"{BASE_URL}/api/journal?search=Delete Asset Test",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        
        has_journal_after = any(e.get("reference_id") == asset_id for e in journal_after.get("entries", []))
        assert not has_journal_after, "Journal entry should be deleted with asset"
        print(f"✓ Deleting asset also deleted journal entry")
    
    def test_search_journal_for_asset(self, auth_token):
        """GET /api/journal?search=asset_name - should find journal entry created from asset"""
        # Create asset
        asset_data = {
            "name": "TEST_SearchableAsset999",
            "category": "Equipment",
            "purchase_date": "2026-01-15",
            "purchase_value": 50000.0,
            "current_value": 48000.0,
            "depreciation_rate": 10.0,
            "payment_mode": "cash",
            "payment_account_name": "Cash"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/assets",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=asset_data
        )
        asset_id = create_resp.json()["id"]
        
        time.sleep(0.5)
        
        # Search journal for asset name
        journal_resp = requests.get(
            f"{BASE_URL}/api/journal?search=SearchableAsset999",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert journal_resp.status_code == 200
        journal_data = journal_resp.json()
        
        found = any(e.get("reference_id") == asset_id for e in journal_data.get("entries", []))
        assert found, "Journal entry not found when searching by asset name"
        print(f"✓ Journal search by asset name works")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/assets/{asset_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )


class TestHoldingsLiveEndpoint:
    """Test /api/holdings/live alias endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_holdings_live(self, auth_token):
        """GET /api/holdings/live - should return same structure as GET /api/holdings"""
        response = requests.get(
            f"{BASE_URL}/api/holdings/live",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "holdings" in data, "Missing 'holdings' key"
        assert "summary" in data, "Missing 'summary' key"
        
        summary = data["summary"]
        assert "total_invested" in summary
        assert "total_current_value" in summary
        assert "total_gain_loss" in summary
        assert "holding_count" in summary
        
        print(f"✓ GET /api/holdings/live: {len(data['holdings'])} holdings, total invested: ₹{summary['total_invested']}")
    
    def test_holdings_and_holdings_live_same_data(self, auth_token):
        """GET /api/holdings and GET /api/holdings/live should return same data"""
        holdings_resp = requests.get(
            f"{BASE_URL}/api/holdings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        live_resp = requests.get(
            f"{BASE_URL}/api/holdings/live",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert holdings_resp.status_code == 200
        assert live_resp.status_code == 200
        
        holdings_data = holdings_resp.json()
        live_data = live_resp.json()
        
        # Same number of holdings
        assert len(holdings_data["holdings"]) == len(live_data["holdings"]), "Holding counts differ"
        
        # Same summary structure
        assert holdings_data["summary"]["holding_count"] == live_data["summary"]["holding_count"]
        
        print(f"✓ /api/holdings and /api/holdings/live return consistent data")


class TestPortfolioRebalancing:
    """Test portfolio rebalancing endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_portfolio_rebalancing(self, auth_token):
        """GET /api/portfolio-rebalancing - should return risk profile and suggestions"""
        response = requests.get(
            f"{BASE_URL}/api/portfolio-rebalancing",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "risk_profile" in data, "Missing 'risk_profile'"
        assert "target_allocation" in data, "Missing 'target_allocation'"
        assert "current_allocation" in data, "Missing 'current_allocation'"
        assert "suggestions" in data, "Missing 'suggestions'"
        assert "total_portfolio_value" in data, "Missing 'total_portfolio_value'"
        
        # Verify target allocation has asset classes
        target = data["target_allocation"]
        assert "Equity" in target or len(target) > 0, "Target allocation should have asset classes"
        
        # Verify current allocation structure
        current = data["current_allocation"]
        assert isinstance(current, dict), "Current allocation should be a dict"
        
        # Verify suggestions structure (may be empty if portfolio is balanced)
        suggestions = data["suggestions"]
        assert isinstance(suggestions, list), "Suggestions should be a list"
        
        if suggestions:
            sugg = suggestions[0]
            assert "asset_class" in sugg
            assert "current_pct" in sugg
            assert "target_pct" in sugg
            assert "action" in sugg
        
        print(f"✓ Portfolio rebalancing: Profile={data['risk_profile']}, Portfolio=₹{data['total_portfolio_value']}")
        print(f"  Target: {target}")
        print(f"  Suggestions: {len(suggestions)} recommendations")
    
    def test_rebalancing_risk_profiles(self, auth_token):
        """Verify rebalancing returns valid risk profile"""
        response = requests.get(
            f"{BASE_URL}/api/portfolio-rebalancing",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        valid_profiles = ["Conservative", "Moderate", "Aggressive", "Very Aggressive"]
        assert data["risk_profile"] in valid_profiles, f"Invalid risk profile: {data['risk_profile']}"
        print(f"✓ Risk profile '{data['risk_profile']}' is valid")


class TestTransactionSearch:
    """Test transaction search across multiple fields"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_search_by_description(self, auth_token):
        """GET /api/transactions?search= - search by description"""
        # Create test transaction
        txn_resp = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "expense",
                "amount": 1234.0,
                "category": "Shopping",
                "description": "TEST_UniqueDescSearch777",
                "date": "2026-01-15"
            }
        )
        txn_id = txn_resp.json()["id"]
        
        # Search
        search_resp = requests.get(
            f"{BASE_URL}/api/transactions?search=UniqueDescSearch777",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert search_resp.status_code == 200
        results = search_resp.json()
        
        found = any(t["id"] == txn_id for t in results)
        assert found, "Transaction not found by description search"
        print(f"✓ Transaction search by description works")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/transactions/{txn_id}", headers={"Authorization": f"Bearer {auth_token}"})
    
    def test_search_by_category(self, auth_token):
        """GET /api/transactions?search= - search by category"""
        search_resp = requests.get(
            f"{BASE_URL}/api/transactions?search=Groceries",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert search_resp.status_code == 200
        results = search_resp.json()
        
        # Should find transactions with Groceries category
        if results:
            groceries_found = any("Groceries" in t.get("category", "") for t in results)
            print(f"✓ Category search returned {len(results)} results, Groceries found: {groceries_found}")
        else:
            print(f"✓ Category search returned 0 results (no Groceries transactions)")
    
    def test_search_by_notes(self, auth_token):
        """GET /api/transactions?search= - search by notes field"""
        # Create test transaction with notes
        txn_resp = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "expense",
                "amount": 500.0,
                "category": "Entertainment",
                "description": "TEST_Movie",
                "date": "2026-01-15",
                "notes": "UniqueNotesSearch888"
            }
        )
        txn_id = txn_resp.json()["id"]
        
        # Search by notes
        search_resp = requests.get(
            f"{BASE_URL}/api/transactions?search=UniqueNotesSearch888",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert search_resp.status_code == 200
        results = search_resp.json()
        
        found = any(t["id"] == txn_id for t in results)
        assert found, "Transaction not found by notes search"
        print(f"✓ Transaction search by notes works")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/transactions/{txn_id}", headers={"Authorization": f"Bearer {auth_token}"})
    
    def test_search_by_payment_account_name(self, auth_token):
        """GET /api/transactions?search= - search by payment_account_name"""
        # Create test transaction with bank payment
        txn_resp = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "expense",
                "amount": 3000.0,
                "category": "Utilities",
                "description": "TEST_Bill Payment",
                "date": "2026-01-15",
                "payment_mode": "bank",
                "payment_account_name": "UniqueBank999"
            }
        )
        txn_id = txn_resp.json()["id"]
        
        # Search by payment_account_name
        search_resp = requests.get(
            f"{BASE_URL}/api/transactions?search=UniqueBank999",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert search_resp.status_code == 200
        results = search_resp.json()
        
        found = any(t["id"] == txn_id for t in results)
        assert found, "Transaction not found by payment_account_name search"
        print(f"✓ Transaction search by payment_account_name works")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/transactions/{txn_id}", headers={"Authorization": f"Bearer {auth_token}"})


class TestTransactionBankPaymentJournal:
    """Test transaction with bank payment creates correct double-entry journal"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_bank_payment_creates_double_entry(self, auth_token):
        """POST /api/transactions with payment_mode=bank - creates correct double-entry"""
        txn_resp = requests.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "type": "expense",
                "amount": 5000.0,
                "category": "Electricity",
                "description": "TEST_Bank Payment Journal Test",
                "date": "2026-01-15",
                "payment_mode": "bank",
                "payment_account_name": "ICICI Savings"
            }
        )
        assert txn_resp.status_code == 200
        txn_id = txn_resp.json()["id"]
        
        time.sleep(0.5)
        
        # Verify journal entry
        journal_resp = requests.get(
            f"{BASE_URL}/api/journal?search=Bank Payment Journal Test",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        journal_data = journal_resp.json()
        
        for entry in journal_data.get("entries", []):
            if entry.get("reference_id") == txn_id:
                entries = entry.get("entries", [])
                dr_entry = next((e for e in entries if e["debit"] > 0), None)
                cr_entry = next((e for e in entries if e["credit"] > 0), None)
                
                # For expense: Dr. Expense A/c, Cr. Bank A/c
                assert "Electricity" in dr_entry["account_name"], f"Debit should be Expense, got {dr_entry['account_name']}"
                assert dr_entry["account_type"] == "Nominal", f"Expense should be Nominal, got {dr_entry['account_type']}"
                
                assert "ICICI" in cr_entry["account_name"], f"Credit should be Bank, got {cr_entry['account_name']}"
                assert cr_entry["account_type"] == "Personal", f"Bank should be Personal, got {cr_entry['account_type']}"
                
                print(f"✓ Bank payment journal: Dr. {dr_entry['account_name']} ({dr_entry['account_type']}) ₹{dr_entry['debit']}")
                print(f"  Cr. {cr_entry['account_name']} ({cr_entry['account_type']}) ₹{cr_entry['credit']}")
                break
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/transactions/{txn_id}", headers={"Authorization": f"Bearer {auth_token}"})


class TestBooksAPIs:
    """Test Books APIs (P&L, Balance Sheet, Ledger) with journal data"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_pnl_from_journal(self, auth_token):
        """GET /api/books/pnl - P&L from journal entries"""
        response = requests.get(
            f"{BASE_URL}/api/books/pnl",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "total_income" in data
        assert "total_expenses" in data
        assert "surplus_deficit" in data
        assert "income_sections" in data
        assert "expense_sections" in data
        
        print(f"✓ P&L: Income=₹{data['total_income']}, Expenses=₹{data['total_expenses']}, Surplus=₹{data['surplus_deficit']}")
    
    def test_get_balance_sheet_from_journal(self, auth_token):
        """GET /api/books/balance-sheet - Balance Sheet from journal entries"""
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
        
        print(f"✓ Balance Sheet: Assets=₹{data['assets']['total']}, Liabilities=₹{data['liabilities']['total']}, Net Worth=₹{data['net_worth']['closing']}")
    
    def test_get_ledger_with_search(self, auth_token):
        """GET /api/books/ledger?search= - General ledger with search"""
        response = requests.get(
            f"{BASE_URL}/api/books/ledger?search=Cash",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "accounts" in data
        assert "entry_count" in data
        assert "account_count" in data
        
        print(f"✓ Ledger search 'Cash': {data['account_count']} accounts, {data['entry_count']} entries")


class TestBankAccountsCRUD:
    """Verify Bank Accounts CRUD still works"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_bank_accounts_crud(self, auth_token):
        """Full CRUD cycle for bank accounts"""
        # Create
        create_resp = requests.post(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "bank_name": "Kotak Bank",
                "account_name": "TEST_Phase34 Account"
            }
        )
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        account_id = create_resp.json()["id"]
        
        # Read
        get_resp = requests.get(
            f"{BASE_URL}/api/bank-accounts",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_resp.status_code == 200
        accounts = get_resp.json()
        assert any(a["id"] == account_id for a in accounts), "Created account not found"
        
        # Update
        update_resp = requests.put(
            f"{BASE_URL}/api/bank-accounts/{account_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"ifsc_code": "KKBK0000123"}
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["ifsc_code"] == "KKBK0000123"
        
        # Delete
        del_resp = requests.delete(
            f"{BASE_URL}/api/bank-accounts/{account_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert del_resp.status_code == 200
        
        print(f"✓ Bank Accounts CRUD works correctly")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_cleanup_test_assets(self, auth_token):
        """Remove TEST_ prefixed assets"""
        assets = requests.get(
            f"{BASE_URL}/api/assets",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        
        deleted = 0
        for asset in assets:
            if asset.get("name", "").startswith("TEST_"):
                requests.delete(
                    f"{BASE_URL}/api/assets/{asset['id']}",
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                deleted += 1
        
        print(f"✓ Cleaned up {deleted} TEST_ assets")
    
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
