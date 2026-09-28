import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

from playwright.sync_api import sync_playwright


REPORT_FOLDER = "reports"

AUTO_FIX_REPORT = os.path.join(
    REPORT_FOLDER,
    "auto_fix_report.json"
)

SOURCE_REPORT = os.path.join(
    REPORT_FOLDER,
    "source_report.json"
)

MASTER_REPORT = os.path.join(
    REPORT_FOLDER,
    "master_report.json"
)

CONFIG_FILE = "config.json"

PATCH_TEST_REPORT = os.path.join(
    REPORT_FOLDER,
    "patch_test_report.json"
)

PATCH_TEST_FOLDER = "patch_test_workspace"


def load_json(path):
    """Load JSON file safely."""

    if not os.path.exists(path):
        return None

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            f"Could not read {path}: {error}"
        )

        return None


def load_config():
    """Load agent configuration."""

    config = load_json(
        CONFIG_FILE
    )

    if not config:
        return {}

    return config


def read_text(path):
    """Read text file."""

    if not os.path.exists(path):
        return None

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return file.read()

    except Exception:

        return None


def get_project_directory(
    config,
    master_report,
    source_report
):
    """Find the original project directory."""

    directory = config.get(
        "project_directory"
    )

    if directory:
        return directory

    directory = master_report.get(
        "project_directory"
    )

    if directory:
        return directory

    return source_report.get(
        "project_directory"
    )


def get_website_url(config):
    """Get website URL."""

    return config.get(
        "website_url",
        "http://127.0.0.1:5000"
    )


def get_server_command(config):
    """Get Flask server command."""

    return config.get(
        "server_command",
        "python app.py"
    )


def prepare_workspace(
    project_directory,
    proposed_file
):
    """
    Create an isolated copy of the project.

    The original project is never changed.
    """

    if os.path.exists(
        PATCH_TEST_FOLDER
    ):

        shutil.rmtree(
            PATCH_TEST_FOLDER
        )

    shutil.copytree(
        project_directory,
        PATCH_TEST_FOLDER,
        ignore=shutil.ignore_patterns(
            ".git",
            "venv",
            ".venv",
            "__pycache__",
            "*.pyc"
        )
    )

    relative_source = None

    proposed_abs = os.path.abspath(
        proposed_file
    )

    source_report = load_json(
        SOURCE_REPORT
    )

    if source_report:

        for item in source_report.get(
            "files",
            []
        ):

            source_file = item.get(
                "file"
            )

            if not source_file:
                continue

            source_path = os.path.join(
                project_directory,
                source_file
            )

            if not os.path.exists(
                source_path
            ):
                continue

            # We identify the source by filename
            # from the auto-fix report later.
            pass

    return PATCH_TEST_FOLDER


def apply_proposed_file(
    workspace,
    original_project,
    source_file,
    proposed_file
):
    """
    Replace only the matching source file
    inside the isolated workspace.
    """

    workspace_file = os.path.join(
        workspace,
        source_file
    )

    if not os.path.exists(
        proposed_file
    ):

        return False, (
            "Proposed file does not exist."
        )

    if not os.path.exists(
        workspace_file
    ):

        return False, (
            "Source file does not exist "
            "inside test workspace."
        )

    shutil.copy2(
        proposed_file,
        workspace_file
    )

    return True, None


