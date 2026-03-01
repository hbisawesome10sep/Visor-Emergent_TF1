"""
Backend tests for Phase 1, 3, 4 features:
- Security: PIN lock, biometric, AES-256 encryption
- Gmail Email Parsing: OAuth connect, status, sync
- SMS Transaction Parsing: Android SMS batch parsing
"""
import pytest
import requests
import os
import sys

# Add backend to path for encryption module testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://portfolio-tracker-211.preview.emergentagent.com')
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestAuthLogin:
    """Test authentication endpoints."""

    def test_login_success(self):
        """Test login with valid credentials returns token and user."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response missing token"
        assert "user" in data, "Response missing user"
        assert data["user"]["email"] == TEST_EMAIL
        assert "full_name" in data["user"]
        assert "pan" in data["user"]
        assert "aadhaar_last4" in data["user"]
        print(f"✓ Login successful for {TEST_EMAIL}")

    def test_login_invalid_password(self):
        """Test login with invalid password returns 401."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": "wrongpassword"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid login correctly returns 401")


class TestGmailIntegration:
    """Test Gmail OAuth and sync endpoints."""

    @pytest.fixture
    def auth_token(self):
        """Get authentication token for tests."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]

    def test_gmail_status_unauthenticated(self):
        """Test Gmail status without auth returns 401."""
        response = requests.get(f"{BASE_URL}/api/gmail/status")
        assert response.status_code == 401
        print("✓ Gmail status correctly requires authentication")

    def test_gmail_status_returns_connected_false(self, auth_token):
        """Test Gmail status returns connected: false for new user."""
        response = requests.get(
            f"{BASE_URL}/api/gmail/status",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data, "Response missing 'connected' field"
        assert data["connected"] == False, f"Expected connected=False, got {data['connected']}"
        print(f"✓ Gmail status returns connected=False for test user")

    def test_gmail_connect_returns_auth_url(self, auth_token):
        """Test Gmail connect returns Google OAuth URL."""
        response = requests.get(
            f"{BASE_URL}/api/gmail/connect",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data, "Response missing auth_url"
        assert data["auth_url"].startswith("https://accounts.google.com"), \
            f"auth_url should start with Google OAuth URL, got: {data['auth_url'][:50]}"
        print(f"✓ Gmail connect returns valid Google OAuth URL")

    def test_gmail_connect_url_contains_required_params(self, auth_token):
        """Test Gmail OAuth URL contains required parameters."""
        response = requests.get(
            f"{BASE_URL}/api/gmail/connect",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        auth_url = data["auth_url"]
        
        # Check required OAuth params
        assert "client_id=" in auth_url, "Missing client_id in OAuth URL"
        assert "redirect_uri=" in auth_url, "Missing redirect_uri in OAuth URL"
        assert "scope=" in auth_url, "Missing scope in OAuth URL"
        assert "state=" in auth_url, "Missing state in OAuth URL"
        assert "gmail.readonly" in auth_url, "Missing gmail.readonly scope"
        print("✓ Gmail OAuth URL contains all required parameters")


class TestSMSParsing:
    """Test SMS transaction parsing endpoint."""

    @pytest.fixture
    def auth_token(self):
        """Get authentication token for tests."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]

    def test_sms_parse_hdfc_debit(self, auth_token):
        """Test parsing HDFC Bank debit SMS."""
        sms_data = [{
            "body": "Rs.5,000.00 debited from a/c XX1234 on 18-02-2026 at Swiggy-HDFC Bank",
            "sender": "HDFCBK"
        }]
        response = requests.post(
            f"{BASE_URL}/api/sms/parse",
            json=sms_data,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
        )
        assert response.status_code == 200, f"SMS parse failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["parsed_count"] == 1
        assert len(data["transactions"]) == 1
        
        txn = data["transactions"][0]
        assert txn["amount"] == 5000.0, f"Expected amount 5000, got {txn['amount']}"
        assert txn["type"] == "expense", f"Expected type expense, got {txn['type']}"
        assert "HDFC" in txn["description"]
        print(f"✓ HDFC debit SMS parsed correctly: ₹{txn['amount']} ({txn['type']})")

    def test_sms_parse_sbi_credit(self, auth_token):
        """Test parsing SBI Bank credit SMS."""
        sms_data = [{
            "body": "Rs.25,000.00 credited to a/c XX5678 on 18-02-2026 SBI",
            "sender": "SBIBNK"
        }]
        response = requests.post(
            f"{BASE_URL}/api/sms/parse",
            json=sms_data,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["parsed_count"] == 1
        
        txn = data["transactions"][0]
        assert txn["amount"] == 25000.0
        assert txn["type"] == "income"
        assert "SBI" in txn["description"]
        print(f"✓ SBI credit SMS parsed correctly: ₹{txn['amount']} ({txn['type']})")

    def test_sms_parse_batch_multiple(self, auth_token):
        """Test parsing multiple SMS in batch."""
        sms_data = [
            {"body": "Rs.1,500.00 debited from a/c XX1234 at Amazon HDFC Bank", "sender": "HDFCBK"},
            {"body": "Rs.3,000.00 debited from a/c XX1234 at Zomato ICICI", "sender": "ICICIB"},
            {"body": "Rs.50,000.00 credited to a/c XX5678 SBI salary", "sender": "SBIBNK"},
        ]
        response = requests.post(
            f"{BASE_URL}/api/sms/parse",
            json=sms_data,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["parsed_count"] >= 2, f"Expected at least 2 parsed, got {data['parsed_count']}"
        print(f"✓ Batch SMS parsing: {data['parsed_count']}/{len(sms_data)} messages parsed")

    def test_sms_parse_creates_transactions(self, auth_token):
        """Test that parsed SMS creates transactions in database."""
        # First parse a unique SMS
        unique_amount = 12345.67
        sms_data = [{
            "body": f"Rs.{unique_amount} debited from a/c XX1234 at TestStore HDFC Bank",
            "sender": "HDFCBK"
        }]
        parse_response = requests.post(
            f"{BASE_URL}/api/sms/parse",
            json=sms_data,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            }
        )
        assert parse_response.status_code == 200
        
        # Then verify the transaction exists
        txn_response = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert txn_response.status_code == 200
        transactions = txn_response.json()
        
        # Find the transaction we just created
        matching = [t for t in transactions if abs(t["amount"] - unique_amount) < 0.01]
        assert len(matching) >= 1, f"Transaction with amount {unique_amount} not found in database"
        print(f"✓ SMS-parsed transaction persisted in database")

    def test_sms_parse_unauthorized(self):
        """Test SMS parsing without auth returns 401."""
        response = requests.post(
            f"{BASE_URL}/api/sms/parse",
            json=[{"body": "test", "sender": "test"}],
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401
        print("✓ SMS parse correctly requires authentication")


class TestEncryption:
    """Test encryption module functionality."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt then decrypt returns original value."""
        from encryption import generate_user_dek, encrypt_field, decrypt_field
        
        original = "ABCDE1234F"  # PAN format
        dek = generate_user_dek()
        
        encrypted = encrypt_field(original, dek)
        assert encrypted.startswith("ENC:"), "Encrypted value should start with ENC:"
        assert encrypted != original, "Encrypted value should differ from original"
        
        decrypted = decrypt_field(encrypted, dek)
        assert decrypted == original, f"Decrypted value '{decrypted}' != original '{original}'"
        print(f"✓ Encryption roundtrip: '{original}' → encrypted → '{decrypted}'")

    def test_encrypt_different_keys_different_output(self):
        """Test that different DEKs produce different ciphertext."""
        from encryption import generate_user_dek, encrypt_field
        
        original = "sensitive_data"
        dek1 = generate_user_dek()
        dek2 = generate_user_dek()
        
        enc1 = encrypt_field(original, dek1)
        enc2 = encrypt_field(original, dek2)
        
        assert enc1 != enc2, "Different DEKs should produce different ciphertext"
        print("✓ Different user DEKs produce different ciphertext")

    def test_decrypt_empty_returns_original(self):
        """Test that decrypting non-encrypted value returns it unchanged."""
        from encryption import decrypt_field, generate_user_dek
        
        plain = "not_encrypted"
        dek = generate_user_dek()
        result = decrypt_field(plain, dek)
        assert result == plain, "Non-encrypted value should return unchanged"
        print("✓ Non-encrypted values pass through unchanged")

    def test_encrypt_sensitive_fields_batch(self):
        """Test batch encryption of multiple sensitive fields."""
        from encryption import generate_user_dek, encrypt_sensitive_fields, decrypt_sensitive_fields
        
        dek = generate_user_dek()
        doc = {
            "id": "test-123",
            "name": "Test User",
            "pan": "ABCDE1234F",
            "aadhaar": "123456789012",
        }
        
        # Encrypt sensitive fields
        encrypted_doc = encrypt_sensitive_fields(doc.copy(), dek, ["pan", "aadhaar"])
        assert encrypted_doc["pan"].startswith("ENC:")
        assert encrypted_doc["aadhaar"].startswith("ENC:")
        assert encrypted_doc["name"] == "Test User"  # Non-sensitive unchanged
        
        # Decrypt back
        decrypted_doc = decrypt_sensitive_fields(encrypted_doc, dek, ["pan", "aadhaar"])
        assert decrypted_doc["pan"] == "ABCDE1234F"
        assert decrypted_doc["aadhaar"] == "123456789012"
        print("✓ Batch encrypt/decrypt of sensitive fields works correctly")


class TestUserProfileEncryption:
    """Test that user profile returns properly decrypted data."""

    @pytest.fixture
    def auth_token(self):
        """Get authentication token for tests."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]

    def test_login_returns_decrypted_pan(self, auth_token):
        """Test that login endpoint returns decrypted PAN."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        data = response.json()
        pan = data["user"]["pan"]
        
        # PAN should be decrypted (10 chars, alphanumeric)
        assert not pan.startswith("ENC:"), "PAN should be decrypted in response"
        assert len(pan) == 10 or pan == "", f"PAN should be 10 chars, got {len(pan)}"
        print(f"✓ Login returns decrypted PAN: {pan}")

    def test_profile_returns_encryption_status(self, auth_token):
        """Test that profile endpoint returns encryption status."""
        response = requests.get(
            f"{BASE_URL}/api/auth/profile",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "is_encrypted" in data, "Profile should include is_encrypted field"
        print(f"✓ Profile encryption status: {data.get('is_encrypted')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
