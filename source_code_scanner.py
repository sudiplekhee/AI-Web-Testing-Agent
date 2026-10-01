import json
import os
import re
from datetime import datetime


CONFIG_FILE = "config.json"
OUTPUT_FILE = "reports/source_report.json"


IGNORE_DIRS = {
    ".git",
    ".github",
    ".vscode",
    ".idea",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    "node_modules",
    "dist",
    "build",
    "vendor",
    "coverage",
    ".next",
    ".nuxt",
}


SOURCE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "React JavaScript",
    ".ts": "TypeScript",
    ".tsx": "React TypeScript",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SASS",
    ".less": "LESS",
    ".json": "JSON",
    ".sql": "SQL",
    ".php": "PHP",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


class SourceScanner:

    def __init__(self):

        self.config = self.load_json(
            CONFIG_FILE
        )

        self.project_directory = (
            self.config.get(
                "project_directory",
                ""
            )
        )

        self.files = []

        self.statistics = {
            "total_files": 0,
            "python_files": 0,
            "javascript_files": 0,
            "typescript_files": 0,
            "html_files": 0,
            "css_files": 0,
            "php_files": 0,
            "other_source_files": 0
        }

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
                "Source Scanner",

            "scan_time":
                datetime.now().isoformat(),

            "project_directory":
                self.project_directory,

            "statistics":
                self.statistics,

            "files":
                self.files
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
    # GET LANGUAGE
    # =========================================================

    def get_language(self, filename):

        extension = os.path.splitext(
            filename
        )[1].lower()

        return SOURCE_EXTENSIONS.get(
            extension
        )

    # =========================================================
    # CHECK IF SOURCE FILE
    # =========================================================

    def is_source_file(self, filename):

        extension = os.path.splitext(
            filename
        )[1].lower()

        return extension in SOURCE_EXTENSIONS

    # =========================================================
    # READ FILE
    # =========================================================

    def read_source_file(self, path):

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                return file.read()

        except Exception as e:

            return ""

    # =========================================================
    # FIND FUNCTIONS / CLASSES
    # =========================================================

    def extract_symbols(
        self,
        content,
        language
    ):

        symbols = []

        lines = content.splitlines()

        for line_number, line in enumerate(
            lines,
            start=1
        ):

            stripped = line.strip()

            # -------------------------------------------------
            # Python
            # -------------------------------------------------

            if language == "Python":

                match = re.match(
                    r"(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)",
                    stripped
                )

                if match:

                    symbols.append({

                        "type": "function",

                        "name":
                            match.group(1),

                        "line":
                            line_number
                    })

                match = re.match(
                    r"class\s+([A-Za-z_][A-Za-z0-9_]*)",
                    stripped
                )

                if match:

                    symbols.append({

                        "type": "class",

                        "name":
                            match.group(1),

                        "line":
                            line_number
                    })

            # -------------------------------------------------
            # JavaScript / TypeScript
            # -------------------------------------------------

            elif language in {
                "JavaScript",
                "React JavaScript",
                "TypeScript",
                "React TypeScript"
            }:

                patterns = [

                    r"(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)",

                    r"(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\(",

                    r"class\s+([A-Za-z_$][A-Za-z0-9_$]*)"
                ]

                for pattern in patterns:

                    match = re.search(
                        pattern,
                        stripped
                    )

                    if match:

                        symbols.append({

                            "type": "symbol",

                            "name":
                                match.group(1),

                            "line":
                                line_number
                        })

                        break

            # -------------------------------------------------
            # PHP
            # -------------------------------------------------

            elif language == "PHP":

                match = re.search(
                    r"function\s+([A-Za-z_][A-Za-z0-9_]*)",
                    stripped
                )

                if match:

                    symbols.append({

                        "type": "function",

                        "name":
                            match.group(1),

                        "line":
                            line_number
                    })

        return symbols

    # =========================================================
    # FIND WEB ROUTES
    # =========================================================

    def extract_routes(
        self,
        content,
        language
    ):

        routes = []

        # -----------------------------------------------------
        # Flask
        # -----------------------------------------------------

        if language == "Python":

            flask_patterns = [

                r"@(?:\w+\.)?route\(\s*['\"]([^'\"]+)",

                r"@(?:\w+\.)?(?:get|post|put|delete|patch)"
                r"\(\s*['\"]([^'\"]+)"
            ]

            for pattern in flask_patterns:

                matches = re.finditer(
                    pattern,
                    content,
                    re.IGNORECASE
                )

                for match in matches:

                    routes.append({

                        "framework":
                            "Python web framework",

                        "route":
                            match.group(1)
                    })

        # -----------------------------------------------------
        # Express
        # -----------------------------------------------------

        if language in {
            "JavaScript",
            "TypeScript",
            "React JavaScript",
            "React TypeScript"
        }:

            pattern = (
                r"(?:app|router)"
                r"\."
                r"(get|post|put|delete|patch)"
                r"\(\s*['\"]([^'\"]+)"
            )

            matches = re.finditer(
                pattern,
                content,
                re.IGNORECASE
            )

            for match in matches:

                routes.append({

                    "framework":
                        "Express",

                    "method":
                        match.group(1).upper(),

                    "route":
                        match.group(2)
                })

        return routes

    # =========================================================
    # ANALYZE FILE
    # =========================================================

    def analyze_file(
        self,
        full_path,
        relative_path
    ):

        language = self.get_language(
            relative_path
        )

        if not language:
            return

        content = self.read_source_file(
            full_path
        )

        lines = content.splitlines()

        symbols = self.extract_symbols(
            content,
            language
        )

        routes = self.extract_routes(
            content,
            language
        )

        file_info = {

            "path":
                relative_path,

            "absolute_path":
                full_path,

            "filename":
                os.path.basename(
                    relative_path
                ),

            "extension":
                os.path.splitext(
                    relative_path
                )[1].lower(),

            "language":
                language,

            "line_count":
                len(lines),

            "size_bytes":
                os.path.getsize(
                    full_path
                ),

            "symbols":
                symbols,

            "routes":
                routes,

            "content":
                content
        }

        self.files.append(
            file_info
        )

        # -----------------------------------------------------
        # Statistics
        # -----------------------------------------------------

        self.statistics[
            "total_files"
        ] += 1

        if language == "Python":

            self.statistics[
                "python_files"
            ] += 1

        elif language in {
            "JavaScript",
            "React JavaScript"
        }:

            self.statistics[
                "javascript_files"
            ] += 1

        elif language in {
            "TypeScript",
            "React TypeScript"
        }:

            self.statistics[
                "typescript_files"
            ] += 1

        elif language == "HTML":

            self.statistics[
                "html_files"
            ] += 1

        elif language in {
            "CSS",
            "SCSS",
            "SASS",
            "LESS"
        }:

            self.statistics[
                "css_files"
            ] += 1

        elif language == "PHP":

            self.statistics[
                "php_files"
            ] += 1

        else:

            self.statistics[
                "other_source_files"
            ] += 1

    # =========================================================
    # SCAN PROJECT
    # =========================================================

    def scan(self):

        print()
        print("=" * 60)
        print("SOURCE CODE SCANNER")
        print("=" * 60)
        print()

        if not self.project_directory:

            print(
                "ERROR: project_directory is missing."
            )

            return False

        if not os.path.isdir(
            self.project_directory
        ):

            print(
                "ERROR: Project directory does not exist:"
            )

            print(
                self.project_directory
            )

            return False

        print(
            f"Project:\n{self.project_directory}"
        )

        print()
        print(
            "Scanning source files..."
        )

        for root, dirs, files in os.walk(
            self.project_directory
        ):

            dirs[:] = [
                directory
                for directory in dirs
                if directory not in IGNORE_DIRS
            ]

            for filename in files:

                if not self.is_source_file(
                    filename
                ):
                    continue

                full_path = os.path.join(
                    root,
                    filename
                )

                relative_path = os.path.relpath(
                    full_path,
                    self.project_directory
                )

                self.analyze_file(
                    full_path,
                    relative_path
                )

        self.save_report()

        # -----------------------------------------------------
        # Summary
        # -----------------------------------------------------

        print()
        print("-" * 60)

        print(
            f"Total source files: "
            f"{self.statistics['total_files']}"
        )

        print(
            f"Python:            "
            f"{self.statistics['python_files']}"
        )

        print(
            f"JavaScript:        "
            f"{self.statistics['javascript_files']}"
        )

        print(
            f"TypeScript:        "
            f"{self.statistics['typescript_files']}"
        )

        print(
            f"HTML:              "
            f"{self.statistics['html_files']}"
        )

        print(
            f"CSS:               "
            f"{self.statistics['css_files']}"
        )

        print(
            f"PHP:               "
            f"{self.statistics['php_files']}"
        )

        print("-" * 60)

        print()
        print(
            f"Report: {OUTPUT_FILE}"
        )

        return True


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    scanner = SourceScanner()

    scanner.scan()