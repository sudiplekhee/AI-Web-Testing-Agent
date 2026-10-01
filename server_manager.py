import json
import os
import socket
import subprocess
import time
from datetime import datetime
from urllib.parse import urlparse


DETECTION_FILE = "reports/project_detection.json"
CONFIG_FILE = "config.json"
REPORT_FILE = "reports/server_manager_report.json"


class ServerManager:

    def __init__(self):
        self.process = None
        self.project_directory = None
        self.server_command = None
        self.website_url = None
        self.start_time = None

        self.load_configuration()

    # =========================================================
    # LOAD CONFIGURATION
    # =========================================================

    def load_configuration(self):

        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError(
                "config.json was not found."
            )

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            self.config = json.load(file)

        self.website_url = self.config.get(
            "website_url",
            "http://127.0.0.1:5000"
        )

        # -----------------------------------------------------
        # Prefer project detector
        # -----------------------------------------------------

        if os.path.exists(DETECTION_FILE):

            try:

                with open(
                    DETECTION_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:

                    detection = json.load(file)

                self.project_directory = detection.get(
                    "project_directory"
                )

                self.server_command = detection.get(
                    "server_command"
                )

            except Exception as e:

                print(
                    f"Could not read project detection: {e}"
                )

        # -----------------------------------------------------
        # Fallback to config.json
        # -----------------------------------------------------

        if not self.project_directory:

            self.project_directory = self.config.get(
                "project_directory"
            )

        if not self.server_command:

            self.server_command = self.config.get(
                "server_command"
            )

        self.startup_wait = self.config.get(
            "server_startup_wait",
            5
        )

        self.startup_timeout = self.config.get(
            "server_startup_timeout",
            30
        )

    # =========================================================
    # PORT DETECTION
    # =========================================================

    def get_port(self):

        try:

            parsed = urlparse(
                self.website_url
            )

            if parsed.port:
                return parsed.port

            if parsed.scheme == "https":
                return 443

            return 80

        except Exception:

            return None

    # =========================================================
    # CHECK PORT
    # =========================================================

    def is_port_open(self):

        port = self.get_port()

        if not port:
            return False

        try:

            parsed = urlparse(
                self.website_url
            )

            host = parsed.hostname or "127.0.0.1"

            with socket.create_connection(
                (host, port),
                timeout=1
            ):

                return True

        except Exception:

            return False

    # =========================================================
    # SAVE REPORT
    # =========================================================

    def save_report(self, status, **extra):

        os.makedirs(
            "reports",
            exist_ok=True
        )

        report = {

            "agent":
                "AI Website Testing Agent",

            "component":
                "Server Manager",

            "time":
                datetime.now().isoformat(),

            "project_directory":
                self.project_directory,

            "server_command":
                self.server_command,

            "website_url":
                self.website_url,

            "port":
                self.get_port(),

            "status":
                status
        }

        report.update(extra)

        with open(
            REPORT_FILE,
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
    # START SERVER
    # =========================================================

    def start(self):

        print()
        print("=" * 60)
        print("SERVER MANAGER")
        print("=" * 60)
        print()

        # -----------------------------------------------------
        # Validate project
        # -----------------------------------------------------

        if not self.project_directory:

            print(
                "ERROR: Project directory was not detected."
            )

            self.save_report(
                "FAILED",
                error="Project directory not found"
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

            self.save_report(
                "FAILED",
                error="Project directory does not exist"
            )

            return False

        # -----------------------------------------------------
        # Validate command
        # -----------------------------------------------------

        if not self.server_command:

            print(
                "ERROR: No server command was detected."
            )

            print(
                "This may be a static website."
            )

            self.save_report(
                "NO_SERVER_COMMAND",
                error="No server command detected"
            )

            return False

        # -----------------------------------------------------
        # Check if server already running
        # -----------------------------------------------------

        if self.is_port_open():

            print(
                "A server is already running."
            )

            print(
                f"Website: {self.website_url}"
            )

            self.save_report(
                "ALREADY_RUNNING"
            )

            return True

        # -----------------------------------------------------
        # Display information
        # -----------------------------------------------------

        print(
            f"Project:\n{self.project_directory}"
        )

        print()

        print(
            f"Command:\n{self.server_command}"
        )

        print()

        print(
            f"Website:\n{self.website_url}"
        )

        print()

        print(
            f"Port:\n{self.get_port()}"
        )

        print()

        print(
            "Starting server..."
        )

        # -----------------------------------------------------
        # Start process
        # -----------------------------------------------------

        try:

            self.start_time = datetime.now()

            creation_flags = 0

            # Windows:
            # prevent a new visible console window

            if os.name == "nt":

                creation_flags = (
                    subprocess.CREATE_NEW_PROCESS_GROUP
                )

            self.process = subprocess.Popen(

                self.server_command,

                cwd=self.project_directory,

                shell=True,

                stdout=subprocess.PIPE,

                stderr=subprocess.STDOUT,

                stdin=subprocess.DEVNULL,

                text=True,

                encoding="utf-8",

                errors="replace",

                bufsize=1,

                creationflags=creation_flags
            )

        except Exception as e:

            print(
                f"ERROR: Could not start server: {e}"
            )

            self.save_report(
                "FAILED",
                error=str(e)
            )

            return False

        # -----------------------------------------------------
        # Wait for startup
        # -----------------------------------------------------

        print()

        print(
            "Waiting for server..."
        )

        deadline = (
            time.time()
            + self.startup_timeout
        )

        output_lines = []

        while time.time() < deadline:

            # -------------------------------------------------
            # Check process crash
            # -------------------------------------------------

            if self.process.poll() is not None:

                remaining_output = ""

                try:

                    remaining_output = (
                        self.process.stdout.read()
                        or ""
                    )

                except Exception:
                    pass

                if remaining_output:

                    output_lines.extend(
                        remaining_output.splitlines()
                    )

                print()
                print(
                    "SERVER FAILED TO START"
                )

                print()

                for line in output_lines[-20:]:

                    print(
                        f"  {line}"
                    )

                self.save_report(

                    "FAILED",

                    exit_code=
                        self.process.returncode,

                    output=
                        output_lines,

                    startup_seconds=
                        round(
                            (
                                datetime.now()
                                - self.start_time
                            ).total_seconds(),
                            2
                        )
                )

                return False

            # -------------------------------------------------
            # Read available output
            # -------------------------------------------------

            try:

                if self.process.stdout:

                    import msvcrt

                    if os.name == "nt":

                        while msvcrt.kbhit():
                            pass

            except Exception:
                pass

            # -------------------------------------------------
            # Check website port
            # -------------------------------------------------

            if self.is_port_open():

                print()
                print(
                    "SERVER STARTED SUCCESSFULLY"
                )

                print()

                print(
                    f"Website is available at:"
                )

                print(
                    self.website_url
                )

                elapsed = round(
                    (
                        datetime.now()
                        - self.start_time
                    ).total_seconds(),
                    2
                )

                self.save_report(

                    "RUNNING",

                    pid=
                        self.process.pid,

                    startup_seconds=
                        elapsed
                )

                return True

            time.sleep(
                self.startup_wait
            )

        # -----------------------------------------------------
        # Timeout
        # -----------------------------------------------------

        print()
        print(
            "SERVER STARTUP TIMEOUT"
        )

        print(
            f"Server did not become available "
            f"within {self.startup_timeout} seconds."
        )

        self.save_report(

            "TIMEOUT",

            pid=
                self.process.pid
            if self.process
            else None,

            startup_timeout=
                self.startup_timeout
        )

        return False

    # =========================================================
    # STOP SERVER
    # =========================================================

    def stop(self):

        print()
        print(
            "=" * 60
        )

        print(
            "STOPPING SERVER"
        )

        print(
            "=" * 60
        )

        if not self.process:

            print(
                "No server process is managed by this agent."
            )

            return

        if self.process.poll() is not None:

            print(
                "Server process has already stopped."
            )

            return

        try:

            if os.name == "nt":

                subprocess.run(

                    [
                        "taskkill",
                        "/PID",
                        str(self.process.pid),
                        "/T",
                        "/F"
                    ],

                    stdout=subprocess.DEVNULL,

                    stderr=subprocess.DEVNULL
                )

            else:

                self.process.terminate()

                try:

                    self.process.wait(
                        timeout=5
                    )

                except subprocess.TimeoutExpired:

                    self.process.kill()

            print(
                "Server stopped successfully."
            )

            self.save_report(
                "STOPPED",
                pid=self.process.pid
            )

        except Exception as e:

            print(
                f"Could not stop server: {e}"
            )

            self.save_report(
                "STOP_FAILED",
                error=str(e)
            )


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    manager = ServerManager()

    started = manager.start()

    if started:

        print()
        print(
            "Server Manager is now monitoring the project."
        )

        print()
        print(
            "Press CTRL+C to stop the server."
        )

        try:

            while True:

                # Detect unexpected server shutdown

                if (
                    manager.process
                    and
                    manager.process.poll()
                    is not None
                ):

                    print()
                    print(
                        "WARNING: Server stopped unexpectedly."
                    )

                    print(
                        f"Exit code: "
                        f"{manager.process.returncode}"
                    )

                    manager.save_report(

                        "CRASHED",

                        exit_code=
                            manager.process.returncode
                    )

                    break

                time.sleep(1)

        except KeyboardInterrupt:

            print()
            print(
                "Shutdown requested."
            )

        finally:

            manager.stop()