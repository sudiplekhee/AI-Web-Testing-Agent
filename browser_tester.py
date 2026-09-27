import json
import os

from playwright.sync_api import sync_playwright


class BrowserTester:

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):

        with open(
            self.config_file,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    def test_website(self):

        website_url = self.config["website_url"]

        browser_name = self.config.get(
            "browser",
            "chromium"
        )

        headless = self.config.get(
            "headless",
            False
        )

        timeout = self.config.get(
            "timeout",
            30000
        )

        take_screenshot = self.config.get(
            "screenshot",
            True
        )

        os.makedirs(
            "reports",
            exist_ok=True
        )

        results = {
            "website": website_url,
            "status": "FAILED",
            "http_status": None,
            "title": None,
            "content_found": False,
            "screenshot": None,
            "error": None
        }

        print()
        print("=" * 45)
        print("       AI WEBSITE TESTING AGENT")
        print("=" * 45)
        print()

        print(f"Website: {website_url}")
        print("Starting browser...")
        print()

        with sync_playwright() as playwright:

            if browser_name == "chromium":

                browser = playwright.chromium.launch(
                    headless=headless
                )

            elif browser_name == "firefox":

                browser = playwright.firefox.launch(
                    headless=headless
                )

            elif browser_name == "webkit":

                browser = playwright.webkit.launch(
                    headless=headless
                )

            else:

                raise ValueError(
                    f"Unsupported browser: {browser_name}"
                )

            page = browser.new_page()

            page.set_default_timeout(timeout)

            try:

                # --------------------------------
                # TEST 1: OPEN WEBSITE
                # --------------------------------

                print("[1/4] Opening website...")

                response = page.goto(
                    website_url,
                    wait_until="domcontentloaded"
                )

                if response:

                    results["http_status"] = response.status

                    print(
                        f"      HTTP Status: "
                        f"{response.status}"
                    )

                # --------------------------------
                # TEST 2: PAGE TITLE
                # --------------------------------

                print("[2/4] Checking page title...")

                title = page.title()

                results["title"] = title

                print(
                    f"      Title: {title}"
                )

                # --------------------------------
                # TEST 3: PAGE CONTENT
                # --------------------------------

                print(
                    "[3/4] Checking page content..."
                )

                body_text = page.locator(
                    "body"
                ).inner_text()

                if body_text.strip():

                    results["content_found"] = True

                    print(
                        "      Page content found."
                    )

                else:

                    print(
                        "      WARNING: "
                        "Page appears empty."
                    )

                # --------------------------------
                # TEST 4: SCREENSHOT
                # --------------------------------

                print(
                    "[4/4] Taking screenshot..."
                )

                if take_screenshot:

                    screenshot_path = (
                        "reports/"
                        "website_screenshot.png"
                    )

                    page.screenshot(
                        path=screenshot_path,
                        full_page=True
                    )

                    results["screenshot"] = (
                        screenshot_path
                    )

                    print(
                        "      Screenshot saved: "
                        f"{screenshot_path}"
                    )

                # --------------------------------
                # DETERMINE RESULT
                # --------------------------------

                if (
                    response
                    and 200 <= response.status < 400
                    and results["content_found"]
                ):

                    results["status"] = "PASSED"

                else:

                    results["status"] = "FAILED"

            except Exception as error:

                results["status"] = "FAILED"

                results["error"] = str(error)

                print()
                print("ERROR:")
                print(error)

            finally:

                browser.close()

        return results