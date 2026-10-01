import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin

import requests


CONFIG_FILE = "config.json"
DETECTION_FILE = "reports/project_detection.json"
OUTPUT_FILE = "reports/api_test_report.json"


class APITester:

    def __init__(self):

        self.config = self.load_json(
            CONFIG_FILE
        )

        self.detection = self.load_json(
            DETECTION_FILE
        )

        self.website_url = self.config.get(
            "website_url",
            "http://127.0.0.1:5000"
        ).rstrip("/")

        self.project_directory = (
            self.detection.get(
                "project_directory",
                self.config.get(
                    "project_directory",
                    ""
                )
            )
        )

        self.framework = self.detection.get(
            "project_type",
            "Unknown"
        )

        self.routes = []

        self.results = []

    # =========================================================
    # JSON
    # =========================================================

    def load_json(self, filename):

        if not os.path.exists(filename):
            return {}

        try:

            with open(
                filename,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except Exception as e:

            print(
                f"Could not read {filename}: {e}"
            )

            return {}

    # =========================================================
    # SAVE REPORT
    # =========================================================

    def save_report(self):

        os.makedirs(
            "reports",
            exist_ok=True
        )

        report = {

            "agent":
                "AI Website Testing Agent",

            "component":
                "API Tester",

            "test_time":
                datetime.now().isoformat(),

            "website":
                self.website_url,

            "framework":
                self.framework,

            "routes_discovered":
                len(self.routes),

            "requests_tested":
                len(self.results),

            "successful_requests":
                sum(
                    1
                    for result in self.results
                    if result["status"]
                    == "PASS"
                ),

            "failed_requests":
                sum(
                    1
                    for result in self.results
                    if result["status"]
                    == "FAIL"
                ),

            "routes":
                self.routes,

            "results":
                self.results
        }

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

    # =========================================================
    # FIND PYTHON ROUTES
    # =========================================================

    def find_python_routes(self):

        if not self.project_directory:
            return

        for root, dirs, files in os.walk(
            self.project_directory
        ):

            dirs[:] = [
                directory
                for directory in dirs
                if directory not in {
                    ".git",
                    "venv",
                    ".venv",
                    "__pycache__",
                    "node_modules",
                    "dist",
                    "build"
                }
            ]

            for filename in files:

                if not filename.endswith(".py"):
                    continue

                path = os.path.join(
                    root,
                    filename
                )

                try:

                    with open(
                        path,
                        "r",
                        encoding="utf-8",
                        errors="ignore"
                    ) as file:

                        content = file.read()

                except Exception:

                    continue

                relative_path = os.path.relpath(
                    path,
                    self.project_directory
                )

                # -------------------------------------------------
                # Flask
                # -------------------------------------------------

                flask_matches = re.finditer(
                    r"@(?:\w+\.)?route\(\s*['\"]([^'\"]+)",
                    content
                )

                for match in flask_matches:

                    route = match.group(1)

                    self.add_route(
                        route,
                        "Flask",
                        relative_path
                    )

                # -------------------------------------------------
                # FastAPI
                # -------------------------------------------------

                fastapi_matches = re.finditer(
                    r"@\w+\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)",
                    content,
                    re.IGNORECASE
                )

                for match in fastapi_matches:

                    method = match.group(1).upper()
                    route = match.group(2)

                    self.add_route(
                        route,
                        f"FastAPI {method}",
                        relative_path
                    )

    # =========================================================
    # FIND NODE ROUTES
    # =========================================================

    def find_node_routes(self):

        if not self.project_directory:
            return

        for root, dirs, files in os.walk(
            self.project_directory
        ):

            dirs[:] = [
                directory
                for directory in dirs
                if directory not in {
                    ".git",
                    "node_modules",
                    "dist",
                    "build"
                }
            ]

            for filename in files:

                if not filename.endswith(
                    (".js", ".ts", ".jsx", ".tsx")
                ):
                    continue

                path = os.path.join(
                    root,
                    filename
                )

                try:

                    with open(
                        path,
                        "r",
                        encoding="utf-8",
                        errors="ignore"
                    ) as file:

                        content = file.read()

                except Exception:

                    continue

                relative_path = os.path.relpath(
                    path,
                    self.project_directory
                )

                # Express:

                matches = re.finditer(

                    r"(?:app|router)"
                    r"\."
                    r"(get|post|put|delete|patch)"
                    r"\(\s*['\"]([^'\"]+)",

                    content,

                    re.IGNORECASE
                )

                for match in matches:

                    method = match.group(1).upper()
                    route = match.group(2)

                    self.add_route(
                        route,
                        f"Express {method}",
                        relative_path
                    )

    # =========================================================
    # FIND DJANGO ROUTES
    # =========================================================

    def find_django_routes(self):

        if not self.project_directory:
            return

        for root, dirs, files in os.walk(
            self.project_directory
        ):

            dirs[:] = [
                directory
                for directory in dirs
                if directory not in {
                    ".git",
                    "venv",
                    ".venv",
                    "__pycache__"
                }
            ]

            for filename in files:

                if filename != "urls.py":
                    continue

                path = os.path.join(
                    root,
                    filename
                )

                try:

                    with open(
                        path,
                        "r",
                        encoding="utf-8",
                        errors="ignore"
                    ) as file:

                        content = file.read()

                except Exception:

                    continue

                relative_path = os.path.relpath(
                    path,
                    self.project_directory
                )

                matches = re.finditer(

                    r"(?:path|re_path)"
                    r"\(\s*['\"]([^'\"]*)",

                    content
                )

                for match in matches:

                    route = match.group(1)

                    if not route.startswith("/"):
                        route = "/" + route

                    self.add_route(
                        route,
                        "Django",
                        relative_path
                    )

    # =========================================================
    # ADD ROUTE
    # =========================================================

    def add_route(
        self,
        route,
        source_type,
        source_file
    ):

        if not route:
            route = "/"

        # Remove Flask dynamic syntax
        route = re.sub(
            r"<[^>]+>",
            "test",
            route
        )

        # Remove Express parameters
        route = re.sub(
            r":[A-Za-z_][A-Za-z0-9_]*",
            "test",
            route
        )

        if not route.startswith("/"):
            route = "/" + route

        item = {

            "route":
                route,

            "source_type":
                source_type,

            "source_file":
                source_file
        }

        if item not in self.routes:

            self.routes.append(item)

    # =========================================================
    # DISCOVER ROUTES
    # =========================================================

    def discover_routes(self):

        print()
        print(
            "Discovering API/application routes..."
        )

        if self.framework in {
            "Flask",
            "FastAPI",
            "Django"
        }:

            self.find_python_routes()

        if self.framework in {
            "Express",
            "React",
            "Next.js",
            "Vue",
            "Angular",
            "Svelte"
        }:

            self.find_node_routes()

        # Also inspect Node files even if framework
        # detection is uncertain.

        if not self.routes:

            self.find_python_routes()
            self.find_node_routes()
            self.find_django_routes()

        # -----------------------------------------------------
        # Add common API candidates
        # -----------------------------------------------------

        common_routes = [
            "/api",
            "/api/health",
            "/api/status",
            "/health",
            "/healthcheck"
        ]

        existing = {
            item["route"]
            for item in self.routes
        }

        for route in common_routes:

            if route not in existing:

                self.routes.append({

                    "route":
                        route,

                    "source_type":
                        "Common API candidate",

                    "source_file":
                        None
                })

        print(
            f"Routes discovered: {len(self.routes)}"
        )

    # =========================================================
    # TEST ROUTE
    # =========================================================

    def test_route(self, route_info):

        route = route_info["route"]

        url = urljoin(
            self.website_url + "/",
            route.lstrip("/")
        )

        print()
        print(
            f"Testing: {url}"
        )

        started = time.time()

        try:

            response = requests.get(
                url,
                timeout=10,
                allow_redirects=True
            )

            elapsed = round(
                time.time() - started,
                3
            )

            status_code = response.status_code

            content_type = response.headers.get(
                "content-type",
                ""
            )

            # -------------------------------------------------
            # Determine result
            # -------------------------------------------------

            if status_code >= 500:

                status = "FAIL"

                error = (
                    "Server returned "
                    f"HTTP {status_code}"
                )

            elif status_code == 404:

                status = "FAIL"

                error = (
                    "Route returned HTTP 404"
                )

            elif status_code >= 400:

                status = "FAIL"

                error = (
                    f"HTTP error {status_code}"
                )

            else:

                status = "PASS"
                error = None

            # -------------------------------------------------
            # JSON detection
            # -------------------------------------------------

            is_json = (
                "application/json"
                in content_type.lower()
            )

            json_valid = None

            if is_json:

                try:

                    response.json()

                    json_valid = True

                except Exception:

                    json_valid = False

                    if status == "PASS":

                        status = "FAIL"

                        error = (
                            "Response claims to be "
                            "JSON but contains invalid JSON"
                        )

            result = {

                "url":
                    url,

                "route":
                    route,

                "source_type":
                    route_info.get(
                        "source_type"
                    ),

                "source_file":
                    route_info.get(
                        "source_file"
                    ),

                "method":
                    "GET",

                "status_code":
                    status_code,

                "response_time_seconds":
                    elapsed,

                "content_type":
                    content_type,

                "is_json":
                    is_json,

                "json_valid":
                    json_valid,

                "status":
                    status,

                "error":
                    error
            }

        except requests.exceptions.ConnectionError:

            result = {

                "url":
                    url,

                "route":
                    route,

                "source_type":
                    route_info.get(
                        "source_type"
                    ),

                "source_file":
                    route_info.get(
                        "source_file"
                    ),

                "method":
                    "GET",

                "status_code":
                    None,

                "response_time_seconds":
                    None,

                "content_type":
                    None,

                "is_json":
                    False,

                "json_valid":
                    None,

                "status":
                    "FAIL",

                "error":
                    "Connection refused or server unavailable"
            }

        except requests.exceptions.Timeout:

            result = {

                "url":
                    url,

                "route":
                    route,

                "source_type":
                    route_info.get(
                        "source_type"
                    ),

                "source_file":
                    route_info.get(
                        "source_file"
                    ),

                "method":
                    "GET",

                "status_code":
                    None,

                "response_time_seconds":
                    None,

                "content_type":
                    None,

                "is_json":
                    False,

                "json_valid":
                    None,

                "status":
                    "FAIL",

                "error":
                    "Request timed out"
            }

        except Exception as e:

            result = {

                "url":
                    url,

                "route":
                    route,

                "source_type":
                    route_info.get(
                        "source_type"
                    ),

                "source_file":
                    route_info.get(
                        "source_file"
                    ),

                "method":
                    "GET",

                "status_code":
                    None,

                "response_time_seconds":
                    None,

                "content_type":
                    None,

                "is_json":
                    False,

                "json_valid":
                    None,

                "status":
                    "FAIL",

                "error":
                    str(e)
            }

        self.results.append(
            result
        )

        # -----------------------------------------------------
        # Display
        # -----------------------------------------------------

        if result["status"] == "PASS":

            print(
                f"  PASS "
                f"HTTP {result['status_code']} "
                f"({result['response_time_seconds']}s)"
            )

        else:

            print(
                f"  FAIL "
                f"{result.get('error')}"
            )

    # =========================================================
    # RUN
    # =========================================================

    def run(self):

        print()
        print("=" * 60)
        print("API TESTER")
        print("=" * 60)

        print()
        print(
            f"Website: {self.website_url}"
        )

        print(
            f"Framework: {self.framework}"
        )

        self.discover_routes()

        # -----------------------------------------------------
        # Avoid testing too many candidates
        # -----------------------------------------------------

        max_routes = self.config.get(
            "max_api_routes",
            50
        )

        routes_to_test = self.routes[
            :max_routes
        ]

        print()
        print(
            f"Testing {len(routes_to_test)} routes..."
        )

        for route in routes_to_test:

            self.test_route(
                route
            )

        self.save_report()

        # -----------------------------------------------------
        # Summary
        # -----------------------------------------------------

        passed = sum(
            1
            for result in self.results
            if result["status"] == "PASS"
        )

        failed = sum(
            1
            for result in self.results
            if result["status"] == "FAIL"
        )

        print()
        print("-" * 60)

        print(
            f"Routes discovered: {len(self.routes)}"
        )

        print(
            f"Requests tested:   {len(self.results)}"
        )

        print(
            f"Passed:            {passed}"
        )

        print(
            f"Failed:            {failed}"
        )

        print("-" * 60)

        print()
        print(
            f"Report: {OUTPUT_FILE}"
        )


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    tester = APITester()

    tester.run()