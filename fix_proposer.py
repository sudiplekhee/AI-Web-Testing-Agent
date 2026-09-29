
import json
import os
from datetime import datetime

TEST_REPORT = "reports/test_report.json"
ERROR_MAP = "reports/error_source_map.json"
SERVER_REPORT = "reports/server_error_report.json"
OUTPUT_FILE = "reports/fix_proposals.json"


def load_json(path):
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Could not read {path}: {e}")
        return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


# ============================================================
# RESOURCE ERROR HELPERS
# ============================================================

def is_real_resource_error(mapping):
    """
    Ignore page URLs such as:
        http://127.0.0.1:5000
        http://127.0.0.1:5000/grounds

    Keep actual resources such as:
        /uploads/image.jpg
        /static/style.css
        /static/app.js
    """

    resource_url = str(
        mapping.get("resource_url", "")
    ).lower()

    filename = str(
        mapping.get("resource_filename", "")
    ).lower()

    resource_type = str(
        mapping.get("resource_type", "")
    ).lower()

    details = str(
        mapping.get("details", "")
    ).lower()

    # Real resource indicators
    resource_extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".css",
        ".js",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".mp4",
        ".pdf"
    )

    if filename.endswith(resource_extensions):
        return True

    if resource_type in (
        "image",
        "stylesheet",
        "script",
        "font",
        "media",
        "document"
    ):
        return True

    if "/uploads/" in resource_url:
        return True

    if "/static/" in resource_url:
        return True

    if "failed to load resource" in details:
        return True

    if "http 404" in details and (
        "/uploads/" in resource_url
        or "/static/" in resource_url
    ):
        return True

    return False


def normalize_mapping(mapping):

    best_source = mapping.get(
        "best_source",
        {}
    )

    return {
        "resource_url": mapping.get(
            "resource_url",
            ""
        ),

        "filename": mapping.get(
            "resource_filename",
            ""
        ),

        "resource_type": mapping.get(
            "resource_type",
            ""
        ),

        "source_page": mapping.get(
            "source_page",
            ""
        ),

        "error_type": mapping.get(
            "error_type",
            ""
        ),

        "details": mapping.get(
            "details",
            ""
        ),

        "existing_file": mapping.get(
            "existing_file",
            ""
        ),

        "source_file": best_source.get(
            "file",
            ""
        ),

        "source_line": best_source.get(
            "line",
            ""
        ),

        "source_code": best_source.get(
            "code",
            ""
        ),

        "match_type": best_source.get(
            "match_type",
            ""
        ),

        "confidence": best_source.get(
            "confidence",
            0
        ),

        "reason": best_source.get(
            "reason",
            ""
        )
    }


# ============================================================
# IMAGE PROPOSAL
# ============================================================

def create_image_proposal(mapping, bug_number):

    filename = mapping["filename"]

    return {
        "bug_id": bug_number,

        "category": "missing_image",

        "error_type": mapping["error_type"] or "HTTP 404",

        "resource_url": mapping["resource_url"],

        "filename": filename,

        "source_file": mapping["source_file"],

        "source_line": mapping["source_line"],

        "source_code": mapping["source_code"],

        "confidence": mapping["confidence"],

        "automatic_patch": False,

        "status": "MANUAL_REVIEW_REQUIRED",

        "root_cause": (
            f"The browser requested '{filename}', "
            "but the Flask server returned HTTP 404."
        ),

        "recommended_checks": [
            f"Check whether '{filename}' exists in the upload directory.",

            "Check the UPLOAD_FOLDER configuration in app.py.",

            "Check the uploaded_file route in app.py.",

            f"Check the database value for the image '{filename}'.",

            "Check whether the image was deleted or moved.",

            "Check whether the database points to an old filename."
        ],

        "suggested_fix": (
            "Verify the physical image file, database filename, "
            "UPLOAD_FOLDER configuration, and uploaded_file route "
            "before modifying the HTML template."
        )
    }


# ============================================================
# OTHER RESOURCE PROPOSAL
# ============================================================

def create_resource_proposal(mapping, bug_number):

    return {
        "bug_id": bug_number,

        "category": "missing_static_resource",

        "error_type": mapping["error_type"] or "HTTP 404",

        "resource_url": mapping["resource_url"],

        "filename": mapping["filename"],

        "source_file": mapping["source_file"],

        "source_line": mapping["source_line"],

        "source_code": mapping["source_code"],

        "confidence": mapping["confidence"],

        "automatic_patch": False,

        "status": "MANUAL_REVIEW_REQUIRED",

        "root_cause": (
            "The browser requested a static resource "
            "that the server could not find."
        ),

        "recommended_checks": [
            "Check whether the file exists.",
            "Check the generated URL.",
            "Check the Flask static directory.",
            "Check filename spelling.",
            "Check filename capitalization."
        ]
    }


