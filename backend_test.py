#!/usr/bin/env python3
"""
Backend API Tests for Visor Finance App
Testing dashboard stats endpoint with date range filtering and health score
Specific focus on health_score behavior across different date ranges
"""
import requests
import json
from datetime import datetime

# Configuration
BACKEND_URL = "https://invest-modular.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
LOGIN_EMAIL = "rajesh@visor.demo"
LOGIN_PASSWORD = "Demo@123"

class BackendTester:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def validate_health_score(self, health_score):
        """Validate health_score structure and values"""
        try:
            # Check overall score exists and is valid
            overall = health_score.get("overall")
            if overall is None:
                self.log("❌ health_score.overall is missing", "ERROR")
                return False
            
            if not isinstance(overall, (int, float)) or overall < 0 or overall > 100:
                self.log(f"❌ health_score.overall must be 0-100, got: {overall}", "ERROR")
                return False
            
            # Check grade exists
            grade = health_score.get("grade")
            if not grade:
                self.log("❌ health_score.grade is missing", "ERROR")
                return False
            
            valid_grades = ["Excellent", "Good", "Fair", "Needs Work", "Critical"]
            if grade not in valid_grades:
                self.log(f"❌ health_score.grade invalid, got: {grade}", "ERROR")
                return False
            
            # Check breakdown exists and has required fields
            breakdown = health_score.get("breakdown", {})
            required_breakdown_fields = ["savings", "investments", "spending", "goals"]
            for field in required_breakdown_fields:
                value = breakdown.get(field)
                if value is None:
                    self.log(f"❌ health_score.breakdown.{field} is missing", "ERROR")
                    return False
                if not isinstance(value, (int, float)) or value < 0 or value > 100:
                    self.log(f"❌ health_score.breakdown.{field} must be 0-100, got: {value}", "ERROR")
                    return False
            
            self.log("✅ Health score structure and values are valid")
            self.log(f"   - Overall: {overall} ({grade})")
            self.log(f"   - Breakdown: Savings={breakdown['savings']}, Investments={breakdown['investments']}, Spending={breakdown['spending']}, Goals={breakdown['goals']}")
            return True
            
        except Exception as e:
            self.log(f"❌ Health score validation failed: {str(e)}", "ERROR")
            return False
        
    def login(self):
        """Test login endpoint and get JWT token"""
        self.log("Testing login endpoint...")
        
        login_data = {
            "email": LOGIN_EMAIL,
            "password": LOGIN_PASSWORD
        }
        
        try:
            response = self.session.post(
                f"{API_BASE}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            self.log(f"Login response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                if self.token:
                    self.log("✅ Login successful - JWT token received")
                    self.log(f"User: {data.get('user', {}).get('email', 'N/A')}")
                    return True
                else:
                    self.log("❌ Login response missing token", "ERROR")
                    return False
            else:
                self.log(f"❌ Login failed: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Login request failed: {str(e)}", "ERROR")
            return False
    
    def test_dashboard_stats_no_dates(self):
        """Test dashboard stats without date parameters - includes health_score validation"""
        self.log("Testing dashboard stats without date parameters...")
        
        if not self.token:
            self.log("❌ No token available", "ERROR")
            return False, None
            
        try:
            response = self.session.get(
                f"{API_BASE}/dashboard/stats",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            self.log(f"Dashboard stats (no dates) response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields including health_score
                required_fields = [
                    "total_income", "total_expenses", "total_investments", 
                    "net_balance", "user_created_at", "date_range", "health_score"
                ]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log(f"❌ Missing required fields: {missing_fields}", "ERROR")
                    return False, None
                
                # Check that date_range is null when no dates provided
                if data["date_range"] is not None:
                    self.log(f"❌ Expected date_range to be null, got: {data['date_range']}", "ERROR")
                    return False, None
                    
                # Check user_created_at exists and is not empty
                if not data.get("user_created_at"):
                    self.log("❌ user_created_at field is empty", "ERROR")
                    return False, None
                
                # CRITICAL: Validate health_score structure and values
                health_score = data.get("health_score", {})
                if not self.validate_health_score(health_score):
                    return False, None
                
                self.log("✅ Dashboard stats (no dates) - All required fields present")
                self.log(f"   - Total Income: ₹{data['total_income']}")
                self.log(f"   - Total Expenses: ₹{data['total_expenses']}")
                self.log(f"   - Net Balance: ₹{data['net_balance']}")
                self.log(f"   - User Created At: {data['user_created_at']}")
                self.log(f"   - Date Range: {data['date_range']}")
                self.log(f"   - Transaction Count: {data.get('transaction_count', 0)}")
                self.log(f"   - Health Score Overall: {health_score.get('overall', 'N/A')} ({health_score.get('grade', 'N/A')})")
                
                return True, health_score
            else:
                self.log(f"❌ Dashboard stats failed: {response.text}", "ERROR")
                return False, None
                
        except Exception as e:
            self.log(f"❌ Dashboard stats request failed: {str(e)}", "ERROR")
            return False, None
    
    def test_dashboard_stats_with_date_range(self, start_date, end_date, test_name, expected_health_score=None):
        """Test dashboard stats with date range filtering - validates health_score consistency"""
        self.log(f"Testing dashboard stats with date range: {start_date} to {end_date}")
        
        if not self.token:
            self.log("❌ No token available", "ERROR")
            return False, None
            
        try:
            params = {
                "start_date": start_date,
                "end_date": end_date
            }
            
            response = self.session.get(
                f"{API_BASE}/dashboard/stats",
                headers={"Authorization": f"Bearer {self.token}"},
                params=params
            )
            
            self.log(f"Dashboard stats ({test_name}) response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields including health_score
                required_fields = [
                    "total_income", "total_expenses", "total_investments", 
                    "net_balance", "user_created_at", "date_range", "health_score"
                ]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log(f"❌ Missing required fields: {missing_fields}", "ERROR")
                    return False, None
                
                # Check that date_range object contains the provided dates
                date_range = data.get("date_range")
                if not date_range:
                    self.log("❌ Expected date_range object, got None", "ERROR")
                    return False, None
                    
                if date_range.get("start") != start_date:
                    self.log(f"❌ Expected start date {start_date}, got {date_range.get('start')}", "ERROR")
                    return False, None
                    
                if date_range.get("end") != end_date:
                    self.log(f"❌ Expected end date {end_date}, got {date_range.get('end')}", "ERROR")
                    return False, None
                
                # Check user_created_at exists
                if not data.get("user_created_at"):
                    self.log("❌ user_created_at field is empty", "ERROR")
                    return False, None
                
                # CRITICAL: Validate health_score structure and values
                health_score = data.get("health_score", {})
                if not self.validate_health_score(health_score):
                    return False, None
                
                # CRITICAL: If we have expected health_score from baseline test, compare it
                if expected_health_score:
                    expected_overall = expected_health_score.get("overall")
                    actual_overall = health_score.get("overall")
                    
                    if expected_overall != actual_overall:
                        self.log(f"❌ CRITICAL: Health score should be identical across date ranges!", "ERROR")
                        self.log(f"   Expected: {expected_overall}, Got: {actual_overall}", "ERROR")
                        return False, None
                    else:
                        self.log(f"✅ CRITICAL VERIFICATION PASSED: Health score consistent across date ranges ({actual_overall})")
                
                self.log(f"✅ Dashboard stats ({test_name}) - All validation passed")
                self.log(f"   - Total Income: ₹{data['total_income']}")
                self.log(f"   - Total Expenses: ₹{data['total_expenses']}")
                self.log(f"   - Net Balance: ₹{data['net_balance']}")
                self.log(f"   - User Created At: {data['user_created_at']}")
                self.log(f"   - Date Range: {data['date_range']}")
                self.log(f"   - Transaction Count: {data.get('transaction_count', 0)}")
                self.log(f"   - Health Score Overall: {health_score.get('overall', 'N/A')} ({health_score.get('grade', 'N/A')})")
                
                return True, health_score
            else:
                self.log(f"❌ Dashboard stats failed: {response.text}", "ERROR")
                return False, None
                
        except Exception as e:
            self.log(f"❌ Dashboard stats request failed: {str(e)}", "ERROR")
            return False, None

    def run_all_tests(self):
        """Run comprehensive health_score tests with date range filtering as per review request"""
        self.log("=" * 80)
        self.log("STARTING VISOR FINANCE HEALTH SCORE COMPREHENSIVE TESTING")
        self.log("Focus: Health score consistency across different date ranges")
        self.log("=" * 80)
        
        results = {
            "login": False,
            "stats_no_dates": False,
            "stats_february_2026": False,
            "stats_q1_2026": False,
            "stats_yearly_2026": False
        }
        
        # Test 1: Login with specific credentials
        self.log(f"Using credentials: {LOGIN_EMAIL} / {LOGIN_PASSWORD}")
        results["login"] = self.login()
        if not results["login"]:
            self.log("❌ Login failed - skipping other tests", "ERROR")
            return results
        
        # Test 2: Dashboard stats WITHOUT date params - Establish baseline health_score
        self.log("\n" + "="*60)
        self.log("TEST 2: Baseline - Dashboard stats WITHOUT date parameters")
        self.log("="*60)
        success, baseline_health_score = self.test_dashboard_stats_no_dates()
        results["stats_no_dates"] = success
        
        if not baseline_health_score:
            self.log("❌ Failed to get baseline health_score - skipping consistency tests", "ERROR")
            return results
        
        # Test 3: February 2026 monthly filter - Health score should be SAME as baseline
        self.log("\n" + "="*60)
        self.log("TEST 3: February 2026 filter - Health score should be SAME as baseline")
        self.log("="*60)
        success, feb_health_score = self.test_dashboard_stats_with_date_range(
            "2026-02-01", "2026-02-28", "February 2026 monthly", baseline_health_score
        )
        results["stats_february_2026"] = success
        
        # Test 4: Q1 2026 filter - Should have more transactions than February alone
        self.log("\n" + "="*60)
        self.log("TEST 4: Q1 2026 filter - Should have higher totals than February alone")
        self.log("="*60)
        success, q1_health_score = self.test_dashboard_stats_with_date_range(
            "2026-01-01", "2026-02-28", "Q1 2026", baseline_health_score
        )
        results["stats_q1_2026"] = success
        
        # Test 5: Yearly 2026 filter - Should return ALL transactions for the year
        self.log("\n" + "="*60)
        self.log("TEST 5: Yearly 2026 filter - Should return ALL transactions")
        self.log("="*60)
        success, yearly_health_score = self.test_dashboard_stats_with_date_range(
            "2026-01-01", "2026-12-31", "Yearly 2026", baseline_health_score
        )
        results["stats_yearly_2026"] = success
        
        # Summary
        self.log("\n" + "="*80)
        self.log("HEALTH SCORE COMPREHENSIVE TEST RESULTS SUMMARY")
        self.log("="*80)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.upper().replace('_', ' ')}: {status}")
        
        # Critical verification summary
        if baseline_health_score:
            self.log("\n" + "-"*60)
            self.log("CRITICAL VERIFICATION SUMMARY:")
            self.log(f"Baseline Health Score: {baseline_health_score.get('overall', 'N/A')} ({baseline_health_score.get('grade', 'N/A')})")
            self.log("✅ Health score should be IDENTICAL across all date ranges")
            self.log("✅ Transaction totals should DIFFER between monthly vs quarterly vs yearly")
            self.log("-"*60)
        
        self.log(f"OVERALL: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL HEALTH SCORE TESTS PASSED! Dashboard endpoint working correctly.")
            self.log("✅ Critical verification: Health score consistent across date ranges")
            self.log("✅ Date filtering: Transaction totals varying correctly by period")
        else:
            self.log("⚠️  Some tests failed. Please check the logs above for details.")
            
        return results

def main():
    """Main test execution"""
    tester = BackendTester()
    results = tester.run_all_tests()
    
    # Exit with error code if any test failed
    if not all(results.values()):
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    main()