def start_server(
    project_directory,
    command
):
    """
    Start the patched Flask project.
    """

    print()
    print(
        "Starting patched website..."
    )

    try:

        process = subprocess.Popen(
            command,
            cwd=project_directory,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return process

    except Exception as error:

        print(
            f"Could not start server: {error}"
        )

        return None


def stop_server(process):

    if not process:
        return

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


def wait_for_server(
    url,
    timeout_seconds=15
):
    """
    Wait until the patched server responds.
    """

    import urllib.request

    start_time = time.time()

    while (
        time.time()
        - start_time
        < timeout_seconds
    ):

        try:

            response = urllib.request.urlopen(
                url,
                timeout=2
            )

            return True

        except Exception:

            time.sleep(0.5)

    return False


def test_patched_website(
    website_url,
    timeout=30000,
    screenshot=True
):
    """
    Run browser tests against patched website.

    This is a lightweight test focused on
    detecting HTTP/resource failures.
    """

    results = []

    screenshots_folder = os.path.join(
        REPORT_FOLDER,
        "patch_screenshots"
    )

    os.makedirs(
        screenshots_folder,
        exist_ok=True
    )

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        context = browser.new_context()

        page = context.new_page()

        console_errors = []

        network_errors = []

        page.on(
            "console",
            lambda message:
                console_errors.append(
                    {
                        "type": message.type,
                        "text": message.text
                    }
                )
                if message.type == "error"
                else None
        )

        def handle_response(response):

            if response.status >= 400:

                network_errors.append(
                    {
                        "url": response.url,
                        "status": response.status,
                        "resource_type":
                            response.request.resource_type
                    }
                )

        page.on(
            "response",
            handle_response
        )

        try:

            response = page.goto(
                website_url,
                wait_until="networkidle",
                timeout=timeout
            )

            time.sleep(1)

            http_status = (
                response.status
                if response
                else None
            )

            title = page.title()

            screenshot_path = None

            if screenshot:

                screenshot_path = os.path.join(
                    screenshots_folder,
                    "patched_homepage.png"
                )

                page.screenshot(
                    path=screenshot_path,
                    full_page=True
                )

            results.append(
                {
                    "url": website_url,
                    "http_status": http_status,
                    "title": title,
                    "console_errors":
                        console_errors,
                    "network_errors":
                        network_errors,
                    "screenshot":
                        screenshot_path
                }
            )

        except Exception as error:

            results.append(
                {
                    "url": website_url,
                    "http_status": None,
                    "title": None,
                    "console_errors":
                        console_errors,
                    "network_errors":
                        network_errors,
                    "error": str(error),
                    "screenshot": None
                }
            )

        finally:

            browser.close()

    return results


def find_patch_candidates(
    auto_fix_report
):
    """
    Return patches that were actually created.
    """

    candidates = []

    for result in auto_fix_report.get(
        "results",
        []
    ):

        if result.get(
            "status"
        ) == "PATCH_CREATED":

            candidates.append(
                result
            )

    return candidates


def main():

    print()
    print("=" * 60)
    print("PATCH TESTING ENGINE")
    print("=" * 60)

    config = load_config()

    master_report = load_json(
        MASTER_REPORT
    )

    source_report = load_json(
        SOURCE_REPORT
    )

    auto_fix_report = load_json(
        AUTO_FIX_REPORT
    )

    if not config:

        print(
            "config.json could not be loaded."
        )

        return

    if not master_report:

        print(
            "master_report.json not found."
        )

        print(
            "Run unified_report.py first."
        )

        return

    if not source_report:

        print(
            "source_report.json not found."
        )

        return

    if not auto_fix_report:

        print(
            "auto_fix_report.json not found."
        )

        print(
            "Run auto_fix_generator.py first."
        )

        return

    project_directory = (
        get_project_directory(
            config,
            master_report,
            source_report
        )
    )

    website_url = get_website_url(
        config
    )

    server_command = get_server_command(
        config
    )

    timeout = config.get(
        "timeout",
        30000
    )

    screenshot = config.get(
        "screenshot",
        True
    )

    patches = find_patch_candidates(
        auto_fix_report
    )

    print()
    print(
        f"Original project:"
    )

    print(
        project_directory
    )

    print()
    print(
        f"Patched website URL:"
    )

    print(
        website_url
    )

    print()
    print(
        f"Patch candidates: "
        f"{len(patches)}"
    )

    if not patches:

        print()
        print(
            "No automatically generated "
            "patches are available."
        )

        print()
        print(
            "Nothing will be modified."
        )

        return

    all_results = []

    for patch_number, patch in enumerate(
        patches,
        start=1
    ):

        source_file = patch.get(
            "source_file"
        )

        proposed_file = patch.get(
            "proposed_file"
        )

        print()
        print("=" * 60)

        print(
            f"TESTING PATCH #{patch_number}"
        )

        print("=" * 60)

        print(
            f"Source file: {source_file}"
        )

        print(
            f"Proposed file: {proposed_file}"
        )

        # --------------------------------------------------
        # CREATE ISOLATED WORKSPACE
        # --------------------------------------------------

        workspace = prepare_workspace(
            project_directory,
            proposed_file
        )

        print()
        print(
            f"Isolated workspace:"
        )

        print(
            os.path.abspath(workspace)
        )

        # --------------------------------------------------
        # APPLY PATCH TO COPY ONLY
        # --------------------------------------------------

        success, error = (
            apply_proposed_file(
                workspace,
                project_directory,
                source_file,
                proposed_file
            )
        )

        if not success:

            print(
                f"Could not prepare patch: {error}"
            )

            all_results.append(
                {
                    "patch_number":
                        patch_number,
                    "status":
                        "PREPARATION_FAILED",
                    "source_file":
                        source_file,
                    "error":
                        error
                }
            )

            continue

        print()
        print(
            "Patch applied to isolated "
            "workspace."
        )

        print(
            "Original project: UNTOUCHED"
        )

        # --------------------------------------------------
        # START PATCHED SERVER
        # --------------------------------------------------

        process = start_server(
            workspace,
            server_command
        )

        if not process:

            all_results.append(
                {
                    "patch_number":
                        patch_number,
                    "status":
                        "SERVER_START_FAILED",
                    "source_file":
                        source_file
                }
            )

            continue

        try:

            print(
                "Waiting for patched server..."
            )

            server_ready = wait_for_server(
                website_url,
                20
            )

            if not server_ready:

                print(
                    "Patched server did not "
                    "respond."
                )

                all_results.append(
                    {
                        "patch_number":
                            patch_number,
                        "status":
                            "SERVER_NOT_READY",
                        "source_file":
                            source_file
                    }
                )

                continue

            print(
                "Patched server is running."
            )

            # --------------------------------------------------
            # BROWSER TEST
            # --------------------------------------------------

            print()
            print(
                "Running browser test "
                "against patched website..."
            )

            browser_results = (
                test_patched_website(
                    website_url,
                    timeout,
                    screenshot
                )
            )

            all_results.append(
                {
                    "patch_number":
                        patch_number,

                    "status":
                        "TEST_COMPLETED",

                    "source_file":
                        source_file,

                    "proposed_file":
                        proposed_file,

                    "workspace":
                        os.path.abspath(
                            workspace
                        ),

                    "browser_results":
                        browser_results
                }
            )

            for result in browser_results:

                print()
                print(
                    f"URL: {result.get('url')}"
                )

                print(
                    f"HTTP status: "
                    f"{result.get('http_status')}"
                )

                print(
                    f"Console errors: "
                    f"{len(result.get('console_errors', []))}"
                )

                print(
                    f"Network errors: "
                    f"{len(result.get('network_errors', []))}"
                )

                if result.get(
                    "error"
                ):

                    print(
                        f"Browser error: "
                        f"{result.get('error')}"
                    )

        finally:

            print()
            print(
                "Stopping patched server..."
            )

            stop_server(
                process
            )

    # ------------------------------------------------------
    # BUILD REPORT
    # ------------------------------------------------------

    completed = sum(
        1
        for result in all_results
        if result.get(
            "status"
        ) == "TEST_COMPLETED"
    )

    report = {

        "tool":
            "AI Website Testing Agent",

        "tester":
            "Patched Website Testing Engine",

        "test_time":
            datetime.now().isoformat(),

        "original_project":
            project_directory,

        "original_project_modified":
            False,

        "website_url":
            website_url,

        "patches_available":
            len(patches),

        "patches_tested":
            completed,

        "results":
            all_results
    }

    with open(
        PATCH_TEST_REPORT,
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
    print("PATCH TESTING COMPLETE")
    print("=" * 60)

    print(
        f"Patches available: {len(patches)}"
    )

    print(
        f"Patches tested: {completed}"
    )

    print()
    print(
        "Original Futsal project modified: NO"
    )

    print()
    print(
        f"Report saved to:"
    )

    print(
        PATCH_TEST_REPORT
    )

    print()


if __name__ == "__main__":
    main()