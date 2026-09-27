import json
import os
import re
from datetime import datetime


TEST_REPORT = "reports/test_report.json"
SOURCE_REPORT = "reports/source_report.json"
OUTPUT_REPORT = "reports/error_source_map.json"


class ErrorSourceMapper:

    def __init__(self):
        self.test_report = {}
        self.source_report = {}

    # ---------------------------------------------------------
    # LOAD REPORTS
    # ---------------------------------------------------------

    def load_reports(self):
        if not os.path.exists(TEST_REPORT):
            print(f"ERROR: {TEST_REPORT} not found.")
            return False

        if not os.path.exists(SOURCE_REPORT):
            print(f"ERROR: {SOURCE_REPORT} not found.")
            return False

        try:
            with open(TEST_REPORT, "r", encoding="utf-8") as file:
                self.test_report = json.load(file)

            with open(SOURCE_REPORT, "r", encoding="utf-8") as file:
                self.source_report = json.load(file)

            return True

        except Exception as error:
            print(f"ERROR loading reports: {error}")
            return False

    # ---------------------------------------------------------
    # CONVERT ERROR TO TEXT
    # ---------------------------------------------------------

    def error_to_text(self, error):
        if isinstance(error, str):
            return error

        if isinstance(error, dict):
            parts = []

            for key, value in error.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)

                parts.append(f"{key}: {value}")

            return " | ".join(parts)

        if isinstance(error, list):
            return " | ".join(self.error_to_text(item) for item in error)

        return str(error)

    # ---------------------------------------------------------
    # GET SOURCE FILES
    # ---------------------------------------------------------

    def get_source_files(self):
        return self.source_report.get("files", [])

    # ---------------------------------------------------------
    # NORMALIZE PATH
    # ---------------------------------------------------------

    def normalize_path(self, path):
        if not path:
            return ""

        path = str(path)

        path = path.replace("\\", "/")
        path = path.strip()

        return path.lower()

    # ---------------------------------------------------------
    # EXTRACT RESOURCE URL
    # ---------------------------------------------------------

    def extract_resource_url(self, error):
        if not isinstance(error, dict):
            return None

        url = error.get("url")

        if url:
            return str(url)

        return None

    # ---------------------------------------------------------
    # EXTRACT RESOURCE FILENAME
    # ---------------------------------------------------------

    def extract_filename(self, url):
        if not url:
            return None

        clean_url = url.split("?")[0]
        clean_url = clean_url.split("#")[0]

        filename = clean_url.rstrip("/").split("/")[-1]

        if filename:
            return filename.lower()

        return None

    # ---------------------------------------------------------
    # EXACT RESOURCE SEARCH
    # ---------------------------------------------------------

    def find_exact_source_matches(self, resource_url):
        matches = []

        if not resource_url:
            return matches

        normalized_url = self.normalize_path(resource_url)

        filename = self.extract_filename(resource_url)

        normalized_filename = ""

        if filename:
            normalized_filename = self.normalize_path(filename)

        for source_file in self.get_source_files():

            file_path = source_file.get("file", "")
            content = source_file.get("content", "")

            normalized_content = self.normalize_path(content)

            exact_matches = []

            # ---------------------------------------------
            # Full URL match
            # ---------------------------------------------

            if normalized_url and normalized_url in normalized_content:
                exact_matches.append("exact URL")

            # ---------------------------------------------
            # URL path without domain
            # ---------------------------------------------

            if normalized_url.startswith("http://") or normalized_url.startswith("https://"):

                try:
                    path_part = re.sub(
                        r"^https?://[^/]+",
                        "",
                        normalized_url
                    )

                    if path_part and path_part in normalized_content:
                        exact_matches.append("exact path")

                except Exception:
                    pass

            # ---------------------------------------------
            # Filename match
            # ---------------------------------------------

            if normalized_filename:

                filename_pattern = normalized_filename

                if filename_pattern in normalized_content:
                    exact_matches.append("filename")

            # ---------------------------------------------
            # Save match
            # ---------------------------------------------

            if exact_matches:

                matches.append({
                    "file": file_path,
                    "match_type": list(dict.fromkeys(exact_matches)),
                    "confidence": "HIGH"
                })

        return matches

    # ---------------------------------------------------------
    # CHECK EXPECTED LOCAL FILE
    # ---------------------------------------------------------

    def check_local_file(self, resource_url):

        if not resource_url:
            return None

        filename = self.extract_filename(resource_url)

        if not filename:
            return None

        project_directory = self.source_report.get(
            "project_directory",
            ""
        )

        if not project_directory:
            return None

        # ---------------------------------------------
        # Possible locations
        # ---------------------------------------------

        possible_paths = [

            os.path.join(
                project_directory,
                "uploads",
                filename
            ),

            os.path.join(
                project_directory,
                "static",
                "uploads",
                filename
            ),

            os.path.join(
                project_directory,
                "static",
                filename
            ),

            os.path.join(
                project_directory,
                filename
            )
        ]

        checked_paths = []

        for path in possible_paths:

            exists = os.path.isfile(path)

            checked_paths.append({
                "path": path,
                "exists": exists
            })

            if exists:

                return {
                    "filename": filename,
                    "status": "FOUND",
                    "path": path,
                    "checked_paths": checked_paths
                }

        return {
            "filename": filename,
            "status": "NOT FOUND",
            "path": None,
            "checked_paths": checked_paths
        }

    # ---------------------------------------------------------
    # FIND RELEVANT SOURCE FILES
    # ---------------------------------------------------------

    def find_relevant_files(self, error_text):

        keywords = set()

        text = error_text.lower()

        words = re.findall(
            r"[a-zA-Z0-9_\-./]+",
            text
        )

        for word in words:

            if len(word) >= 3:
                keywords.add(word)

        scored_files = []

        for source_file in self.get_source_files():

            file_path = source_file.get("file", "")
            content = source_file.get("content", "")

            searchable = (
                file_path.lower()
                + " "
                + content.lower()
            )

            score = 0

            for keyword in keywords:

                if keyword in searchable:
                    score += 1

            if score > 0:

                scored_files.append({
                    "file": file_path,
                    "score": score,
                    "confidence": "LOW"
                })

        scored_files.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return scored_files[:5]

    # ---------------------------------------------------------
    # ANALYZE ONE ERROR
    # ---------------------------------------------------------

    def analyze_error(self, error, number):

        error_text = self.error_to_text(error)

        resource_url = self.extract_resource_url(error)

        result = {
            "error_number": number,
            "error": error,
            "error_text": error_text,
            "resource_url": resource_url,
            "exact_source_matches": [],
            "local_file_check": None,
            "possible_source_files": []
        }

        # -----------------------------------------------------
        # EXACT RESOURCE ANALYSIS
        # -----------------------------------------------------

        if resource_url:

            exact_matches = self.find_exact_source_matches(
                resource_url
            )

            result["exact_source_matches"] = exact_matches

            result["local_file_check"] = self.check_local_file(
                resource_url
            )

        # -----------------------------------------------------
        # FALLBACK KEYWORD MAPPING
        # -----------------------------------------------------

        result["possible_source_files"] = self.find_relevant_files(
            error_text
        )

        return result

    # ---------------------------------------------------------
    # ANALYZE ALL ERRORS
    # ---------------------------------------------------------

    def analyze(self):

        errors = self.test_report.get("errors", [])

        print()
        print("=" * 60)
        print("       ERROR → SOURCE CODE MAPPER")
        print("=" * 60)

        print()
        print("Analyzing detected errors...")

        mappings = []

        for number, error in enumerate(errors, start=1):

            result = self.analyze_error(
                error,
                number
            )

            mappings.append(result)

            resource_url = result.get("resource_url")

            print()
            print(f"Error {number}: {resource_url or 'Unknown'}")

            print()
            print("ERROR")
            print("-" * 60)

            print(result["error_text"])

            print("-" * 60)

            # -------------------------------------------------
            # EXACT SOURCE MATCH
            # -------------------------------------------------

            exact_matches = result["exact_source_matches"]

            if exact_matches:

                print()
                print("EXACT SOURCE MATCHES:")

                for match in exact_matches:

                    print(
                        f"  ✓ {match['file']}"
                    )

                    print(
                        f"    Match: "
                        f"{', '.join(match['match_type'])}"
                    )

                    print(
                        f"    Confidence: "
                        f"{match['confidence']}"
                    )

            else:

                print()
                print("EXACT SOURCE MATCHES:")
                print("  None found")

            # -------------------------------------------------
            # LOCAL FILE CHECK
            # -------------------------------------------------

            local_check = result["local_file_check"]

            if local_check:

                print()
                print("LOCAL FILE CHECK:")
                print(
                    f"  File: {local_check['filename']}"
                )

                if local_check["status"] == "FOUND":

                    print("  Status: ✓ FOUND")
                    print(
                        f"  Path: {local_check['path']}"
                    )

                else:

                    print("  Status: ✗ NOT FOUND")

                    print()
                    print("  Checked locations:")

                    for checked in local_check["checked_paths"]:

                        symbol = "✓" if checked["exists"] else "✗"

                        print(
                            f"    {symbol} {checked['path']}"
                        )

            # -------------------------------------------------
            # FALLBACK RESULTS
            # -------------------------------------------------

            possible_files = result[
                "possible_source_files"
            ]

            if possible_files:

                print()
                print(
                    "POSSIBLE SOURCE FILES "
                    "(keyword fallback):"
                )

                for item in possible_files:

                    print(
                        f"  {item['file']} "
                        f"(score: {item['score']})"
                    )

        # -----------------------------------------------------
        # SAVE REPORT
        # -----------------------------------------------------

        report = {
            "mapper": "AI Website Testing Agent",
            "mapping_time": datetime.now().isoformat(
                timespec="seconds"
            ),
            "test_report": TEST_REPORT,
            "source_report": SOURCE_REPORT,
            "errors_analyzed": len(mappings),
            "mappings": mappings
        }

        os.makedirs(
            os.path.dirname(OUTPUT_REPORT),
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
        print("=" * 60)
        print("MAPPING COMPLETE")
        print("=" * 60)

        print(
            f"Errors analyzed: {len(mappings)}"
        )

        print(
            f"Report saved to: {OUTPUT_REPORT}"
        )

        print("=" * 60)


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    mapper = ErrorSourceMapper()

    if mapper.load_reports():

        mapper.analyze()