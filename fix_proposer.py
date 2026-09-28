import json
import os
import re
from datetime import datetime


MASTER_REPORT = "reports/master_report.json"
SOURCE_REPORT = "reports/source_report.json"

OUTPUT_REPORT = "reports/fix_proposals.json"


class FixProposer:

    def __init__(self):

        self.master_report = {}
        self.source_report = {}

    # =========================================================
    # LOAD JSON
    # =========================================================

    def load_json(self, filename):

        if not os.path.exists(filename):

            print(
                f"ERROR: {filename} not found."
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
    # LOAD REPORTS
    # =========================================================

    def load_reports(self):

        self.master_report = self.load_json(
            MASTER_REPORT
        )

        self.source_report = self.load_json(
            SOURCE_REPORT
        )

        if not self.master_report:

            return False

        if not self.source_report:

            return False

        return True

    # =========================================================
    # FIND SOURCE FILE
    # =========================================================

    def find_source_file(
        self,
        filename
    ):

        if not filename:

            return None

        normalized_filename = (
            filename
            .replace("\\", "/")
            .lower()
        )

        for source_file in self.source_report.get(
            "files",
            []
        ):

            current_file = (
                source_file
                .get(
                    "file",
                    ""
                )
                .replace("\\", "/")
                .lower()
            )

            if current_file == normalized_filename:

                return source_file

        # -----------------------------------------------------
        # Try partial path
        # -----------------------------------------------------

        for source_file in self.source_report.get(
            "files",
            []
        ):

            current_file = (
                source_file
                .get(
                    "file",
                    ""
                )
                .replace("\\", "/")
                .lower()
            )

            if (
                normalized_filename in current_file
                or current_file in normalized_filename
            ):

                return source_file

        return None

    # =========================================================
    # GET ERROR URL
    # =========================================================

    def get_error_url(
        self,
        error
    ):

        if not isinstance(
            error,
            dict
        ):

            return None

        return error.get(
            "url"
        )

    # =========================================================
    # GET RESOURCE TYPE
    # =========================================================

    def get_resource_type(
        self,
        error
    ):

        if not isinstance(
            error,
            dict
        ):

            return ""

        return str(
            error.get(
                "resource_type",
                ""
            )
        ).lower()

    # =========================================================
    # EXTRACT FILENAME FROM URL
    # =========================================================

    def extract_filename(
        self,
        url
    ):

        if not url:

            return None

        clean_url = (
            str(url)
            .split("?")[0]
            .split("#")[0]
        )

        filename = (
            clean_url
            .rstrip("/")
            .split("/")[-1]
        )

        return filename

    # =========================================================
    # FIND REFERENCES TO RESOURCE
    # =========================================================

    def find_resource_references(
        self,
        resource_url
    ):

        if not resource_url:

            return []

        filename = self.extract_filename(
            resource_url
        )

        references = []

        for source_file in self.source_report.get(
            "files",
            []
        ):

            content = source_file.get(
                "content",
                ""
            )

            if not content:

                continue

            if filename and filename.lower() in content.lower():

                lines = content.splitlines()

                matching_lines = []

                for number, line in enumerate(
                    lines,
                    start=1
                ):

                    if filename.lower() in line.lower():

                        matching_lines.append({
                            "line": number,
                            "content": line.strip()
                        })

                references.append({
                    "file": source_file.get(
                        "file"
                    ),
                    "matches": matching_lines
                })

        return references

    # =========================================================
    # CREATE IMAGE FIX
    # =========================================================

    def create_image_fix(
        self,
        error,
        mapping
    ):

        url = self.get_error_url(
            error
        )

        filename = self.extract_filename(
            url
        )

        source_file = None

        exact_matches = mapping.get(
            "exact_source_matches",
            []
        )

        if exact_matches:

            source_file = exact_matches[0].get(
                "file"
            )

        references = (
            self.find_resource_references(
                url
            )
        )

        proposal = {

            "problem": (
                f"The image '{filename}' "
                f"returns HTTP 404."
            ),

            "likely_cause": (
                "The page references an image "
                "that does not exist at the "
                "requested server path."
            ),

            "source_file": source_file,

            "resource_url": url,

            "recommended_fix": [
                "Verify that the image file exists.",
                "Check whether the image is stored in the correct uploads directory.",
                "Check the URL used by the HTML template.",
                "Make the URL match the actual Flask static/upload configuration."
            ],

            "automatic_change": False,

            "reason": (
                "The testing agent will not "
                "create, move, or delete image "
                "files automatically."
            ),

            "references": references
        }

        return proposal

    # =========================================================
    # CREATE CSS FIX
    # =========================================================

    def create_css_fix(
        self,
        error,
        mapping
    ):

        url = self.get_error_url(
            error
        )

        source_file = None

        exact_matches = mapping.get(
            "exact_source_matches",
            []
        )

        if exact_matches:

            source_file = exact_matches[0].get(
                "file"
            )

        return {

            "problem": (
                f"The stylesheet '{url}' "
                "returns HTTP 404."
            ),

            "likely_cause": (
                "The HTML references a CSS "
                "file that cannot be found."
            ),

            "source_file": source_file,

            "resource_url": url,

            "recommended_fix": [
                "Check the stylesheet path.",
                "Verify that the CSS file exists.",
                "Verify the Flask static directory configuration.",
                "Make the HTML path match the actual CSS location."
            ],

            "automatic_change": False,

            "reason": (
                "The agent will not modify "
                "static files automatically."
            )
        }

    # =========================================================
    # CREATE JS FIX
    # =========================================================

    def create_js_fix(
        self,
        error,
        mapping
    ):

        url = self.get_error_url(
            error
        )

        source_file = None

        exact_matches = mapping.get(
            "exact_source_matches",
            []
        )

        if exact_matches:

            source_file = exact_matches[0].get(
                "file"
            )

        return {

            "problem": (
                f"The JavaScript resource "
                f"'{url}' returns HTTP 404."
            ),

            "likely_cause": (
                "The page references a JavaScript "
                "file that cannot be found."
            ),

            "source_file": source_file,

            "resource_url": url,

            "recommended_fix": [
                "Check the JavaScript file path.",
                "Verify that the JS file exists.",
                "Check the Flask static configuration.",
                "Verify the script tag in the HTML."
            ],

            "automatic_change": False,

            "reason": (
                "The agent will not modify "
                "JavaScript automatically."
            )
        }

    # =========================================================
    # CREATE FLASK ROUTE FIX
    # =========================================================

    def create_route_fix(
        self,
        error,
        mapping
    ):

        url = self.get_error_url(
            error
        )

        source_file = None

        exact_matches = mapping.get(
            "exact_source_matches",
            []
        )

        if exact_matches:

            source_file = exact_matches[0].get(
                "file"
            )

        if not source_file:

            source_file = "app.py"

        return {

            "problem": (
                f"The requested URL '{url}' "
                "returned HTTP 404."
            ),

            "likely_cause": (
                "No matching Flask route may "
                "exist for the requested URL."
            ),

            "source_file": source_file,

            "resource_url": url,

            "recommended_fix": [
                "Check the Flask routes in app.py.",
                "Verify that the requested URL has a corresponding route.",
                "Check for spelling differences between the link and route.",
                "Do not add a new route until the existing routes have been checked."
            ],

            "automatic_change": False,

            "reason": (
                "Adding routes automatically can "
                "change application behavior, so "
                "the agent will only propose the change."
            )
        }

    # =========================================================
    # CREATE PYTHON ERROR FIX
    # =========================================================

    def create_python_fix(
        self,
        error,
        mapping
    ):

        details = ""

        if isinstance(
            error,
            dict
        ):

            details = str(
                error.get(
                    "details",
                    ""
                )
            )

        exception_type = None

        exception_names = [
            "TemplateNotFound",
            "UndefinedError",
            "BuildError",
            "TypeError",
            "ValueError",
            "KeyError",
            "IndexError",
            "AttributeError",
            "NameError",
            "ImportError",
            "ModuleNotFoundError",
            "IndentationError",
            "SyntaxError",
            "OperationalError",
            "IntegrityError"
        ]

        for name in exception_names:

            if name in details:

                exception_type = name

                break

        source_file = None

        traceback = (
            self.master_report
            .get(
                "traceback_analysis",
                {}
            )
        )

        locations = traceback.get(
            "source_locations",
            []
        )

        if locations:

            source_file = locations[-1].get(
                "file"
            )

        return {

            "problem": (
                f"Server-side error detected: "
                f"{exception_type or 'Python error'}"
            ),

            "details": details,

            "exception_type": exception_type,

            "source_file": source_file,

            "recommended_fix": [
                "Inspect the traceback before changing code.",
                "Check the source file and line number.",
                "Identify the failing function or template.",
                "Make the smallest appropriate change.",
                "Run the website tests again after the change."
            ],

            "automatic_change": False,

            "reason": (
                "Server-side code changes require "
                "careful inspection before applying them."
            )
        }

    # =========================================================
    # CREATE GENERIC FIX
    # =========================================================

    def create_generic_fix(
        self,
        error,
        mapping
    ):

        source_file = None

        exact_matches = mapping.get(
            "exact_source_matches",
            []
        )

        if exact_matches:

            source_file = exact_matches[0].get(
                "file"
            )

        return {

            "problem": (
                "The testing agent detected "
                "an application error."
            ),

            "source_file": source_file,

            "recommended_fix": [
                "Inspect the error details.",
                "Inspect the mapped source file.",
                "Make the smallest required change.",
                "Run the tests again."
            ],

            "automatic_change": False,

            "reason": (
                "The agent does not have enough "
                "evidence to safely generate an "
                "automatic code change."
            )
        }

    # =========================================================
    # GENERATE PROPOSAL
    # =========================================================

    def generate_proposal(
        self,
        error,
        mapping
    ):

        resource_type = (
            self.get_resource_type(
                error
            )
        )

        status = None

        if isinstance(
            error,
            dict
        ):

            status = error.get(
                "status"
            )

        # -----------------------------------------------------
        # IMAGE
        # -----------------------------------------------------

        if (
            status == 404
            and resource_type == "image"
        ):

            return self.create_image_fix(
                error,
                mapping
            )

        # -----------------------------------------------------
        # CSS
        # -----------------------------------------------------

        if (
            status == 404
            and resource_type == "stylesheet"
        ):

            return self.create_css_fix(
                error,
                mapping
            )

        # -----------------------------------------------------
        # JS
        # -----------------------------------------------------

        if (
            status == 404
            and resource_type == "script"
        ):

            return self.create_js_fix(
                error,
                mapping
            )

        # -----------------------------------------------------
        # DOCUMENT / ROUTE
        # -----------------------------------------------------

        if (
            status == 404
            and resource_type == "document"
        ):

            return self.create_route_fix(
                error,
                mapping
            )

        # -----------------------------------------------------
        # SERVER ERROR
        # -----------------------------------------------------

        error_type = ""

        if isinstance(
            error,
            dict
        ):

            error_type = str(
                error.get(
                    "type",
                    ""
                )
            ).lower()

        if (
            "python" in error_type
            or "flask" in error_type
        ):

            return self.create_python_fix(
                error,
                mapping
            )

        # -----------------------------------------------------
        # GENERIC
        # -----------------------------------------------------

        return self.create_generic_fix(
            error,
            mapping
        )

    # =========================================================
    # RUN
    # =========================================================

    def run(self):

        if not self.load_reports():

            return

        browser_errors = (
            self.master_report
            .get(
                "browser_errors",
                []
            )
        )

        server_errors = (
            self.master_report
            .get(
                "server_errors",
                []
            )
        )

        all_errors = (
            browser_errors
            + server_errors
        )

        mappings = (
            self.master_report
            .get(
                "source_mappings",
                []
            )
        )

        proposals = []

        print()
        print("=" * 70)
        print("              FIX PROPOSAL GENERATOR")
        print("=" * 70)

        print()
        print(
            f"Errors received: "
            f"{len(all_errors)}"
        )

        print()

        for index, error in enumerate(
            all_errors
        ):

            mapping = {}

            if index < len(mappings):

                mapping = mappings[index]

            proposal = self.generate_proposal(
                error,
                mapping
            )

            proposal["bug_number"] = (
                index + 1
            )

            proposal["original_error"] = (
                error
            )

            proposals.append(
                proposal
            )

            print("=" * 70)

            print(
                f"FIX PROPOSAL #{index + 1}"
            )

            print("-" * 70)

            print(
                "PROBLEM:"
            )

            print(
                proposal.get(
                    "problem",
                    "Unknown"
                )
            )

            print()

            print(
                "SOURCE FILE:"
            )

            print(
                proposal.get(
                    "source_file"
                )
                or
                "Not determined"
            )

            print()

            print(
                "RECOMMENDED ACTION:"
            )

            for action in proposal.get(
                "recommended_fix",
                []
            ):

                print(
                    f"  • {action}"
                )

            print()

            print(
                "AUTOMATIC CHANGE:"
            )

            print(
                "  NO"
            )

            print()

        # =====================================================
        # SAVE
        # =====================================================

        report = {

            "agent": (
                "AI Website Testing Agent"
            ),

            "report_type": (
                "Fix Proposal Report"
            ),

            "generated_at": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ),

            "total_errors": len(
                all_errors
            ),

            "proposals": proposals
        }

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
        print("=" * 70)
        print("FIX PROPOSAL GENERATION COMPLETE")
        print("=" * 70)

        print(
            f"Proposals generated: "
            f"{len(proposals)}"
        )

        print(
            f"Report saved to: "
            f"{OUTPUT_REPORT}"
        )

        print("=" * 70)


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    proposer = FixProposer()

    proposer.run()