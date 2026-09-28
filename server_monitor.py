import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime


CONFIG_FILE = "config.json"
OUTPUT_REPORT = "reports/server_error_report.json"


class ServerMonitor:

    def __init__(self):

        self.config = self.load_config()

        self.website_url = self.config.get(
            "website_url",
            "http://127.0.0.1:5000"
        )

        self.project_directory = self.config.get(
            "project_directory",
            ""
        )

        self.server_command = self.config.get(
            "server_command",
            "python app.py"
        )

        self.startup_wait = self.config.get(
            "server_startup_wait",
            5
        )

        self.errors = []
        self.output_lines = []

    # =========================================================
    # LOAD CONFIG
    # =========================================================

    def load_config(self):

        if not os.path.exists(CONFIG_FILE):

            print(
                f"ERROR: {CONFIG_FILE} not found."
            )

            return {}

        try:

            with open(
                CONFIG_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except Exception as error:

            print(
                f"ERROR loading config: {error}"
            )

            return {}

    # =========================================================
    # DETECT PYTHON ERRORS
    # =========================================================

    def detect_python_error(
        self,
        line
    ):

        error_patterns = [

            "Traceback (most recent call last):",

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

            "FileNotFoundError",

            "PermissionError",

            "ConnectionError",

            "TimeoutError",

            "sqlite3.Error",

            "sqlite3.OperationalError",

            "OperationalError",

            "IntegrityError",

            "ProgrammingError",

            "Internal Server Error",

            "500 (INTERNAL SERVER ERROR)",

            "500 INTERNAL SERVER ERROR"
        ]

        line_lower = line.lower()

        for pattern in error_patterns:

            if pattern.lower() in line_lower:

                return True

        return False

    # =========================================================
    # DETECT HTTP SERVER ERRORS
    # =========================================================

    def detect_http_error(
        self,
        line
    ):

        patterns = [

            r"\b500\b",
            r"\b502\b",
            r"\b503\b",
            r"\b504\b",

            r"internal server error",

            r"bad gateway",

            r"service unavailable",

            r"gateway timeout"
        ]

        for pattern in patterns:

            if re.search(
                pattern,
                line,
                re.IGNORECASE
            ):

                return True

        return False

    # =========================================================
    # EXTRACT EXCEPTION TYPE
    # =========================================================

    def extract_exception_type(
        self,
        lines
    ):

        exception_types = [

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
            "FileNotFoundError",
            "PermissionError",
            "ConnectionError",
            "TimeoutError",
            "OperationalError",
            "IntegrityError",
            "ProgrammingError"
        ]

        text = "\n".join(lines)

        for exception_type in exception_types:

            if exception_type in text:

                return exception_type

        return None

    # =========================================================
    # EXTRACT SOURCE LOCATION
    # =========================================================

    def extract_source_location(
        self,
        lines
    ):

        location_pattern = re.compile(
            r'File "(.+?)", line (\d+)'
        )

        locations = []

        for line in lines:

            match = location_pattern.search(
                line
            )

            if match:

                locations.append({
                    "file": match.group(1),
                    "line": int(
                        match.group(2)
                    )
                })

        return locations

    # =========================================================
    # START SERVER
    # =========================================================

    def start_server(self):

        print()
        print("=" * 60)
        print("              SERVER MONITOR")
        print("=" * 60)

        print()
        print(
            "Starting Flask server..."
        )

        print(
            f"Project: {self.project_directory}"
        )

        print(
            f"Command: {self.server_command}"
        )

        print()

        if not self.project_directory:

            print(
                "ERROR: project_directory is not "
                "configured in config.json."
            )

            return None

        if not os.path.exists(
            self.project_directory
        ):

            print(
                "ERROR: Project directory does not exist:"
            )

            print(
                self.project_directory
            )

            return None

        try:

            command = self.server_command.split()

            process = subprocess.Popen(
                command,
                cwd=self.project_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            print(
                f"Waiting {self.startup_wait} seconds "
                "for the server..."
            )

            time.sleep(
                self.startup_wait
            )

            return process

        except Exception as error:

            print(
                f"ERROR starting server: {error}"
            )

            return None

    # =========================================================
    # READ SERVER OUTPUT
    # =========================================================

    def read_server_output(
        self,
        process
    ):

        if process is None:

            return

        print()
        print(
            "Reading server output..."
        )

        print()

        start_time = time.time()

        monitor_seconds = self.config.get(
            "server_monitor_seconds",
            15
        )

        while (
            time.time() - start_time
            < monitor_seconds
        ):

            line = process.stdout.readline()

            if not line:

                if process.poll() is not None:

                    break

                time.sleep(
                    0.1
                )

                continue

            line = line.rstrip()

            if not line:
                continue

            self.output_lines.append(
                line
            )

            print(
                line
            )

            # -------------------------------------------------
            # PYTHON ERROR
            # -------------------------------------------------

            if self.detect_python_error(
                line
            ):

                self.errors.append({
                    "type": "Python/Flask Error",
                    "details": line
                })

            # -------------------------------------------------
            # HTTP ERROR
            # -------------------------------------------------

            elif self.detect_http_error(
                line
            ):

                self.errors.append({
                    "type": "HTTP Server Error",
                    "details": line
                })

    # =========================================================
    # BUILD TRACEBACK
    # =========================================================

    def build_traceback_report(self):

        exception_type = (
            self.extract_exception_type(
                self.output_lines
            )
        )

        locations = (
            self.extract_source_location(
                self.output_lines
            )
        )

        traceback_lines = []

        inside_traceback = False

        for line in self.output_lines:

            if "Traceback (most recent call last):" in line:

                inside_traceback = True

            if inside_traceback:

                traceback_lines.append(
                    line
                )

        return {
            "exception_type": exception_type,
            "source_locations": locations,
            "traceback": traceback_lines
        }

    # =========================================================
    # REMOVE DUPLICATE ERRORS
    # =========================================================

    def deduplicate_errors(self):

        unique = []

        seen = set()

        for error in self.errors:

            key = (
                error.get("type"),
                error.get("details")
            )

            if key in seen:
                continue

            seen.add(key)

            unique.append(
                error
            )

        self.errors = unique

    # =========================================================
    # SAVE REPORT
    # =========================================================

    def save_report(
        self,
        traceback_report
    ):

        self.deduplicate_errors()

        report = {

            "monitor": (
                "AI Website Testing Agent"
            ),

            "scan_time": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ),

            "website": self.website_url,

            "project_directory": (
                self.project_directory
            ),

            "server_command": (
                self.server_command
            ),

            "errors_found": len(
                self.errors
            ),

            "errors": self.errors,

            "traceback_analysis": (
                traceback_report
            )
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

        print()
        print("=" * 60)
        print("SERVER MONITOR COMPLETE")
        print("=" * 60)

        print(
            f"Server errors found: "
            f"{len(self.errors)}"
        )

        print(
            f"Report saved to: "
            f"{OUTPUT_REPORT}"
        )

        print("=" * 60)

    # =========================================================
    # STOP SERVER
    # =========================================================

    def stop_server(
        self,
        process
    ):

        if process is None:
            return

        if process.poll() is None:

            print()
            print(
                "Stopping monitored server..."
            )

            try:

                process.terminate()

                process.wait(
                    timeout=5
                )

            except Exception:

                try:

                    process.kill()

                except Exception:
                    pass

    # =========================================================
    # RUN
    # =========================================================

    def run(self):

        process = self.start_server()

        if process is None:

            self.save_report(
                {
                    "exception_type": None,
                    "source_locations": [],
                    "traceback": []
                }
            )

            return

        try:

            self.read_server_output(
                process
            )

            traceback_report = (
                self.build_traceback_report()
            )

            self.save_report(
                traceback_report
            )

        finally:

            self.stop_server(
                process
            )


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    monitor = ServerMonitor()

    monitor.run()