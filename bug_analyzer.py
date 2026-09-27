import json
import os
from datetime import datetime


TEST_REPORT = "reports/test_report.json"
SOURCE_MAP = "reports/error_source_map.json"
OUTPUT_REPORT = "reports/bug_analysis.json"


class BugAnalyzer:

    def __init__(self):
        self.test_report = {}
        self.source_map = {}

    # =========================================================
    # LOAD REPORTS
    # =========================================================

    def load_reports(self):

        if not os.path.exists(TEST_REPORT):
            print(f"ERROR: {TEST_REPORT} not found.")
            return False

        if not os.path.exists(SOURCE_MAP):
            print(f"ERROR: {SOURCE_MAP} not found.")
            return False

        try:

            with open(
                TEST_REPORT,
                "r",
                encoding="utf-8"
            ) as file:

                self.test_report = json.load(file)

            with open(
                SOURCE_MAP,
                "r",
                encoding="utf-8"
            ) as file:

                self.source_map = json.load(file)

            return True

        except Exception as error:

            print(
                f"ERROR loading reports: {error}"
            )

            return False

    # =========================================================
    # GET RESOURCE TYPE
    # =========================================================

    def get_resource_type(self, error):

        if not isinstance(error, dict):
            return "unknown"

        resource_type = error.get(
            "resource_type",
            ""
        )

        if resource_type:
            return resource_type.lower()

        error_type = error.get(
            "type",
            ""
        )

        return str(error_type).lower()

    # =========================================================
    # GET ERROR STATUS
    # =========================================================

    def get_status(self, error):

        if not isinstance(error, dict):
            return None

        return error.get("status")

    # =========================================================
    # GET URL
    # =========================================================

    def get_url(self, error):

        if not isinstance(error, dict):
            return None

        return error.get("url")

    # =========================================================
    # GET SOURCE FILE
    # =========================================================

    def get_source_file(self, mapping):

        exact_matches = mapping.get(
            "exact_source_matches",
            []
        )

        if exact_matches:

            return exact_matches[0].get(
                "file"
            )

        possible_files = mapping.get(
            "possible_source_files",
            []
        )

        if possible_files:

            return possible_files[0].get(
                "file"
            )

        return None

    # =========================================================
    # EXPLAIN 404 ERROR
    # =========================================================

    def explain_404(
        self,
        error,
        mapping
    ):

        url = self.get_url(error)

        resource_type = self.get_resource_type(
            error
        )

        source_file = self.get_source_file(
            mapping
        )

        local_file_check = mapping.get(
            "local_file_check"
        )

        # -----------------------------------------------------
        # IMAGE
        # -----------------------------------------------------

        if resource_type == "image":

            filename = None

            if local_file_check:

                filename = local_file_check.get(
                    "filename"
                )

            if not filename and url:

                filename = url.rstrip(
                    "/"
                ).split("/")[-1]

            if not filename:

                filename = "image file"

            explanation = (
                f"The website requested the image "
                f"'{filename}', but the server returned "
                f"HTTP 404. This means the image could "
                f"not be found at the requested path."
            )

            cause = (
                "The HTML/database may contain an image "
                "path that does not match the actual "
                "location of the image file."
            )

            if local_file_check:

                if local_file_check.get(
                    "status"
                ) == "NOT FOUND":

                    cause = (
                        f"The image '{filename}' was not "
                        f"found in the expected project "
                        f"locations checked by the testing "
                        f"agent."
                    )

            action = (
                "Check the image path, verify that the "
                "image file exists, and make sure the "
                "Flask/static/uploads configuration "
                "matches the URL used by the page."
            )

        # -----------------------------------------------------
        # CSS
        # -----------------------------------------------------

        elif resource_type == "stylesheet":

            explanation = (
                f"The page requested the stylesheet "
                f"'{url}', but the server returned "
                f"HTTP 404."
            )

            cause = (
                "The CSS file may be missing or the "
                "HTML may contain an incorrect CSS path."
            )

            action = (
                "Check the stylesheet path in the HTML "
                "and verify that the CSS file exists."
            )

        # -----------------------------------------------------
        # JAVASCRIPT
        # -----------------------------------------------------

        elif resource_type == "script":

            explanation = (
                f"The page requested the JavaScript "
                f"resource '{url}', but the server "
                f"returned HTTP 404."
            )

            cause = (
                "The JavaScript file may be missing or "
                "the script URL may be incorrect."
            )

            action = (
                "Check the script path and verify that "
                "the JavaScript file exists."
            )

        # -----------------------------------------------------
        # FONT
        # -----------------------------------------------------

        elif resource_type == "font":

            explanation = (
                f"The page requested a font resource "
                f"'{url}', but the server returned "
                f"HTTP 404."
            )

            cause = (
                "The font file may be missing or the "
                "font URL may be incorrect."
            )

            action = (
                "Check the font path and verify that "
                "the required font file exists."
            )

        # -----------------------------------------------------
        # DOCUMENT
        # -----------------------------------------------------

        elif resource_type == "document":

            explanation = (
                f"The browser requested the page "
                f"'{url}', but the server returned "
                f"HTTP 404."
            )

            cause = (
                "There may be no Flask route matching "
                "this URL."
            )

            action = (
                "Check the Flask routes in app.py and "
                "verify that the requested URL has a "
                "corresponding route."
            )

        # -----------------------------------------------------
        # OTHER
        # -----------------------------------------------------

        else:

            explanation = (
                f"The resource '{url}' returned "
                f"HTTP 404."
            )

            cause = (
                "The requested resource could not be "
                "found by the web application."
            )

            action = (
                "Check the URL, Flask route, static-file "
                "configuration, and existence of the "
                "requested resource."
            )

        return {
            "explanation": explanation,
            "likely_cause": cause,
            "suggested_action": action,
            "source_file": source_file
        }

    # =========================================================
    # EXPLAIN CONSOLE ERROR
    # =========================================================

    def explain_console_error(
        self,
        error,
        mapping
    ):

        details = ""

        if isinstance(error, dict):

            details = str(
                error.get(
                    "details",
                    ""
                )
            )

        source_file = self.get_source_file(
            mapping
        )

        explanation = (
            "The browser reported a JavaScript "
            "console error while loading the page."
        )

        cause = (
            "A page resource, JavaScript operation, "
            "or browser-side request may have failed."
        )

        action = (
            "Inspect the browser console details and "
            "the resources requested by the affected page."
        )

        if "404" in details:

            explanation = (
                "The browser reported a failed resource "
                "request with HTTP 404."
            )

            cause = (
                "The page is requesting a resource that "
                "the server cannot find."
            )

            action = (
                "Check the exact missing resource URL "
                "and its corresponding source reference."
            )

        return {
            "explanation": explanation,
            "likely_cause": cause,
            "suggested_action": action,
            "source_file": source_file
        }

    # =========================================================
    # EXPLAIN GENERAL ERROR
    # =========================================================

    def explain_general_error(
        self,
        error,
        mapping
    ):

        source_file = self.get_source_file(
            mapping
        )

        if isinstance(error, dict):

            details = str(
                error.get(
                    "details",
                    error
                )
            )

        else:

            details = str(error)

        return {
            "explanation": (
                f"The testing agent detected this "
                f"problem: {details}"
            ),
            "likely_cause": (
                "The exact cause requires checking "
                "the affected page and source code."
            ),
            "suggested_action": (
                "Inspect the source file and reproduce "
                "the problem manually."
            ),
            "source_file": source_file
        }

    # =========================================================
    # ANALYZE ONE BUG
    # =========================================================

    def analyze_bug(
        self,
        error,
        mapping
    ):

        status = self.get_status(
            error
        )

        error_type = ""

        if isinstance(error, dict):

            error_type = str(
                error.get(
                    "type",
                    ""
                )
            ).lower()

        # -----------------------------------------------------
        # 404
        # -----------------------------------------------------

        if status == 404:

            return self.explain_404(
                error,
                mapping
            )

        # -----------------------------------------------------
        # CONSOLE
        # -----------------------------------------------------

        if "console" in error_type:

            return self.explain_console_error(
                error,
                mapping
            )

        # -----------------------------------------------------
        # GENERAL
        # -----------------------------------------------------

        return self.explain_general_error(
            error,
            mapping
        )

    # =========================================================
    # MAIN ANALYSIS
    # =========================================================

    def analyze(self):

        errors = self.test_report.get(
            "errors",
            []
        )

        mappings = self.source_map.get(
            "mappings",
            []
        )

        bugs = []

        print()
        print("=" * 70)
        print("             AUTOMATIC BUG ANALYZER")
        print("=" * 70)

        print()
        print(
            f"Errors received: {len(errors)}"
        )

        print()

        for index, error in enumerate(
            errors
        ):

            mapping = {}

            if index < len(mappings):

                mapping = mappings[index]

            explanation = self.analyze_bug(
                error,
                mapping
            )

            bug = {
                "bug_number": index + 1,
                "error": error,
                "source_mapping": mapping,
                "analysis": explanation
            }

            bugs.append(
                bug
            )

            # -------------------------------------------------
            # PRINT RESULT
            # -------------------------------------------------

            print("=" * 70)

            print(
                f"BUG #{index + 1}"
            )

            print("-" * 70)

            url = self.get_url(
                error
            )

            if url:

                print(
                    f"URL: {url}"
                )

            print()

            print(
                "EXPLANATION:"
            )

            print(
                explanation[
                    "explanation"
                ]
            )

            print()

            print(
                "LIKELY CAUSE:"
            )

            print(
                explanation[
                    "likely_cause"
                ]
            )

            print()

            print(
                "SUGGESTED ACTION:"
            )

            print(
                explanation[
                    "suggested_action"
                ]
            )

            print()

            if explanation.get(
                "source_file"
            ):

                print(
                    "SOURCE FILE:"
                )

                print(
                    explanation[
                        "source_file"
                    ]
                )

            else:

                print(
                    "SOURCE FILE:"
                )

                print(
                    "Not determined"
                )

            print()

        # =====================================================
        # SAVE REPORT
        # =====================================================

        report = {
            "analyzer": "AI Website Testing Agent",
            "analysis_time": datetime.now().isoformat(
                timespec="seconds"
            ),
            "test_report": TEST_REPORT,
            "source_map": SOURCE_MAP,
            "bugs_found": len(bugs),
            "bugs": bugs
        }

        os.makedirs(
            os.path.dirname(
                OUTPUT_REPORT
            ),
            exist_ok=True
        )

        with open(
            OUTPUT_REPORT,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("=" * 70)
        print("BUG ANALYSIS COMPLETE")
        print("=" * 70)

        print(
            f"Bugs analyzed: {len(bugs)}"
        )

        print(
            f"Report saved to: {OUTPUT_REPORT}"
        )

        print("=" * 70)


# =============================================================
# RUN
# =============================================================

if __name__ == "__main__":

    analyzer = BugAnalyzer()

    if analyzer.load_reports():

        analyzer.analyze()