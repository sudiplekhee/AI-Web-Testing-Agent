import json
import os
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright


class BrowserTester:

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_config()

    # ==========================================
    # CONFIGURATION
    # ==========================================

    def load_config(self):

        with open(
            self.config_file,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    # ==========================================
    # URL HELPERS
    # ==========================================

    def get_domain(self, url):

        parsed_url = urlparse(url)

        return parsed_url.netloc

    def is_internal_link(
        self,
        link,
        base_url
    ):

        link_domain = self.get_domain(link)
        base_domain = self.get_domain(base_url)

        return (
            link_domain == base_domain
            or link_domain == ""
        )

    def clean_url(self, url):

        parsed = urlparse(url)

        return parsed._replace(
            fragment=""
        ).geturl()

    # ==========================================
    # FIND LINKS
    # ==========================================

    def find_links(
        self,
        page,
        current_url
    ):

        links = page.locator("a")

        discovered_links = []

        for i in range(links.count()):

            try:

                href = links.nth(i).get_attribute(
                    "href"
                )

                if not href:
                    continue

                if href.startswith("#"):
                    continue

                if href.startswith(
                    (
                        "mailto:",
                        "tel:",
                        "javascript:"
                    )
                ):
                    continue

                full_url = urljoin(
                    current_url,
                    href
                )

                full_url = self.clean_url(
                    full_url
                )

                if self.is_internal_link(
                    full_url,
                    current_url
                ):

                    if (
                        full_url
                        not in discovered_links
                    ):

                        discovered_links.append(
                            full_url
                        )

            except Exception:

                continue

        return discovered_links

    # ==========================================
    # TEST PAGE
    # ==========================================

    def test_page(
        self,
        page,
        url,
        screenshot_number
    ):

        result = {
            "url": url,
            "status": "FAILED",
            "http_status": None,
            "title": None,
            "content_found": False,

            "links_found": 0,
            "links_tested": 0,

            "buttons_found": 0,
            "buttons_tested": 0,

            "forms_found": 0,
            "forms_tested": 0,

            "form_details": [],

            "interaction_errors": [],

            "screenshot": None,
            "error": None
        }

        try:

            print()
            print("=" * 60)
            print(f"Testing page: {url}")
            print("=" * 60)

            # ----------------------------------
            # OPEN PAGE
            # ----------------------------------

            response = page.goto(
                url,
                wait_until="domcontentloaded"
            )

            if response:

                result["http_status"] = response.status

                print(
                    f"HTTP Status: "
                    f"{response.status}"
                )

            # ----------------------------------
            # TITLE
            # ----------------------------------

            title = page.title()

            result["title"] = title

            print(
                f"Page Title: {title}"
            )

            # ----------------------------------
            # CONTENT
            # ----------------------------------

            body_text = page.locator(
                "body"
            ).inner_text()

            if body_text.strip():

                result["content_found"] = True

                print(
                    "Page Content: ✓ Found"
                )

            else:

                print(
                    "Page Content: ✗ Empty"
                )

            # ----------------------------------
            # LINKS
            # ----------------------------------

            links = page.locator("a")

            result["links_found"] = links.count()

            print(
                f"Links Found: "
                f"{result['links_found']}"
            )

            if self.config.get(
                "test_links",
                True
            ):

                self.test_links(
                    page,
                    url,
                    result
                )

            # ----------------------------------
            # BUTTONS
            # ----------------------------------

            buttons = page.locator(
                "button"
            )

            result["buttons_found"] = (
                buttons.count()
            )

            print(
                f"Buttons Found: "
                f"{result['buttons_found']}"
            )

            if self.config.get(
                "test_buttons",
                True
            ):

                self.test_buttons(
                    page,
                    result
                )

            # ----------------------------------
            # FORMS
            # ----------------------------------

            forms = page.locator("form")

            result["forms_found"] = (
                forms.count()
            )

            print(
                f"Forms Found: "
                f"{result['forms_found']}"
            )

            if self.config.get(
                "test_forms",
                True
            ):

                self.test_forms(
                    page,
                    result
                )

            # ----------------------------------
            # SCREENSHOT
            # ----------------------------------

            if self.config.get(
                "screenshot",
                True
            ):

                screenshot_path = (
                    "reports/"
                    f"page_{screenshot_number}.png"
                )

                page.screenshot(
                    path=screenshot_path,
                    full_page=True
                )

                result["screenshot"] = (
                    screenshot_path
                )

                print(
                    f"Screenshot: "
                    f"{screenshot_path}"
                )

            # ----------------------------------
            # FINAL RESULT
            # ----------------------------------

            if (
                response
                and 200 <= response.status < 400
                and result["content_found"]
                and not result["interaction_errors"]
            ):

                result["status"] = "PASSED"

                print(
                    "Page Result: ✓ PASSED"
                )

            else:

                result["status"] = "FAILED"

                print(
                    "Page Result: ✗ FAILED"
                )

        except Exception as error:

            result["status"] = "FAILED"

            result["error"] = str(error)

            print(
                "Page Result: ✗ FAILED"
            )

            print(
                f"Error: {error}"
            )

        return result

    # ==========================================
    # TEST LINKS
    # ==========================================

    def test_links(
        self,
        page,
        current_url,
        result
    ):

        print()
        print("Testing links...")

        links = page.locator("a")

        total_links = links.count()

        tested = 0

        for i in range(total_links):

            try:

                href = links.nth(i).get_attribute(
                    "href"
                )

                text = links.nth(i).inner_text()

                if not href:
                    continue

                if href.startswith("#"):
                    continue

                if href.startswith(
                    (
                        "mailto:",
                        "tel:",
                        "javascript:"
                    )
                ):
                    continue

                full_url = urljoin(
                    current_url,
                    href
                )

                full_url = self.clean_url(
                    full_url
                )

                if not self.is_internal_link(
                    full_url,
                    current_url
                ):
                    continue

                print(
                    f"  Link: "
                    f"{text.strip() or '[No text]'}"
                )

                try:

                    response = page.request.get(
                        full_url,
                        timeout=self.config.get(
                            "timeout",
                            30000
                        )
                    )

                    status = response.status

                    tested += 1

                    if 200 <= status < 400:

                        print(
                            f"    ✓ HTTP {status}"
                        )

                    else:

                        print(
                            f"    ✗ HTTP {status}"
                        )

                        result[
                            "interaction_errors"
                        ].append(
                            f"Broken link: "
                            f"{full_url} "
                            f"(HTTP {status})"
                        )

                except Exception as error:

                    print(
                        "    ✗ ERROR"
                    )

                    result[
                        "interaction_errors"
                    ].append(
                        f"Link error: "
                        f"{full_url} - "
                        f"{error}"
                    )

            except Exception:

                continue

        result["links_tested"] = tested

    # ==========================================
    # TEST BUTTONS
    # ==========================================

    def test_buttons(
        self,
        page,
        result
    ):

        print()
        print("Testing buttons...")

        buttons = page.locator(
            "button"
        )

        total_buttons = buttons.count()

        tested = 0

        dangerous_words = [
            "delete",
            "remove",
            "logout",
            "sign out",
            "cancel booking",
            "cancel",
            "purchase",
            "pay",
            "checkout"
        ]

        for i in range(total_buttons):

            try:

                button = buttons.nth(i)

                text = button.inner_text().strip()

                if not text:

                    text = "[Unnamed button]"

                print(
                    f"  Button: {text}"
                )

                lower_text = text.lower()

                if any(
                    word in lower_text
                    for word in dangerous_words
                ):

                    print(
                        "    SKIPPED "
                        "(potentially destructive)"
                    )

                    continue

                if not button.is_visible():

                    print(
                        "    SKIPPED "
                        "(not visible)"
                    )

                    continue

                if not button.is_enabled():

                    print(
                        "    SKIPPED "
                        "(disabled)"
                    )

                    continue

                try:

                    button.click(
                        timeout=self.config.get(
                            "timeout",
                            30000
                        )
                    )

                    tested += 1

                    print(
                        "    ✓ Clicked"
                    )

                    page.wait_for_timeout(
                        500
                    )

                except Exception as error:

                    print(
                        "    ✗ Failed"
                    )

                    result[
                        "interaction_errors"
                    ].append(
                        f"Button error: "
                        f"{text} - "
                        f"{error}"
                    )

            except Exception as error:

                result[
                    "interaction_errors"
                ].append(
                    f"Button inspection error: "
                    f"{error}"
                )

        result["buttons_tested"] = tested

    # ==========================================
    # ANALYZE FORM
    # ==========================================

    def analyze_form(
        self,
        form,
        form_number
    ):

        details = {
            "form_number": form_number,
            "action": None,
            "method": None,
            "inputs": [],
            "required_fields": [],
            "submit_buttons": []
        }

        # --------------------------------------
        # FORM ACTION
        # --------------------------------------

        details["action"] = (
            form.get_attribute("action")
            or ""
        )

        details["method"] = (
            form.get_attribute("method")
            or "GET"
        ).upper()

        # --------------------------------------
        # INPUTS
        # --------------------------------------

        inputs = form.locator(
            "input, textarea, select"
        )

        for i in range(inputs.count()):

            try:

                element = inputs.nth(i)

                tag_name = element.evaluate(
                    "(el) => el.tagName.toLowerCase()"
                )

                input_type = (
                    element.get_attribute("type")
                    or (
                        "textarea"
                        if tag_name == "textarea"
                        else (
                            "select"
                            if tag_name == "select"
                            else "text"
                        )
                    )
                )

                name = (
                    element.get_attribute("name")
                    or ""
                )

                element_id = (
                    element.get_attribute("id")
                    or ""
                )

                placeholder = (
                    element.get_attribute(
                        "placeholder"
                    )
                    or ""
                )

                required = element.is_required()

                field = {
                    "tag": tag_name,
                    "type": input_type,
                    "name": name,
                    "id": element_id,
                    "placeholder": placeholder,
                    "required": required
                }

                details["inputs"].append(
                    field
                )

                if required:

                    details[
                        "required_fields"
                    ].append(
                        name
                        or element_id
                        or placeholder
                        or input_type
                    )

            except Exception:

                continue

        # --------------------------------------
        # SUBMIT BUTTONS
        # --------------------------------------

        submit_buttons = form.locator(
            "button[type='submit'], "
            "input[type='submit']"
        )

        for i in range(
            submit_buttons.count()
        ):

            try:

                button = submit_buttons.nth(i)

                text = (
                    button.inner_text().strip()
                    if button.evaluate(
                        "(el) => el.tagName.toLowerCase() === 'button'"
                    )
                    else (
                        button.get_attribute(
                            "value"
                        )
                        or "Submit"
                    )
                )

                details[
                    "submit_buttons"
                ].append(text)

            except Exception:

                continue

        return details

    # ==========================================
    # TEST FORMS
    # ==========================================

    def test_forms(
        self,
        page,
        result
    ):

        print()
        print("Testing forms...")

        forms = page.locator("form")

        total_forms = forms.count()

        print(
            f"  Total forms: {total_forms}"
        )

        tested = 0

        for i in range(total_forms):

            form_number = i + 1

            try:

                form = forms.nth(i)

                print()
                print(
                    f"  Form {form_number}"
                )

                details = self.analyze_form(
                    form,
                    form_number
                )

                result[
                    "form_details"
                ].append(details)

                # --------------------------------
                # DISPLAY FORM INFORMATION
                # --------------------------------

                print(
                    f"    Method: "
                    f"{details['method']}"
                )

                print(
                    f"    Action: "
                    f"{details['action'] or '[current page]'}"
                )

                print(
                    f"    Fields: "
                    f"{len(details['inputs'])}"
                )

                print(
                    f"    Required fields: "
                    f"{len(details['required_fields'])}"
                )

                print(
                    f"    Submit buttons: "
                    f"{len(details['submit_buttons'])}"
                )

                # --------------------------------
                # CHECK REQUIRED FIELDS
                # --------------------------------

                required_fields = (
                    form.locator(
                        "input[required], "
                        "textarea[required], "
                        "select[required]"
                    )
                )

                if required_fields.count() > 0:

                    print(
                        "    Required fields: ✓ Detected"
                    )

                else:

                    print(
                        "    Required fields: "
                        "None detected"
                    )

                # --------------------------------
                # EMPTY FORM TEST
                # --------------------------------

                submit_button = form.locator(
                    "button[type='submit'], "
                    "input[type='submit']"
                ).first

                if submit_button.count() > 0:

                    if submit_button.is_visible():

                        print(
                            "    Empty submission test..."
                        )

                        try:

                            # We only test browser
                            # validation here.
                            #
                            # We do NOT force-submit
                            # a real form.

                            submit_button.click(
                                timeout=5000
                            )

                            page.wait_for_timeout(
                                500
                            )

                            invalid_count = (
                                form.locator(
                                    ":invalid"
                                ).count()
                            )

                            if (
                                required_fields.count()
                                > 0
                                and invalid_count > 0
                            ):

                                print(
                                    "    ✓ Browser "
                                    "validation detected"
                                )

                            elif (
                                required_fields.count()
                                == 0
                            ):

                                print(
                                    "    ✓ Form has "
                                    "no required fields"
                                )

                            else:

                                print(
                                    "    ⚠ No browser "
                                    "validation detected"
                                )

                        except Exception as error:

                            print(
                                "    ⚠ Could not "
                                "test empty submission"
                            )

                            print(
                                f"      {error}"
                            )

                tested += 1

            except Exception as error:

                print(
                    f"    ✗ Form error: "
                    f"{error}"
                )

                result[
                    "interaction_errors"
                ].append(
                    f"Form {form_number} "
                    f"error: {error}"
                )

        result["forms_tested"] = tested

    # ==========================================
    # CRAWL WEBSITE
    # ==========================================

    def crawl_website(self):

        website_url = self.config[
            "website_url"
        ]

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

        max_pages = self.config.get(
            "max_pages",
            10
        )

        os.makedirs(
            "reports",
            exist_ok=True
        )

        results = []

        pages_to_visit = [
            website_url
        ]

        visited_pages = set()

        print()
        print("=" * 60)
        print("        AI WEBSITE TESTING AGENT")
        print("=" * 60)
        print()

        print(
            f"Website: {website_url}"
        )

        print(
            f"Maximum pages: {max_pages}"
        )

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
                    f"Unsupported browser: "
                    f"{browser_name}"
                )

            page = browser.new_page()

            page.set_default_timeout(
                timeout
            )

            screenshot_number = 1

            while (
                pages_to_visit
                and len(visited_pages)
                < max_pages
            ):

                current_url = (
                    pages_to_visit.pop(0)
                )

                current_url = (
                    self.clean_url(
                        current_url
                    )
                )

                if current_url in visited_pages:

                    continue

                visited_pages.add(
                    current_url
                )

                result = self.test_page(
                    page,
                    current_url,
                    screenshot_number
                )

                results.append(
                    result
                )

                screenshot_number += 1

                # --------------------------------
                # DISCOVER MORE PAGES
                # --------------------------------

                if (
                    result["http_status"]
                    and 200
                    <= result["http_status"]
                    < 400
                ):

                    try:

                        new_links = (
                            self.find_links(
                                page,
                                current_url
                            )
                        )

                        for link in new_links:

                            if (
                                link
                                not in visited_pages
                                and link
                                not in pages_to_visit
                                and (
                                    len(visited_pages)
                                    + len(pages_to_visit)
                                    < max_pages
                                )
                            ):

                                pages_to_visit.append(
                                    link
                                )

                    except Exception:

                        pass

            browser.close()

        return results