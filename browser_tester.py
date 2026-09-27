import json
import os
from urllib.parse import urlparse, urljoin

from playwright.sync_api import sync_playwright


class BrowserTester:

    def __init__(self):

        self.config = self.load_config()

        self.base_url = self.config["website_url"].rstrip("/")

        self.browser_name = self.config.get(
            "browser",
            "chromium"
        )

        self.timeout = self.config.get(
            "timeout",
            30000
        )

        self.max_pages = self.config.get(
            "max_pages",
            10
        )

        self.screenshot_enabled = self.config.get(
            "screenshot",
            True
        )

        self.test_links_enabled = self.config.get(
            "test_links",
            True
        )

        self.test_buttons_enabled = self.config.get(
            "test_buttons",
            True
        )

        self.test_forms_enabled = self.config.get(
            "test_forms",
            True
        )

    # ==================================================
    # CONFIG
    # ==================================================

    def load_config(self):

        with open(
            "config.json",
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    # ==================================================
    # URL HELPERS
    # ==================================================

    def get_domain(self, url):

        return urlparse(url).netloc

    def is_internal_link(self, url):

        try:

            return (
                self.get_domain(url)
                == self.get_domain(
                    self.base_url
                )
            )

        except Exception:

            return False

    def clean_url(self, url):

        parsed = urlparse(url)

        return parsed._replace(
            fragment=""
        ).geturl()

    # ==================================================
    # FIND LINKS
    # ==================================================

    def find_links(self, page):

        links = page.locator("a")

        found_links = []

        for i in range(
            links.count()
        ):

            try:

                href = links.nth(i).get_attribute(
                    "href"
                )

                if not href:
                    continue

                if href.startswith(
                    (
                        "#",
                        "mailto:",
                        "tel:",
                        "javascript:"
                    )
                ):
                    continue

                full_url = urljoin(
                    page.url,
                    href
                )

                full_url = self.clean_url(
                    full_url
                )

                if self.is_internal_link(
                    full_url
                ):

                    if full_url not in found_links:

                        found_links.append(
                            full_url
                        )

            except Exception:

                continue

        return found_links

    # ==================================================
    # LINK TESTING
    # ==================================================

    def test_links(
        self,
        page,
        links
    ):

        tested = 0

        errors = []

        for url in links:

            try:

                response = page.request.get(
                    url,
                    timeout=self.timeout
                )

                tested += 1

                if response.status >= 400:

                    errors.append(
                        {
                            "type": "Broken Link",
                            "url": url,
                            "details": (
                                f"HTTP status "
                                f"{response.status}"
                            )
                        }
                    )

            except Exception as error:

                tested += 1

                errors.append(
                    {
                        "type": "Link Request Error",
                        "url": url,
                        "details": str(error)
                    }
                )

        return tested, errors

    # ==================================================
    # BUTTON TESTING
    # ==================================================

    def test_buttons(
        self,
        page
    ):

        buttons = page.locator(
            "button"
        )

        found = buttons.count()

        tested = 0

        errors = []

        dangerous_words = [
            "delete",
            "remove",
            "logout",
            "log out",
            "sign out",
            "cancel",
            "cancel booking",
            "purchase",
            "pay",
            "checkout"
        ]

        for i in range(found):

            try:

                button = buttons.nth(i)

                if not button.is_visible():
                    continue

                if not button.is_enabled():
                    continue

                text = (
                    button.inner_text()
                    .strip()
                    .lower()
                )

                if any(
                    word in text
                    for word in dangerous_words
                ):
                    continue

                tested += 1

                before_url = page.url

                try:

                    button.click(
                        timeout=self.timeout
                    )

                    page.wait_for_timeout(
                        500
                    )

                except Exception as error:

                    errors.append(
                        {
                            "type": "Button Error",
                            "url": before_url,
                            "details": (
                                f"Button '{text}': "
                                f"{str(error)}"
                            )
                        }
                    )

                try:

                    if page.url != before_url:

                        page.goto(
                            before_url,
                            wait_until="domcontentloaded",
                            timeout=self.timeout
                        )

                except Exception:

                    pass

            except Exception as error:

                errors.append(
                    {
                        "type": "Button Detection Error",
                        "url": page.url,
                        "details": str(error)
                    }
                )

        return found, tested, errors

    # ==================================================
    # FORM ANALYSIS
    # ==================================================

    def analyze_form(
        self,
        form
    ):

        action = form.get_attribute(
            "action"
        )

        method = form.get_attribute(
            "method"
        )

        if not method:

            method = "GET"

        fields = form.locator(
            "input, textarea, select"
        )

        field_details = []

        required_fields = []

        for i in range(
            fields.count()
        ):

            field = fields.nth(i)

            try:

                field_type = (
                    field.get_attribute(
                        "type"
                    )
                    or "text"
                )

                name = (
                    field.get_attribute(
                        "name"
                    )
                    or ""
                )

                field_id = (
                    field.get_attribute(
                        "id"
                    )
                    or ""
                )

                placeholder = (
                    field.get_attribute(
                        "placeholder"
                    )
                    or ""
                )

                required = (
                    field.get_attribute(
                        "required"
                    )
                    is not None
                )

                details = {
                    "type": field_type,
                    "name": name,
                    "id": field_id,
                    "placeholder": placeholder,
                    "required": required
                }

                field_details.append(
                    details
                )

                if required:

                    required_fields.append(
                        details
                    )

            except Exception:

                continue

        submit_buttons = form.locator(
            "button[type='submit'], "
            "input[type='submit'], "
            "button:not([type])"
        )

        return {
            "action": action or "",
            "method": method.upper(),
            "fields": field_details,
            "required_fields": required_fields,
            "submit_buttons": submit_buttons.count()
        }

    # ==================================================
    # FORM TESTING
    # ==================================================

    def test_forms(
        self,
        page
    ):

        forms = page.locator(
            "form"
        )

        found = forms.count()

        tested = 0

        details = []

        errors = []

        for i in range(found):

            try:

                form = forms.nth(i)

                info = self.analyze_form(
                    form
                )

                info["form_number"] = i + 1

                details.append(
                    info
                )

                tested += 1

                required_fields = form.locator(
                    "input:required, "
                    "textarea:required, "
                    "select:required"
                )

                submit_buttons = form.locator(
                    "button[type='submit'], "
                    "input[type='submit'], "
                    "button:not([type])"
                )

                if (
                    required_fields.count()
                    > 0
                    and submit_buttons.count()
                    > 0
                ):

                    try:

                        submit_button = (
                            submit_buttons.nth(0)
                        )

                        if (
                            submit_button.is_visible()
                            and submit_button.is_enabled()
                        ):

                            submit_button.click(
                                timeout=3000
                            )

                            page.wait_for_timeout(
                                500
                            )

                            invalid_fields = page.locator(
                                ":invalid"
                            )

                            if (
                                invalid_fields.count()
                                == 0
                            ):

                                errors.append(
                                    {
                                        "type": "Form Validation",
                                        "url": page.url,
                                        "details": (
                                            "Required fields "
                                            "exist, but browser "
                                            "validation did not "
                                            "detect an invalid "
                                            "empty submission."
                                        )
                                    }
                                )

                    except Exception as error:

                        errors.append(
                            {
                                "type": "Form Test Error",
                                "url": page.url,
                                "details": str(error)
                            }
                        )

            except Exception as error:

                errors.append(
                    {
                        "type": "Form Detection Error",
                        "url": page.url,
                        "details": str(error)
                    }
                )

        return (
            found,
            tested,
            details,
            errors
        )

    # ==================================================
    # RESOURCE ERROR
    # ==================================================

    def classify_resource(
        self,
        resource_type
    ):

        resource_map = {

            "stylesheet": "CSS",

            "script": "JavaScript",

            "image": "Image",

            "font": "Font",

            "media": "Media",

            "xhr": "API/XHR",

            "fetch": "API/Fetch",

            "document": "HTML",

            "manifest": "Manifest",

            "texttrack": "Text Track"

        }

        return resource_map.get(
            resource_type,
            resource_type
        )

    # ==================================================
    # PAGE TESTING
    # ==================================================

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

            "console_errors": [],

            "network_errors": [],

            "interaction_errors": [],

            "screenshot": None,

            "error": None
        }

        console_errors = []

        network_errors = []

        # ------------------------------------------------
        # Console
        # ------------------------------------------------

        def handle_console(message):

            try:

                if message.type == "error":

                    console_errors.append(
                        message.text
                    )

            except Exception:

                pass

        # ------------------------------------------------
        # Network responses
        # ------------------------------------------------

        def handle_response(response):

            try:

                if response.status >= 400:

                    request = response.request

                    resource_type = (
                        request.resource_type
                    )

                    network_error = {

                        "type": "HTTP Resource Error",

                        "url": response.url,

                        "status": response.status,

                        "resource_type": resource_type,

                        "resource_category": (
                            self.classify_resource(
                                resource_type
                            )
                        ),

                        "source_page": page.url

                    }

                    network_errors.append(
                        network_error
                    )

            except Exception:

                pass

        # ------------------------------------------------
        # Failed network requests
        # ------------------------------------------------

        def handle_request_failed(
            request
        ):

            try:

                network_errors.append(
                    {

                        "type": "Network Request Failed",

                        "url": request.url,

                        "status": None,

                        "resource_type": (
                            request.resource_type
                        ),

                        "resource_category": (
                            self.classify_resource(
                                request.resource_type
                            )
                        ),

                        "source_page": page.url,

                        "failure": (
                            request.failure
                        )

                    }
                )

            except Exception:

                pass

        page.on(
            "console",
            handle_console
        )

        page.on(
            "response",
            handle_response
        )

        page.on(
            "requestfailed",
            handle_request_failed
        )

        try:

            # ------------------------------------------------
            # Navigate
            # ------------------------------------------------

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.timeout
            )

            if response:

                result["http_status"] = (
                    response.status
                )

                if response.status >= 400:

                    result["error"] = (
                        f"Page returned HTTP "
                        f"{response.status}"
                    )

            # ------------------------------------------------
            # Title
            # ------------------------------------------------

            try:

                result["title"] = page.title()

            except Exception:

                pass

            # ------------------------------------------------
            # Body
            # ------------------------------------------------

            try:

                body_text = page.locator(
                    "body"
                ).inner_text()

                result["content_found"] = (
                    len(
                        body_text.strip()
                    ) > 0
                )

            except Exception:

                pass

            # ------------------------------------------------
            # Screenshot
            # ------------------------------------------------

            if self.screenshot_enabled:

                os.makedirs(
                    "reports",
                    exist_ok=True
                )

                screenshot_path = (
                    f"reports/page_"
                    f"{screenshot_number}.png"
                )

                try:

                    page.screenshot(
                        path=screenshot_path,
                        full_page=True
                    )

                    result["screenshot"] = (
                        screenshot_path
                    )

                except Exception as error:

                    result[
                        "interaction_errors"
                    ].append(
                        {
                            "type": "Screenshot Error",
                            "url": url,
                            "details": str(error)
                        }
                    )

            # ------------------------------------------------
            # Links
            # ------------------------------------------------

            links = self.find_links(
                page
            )

            result["links_found"] = len(
                links
            )

            if self.test_links_enabled:

                (
                    links_tested,
                    link_errors
                ) = self.test_links(
                    page,
                    links
                )

                result[
                    "links_tested"
                ] = links_tested

                result[
                    "interaction_errors"
                ].extend(
                    link_errors
                )

            # ------------------------------------------------
            # Buttons
            # ------------------------------------------------

            if self.test_buttons_enabled:

                (
                    buttons_found,
                    buttons_tested,
                    button_errors
                ) = self.test_buttons(
                    page
                )

                result[
                    "buttons_found"
                ] = buttons_found

                result[
                    "buttons_tested"
                ] = buttons_tested

                result[
                    "interaction_errors"
                ].extend(
                    button_errors
                )

            # ------------------------------------------------
            # Forms
            # ------------------------------------------------

            if self.test_forms_enabled:

                (
                    forms_found,
                    forms_tested,
                    form_details,
                    form_errors
                ) = self.test_forms(
                    page
                )

                result[
                    "forms_found"
                ] = forms_found

                result[
                    "forms_tested"
                ] = forms_tested

                result[
                    "form_details"
                ] = form_details

                result[
                    "interaction_errors"
                ].extend(
                    form_errors
                )

            # ------------------------------------------------
            # Console errors
            # ------------------------------------------------

            result[
                "console_errors"
            ] = list(
                dict.fromkeys(
                    console_errors
                )
            )

            # ------------------------------------------------
            # Network errors
            # ------------------------------------------------

            unique_network_errors = []

            seen_network_errors = set()

            for error in network_errors:

                key = (
                    error.get(
                        "url"
                    ),
                    error.get(
                        "status"
                    ),
                    error.get(
                        "resource_type"
                    )
                )

                if key in seen_network_errors:

                    continue

                seen_network_errors.add(
                    key
                )

                unique_network_errors.append(
                    error
                )

            result[
                "network_errors"
            ] = unique_network_errors

            # ------------------------------------------------
            # Add console errors
            # ------------------------------------------------

            for console_error in (
                result["console_errors"]
            ):

                result[
                    "interaction_errors"
                ].append(
                    {
                        "type":
                            "JavaScript Console Error",

                        "url":
                            url,

                        "details":
                            console_error
                    }
                )

            # ------------------------------------------------
            # Add network errors
            # ------------------------------------------------

            for network_error in (
                result["network_errors"]
            ):

                result[
                    "interaction_errors"
                ].append(
                    {
                        "type":
                            "HTTP Resource Error",

                        "url":
                            network_error["url"],

                        "details":
                            (
                                f"HTTP "
                                f"{network_error['status']} "
                                f""
                                f"{network_error['resource_category']} "
                                f"resource"
                            ),

                        "status":
                            network_error["status"],

                        "resource_type":
                            network_error[
                                "resource_type"
                            ],

                        "source_page":
                            network_error[
                                "source_page"
                            ]
                    }
                )

            # ------------------------------------------------
            # Determine final status
            # ------------------------------------------------

            if (
                result["http_status"]
                is not None
                and result["http_status"] >= 400
            ):

                result["status"] = "FAILED"

            elif (
                result["interaction_errors"]
            ):

                result["status"] = "FAILED"

            else:

                result["status"] = "PASSED"

        except Exception as error:

            result["status"] = "FAILED"

            result["error"] = str(
                error
            )

            result[
                "interaction_errors"
            ].append(
                {
                    "type":
                        "Page Error",

                    "url":
                        url,

                    "details":
                        str(error)
                }
            )

        return result

    # ==================================================
    # CRAWLER
    # ==================================================

    def crawl_website(self):

        visited = set()

        pages_to_visit = [
            self.base_url
        ]

        results = []

        with sync_playwright() as playwright:

            if (
                self.browser_name
                == "firefox"
            ):

                browser = (
                    playwright.firefox.launch(
                        headless=self.config.get(
                            "headless",
                            False
                        )
                    )
                )

            elif (
                self.browser_name
                == "webkit"
            ):

                browser = (
                    playwright.webkit.launch(
                        headless=self.config.get(
                            "headless",
                            False
                        )
                    )
                )

            else:

                browser = (
                    playwright.chromium.launch(
                        headless=self.config.get(
                            "headless",
                            False
                        )
                    )
                )

            page = browser.new_page()

            screenshot_number = 1

            while (
                pages_to_visit
                and len(visited)
                < self.max_pages
            ):

                url = pages_to_visit.pop(
                    0
                )

                url = self.clean_url(
                    url
                )

                if url in visited:

                    continue

                if not self.is_internal_link(
                    url
                ):

                    continue

                visited.add(
                    url
                )

                print(
                    f"\nTesting page "
                    f"{len(visited)}: "
                    f"{url}"
                )

                result = self.test_page(
                    page,
                    url,
                    screenshot_number
                )

                results.append(
                    result
                )

                screenshot_number += 1

                try:

                    discovered_links = (
                        self.find_links(
                            page
                        )
                    )

                    for link in (
                        discovered_links
                    ):

                        if (
                            link not in visited
                            and link not in pages_to_visit
                        ):

                            pages_to_visit.append(
                                link
                            )

                except Exception:

                    pass

            browser.close()

        return results