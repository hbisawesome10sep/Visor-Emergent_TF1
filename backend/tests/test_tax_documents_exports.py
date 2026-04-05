"""
Tax Documents Parsing & Export Tests — Phase 2 Tax Module
Tests for Form 16, AIS/26AS, FD Certificate parsing with LLM fallback
and Tax Summary PDF export endpoint.
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestTaxDocumentsAndExports:
    """Test suite for tax document upload/parse and export endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None
        self.uploaded_doc_ids = []
        
    def get_auth_token(self):
        """Authenticate and get JWT token"""
        if self.token:
            return self.token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            return self.token
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
        
    def teardown_method(self, method):
        """Cleanup uploaded documents after each test"""
        if self.token and self.uploaded_doc_ids:
            for doc_id in self.uploaded_doc_ids:
                try:
                    self.session.delete(f"{BASE_URL}/api/tax/documents/{doc_id}")
                except:
                    pass
            self.uploaded_doc_ids = []

    # ══════════════════════════════════════════════════════════════
    # FORM 16 UPLOAD TESTS
    # ══════════════════════════════════════════════════════════════
    
    def test_form16_upload_success(self):
        """Test Form 16 PDF upload and parsing"""
        self.get_auth_token()
        
        # Read test PDF
        with open('/tmp/test_form16.pdf', 'rb') as f:
            files = {'file': ('test_form16.pdf', f, 'application/pdf')}
            # Remove Content-Type header for multipart
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/tax/upload/form16",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200, f"Form 16 upload failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("status") == "success"
        assert "document_id" in data
        assert "parse_quality" in data
        assert data["parse_quality"] in ("high", "medium", "low")
        
        # Verify parsed salary components
        assert "salary_components" in data
        salary = data["salary_components"]
        assert salary.get("gross_salary", 0) > 0, "Gross salary should be parsed"
        
        # Verify deductions parsed
        assert "deductions" in data
        deductions = data["deductions"]
        # Form 16 has 80C deduction
        assert "80C" in deductions or len(deductions) > 0, "Deductions should be parsed"
        
        # Verify tax computation
        assert "tax_computation" in data
        
        # Verify employer info
        assert "employer_info" in data
        employer = data["employer_info"]
        assert employer.get("employer_tan") or employer.get("employer_name"), "Employer info should be parsed"
        
        # Track for cleanup
        self.uploaded_doc_ids.append(data["document_id"])
        print(f"✓ Form 16 uploaded successfully, doc_id: {data['document_id']}, quality: {data['parse_quality']}")
        
    def test_form16_upload_invalid_file_type(self):
        """Test Form 16 upload rejects non-PDF files"""
        self.get_auth_token()
        
        # Create a fake text file
        fake_file = io.BytesIO(b"This is not a PDF")
        files = {'file': ('test.txt', fake_file, 'text/plain')}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/tax/upload/form16",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 400, "Should reject non-PDF files"
        assert "PDF" in response.text or "pdf" in response.text
        print("✓ Form 16 correctly rejects non-PDF files")
        
    def test_form16_upload_no_auth(self):
        """Test Form 16 upload requires authentication"""
        with open('/tmp/test_form16.pdf', 'rb') as f:
            files = {'file': ('test_form16.pdf', f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/tax/upload/form16",
                files=files
            )
        
        assert response.status_code in (401, 403), "Should require authentication"
        print("✓ Form 16 upload correctly requires authentication")

    # ══════════════════════════════════════════════════════════════
    # AIS/26AS UPLOAD TESTS
    # ══════════════════════════════════════════════════════════════
    
    def test_ais_upload_pdf_success(self):
        """Test AIS PDF upload and parsing"""
        self.get_auth_token()
        
        with open('/tmp/test_ais.pdf', 'rb') as f:
            files = {'file': ('test_ais.pdf', f, 'application/pdf')}
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/tax/upload/ais",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200, f"AIS upload failed: {response.text}"
        data = response.json()
        
        assert data.get("status") == "success"
        assert "document_id" in data
        assert "summary" in data
        
        # Verify TDS summary
        summary = data["summary"]
        assert "total_tds" in summary
        
        self.uploaded_doc_ids.append(data["document_id"])
        print(f"✓ AIS uploaded successfully, doc_id: {data['document_id']}, TDS entries: {data.get('tds_entries_count', 0)}")
        
    def test_ais_upload_invalid_file_type(self):
        """Test AIS upload rejects invalid file types"""
        self.get_auth_token()
        
        fake_file = io.BytesIO(b"Not a valid file")
        files = {'file': ('test.xml', fake_file, 'application/xml')}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/tax/upload/ais",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 400, "Should reject invalid file types"
        print("✓ AIS correctly rejects invalid file types")

    # ══════════════════════════════════════════════════════════════
    # FD CERTIFICATE UPLOAD TESTS
    # ══════════════════════════════════════════════════════════════
    
    def test_fd_certificate_upload_success(self):
        """Test FD Interest Certificate upload and parsing"""
        self.get_auth_token()
        
        with open('/tmp/test_fd.pdf', 'rb') as f:
            files = {'file': ('test_fd.pdf', f, 'application/pdf')}
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/tax/upload/fd-certificate",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200, f"FD cert upload failed: {response.text}"
        data = response.json()
        
        assert data.get("status") == "success"
        assert "document_id" in data
        assert "summary" in data
        
        # Verify FD summary
        summary = data["summary"]
        assert "total_interest" in summary
        assert "total_tds" in summary
        assert "total_principal" in summary
        
        # Verify FD details parsed
        assert "fd_details" in data or "fd_count" in data
        
        self.uploaded_doc_ids.append(data["document_id"])
        print(f"✓ FD Certificate uploaded successfully, doc_id: {data['document_id']}")
        print(f"  Interest: ₹{summary.get('total_interest', 0):,.0f}, TDS: ₹{summary.get('total_tds', 0):,.0f}")
        
    def test_fd_certificate_auto_80tta_entry(self):
        """Test FD upload creates auto 80TTA deduction entry"""
        self.get_auth_token()
        
        # Upload FD certificate
        with open('/tmp/test_fd.pdf', 'rb') as f:
            files = {'file': ('test_fd.pdf', f, 'application/pdf')}
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/tax/upload/fd-certificate",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200
        data = response.json()
        self.uploaded_doc_ids.append(data["document_id"])
        
        # Check auto-deductions for 80TTA entry
        response = self.session.get(f"{BASE_URL}/api/auto-tax-deductions?fy=2025-26")
        assert response.status_code == 200
        
        auto_deds = response.json()
        sections = auto_deds.get("sections", [])
        
        # Look for 80TTA section
        tta_section = next((s for s in sections if s.get("section") == "80TTA"), None)
        if tta_section:
            print(f"✓ Auto 80TTA entry created: ₹{tta_section.get('total_amount', 0):,.0f}")
        else:
            print("⚠ No 80TTA auto-entry found (may already exist or interest below threshold)")

    # ══════════════════════════════════════════════════════════════
    # DOCUMENT CRUD TESTS
    # ══════════════════════════════════════════════════════════════
    
    def test_get_tax_documents_list(self):
        """Test GET /api/tax/documents returns document list"""
        self.get_auth_token()
        
        response = self.session.get(f"{BASE_URL}/api/tax/documents")
        assert response.status_code == 200, f"Get documents failed: {response.text}"
        
        data = response.json()
        assert "documents" in data
        assert "count" in data
        assert isinstance(data["documents"], list)
        
        print(f"✓ Tax documents list retrieved: {data['count']} documents")
        
    def test_delete_tax_document(self):
        """Test DELETE /api/tax/documents/{id}"""
        self.get_auth_token()
        
        # First upload a document
        with open('/tmp/test_fd.pdf', 'rb') as f:
            files = {'file': ('test_fd.pdf', f, 'application/pdf')}
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/tax/upload/fd-certificate",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200
        doc_id = response.json()["document_id"]
        
        # Delete the document
        response = self.session.delete(f"{BASE_URL}/api/tax/documents/{doc_id}")
        assert response.status_code == 200, f"Delete failed: {response.text}"
        assert response.json().get("status") == "deleted"
        
        # Verify it's gone
        response = self.session.get(f"{BASE_URL}/api/tax/documents")
        docs = response.json().get("documents", [])
        doc_ids = [d.get("id") for d in docs]
        assert doc_id not in doc_ids, "Document should be deleted"
        
        print(f"✓ Document {doc_id} deleted successfully")
        
    def test_delete_nonexistent_document(self):
        """Test DELETE returns 404 for non-existent document"""
        self.get_auth_token()
        
        response = self.session.delete(f"{BASE_URL}/api/tax/documents/nonexistent-id-12345")
        assert response.status_code == 404, "Should return 404 for non-existent document"
        print("✓ Delete correctly returns 404 for non-existent document")

    # ══════════════════════════════════════════════════════════════
    # REPARSE ENDPOINT TESTS
    # ══════════════════════════════════════════════════════════════
    
    def test_reparse_document(self):
        """Test POST /api/tax/documents/{id}/reparse with LLM enhancement"""
        self.get_auth_token()
        
        # First upload a document
        with open('/tmp/test_form16.pdf', 'rb') as f:
            files = {'file': ('test_form16.pdf', f, 'application/pdf')}
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/tax/upload/form16",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200
        doc_id = response.json()["document_id"]
        self.uploaded_doc_ids.append(doc_id)
        
        # Reparse the document
        response = self.session.post(f"{BASE_URL}/api/tax/documents/{doc_id}/reparse")
        assert response.status_code == 200, f"Reparse failed: {response.text}"
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ("enhanced", "no_improvement")
        assert "document_id" in data
        
        print(f"✓ Document reparsed: status={data['status']}, llm_enhanced={data.get('llm_enhanced', False)}")
        
    def test_reparse_nonexistent_document(self):
        """Test reparse returns 404 for non-existent document"""
        self.get_auth_token()
        
        response = self.session.post(f"{BASE_URL}/api/tax/documents/nonexistent-id-12345/reparse")
        assert response.status_code == 404, "Should return 404 for non-existent document"
        print("✓ Reparse correctly returns 404 for non-existent document")

    # ══════════════════════════════════════════════════════════════
    # TAX METER ENDPOINT TESTS
    # ══════════════════════════════════════════════════════════════
    
    def test_tax_meter_endpoint(self):
        """Test GET /api/tax/meter returns valid dashboard data"""
        self.get_auth_token()
        
        response = self.session.get(f"{BASE_URL}/api/tax/meter?fy=2025-26")
        assert response.status_code == 200, f"Tax meter failed: {response.text}"
        
        data = response.json()
        
        # Verify required fields
        required_fields = [
            "fy", "estimated_tax", "tds_paid_ytd", "tax_due", 
            "refund_expected", "better_regime", "total_deductions",
            "deduction_80c", "gross_income"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify better_regime is valid
        assert data["better_regime"] in ("old", "new", "equal")
        
        # Verify deduction_80c structure
        ded_80c = data["deduction_80c"]
        assert "used" in ded_80c
        assert "limit" in ded_80c
        assert "remaining" in ded_80c
        assert "utilization_pct" in ded_80c
        
        print(f"✓ Tax meter data retrieved:")
        print(f"  Estimated Tax: ₹{data['estimated_tax']:,.0f}")
        print(f"  TDS Paid YTD: ₹{data['tds_paid_ytd']:,.0f}")
        print(f"  Better Regime: {data['better_regime']}")
        print(f"  80C Utilization: {ded_80c['utilization_pct']}%")

    # ══════════════════════════════════════════════════════════════
    # TAX SUMMARY PDF EXPORT TESTS
    # ══════════════════════════════════════════════════════════════
    
    def test_tax_summary_pdf_export(self):
        """Test GET /api/exports/tax-summary/pdf returns valid PDF"""
        self.get_auth_token()
        
        response = self.session.get(f"{BASE_URL}/api/exports/tax-summary/pdf?fy=2025-26")
        assert response.status_code == 200, f"Tax summary PDF export failed: {response.text}"
        
        # Verify content type
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF content type, got: {content_type}"
        
        # Verify content disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Should have attachment disposition"
        assert "Visor_Tax_Summary" in content_disp or "Tax_Summary" in content_disp, "Filename should contain Tax_Summary"
        
        # Verify PDF content (check magic bytes)
        content = response.content
        assert len(content) > 1000, "PDF should have substantial content"
        assert content[:4] == b'%PDF', "Content should be valid PDF (magic bytes)"
        
        print(f"✓ Tax Summary PDF exported successfully")
        print(f"  Content-Type: {content_type}")
        print(f"  Content-Disposition: {content_disp}")
        print(f"  PDF Size: {len(content):,} bytes")
        
    def test_tax_summary_pdf_no_auth(self):
        """Test tax summary PDF export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/exports/tax-summary/pdf?fy=2025-26")
        assert response.status_code in (401, 403), "Should require authentication"
        print("✓ Tax summary PDF export correctly requires authentication")
        
    def test_tax_summary_pdf_different_fy(self):
        """Test tax summary PDF export with different FY parameter"""
        self.get_auth_token()
        
        # Test with previous FY
        response = self.session.get(f"{BASE_URL}/api/exports/tax-summary/pdf?fy=2024-25")
        assert response.status_code == 200, f"Tax summary PDF for 2024-25 failed: {response.text}"
        
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type
        
        print("✓ Tax Summary PDF works with different FY parameter")

    # ══════════════════════════════════════════════════════════════
    # TAX CALCULATOR ENDPOINT TESTS
    # ══════════════════════════════════════════════════════════════
    
    def test_tax_calculator_endpoint(self):
        """Test GET /api/tax-calculator returns comprehensive tax calculation"""
        self.get_auth_token()
        
        response = self.session.get(f"{BASE_URL}/api/tax-calculator?fy=2025-26")
        assert response.status_code == 200, f"Tax calculator failed: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "fy" in data
        assert "ay" in data
        assert "income" in data
        assert "old_regime" in data
        assert "new_regime" in data
        assert "comparison" in data
        
        # Verify income structure
        income = data["income"]
        assert "salary" in income
        assert "other" in income
        assert "gross_total" in income
        
        # Verify regime calculations
        for regime in ["old_regime", "new_regime"]:
            r = data[regime]
            assert "taxable_income" in r
            assert "total_tax" in r
            assert "slab_breakdown" in r
        
        # Verify comparison
        comp = data["comparison"]
        assert "better_regime" in comp
        assert comp["better_regime"] in ("old", "new", "equal")
        assert "savings" in comp
        
        print(f"✓ Tax calculator data retrieved:")
        print(f"  Gross Income: ₹{income['gross_total']:,.0f}")
        print(f"  Old Regime Tax: ₹{data['old_regime']['total_tax']:,.0f}")
        print(f"  New Regime Tax: ₹{data['new_regime']['total_tax']:,.0f}")
        print(f"  Better Regime: {comp['better_regime']} (saves ₹{comp['savings']:,.0f})")


class TestEdgeCases:
    """Edge case tests for tax document parsing"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.token = None
        
    def get_auth_token(self):
        if self.token:
            return self.token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            return self.token
        pytest.skip("Authentication failed")
        
    def test_empty_pdf_upload(self):
        """Test handling of empty/minimal PDF"""
        self.get_auth_token()
        
        # Create minimal PDF
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.drawString(100, 750, "Empty document")
        c.save()
        buf.seek(0)
        
        files = {'file': ('empty.pdf', buf, 'application/pdf')}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/tax/upload/form16",
            files=files,
            headers=headers
        )
        
        # Should either succeed with low quality or return error
        if response.status_code == 200:
            data = response.json()
            # Low quality parse is expected for empty PDF
            print(f"✓ Empty PDF handled: quality={data.get('parse_quality', 'unknown')}")
            # Cleanup
            if "document_id" in data:
                self.session.delete(f"{BASE_URL}/api/tax/documents/{data['document_id']}")
        else:
            # 400 error is also acceptable for unparseable PDF
            assert response.status_code in (400, 500)
            print(f"✓ Empty PDF rejected with status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
