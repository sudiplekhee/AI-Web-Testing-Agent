import json
import os
import difflib
from datetime import datetime


REPORT_FOLDER = "reports"

PATCH_REPORT = os.path.join(
    REPORT_FOLDER,
    "patch_report.json"
)

SOURCE_REPORT = os.path.join(
    REPORT_FOLDER,
    "source_report.json"
)

VALIDATION_REPORT = os.path.join(
    REPORT_FOLDER,
    "patch_validation_report.json"
)


def load_json(path):
    """Load JSON safely."""

    if not os.path.exists(path):
        print(f"File not found: {path}")
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


def normalize_path(path):
    """Normalize Windows paths."""

    if not path:
        return ""

    return os.path.normpath(
        path
    ).replace("\\", "/")


def get_project_directory(source_report):
    """Get original project directory."""

    if not source_report:
        return None

    return source_report.get(
        "project_directory"
    )


def get_original_file_path(
    project_directory,
    source_file
):
    """Build original source path."""

    return os.path.join(
        project_directory,
        source_file
    )


def read_file(path):
    """Read a text file."""

    if not os.path.exists(path):
        return None

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return file.read()

    except UnicodeDecodeError:

        try:

            with open(
                path,
                "r",
                encoding="utf-8-sig"
            ) as file:

                return file.read()

        except Exception:

            return None

    except Exception:

        return None


def create_diff(
    original_content,
    proposed_content,
    source_file
):
    """Create a unified diff."""

    original_lines = (
        original_content.splitlines(
            keepends=True
        )
    )

    proposed_lines = (
        proposed_content.splitlines(
            keepends=True
        )
    )

    diff = difflib.unified_diff(
        original_lines,
        proposed_lines,
        fromfile=f"original/{source_file}",
        tofile=f"proposed/{source_file}"
    )

    return "".join(diff)


def count_changes(diff):
    """Count added and removed lines."""

    added = 0
    removed = 0

    for line in diff.splitlines():

        if (
            line.startswith("+")
            and not line.startswith("+++")
        ):
            added += 1

        elif (
            line.startswith("-")
            and not line.startswith("---")
        ):
            removed += 1

    return added, removed


def validate_patch(
    patch,
    project_directory
):
    """Validate one proposed patch."""

    patch_number = patch.get(
        "patch_number"
    )

    source_file = patch.get(
        "source_file"
    )

    proposed_file = patch.get(
        "original_copy"
    )

    result = {

        "patch_number": patch_number,

        "source_file": source_file,

        "proposed_file": proposed_file,

        "status": "UNKNOWN",

        "original_exists": False,

        "proposed_exists": False,

        "files_identical": None,

        "lines_added": 0,

        "lines_removed": 0,

        "change_detected": False,

        "syntax_check": "NOT_RUN",

        "ready_for_testing": False,

        "warnings": [],

        "diff": ""
    }

    if not source_file:

        result["status"] = (
            "INVALID"
        )

        result["warnings"].append(
            "No source file was provided."
        )

        return result

    original_path = (
        get_original_file_path(
            project_directory,
            source_file
        )
    )

    if os.path.exists(original_path):

        result[
            "original_exists"
        ] = True

    else:

        result["warnings"].append(
            "Original source file does not exist."
        )

    if proposed_file and os.path.exists(
        proposed_file
    ):

        result[
            "proposed_exists"
        ] = True

    else:

        result["warnings"].append(
            "Proposed file does not exist."
        )

    if not result["original_exists"]:

        result["status"] = (
            "INVALID"
        )

        return result

    if not result["proposed_exists"]:

        result["status"] = (
            "INVALID"
        )

        return result

    original_content = read_file(
        original_path
    )

    proposed_content = read_file(
        proposed_file
    )

    if original_content is None:

        result["status"] = (
            "READ_ERROR"
        )

        result["warnings"].append(
            "Could not read original file."
        )

        return result

    if proposed_content is None:

        result["status"] = (
            "READ_ERROR"
        )

        result["warnings"].append(
            "Could not read proposed file."
        )

        return result

    result[
        "files_identical"
    ] = (
        original_content
        == proposed_content
    )

    if result["files_identical"]:

        result["status"] = (
            "NO_CHANGE"
        )

        result["warnings"].append(
            "The proposed file is identical "
            "to the original file."
        )

        return result

    diff = create_diff(
        original_content,
        proposed_content,
        source_file
    )

    result["diff"] = diff

    added, removed = count_changes(
        diff
    )

    result["lines_added"] = added

    result["lines_removed"] = removed

    result["change_detected"] = True

    extension = os.path.splitext(
        source_file
    )[1].lower()

    # --------------------------------------------------
    # PYTHON SYNTAX CHECK
    # --------------------------------------------------

    if extension == ".py":

        try:

            compile(
                proposed_content,
                proposed_file,
                "exec"
            )

            result[
                "syntax_check"
            ] = "PASSED"

        except SyntaxError as error:

            result[
                "syntax_check"
            ] = "FAILED"

            result["warnings"].append(
                f"Python syntax error: {error}"
            )

            result["status"] = (
                "INVALID"
            )

            return result

    else:

        result[
            "syntax_check"
        ] = "NOT_APPLICABLE"

    # --------------------------------------------------
    # BASIC HTML CHECK
    # --------------------------------------------------

    if extension in [
        ".html",
        ".htm"
    ]:

        lower_content = (
            proposed_content.lower()
        )

        if "<html" not in lower_content:

            result["warnings"].append(
                "No <html> tag detected."
            )

        if "</html>" not in lower_content:

            result["warnings"].append(
                "No closing </html> tag detected."
            )

    # --------------------------------------------------
    # BASIC CSS CHECK
    # --------------------------------------------------

    if extension == ".css":

        if "{" not in proposed_content:

            result["warnings"].append(
                "No CSS block detected."
            )

    # --------------------------------------------------
    # BASIC JAVASCRIPT CHECK
    # --------------------------------------------------

    if extension == ".js":

        if proposed_content.strip() == "":

            result["warnings"].append(
                "JavaScript file is empty."
            )

    result["status"] = (
        "VALIDATION_PASSED"
    )

    result[
        "ready_for_testing"
    ] = True

    return result


