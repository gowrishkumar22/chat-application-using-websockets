#!/usr/bin/env python3
"""
Simple test script to verify all routes are working correctly.
Run this script to test the ChatFlow application endpoints.
"""

import requests
import sys

def test_route(url, expected_status=200, description=""):
    """Test a single route and return the result."""
    try:
        response = requests.get(url, timeout=5)
        status = "✅ PASS" if response.status_code == expected_status else "❌ FAIL"
        print(f"{status} - {description}")
        print(f"    URL: {url}")
        print(f"    Status: {response.status_code} (expected: {expected_status})")
        if response.status_code != expected_status:
            print(f"    Error: Unexpected status code")
        print()
        return response.status_code == expected_status
    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL - {description}")
        print(f"    URL: {url}")
        print(f"    Error: {e}")
        print()
        return False

def main():
    """Run all route tests."""
    base_url = "http://localhost:5000"
    
    print("🚀 Testing ChatFlow Application Routes")
    print("=" * 50)
    print()
    
    tests = [
        (f"{base_url}/", 200, "Landing Page (/)"),
        (f"{base_url}/login", 200, "Login Page (/login)"),
        (f"{base_url}/register", 200, "Register Page (/register)"),
        (f"{base_url}/home", 302, "Home Page (/home) - Should redirect to login"),
        (f"{base_url}/chat", 302, "Chat Page (/chat) - Should redirect to login"),
        (f"{base_url}/nonexistent", 404, "404 Error Page (nonexistent route)"),
    ]
    
    passed = 0
    total = len(tests)
    
    for url, expected_status, description in tests:
        if test_route(url, expected_status, description):
            passed += 1
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your ChatFlow application is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the application.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)
