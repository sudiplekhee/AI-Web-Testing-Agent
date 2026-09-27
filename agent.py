import json
import os
from datetime import datetime

from browser_tester import BrowserTester


REPORT_FOLDER = "reports"
REPORT_FILE = os.path.join(REPORT_FOLDER, "test_report.json")


def save_report(report):
    os.makedirs(REPORT_FOLDER, exist_ok=True)

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)


def print_summary(report):
    print("\n")
    print("=" * 60)
    print("             AI WEBSITE TEST REPORT")
    print("=" * 60)

    print(f"Website:        {report['website']}")
    print(f"Test time:      {report['test_time']}")
    print("-" * 60)

    print(f"Pages tested:   {report['summary']['pages_tested']}")
    print(f"Pages passed:   {report['summary']['pages_passed']}")
    print(f"Pages failed:   {report['summary']['pages_failed']}")
    print(f"Links tested:   {report['summary']['links_tested']}")
    print(f"Buttons tested: {report['summary']['buttons_tested']}")
    print(f"Forms tested:   {report['summary']['forms_tested']}")
    print(f"Errors found:   {report['summary']['errors_found']}")

    print("-" * 60)

    if report["errors"]:
        print("FAILURES")
        print()

        for error in report["errors"]:
            print(f"✗ {error['url']}")
            print(f"  Type: {error['type']}")
            print(f"  Details: {error['details']}")
            print()

    else:
        print("✓ No major errors found.")

    print("=" * 60)
    print(f"Report saved to: {REPORT_FILE}")
    print("=" * 60)


def main():
    print("\nStarting AI Website Testing Agent...")
    print("Please wait while the website is being tested.\n")

    tester = BrowserTester()

    results = tester.crawl_website()

    pages_tested = len(results)
    pages_passed = 0
    pages_failed = 0

    links_tested = 0
    buttons_tested = 0
    forms_tested = 0

    errors = []

    for result in results:

        if result.get("status") == "PASSED":
            pages_passed += 1
        else:
            pages_failed += 1

        links_tested += result.get("links_tested", 0)
        buttons_tested += result.get("buttons_tested", 0)
        forms_tested += result.get("forms_tested", 0)

        # Page-level error
        if result.get("error"):
            errors.append({
                "url": result.get("url"),
                "type": "Page Error",
                "details": result.get("error")
            })

        # Interaction errors
        for interaction_error in result.get("interaction_errors", []):
            errors.append({
                "url": result.get("url"),
                "type": "Interaction Error",
                "details": interaction_error
            })

    report = {
        "agent": "AI Website Testing Agent",
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        "website": tester.config.get(
            "website_url",
            "Unknown"
        ),

        "summary": {
            "pages_tested": pages_tested,
            "pages_passed": pages_passed,
            "pages_failed": pages_failed,
            "links_tested": links_tested,
            "buttons_tested": buttons_tested,
            "forms_tested": forms_tested,
            "errors_found": len(errors)
        },

        "errors": errors,

        "pages": results
    }

    save_report(report)

    print_summary(report)


if __name__ == "__main__":
    main()