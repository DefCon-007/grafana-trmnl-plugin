#!/usr/bin/env python3
"""
Simple test runner for the Grafana TRMNL plugin server.
"""

import os
import subprocess
import sys


def run_tests():
    """Run all tests with coverage reporting"""
    print("Running tests for Grafana TRMNL Plugin Server...")
    print("=" * 50)

    # Change to the server directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    try:
        # Run tests with coverage
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "test_main.py",
                "-v",
                "--cov=main",
                "--cov=html_utils",
                "--cov=grafana_utils",
                "--cov-report=term-missing",
            ],
            check=True,
        )

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print("❌ pytest not found. Please install with: pip install pytest pytest-cov")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
