from browser_tester import BrowserTester


def main():

    print()
    print("Starting AI Website Testing Agent...")
    print()

    tester = BrowserTester()

    results = tester.crawl_website()

    total_pages = len(results)

    passed_pages = sum(
        1
        for result in results
        if result["status"] == "PASSED"
    )

    failed_pages = sum(
        1
        for result in results
        if result["status"] == "FAILED"
    )

    total_links = sum(
        result["links_found"]
        for result in results
    )

    tested_links = sum(
        result["links_tested"]
        for result in results
    )

    total_buttons = sum(
        result["buttons_found"]
        for result in results
    )

    tested_buttons = sum(
        result["buttons_tested"]
        for result in results
    )

    print()
    print("=" * 60)
    print("                 FINAL REPORT")
    print("=" * 60)
    print()

    print(
        f"Pages tested:       {total_pages}"
    )

    print(
        f"Pages passed:       {passed_pages}"
    )

    print(
        f"Pages failed:       {failed_pages}"
    )

    print()

    print(
        f"Links discovered:   {total_links}"
    )

    print(
        f"Links tested:       {tested_links}"
    )

    print()

    print(
        f"Buttons discovered: {total_buttons}"
    )

    print(
        f"Buttons tested:     {tested_buttons}"
    )

    print()

    print("-" * 60)

    for number, result in enumerate(
        results,
        start=1
    ):

        if result["status"] == "PASSED":

            symbol = "✓"

        else:

            symbol = "✗"

        print(
            f"{symbol} {number}. "
            f"{result['url']}"
        )

        print(
            f"   HTTP: "
            f"{result['http_status']}"
        )

        print(
            f"   Title: "
            f"{result['title']}"
        )

        print(
            f"   Links: "
            f"{result['links_tested']}/"
            f"{result['links_found']}"
        )

        print(
            f"   Buttons: "
            f"{result['buttons_tested']}/"
            f"{result['buttons_found']}"
        )

        if result["interaction_errors"]:

            print(
                "   Problems:"
            )

            for error in result[
                "interaction_errors"
            ]:

                print(
                    f"     - {error}"
                )

        if result["error"]:

            print(
                f"   Error: "
                f"{result['error']}"
            )

        print()

    print("=" * 60)

    if failed_pages == 0:

        print(
            "✓ ALL TESTED PAGES PASSED"
        )

    else:

        print(
            f"✗ {failed_pages} "
            f"PAGE(S) FAILED"
        )

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()