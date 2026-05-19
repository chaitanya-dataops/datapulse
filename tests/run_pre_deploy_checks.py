"""
DataPulse Pre-Deployment Check Script
Run this before deploying to verify all tabs and components work correctly

Usage:
    python tests/run_pre_deploy_checks.py

Exit codes:
    0 - All tests passed, safe to deploy
    1 - Tests failed, do not deploy
"""

import subprocess
import sys
import os
from datetime import datetime

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header():
    print(f"""
{BLUE}╔══════════════════════════════════════════════════════════════╗
║           DataPulse Pre-Deployment Test Suite                ║
║                     22 Tabs Coverage                         ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")


def run_import_checks():
    """Quick check that all modules can be imported"""
    print(f"{YELLOW}[1/4] Running import checks...{RESET}")
    
    modules = [
        ("data.mock_data", "Mock Data"),
        ("utils.anomaly_detector", "Anomaly Detector"),
        ("utils.column_profiler", "Column Profiler"),
        ("utils.history_store", "History Store"),
        ("utils.notifications", "Notifications"),
        ("utils.pii_detector", "PII Detector"),
        ("utils.data_lineage", "Data Lineage"),
        ("utils.sql_rules", "SQL Rules"),
        ("utils.drift_detector", "Drift Detector"),
        ("utils.root_cause", "Root Cause"),
        ("utils.data_contracts", "Data Contracts"),
        ("utils.incident_manager", "Incident Manager"),
        ("utils.relationship_quality", "Relationship Quality"),
        ("utils.sla_manager", "SLA Manager"),
        ("utils.predictive_monitor", "Predictive Monitor"),
        ("utils.ml_feature_monitor", "ML Feature Monitor"),
        ("utils.conformance_validator", "Conformance Validator"),
    ]
    
    failed = []
    for module, name in modules:
        try:
            __import__(module)
            print(f"  {GREEN}✓{RESET} {name}")
        except Exception as e:
            print(f"  {RED}✗{RESET} {name}: {str(e)[:50]}")
            failed.append((name, str(e)))
    
    return len(failed) == 0, failed


def run_pytest():
    """Run full pytest suite"""
    print(f"\n{YELLOW}[2/4] Running pytest suite...{RESET}")
    
    test_file = os.path.join(os.path.dirname(__file__), "test_all_tabs.py")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )
    
    # Count passed/failed from output
    lines = result.stdout.split("\n")
    for line in lines:
        if "passed" in line or "failed" in line or "error" in line:
            print(f"  {line}")
    
    return result.returncode == 0, result.stdout, result.stderr


def run_app_syntax_check():
    """Check app.py for syntax errors"""
    print(f"\n{YELLOW}[3/4] Checking app.py syntax...{RESET}")
    
    app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
    
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", app_path],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"  {GREEN}✓{RESET} app.py syntax OK")
        return True
    else:
        print(f"  {RED}✗{RESET} app.py has syntax errors:")
        print(result.stderr)
        return False


def run_streamlit_check():
    """Verify streamlit can import the app"""
    print(f"\n{YELLOW}[4/4] Verifying Streamlit compatibility...{RESET}")
    
    check_code = """
import sys
sys.path.insert(0, '.')
try:
    import app
    print("OK")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", check_code],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )
    
    if "OK" in result.stdout:
        print(f"  {GREEN}✓{RESET} Streamlit app imports successfully")
        return True
    else:
        print(f"  {RED}✗{RESET} Streamlit app import failed:")
        print(result.stdout)
        print(result.stderr)
        return False


def generate_report(results):
    """Generate test report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
{'='*60}
DataPulse Pre-Deployment Test Report
Generated: {timestamp}
{'='*60}

SUMMARY:
--------
Import Checks: {'PASS' if results['imports'] else 'FAIL'}
Pytest Suite:  {'PASS' if results['pytest'] else 'FAIL'}
Syntax Check:  {'PASS' if results['syntax'] else 'FAIL'}
Streamlit:     {'PASS' if results['streamlit'] else 'FAIL'}

OVERALL: {'PASS - Safe to deploy' if all(results.values()) else 'FAIL - Do not deploy'}
{'='*60}
"""
    return report


def main():
    print_header()
    
    # Change to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    sys.path.insert(0, project_root)
    
    results = {}
    
    # Run checks
    imports_ok, import_failures = run_import_checks()
    results['imports'] = imports_ok
    
    pytest_ok, stdout, stderr = run_pytest()
    results['pytest'] = pytest_ok
    
    syntax_ok = run_app_syntax_check()
    results['syntax'] = syntax_ok
    
    streamlit_ok = run_streamlit_check()
    results['streamlit'] = streamlit_ok
    
    # Generate report
    report = generate_report(results)
    print(report)
    
    # Save report
    report_path = os.path.join(project_root, "tests", "pre_deploy_report.txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Report saved to: {report_path}")
    
    # Exit with appropriate code
    if all(results.values()):
        print(f"\n{GREEN}{BOLD}✓ All checks passed! Safe to deploy.{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}✗ Some checks failed. Do not deploy.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
