import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse


TEST_REPORT = "reports/test_report.json"
API_REPORT = "reports/api_test_report.json"
SERVER_REPORT = "reports/server_error_report.json"
SOURCE_REPORT = "reports/source_report.json"

OUTPUT_FILE = "reports/error_source_map.json"


class IntelligentErrorMapper:

    def __init__(self):

        self.test_report = self.load_json(
            TEST_REPORT
        )

        self.api_report = self.load_json(
            API_REPORT
        )

        self.server_report = self.load_json(
            SERVER_REPORT
        )

        self.source_report = self.load_json(
            SOURCE_REPORT
        )

        self.source_files = self.source_report.get(
            "files",
            []
        )

        self.mappings = []

    # =========================================================
    # LOAD JSON
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
    # SAVE
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
                "Intelligent Error Mapper",

            "mapping_time":
                datetime.now().isoformat(),

            "errors_analyzed":
                len(self.mappings),

            "mappings":
                self.mappings
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
    # NORMALIZE
    # =========================================================

    def normalize(self, value):

        if value is None:
            return ""

        return str(value).lower().replace(
            "\\",
            "/"
        )

    # =========================================================
    # GET FILENAME
    # =========================================================

    def get_filename_from_url(self, url):

        if not url:
            return ""

        try:

            parsed = urlparse(url)

            path = parsed.path

            filename = os.path.basename(
                path
            )

            return filename

        except Exception:

            return ""

    # =========================================================
    # GET EXTENSION
    # =========================================================

    def get_extension(self, filename):

        return os.path.splitext(
            filename
        )[1].lower()

    # =========================================================
    # SEARCH SOURCE
    # =========================================================

    def search_source(
        self,
        keywords
    ):

        matches = []

        if not keywords:
            return matches

        normalized_keywords = [
            self.normalize(keyword)
            for keyword in keywords
            if keyword
        ]

        for source_file in self.source_files:

            path = source_file.get(
                "path",
                ""
            )

            content = source_file.get(
                "content",
                ""
            )

            normalized_path = self.normalize(
                path
            )

            normalized_content = self.normalize(
                content
            )

            score = 0
            matched_keywords = []

            for keyword in normalized_keywords:

                if not keyword:
                    continue

                # Filename/path match

                if keyword in normalized_path:

                    score += 40

                    matched_keywords.append(
                        keyword
                    )

                # Content match

                if keyword in normalized_content:

                    score += 10

                    matched_keywords.append(
                        keyword
                    )

            if score > 0:

                matches.append({

                    "file":
                        path,

                    "score":
                        score,

                    "matched_keywords":
                        list(
                            dict.fromkeys(
                                matched_keywords
                            )
                        ),

                    "content":
                        content,

                    "language":
                        source_file.get(
                            "language"
                        )
                })

        matches.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return matches

    # =========================================================
    # FIND LINE
    # =========================================================

    def find_best_line(
        self,
        source_file,
        keywords
    ):

        content = source_file.get(
            "content",
            ""
        )

        if not content:
            return None

        lines = content.splitlines()

        normalized_keywords = [
            self.normalize(keyword)
            for keyword in keywords
            if keyword
        ]

        best_line = None
        best_score = 0

        for number, line in enumerate(
            lines,
            start=1
        ):

            normalized_line = self.normalize(
                line
            )

            score = 0

            for keyword in normalized_keywords:

                if keyword and keyword in normalized_line:

                    score += 1

            if score > best_score:

                best_score = score
                best_line = number

        if best_line:

            start = max(
                1,
                best_line - 2
            )

            end = min(
                len(lines),
                best_line + 2
            )

            context = []

            for number in range(
                start,
                end + 1
            ):

                context.append({

                    "line":
                        number,

                    "code":
                        lines[number - 1]
                })

            return {

                "line":
                    best_line,

                "code":
                    lines[best_line - 1],

                "context":
                    context
            }

        return None

    # =========================================================
    # MAP RESOURCE ERROR
    # =========================================================

    def map_resource_error(
        self,
        error
    ):

        url = error.get(
            "url",
            error.get(
                "resource_url",
                ""
            )
        )

        details = error.get(
            "details",
            error.get(
                "error",
                ""
            )
        )

        source_page = error.get(
            "source_page",
            ""
        )

        filename = (
            self.get_filename_from_url(
                url
            )
        )

        extension = self.get_extension(
            filename
        )

        keywords = []

        if filename:

            keywords.append(
                filename
            )

            name_without_extension = (
                os.path.splitext(
                    filename
                )[0]
            )

            if name_without_extension:
                keywords.append(
                    name_without_extension
                )

        # -----------------------------------------------------
        # Search exact filename
        # -----------------------------------------------------

        matches = self.search_source(
            keywords
        )

        # -----------------------------------------------------
        # If filename wasn't enough,
        # search the source page
        # -----------------------------------------------------

        if not matches and source_page:

            page_filename = (
                self.get_filename_from_url(
                    source_page
                )
            )

            if page_filename:

                matches = self.search_source(
                    [page_filename]
                )

        # -----------------------------------------------------
        # Best source
        # -----------------------------------------------------

        best_source = None

        if matches:

            candidate = matches[0]

            line_info = self.find_best_line(
                candidate,
                keywords
            )

            confidence = min(
                95,
                50 + candidate["score"]
            )

            best_source = {

                "file":
                    candidate["file"],

                "line":
                    line_info["line"]
                    if line_info
                    else None,

                "code":
                    line_info["code"]
                    if line_info
                    else None,

                "context":
                    line_info["context"]
                    if line_info
                    else [],

                "match_type":
                    "filename/content",

                "confidence":
                    confidence,

                "reason":
                    (
                        "Source code contains "
                        "a reference related to "
                        "the failing resource."
                    )
            }

        mapping = {

            "error_type":
                error.get(
                    "error_type",
                    error.get(
                        "type",
                        "Resource Error"
                    )
                ),

            "resource_url":
                url,

            "resource_filename":
                filename,

            "resource_extension":
                extension,

            "source_page":
                source_page,

            "details":
                details,

            "best_source":
                best_source
        }

        self.mappings.append(
            mapping
        )

    # =========================================================
    # MAP API ERROR
    # =========================================================

    def map_api_error(
        self,
        error
    ):

        url = error.get(
            "url",
            ""
        )

        route = error.get(
            "route",
            ""
        )

        source_file = error.get(
            "source_file"
        )

        error_message = error.get(
            "error",
            ""
        )

        keywords = []

        if route:

            keywords.append(
                route
            )

            route_clean = route.strip(
                "/"
            )

            if route_clean:

                keywords.append(
                    route_clean
                )

        # -----------------------------------------------------
        # Direct source file
        # -----------------------------------------------------

        direct_match = None

        if source_file:

            normalized_source = (
                self.normalize(
                    source_file
                )
            )

            for source in self.source_files:

                if (
                    self.normalize(
                        source.get(
                            "path",
                            ""
                        )
                    )
                    == normalized_source
                ):

                    direct_match = source
                    break

        # -----------------------------------------------------
        # Search route
        # -----------------------------------------------------

        matches = []

        if not direct_match:

            matches = self.search_source(
                keywords
            )

            if matches:

                direct_match = matches[0]

        best_source = None

        if direct_match:

            line_info = self.find_best_line(
                direct_match,
                keywords
            )

            confidence = 95 if source_file else 75

            best_source = {

                "file":
                    direct_match.get(
                        "path"
                    ),

                "line":
                    line_info["line"]
                    if line_info
                    else None,

                "code":
                    line_info["code"]
                    if line_info
                    else None,

                "context":
                    line_info["context"]
                    if line_info
                    else [],

                "match_type":
                    (
                        "API source file"
                        if source_file
                        else "route search"
                    ),

                "confidence":
                    confidence,

                "reason":
                    (
                        "API test identified "
                        "a source file or route "
                        "associated with this endpoint."
                    )
            }

        mapping = {

            "error_type":
                "API Error",

            "resource_url":
                url,

            "route":
                route,

            "details":
                error_message,

            "status_code":
                error.get(
                    "status_code"
                ),

            "source_file":
                source_file,

            "best_source":
                best_source
        }

        self.mappings.append(
            mapping
        )

    # =========================================================
    # MAP SERVER ERROR
    # =========================================================

    def map_server_error(
        self,
        error
    ):

        traceback_analysis = (
            self.server_report.get(
                "traceback_analysis",
                {}
            )
        )

        exception_type = (
            traceback_analysis.get(
                "exception_type"
            )
        )

        source_locations = (
            traceback_analysis.get(
                "source_locations",
                []
            )
        )

        traceback_lines = (
            traceback_analysis.get(
                "traceback",
                []
            )
        )

        # -----------------------------------------------------
        # Find source location
        # -----------------------------------------------------

        best_source = None

        if source_locations:

            location = source_locations[0]

            absolute_file = location.get(
                "file"
            )

            line_number = location.get(
                "line"
            )

            relative_file = None

            for source in self.source_files:

                source_absolute = source.get(
                    "absolute_path",
                    ""
                )

                if self.normalize(
                    source_absolute
                ) == self.normalize(
                    absolute_file
                ):

                    relative_file = source.get(
                        "path"
                    )

                    break

            if not relative_file:

                relative_file = (
                    absolute_file
                )

            code = None
            context = []

            # -------------------------------------------------
            # Get source code
            # -------------------------------------------------

            for source in self.source_files:

                if (
                    self.normalize(
                        source.get(
                            "path",
                            ""
                        )
                    )
                    == self.normalize(
                        relative_file
                    )
                ):

                    content = source.get(
                        "content",
                        ""
                    )

                    lines = content.splitlines()

                    if (
                        line_number
                        and
                        1 <= line_number
                        <= len(lines)
                    ):

                        code = lines[
                            line_number - 1
                        ]

                        start = max(
                            1,
                            line_number - 2
                        )

                        end = min(
                            len(lines),
                            line_number + 2
                        )

                        for number in range(
                            start,
                            end + 1
                        ):

                            context.append({

                                "line":
                                    number,

                                "code":
                                    lines[
                                        number - 1
                                    ]
                            })

                    break

            best_source = {

                "file":
                    relative_file,

                "line":
                    line_number,

                "code":
                    code,

                "context":
                    context,

                "match_type":
                    "traceback",

                "confidence":
                    99,

                "reason":
                    (
                        "The server traceback "
                        "identified the exact "
                        "source location."
                    )
            }

        mapping = {

            "error_type":
                error.get(
                    "type",
                    "Server Error"
                ),

            "details":
                error.get(
                    "details",
                    ""
                ),

            "exception_type":
                exception_type,

            "traceback":
                traceback_lines,

            "best_source":
                best_source
        }

        self.mappings.append(
            mapping
        )

    # =========================================================
    # BROWSER ERROR COLLECTION
    # =========================================================

    def get_browser_errors(self):

        errors = []

        # -----------------------------------------------------
        # Main test report
        # -----------------------------------------------------

        report_errors = self.test_report.get(
            "errors",
            []
        )

        for error in report_errors:

            if isinstance(
                error,
                dict
            ):

                errors.append(
                    error
                )

        # -----------------------------------------------------
        # Page errors
        # -----------------------------------------------------

        pages = self.test_report.get(
            "pages",
            []
        )

        for page in pages:

            page_errors = page.get(
                "errors",
                []
            )

            if isinstance(
                page_errors,
                list
            ):

                for error in page_errors:

                    if isinstance(
                        error,
                        dict
                    ):

                        errors.append(
                            error
                        )

        return errors

    # =========================================================
    # MAP ALL ERRORS
    # =========================================================

    def run(self):

        print()
        print("=" * 60)
        print("INTELLIGENT ERROR MAPPER")
        print("=" * 60)
        print()

        print(
            f"Source files loaded: "
            f"{len(self.source_files)}"
        )

        # -----------------------------------------------------
        # Browser/resource errors
        # -----------------------------------------------------

        browser_errors = (
            self.get_browser_errors()
        )

        print(
            f"Browser errors: "
            f"{len(browser_errors)}"
        )

        for error in browser_errors:

            self.map_resource_error(
                error
            )

        # -----------------------------------------------------
        # API errors
        # -----------------------------------------------------

        api_results = (
            self.api_report.get(
                "results",
                []
            )
        )

        api_errors = [

            result
            for result in api_results

            if result.get(
                "status"
            ) == "FAIL"

        ]

        print(
            f"API errors: "
            f"{len(api_errors)}"
        )

        for error in api_errors:

            self.map_api_error(
                error
            )

        # -----------------------------------------------------
        # Server errors
        # -----------------------------------------------------

        server_errors = (
            self.server_report.get(
                "errors",
                []
            )
        )

        print(
            f"Server errors: "
            f"{len(server_errors)}"
        )

        traceback_analysis = (
            self.server_report.get(
                "traceback_analysis"
            )
        )

        if (
            server_errors
            or traceback_analysis
        ):

            for error in server_errors:

                self.map_server_error(
                    error
                )

            if (
                not server_errors
                and traceback_analysis
            ):

                self.map_server_error({

                    "type":
                        "Server Error",

                    "details":
                        traceback_analysis.get(
                            "exception_type",
                            ""
                        )
                })

        # -----------------------------------------------------
        # Save
        # -----------------------------------------------------

        self.save_report()

        print()
        print("-" * 60)

        print(
            f"Errors analyzed: "
            f"{len(self.mappings)}"
        )

        print(
            f"Report: {OUTPUT_FILE}"
        )

        print("-" * 60)

        # -----------------------------------------------------
        # Display mappings
        # -----------------------------------------------------

        for number, mapping in enumerate(
            self.mappings,
            start=1
        ):

            best = mapping.get(
                "best_source"
            )

            print()
            print(
                f"Error {number}"
            )

            print(
                f"Type: "
                f"{mapping.get('error_type')}"
            )

            if best:

                print(
                    f"Source: "
                    f"{best.get('file')}"
                )

                print(
                    f"Line: "
                    f"{best.get('line')}"
                )

                print(
                    f"Confidence: "
                    f"{best.get('confidence')}%"
                )

                print(
                    f"Reason: "
                    f"{best.get('reason')}"
                )

            else:

                print(
                    "Source: NOT FOUND"
                )


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    mapper = IntelligentErrorMapper()

    mapper.run()