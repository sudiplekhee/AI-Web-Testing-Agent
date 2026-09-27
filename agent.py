from browser_tester import BrowserTester


def main():

    print()
    print("Starting AI Website Testing Agent...")
    print()

    tester = BrowserTester()

    results = tester.test_website()

    print()
    print("=" * 45)
    print("             TEST RESULT")
    print("=" * 45)
    print()

    print(
        f"Website: {results['website']}"
    )

    print(
        f"Status: {results['status']}"
    )

    print(
        f"HTTP Status: "
        f"{results['http_status']}"
    )

    print(
        f"Page Title: "
        f"{results['title']}"
    )

    print(
        f"Content Found: "
        f"{results['content_found']}"
    )

    if results["screenshot"]:

        print(
            f"Screenshot: "
            f"{results['screenshot']}"
        )

    if results["error"]:

        print()
        print("Error:")
        print(results["error"])

    print()
    print("=" * 45)

    if results["status"] == "PASSED":

        print(
            "       ✓ WEBSITE TEST PASSED"
        )

    else:

        print(
            "       ✗ WEBSITE TEST FAILED"
        )

    print("=" * 45)
    print()


if __name__ == "__main__":
    main()