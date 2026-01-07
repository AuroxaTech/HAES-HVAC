#!/usr/bin/env python3
"""
HAES HVAC - HTTP Endpoint Verification Script

Verifies that core HTTP endpoints are responding correctly.

Usage:
    uv run python scripts/verify_http.py --base-url http://localhost:8000
"""

import argparse
import sys

import httpx


def main() -> int:
    """Run HTTP endpoint verification checks."""
    parser = argparse.ArgumentParser(description="Verify HAES HVAC HTTP endpoints")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the HAES HVAC API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Request timeout in seconds (default: 10.0)",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    timeout = args.timeout

    print("=" * 60)
    print("HAES HVAC - HTTP Endpoint Verification")
    print("=" * 60)
    print(f"\nBase URL: {base_url}")
    print(f"Timeout: {timeout}s")

    all_passed = True

    # Test 1: Root endpoint
    print("\n[1/3] Testing GET / (root)...")
    try:
        response = httpx.get(f"{base_url}/", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if "service" in data and "version" in data:
                print(f"  ✓ Status: {response.status_code}")
                print(f"  ✓ Service: {data.get('service')}")
                print(f"  ✓ Version: {data.get('version')}")
            else:
                print(f"  ✗ Missing expected fields in response: {data}")
                all_passed = False
        else:
            print(f"  ✗ Unexpected status code: {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Request failed: {e}")
        all_passed = False

    # Test 2: Health endpoint
    print("\n[2/3] Testing GET /health...")
    try:
        response = httpx.get(f"{base_url}/health", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            if status in ("ok", "degraded"):
                print(f"  ✓ Status: {response.status_code}")
                print(f"  ✓ Health status: {status}")
                components = data.get("components", {})
                db_status = components.get("database", {}).get("status")
                print(f"  ✓ Database status: {db_status}")
            else:
                print(f"  ✗ Unexpected health status: {status}")
                all_passed = False
        else:
            print(f"  ✗ Unexpected status code: {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Request failed: {e}")
        all_passed = False

    # Test 3: Metrics endpoint
    print("\n[3/3] Testing GET /monitoring/metrics...")
    try:
        response = httpx.get(f"{base_url}/monitoring/metrics", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if "uptime_seconds" in data and "requests_total" in data:
                print(f"  ✓ Status: {response.status_code}")
                print(f"  ✓ Uptime: {data.get('uptime_seconds')}s")
                print(f"  ✓ Requests total: {data.get('requests_total')}")
            else:
                print(f"  ✗ Missing expected fields in response: {data}")
                all_passed = False
        else:
            print(f"  ✗ Unexpected status code: {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Request failed: {e}")
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("PASS - All HTTP endpoint checks completed successfully")
    else:
        print("FAIL - Some HTTP endpoint checks failed")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

