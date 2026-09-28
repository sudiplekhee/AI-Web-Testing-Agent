import json
import os
from datetime import datetime


TEST_REPORT = "reports/test_report.json"
SERVER_REPORT = "reports/server_error_report.json"
SOURCE_MAP = "reports/error_source_map.json"
BUG_ANALYSIS = "reports/bug_analysis.json"

OUTPUT_REPORT = "reports/master_report.json"


class UnifiedReport:

    def __init__(self):

        self.test_report = {}
        self.server_report = {}
        self.source_map = {}
        self.bug_analysis = {}

    # =========================================================
    # LOAD JSON FILE
    # =========================================================

    def load_json(self, filename):

        if not os.path.exists(filename):

            print(
                f"WARNING: {filename} not found."
            )

            return {}

        try:

            with open(
                filename,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except Exception as error:

            print(
                f"ERROR reading {filename}: {error}"
            )

            return {}

    # =========================================================
    # LOAD ALL REPORTS
    # =========================================================

    def load_reports(self):

        print()
        print(
            "Loading testing reports..."
        )

        self.test_report = self.load_json(
            TEST_REPORT
        )

        self.server_report = self.load_json(
            SERVER_REPORT
        )

        self.source_map = self.load_json(
            SOURCE_MAP
        )

        self.bug_analysis = self.load_json(
            BUG_ANALYSIS
        )

    # =========================================================
    # GET BROWSER ERRORS
    # =========================================================

    def get_browser_errors(self):

        return self.test_report.get(
            "errors",
            []
        )

    # =========================================================
    # GET SERVER ERRORS
    # =========================================================

    def get_server_errors(self):

        return self.server_report.get(
            "errors",
            []
        )

    # =========================================================
    # COUNT ERROR TYPES
    # =========================================================

    def count_error_types(
        self,
        browser_errors,
        server_errors
    ):

        counts = {}

        for error in browser_errors:

            if isinstance(error, dict):

                error_type = error.get(
                    "type",
                    "Unknown"
                )

            else:

                error_type = "Unknown"

            counts[error_type] = (
                counts.get(
                    error_type,
                    0
                ) + 1
            )

        for error in server_errors:

            if isinstance(error, dict):

                error_type = error.get(
                    "type",
                    "Unknown"
                )

            else:

                error_type = "Unknown"

            counts[error_type] = (
                counts.get(
                    error_type,
                    0
                ) + 1
            )

        return counts

    # =========================================================
    # GET SERVER TRACEBACK
    # =========================================================

    def get_traceback_analysis(self):

        return self.server_report.get(
            "traceback_analysis",
            {}
        )

    # =========================================================
    # BUILD MASTER REPORT
    # =========================================================

    def build_report(self):

        browser_errors = (
            self.get_browser_errors()
        )

        server_errors = (
            self.get_server_errors()
        )

        traceback_analysis = (
            self.get_traceback_analysis()
        )

        bug_list = self.bug_analysis.get(
            "bugs",
            []
        )

        error_counts = self.count_error_types(
            browser_errors,
            server_errors
        )

        report = {

            "agent": (
                "AI Website Testing Agent"
            ),

            "report_type": (
                "Unified Master Test Report"
            ),

            "generated_at": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ),

            "website": (
                self.test_report.get(
                    "website",
                    self.server_report.get(
                        "website"
                    )
                )
            ),

            "project_directory": (
                self.server_report.get(
                    "project_directory"
                )
            ),

            "summary": {

                "pages_tested": (
                    self.test_report
                    .get(
                        "summary",
                        {}
                    )
                    .get(
                        "pages_tested",
                        0
                    )
                ),

                "pages_passed": (
                    self.test_report
                    .get(
                        "summary",
                        {}
                    )
                    .get(
                        "pages_passed",
                        0
                    )
                ),

                "pages_failed": (
                    self.test_report
                    .get(
                        "summary",
                        {}
                    )
                    .get(
                        "pages_failed",
                        0
                    )
                ),

                "links_tested": (
                    self.test_report
                    .get(
                        "summary",
                        {}
                    )
                    .get(
                        "links_tested",
                        0
                    )
                ),

                "buttons_tested": (
                    self.test_report
                    .get(
                        "summary",
                        {}
                    )
                    .get(
                        "buttons_tested",
                        0
                    )
                ),

                "forms_tested": (
                    self.test_report
                    .get(
                        "summary",
                        {}
                    )
                    .get(
                        "forms_tested",
                        0
                    )
                ),

                "browser_errors": len(
                    browser_errors
                ),

                "server_errors": len(
                    server_errors
                ),

                "total_errors": (
                    len(browser_errors)
                    + len(server_errors)
                )
            },

            "error_types": error_counts,

            "browser_errors": browser_errors,

            "server_errors": server_errors,

            "traceback_analysis": (
                traceback_analysis
            ),

            "source_mappings": (
                self.source_map.get(
                    "mappings",
                    []
                )
            ),

            "bug_analysis": bug_list
        }

        return report

    # =========================================================
    # SAVE MASTER REPORT
    # =========================================================

    def save_report(
        self,
        report
    ):

        os.makedirs(
            "reports",
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

        print()
        print(
            "=" * 65
        )

        print(
            "             MASTER TEST REPORT"
        )

        print(
            "=" * 65
        )

        summary = report[
            "summary"
        ]

        print()
        print(
            f"Website: "
            f"{report.get('website')}"
        )

        print(
            f"Pages tested: "
            f"{summary['pages_tested']}"
        )

        print(
            f"Pages passed: "
            f"{summary['pages_passed']}"
        )

        print(
            f"Pages failed: "
            f"{summary['pages_failed']}"
        )

        print(
            f"Links tested: "
            f"{summary['links_tested']}"
        )

        print(
            f"Buttons tested: "
            f"{summary['buttons_tested']}"
        )

        print(
            f"Forms tested: "
            f"{summary['forms_tested']}"
        )

        print(
            f"Browser errors: "
            f"{summary['browser_errors']}"
        )

        print(
            f"Server errors: "
            f"{summary['server_errors']}"
        )

        print(
            f"Total errors: "
            f"{summary['total_errors']}"
        )

        print()

        if summary["total_errors"] == 0:

            print(
                "STATUS: ✓ NO ERRORS DETECTED"
            )

        else:

            print(
                "STATUS: ✗ ERRORS DETECTED"
            )

        print()

        print(
            "Error types:"
        )

        for error_type, count in (
            report["error_types"].items()
        ):

            print(
                f"  {error_type}: {count}"
            )

        print()

        print(
            f"Master report saved to:"
        )

        print(
            OUTPUT_REPORT
        )

        print()

        print(
            "=" * 65
        )

    # =========================================================
    # RUN
    # =========================================================

    def run(self):

        self.load_reports()

        report = self.build_report()

        self.save_report(
            report
        )


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    unified = UnifiedReport()

    unified.run()