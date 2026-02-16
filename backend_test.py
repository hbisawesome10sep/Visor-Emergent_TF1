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
BACKEND_URL = "https://bookkeeping-ui-fix.preview.emergentagent.com"
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
    
    def test_dashboard_stats_with_date_range(self, start_date, end_date, test_name):
        """Test dashboard stats with date range filtering"""
        self.log(f"Testing dashboard stats with date range: {start_date} to {end_date}")
        
        if not self.token:
            self.log("❌ No token available", "ERROR")
            return False
            
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
                
                # Check required fields
                required_fields = [
                    "total_income", "total_expenses", "total_investments", 
                    "net_balance", "user_created_at", "date_range"
                ]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log(f"❌ Missing required fields: {missing_fields}", "ERROR")
                    return False
                
                # Check that date_range object contains the provided dates
                date_range = data.get("date_range")
                if not date_range:
                    self.log("❌ Expected date_range object, got None", "ERROR")
                    return False
                    
                if date_range.get("start") != start_date:
                    self.log(f"❌ Expected start date {start_date}, got {date_range.get('start')}", "ERROR")
                    return False
                    
                if date_range.get("end") != end_date:
                    self.log(f"❌ Expected end date {end_date}, got {date_range.get('end')}", "ERROR")
                    return False
                
                # Check user_created_at exists
                if not data.get("user_created_at"):
                    self.log("❌ user_created_at field is empty", "ERROR")
                    return False
                
                self.log(f"✅ Dashboard stats ({test_name}) - All validation passed")
                self.log(f"   - Total Income: ₹{data['total_income']}")
                self.log(f"   - Total Expenses: ₹{data['total_expenses']}")
                self.log(f"   - Net Balance: ₹{data['net_balance']}")
                self.log(f"   - User Created At: {data['user_created_at']}")
                self.log(f"   - Date Range: {data['date_range']}")
                self.log(f"   - Transaction Count: {data.get('transaction_count', 0)}")
                
                return True
            else:
                self.log(f"❌ Dashboard stats failed: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Dashboard stats request failed: {str(e)}", "ERROR")
            return False

    def run_all_tests(self):
        """Run all backend tests for dashboard stats"""
        self.log("=" * 60)
        self.log("STARTING VISOR FINANCE BACKEND API TESTS")
        self.log("=" * 60)
        
        results = {
            "login": False,
            "stats_no_dates": False,
            "stats_current_year": False,
            "stats_old_dates": False
        }
        
        # Test 1: Login
        results["login"] = self.login()
        if not results["login"]:
            self.log("❌ Login failed - skipping other tests", "ERROR")
            return results
        
        # Test 2: Dashboard stats without dates
        results["stats_no_dates"] = self.test_dashboard_stats_no_dates()
        
        # Test 3: Dashboard stats with current year date range
        results["stats_current_year"] = self.test_dashboard_stats_with_date_range(
            "2025-01-01", "2025-12-31", "current year 2025"
        )
        
        # Test 4: Dashboard stats with old date range (should return mostly zeros)
        results["stats_old_dates"] = self.test_dashboard_stats_with_date_range(
            "2020-01-01", "2020-12-31", "old dates 2020"
        )
        
        # Summary
        self.log("=" * 60)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 60)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.upper()}: {status}")
        
        self.log("-" * 60)
        self.log(f"OVERALL: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL TESTS PASSED! Dashboard stats endpoint working correctly.")
        else:
            self.log("⚠️  Some tests failed. Please check the logs above.")
            
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