# ============================================================
# SERVER TRACEBACK ANALYSIS
# ============================================================

def get_server_traceback(server_report):

    traceback_analysis = server_report.get(
        "traceback_analysis",
        {}
    )

    exception_type = traceback_analysis.get(
        "exception_type",
        ""
    )

    source_locations = traceback_analysis.get(
        "source_locations",
        []
    )

    traceback_lines = traceback_analysis.get(
        "traceback",
        []
    )

    return (
        exception_type,
        source_locations,
        traceback_lines
    )


def find_missing_module(traceback_lines):

    for line in traceback_lines:

        if "ModuleNotFoundError" in line:

            # Example:
            # ModuleNotFoundError: No module named 'flask_wtf'

            marker = "No module named"

            if marker in line:

                module_name = line.split(
                    marker,
                    1
                )[1].strip()

                module_name = module_name.strip(
                    "'\""
                )

                return module_name

    return ""


def create_server_proposals(server_report, start_bug_number):

    proposals = []

    (
        exception_type,
        source_locations,
        traceback_lines
    ) = get_server_traceback(server_report)

    # --------------------------------------------------------
    # Find primary source location
    # --------------------------------------------------------

    source_file = ""
    source_line = ""

    if source_locations:

        first_location = source_locations[0]

        source_file = first_location.get(
            "file",
            ""
        )

        source_line = first_location.get(
            "line",
            ""
        )

    # --------------------------------------------------------
    # Complete traceback
    # --------------------------------------------------------

    traceback_text = "\n".join(
        traceback_lines
    )

    # --------------------------------------------------------
    # Missing module
    # --------------------------------------------------------

    missing_module = find_missing_module(
        traceback_lines
    )

    if missing_module:

        proposal = {
            "bug_id": start_bug_number,

            "category": "missing_python_dependency",

            "error_type": exception_type,

            "source_file": source_file,

            "source_line": source_line,

            "module": missing_module,

            "traceback": traceback_lines,

            "automatic_patch": False,

            "status": "MANUAL_REVIEW_REQUIRED",

            "root_cause": (
                f"The Python application imports "
                f"'{missing_module}', but that package "
                "is not installed in the active environment."
            ),

            "failing_code": (
                "from flask_wtf.csrf import CSRFProtect"
            ),

            "recommended_fix": (
                f"Install the missing package '{missing_module}' "
                "inside the project's virtual environment."
            ),

            "recommended_commands": [
                f"pip install {missing_module}",
                "pip freeze > requirements.txt"
            ],

            "safety_note": (
                "The testing agent should not automatically "
                "install packages or modify requirements.txt "
                "without explicit approval."
            )
        }

        proposals.append(
            proposal
        )

        start_bug_number += 1

        return proposals

    # --------------------------------------------------------
    # Other server errors
    # --------------------------------------------------------

    category = "server_error"

    recommended_fix = (
        "Inspect the traceback and identify the exact "
        "failing Python operation."
    )

    if "TemplateNotFound" in traceback_text:

        category = "missing_template"

        recommended_fix = (
            "Check that the required HTML template exists "
            "inside the templates directory."
        )

    elif "UndefinedError" in traceback_text:

        category = "jinja_template_error"

        recommended_fix = (
            "Check the Jinja template variable and the "
            "Python value passed to the template."
        )

    elif "TypeError" in traceback_text:

        category = "python_type_error"

        recommended_fix = (
            "Inspect the failing line and verify the types "
            "of the variables being used."
        )

    elif "IndentationError" in traceback_text:

        category = "python_indentation_error"

        recommended_fix = (
            "Fix the Python indentation around the reported "
            "line."
        )

    elif "SyntaxError" in traceback_text:

        category = "python_syntax_error"

        recommended_fix = (
            "Fix the Python syntax around the reported line."
        )

    elif (
        "sqlite3" in traceback_text
        or "OperationalError" in traceback_text
    ):

        category = "database_error"

        recommended_fix = (
            "Check the SQLite database connection, table, "
            "SQL query, and database structure."
        )

    proposal = {
        "bug_id": start_bug_number,

        "category": category,

        "error_type": exception_type or "Python/Flask Error",

        "source_file": source_file,

        "source_line": source_line,

        "traceback": traceback_lines,

        "automatic_patch": False,

        "status": "MANUAL_REVIEW_REQUIRED",

        "root_cause": (
            "The Flask application produced a server-side "
            "Python error."
        ),

        "recommended_fix": recommended_fix
    }

    proposals.append(
        proposal
    )

    return proposals


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("INTELLIGENT FIX PROPOSAL GENERATOR")
    print("=" * 60)

    test_report = load_json(
        TEST_REPORT
    )

    error_map = load_json(
        ERROR_MAP
    )

    server_report = load_json(
        SERVER_REPORT
    )

    proposals = []

    # ========================================================
    # RESOURCE ERRORS
    # ========================================================

    mappings = error_map.get(
        "mappings",
        []
    )

    real_mappings = []

    seen_urls = set()

    for mapping in mappings:

        if not isinstance(mapping, dict):
            continue

        if not is_real_resource_error(
            mapping
        ):
            continue

        normalized = normalize_mapping(
            mapping
        )

        url = normalized["resource_url"]

        if url in seen_urls:
            continue

        seen_urls.add(url)

        real_mappings.append(
            normalized
        )

    print()
    print(
        f"Real browser/resource errors found: "
        f"{len(real_mappings)}"
    )

    bug_number = 1

    for mapping in real_mappings:

        print()
        print(
            f"Analyzing resource error "
            f"{bug_number}"
        )

        print(
            f"Resource:   "
            f"{mapping['resource_url']}"
        )

        print(
            f"Filename:   "
            f"{mapping['filename']}"
        )

        print(
            f"Source:     "
            f"{mapping['source_file'] or 'NOT FOUND'}"
        )

        print(
            f"Line:       "
            f"{mapping['source_line'] or 'NOT FOUND'}"
        )

        print(
            f"Confidence: "
            f"{mapping['confidence']}"
        )

        resource_type = (
            mapping["resource_type"]
            .lower()
        )

        filename = (
            mapping["filename"]
            .lower()
        )

        if (
            resource_type == "image"
            or filename.endswith(
                (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                    ".webp",
                    ".svg"
                )
            )
        ):

            proposal = create_image_proposal(
                mapping,
                bug_number
            )

        else:

            proposal = create_resource_proposal(
                mapping,
                bug_number
            )

        proposals.append(
            proposal
        )

        bug_number += 1

    # ========================================================
    # SERVER ERRORS
    # ========================================================

    server_errors_count = server_report.get(
        "errors_found",
        0
    )

    print()
    print(
        f"Server errors found: "
        f"{server_errors_count}"
    )

    server_proposals = create_server_proposals(
        server_report,
        bug_number
    )

    for proposal in server_proposals:

        print()
        print(
            f"Analyzing server error "
            f"{proposal['bug_id']}"
        )

        print(
            f"Type:       "
            f"{proposal['error_type']}"
        )

        print(
            f"Source:     "
            f"{proposal['source_file'] or 'NOT FOUND'}"
        )

        print(
            f"Line:       "
            f"{proposal['source_line'] or 'NOT FOUND'}"
        )

        if proposal.get("module"):

            print(
                f"Module:     "
                f"{proposal['module']}"
            )

        proposals.append(
            proposal
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    automatic_patches = [
        proposal
        for proposal in proposals
        if proposal.get(
            "automatic_patch"
        ) is True
    ]

    manual_review = [
        proposal
        for proposal in proposals
        if proposal.get(
            "status"
        ) == "MANUAL_REVIEW_REQUIRED"
    ]

    output = {

        "generated_at":
            datetime.now().isoformat(),

        "project":
            test_report.get(
                "website",
                "Unknown"
            ),

        "summary": {

            "errors_analyzed":
                len(proposals),

            "automatic_patches":
                len(automatic_patches),

            "manual_review_required":
                len(manual_review)
        },

        "proposals":
            proposals
    }

    save_json(
        OUTPUT_FILE,
        output
    )

    print()
    print("=" * 60)
    print("FIX PROPOSAL GENERATION COMPLETE")
    print("=" * 60)

    print(
        f"Errors analyzed:          "
        f"{len(proposals)}"
    )

    print(
        f"Automatic patches:        "
        f"{len(automatic_patches)}"
    )

    print(
        f"Manual review required:   "
        f"{len(manual_review)}"
    )

    print()
    print(
        f"Report: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()