def print_patch_result(result):

    print()
    print("-" * 60)

    print(
        f"PATCH #{result.get('patch_number')}"
    )

    print(
        f"Source: {result.get('source_file')}"
    )

    print(
        f"Status: {result.get('status')}"
    )

    print(
        f"Original exists: "
        f"{result.get('original_exists')}"
    )

    print(
        f"Proposed exists: "
        f"{result.get('proposed_exists')}"
    )

    print(
        f"Change detected: "
        f"{result.get('change_detected')}"
    )

    print(
        f"Lines added: "
        f"{result.get('lines_added')}"
    )

    print(
        f"Lines removed: "
        f"{result.get('lines_removed')}"
    )

    print(
        f"Syntax check: "
        f"{result.get('syntax_check')}"
    )

    print(
        f"Ready for testing: "
        f"{result.get('ready_for_testing')}"
    )

    warnings = result.get(
        "warnings",
        []
    )

    if warnings:

        print()
        print("Warnings:")

        for warning in warnings:

            print(
                f"  - {warning}"
            )


def main():

    print()
    print("=" * 60)
    print("PROPOSED PATCH VALIDATOR")
    print("=" * 60)

    patch_report = load_json(
        PATCH_REPORT
    )

    source_report = load_json(
        SOURCE_REPORT
    )

    if not patch_report:

        print()
        print(
            "patch_report.json was not found."
        )

        print(
            "Run patch_generator.py first."
        )

        return

    if not source_report:

        print()
        print(
            "source_report.json was not found."
        )

        print(
            "Run source_code_scanner.py first."
        )

        return

    project_directory = (
        get_project_directory(
            source_report
        )
    )

    if not project_directory:

        print()
        print(
            "Project directory could not "
            "be determined."
        )

        return

    patches = patch_report.get(
        "patches",
        []
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
        f"Patches to validate: "
        f"{len(patches)}"
    )

    results = []

    for patch in patches:

        result = validate_patch(
            patch,
            project_directory
        )

        results.append(
            result
        )

        print_patch_result(
            result
        )

    valid_count = sum(
        1
        for result in results
        if result.get("status")
        == "VALIDATION_PASSED"
    )

    invalid_count = sum(
        1
        for result in results
        if result.get("status")
        == "INVALID"
    )

    no_change_count = sum(
        1
        for result in results
        if result.get("status")
        == "NO_CHANGE"
    )

    validation_report = {

        "tool": (
            "AI Website Testing Agent"
        ),

        "validator": (
            "Proposed Patch Validator"
        ),

        "validation_time": (
            datetime.now().isoformat()
        ),

        "project_directory": (
            project_directory
        ),

        "original_project_modified": False,

        "summary": {

            "patches_checked": (
                len(results)
            ),

            "valid_patches": (
                valid_count
            ),

            "invalid_patches": (
                invalid_count
            ),

            "unchanged_patches": (
                no_change_count
            )
        },

        "patches": results
    }

    with open(
        VALIDATION_REPORT,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            validation_report,
            file,
            indent=4,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)

    print(
        f"Patches checked: {len(results)}"
    )

    print(
        f"Valid patches: {valid_count}"
    )

    print(
        f"Invalid patches: {invalid_count}"
    )

    print(
        f"Unchanged patches: {no_change_count}"
    )

    print()
    print(
        "Original project modified: NO"
    )

    print()
    print(
        f"Report saved to:"
    )

    print(
        VALIDATION_REPORT
    )

    print()


if __name__ == "__main__":
    main()