import json
import os
import re
import shutil
from datetime import datetime


REPORT_FOLDER = "reports"
OUTPUT_FOLDER = "proposed_fixes"

MASTER_REPORT = os.path.join(REPORT_FOLDER, "master_report.json")
SOURCE_REPORT = os.path.join(REPORT_FOLDER, "source_report.json")
FIX_REPORT = os.path.join(REPORT_FOLDER, "fix_proposals.json")

PATCH_REPORT = os.path.join(
    REPORT_FOLDER,
    "patch_report.json"
)


def load_json(path):
    """Load a JSON file safely."""

    if not os.path.exists(path):
        print(f"File not found: {path}")
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as error:
        print(f"Could not read {path}: {error}")
        return None


def normalize_path(path):
    """Normalize Windows/Linux paths."""

    if not path:
        return ""

    return os.path.normpath(path).replace("\\", "/")


def get_project_directory():
    """Get project directory from master report."""

    master = load_json(MASTER_REPORT)

    if not master:
        return None

    return master.get("project_directory")


def get_source_file_content(source_report, file_name):
    """Find source file content inside source_report.json."""

    if not source_report:
        return None

    files = source_report.get("files", [])

    normalized_target = normalize_path(file_name)

    for item in files:

        current_file = normalize_path(
            item.get("file", "")
        )

        if current_file == normalized_target:
            return item.get("content", "")

    return None


def find_source_file(source_report, file_name):
    """Find source file metadata."""

    if not source_report:
        return None

    files = source_report.get("files", [])

    normalized_target = normalize_path(file_name)

    for item in files:

        current_file = normalize_path(
            item.get("file", "")
        )

        if current_file == normalized_target:
            return item

    return None


def extract_resource_filename(resource_url):
    """Extract filename from a resource URL."""

    if not resource_url:
        return None

    clean_url = resource_url.split("?")[0]
    clean_url = clean_url.split("#")[0]

    filename = os.path.basename(clean_url)

    return filename if filename else None


def find_references(content, filename):
    """Find lines containing a filename."""

    if not content or not filename:
        return []

    matches = []

    lines = content.splitlines()

    filename_lower = filename.lower()

    for line_number, line in enumerate(lines, start=1):

        if filename_lower in line.lower():

            matches.append({
                "line": line_number,
                "content": line.strip()
            })

    return matches


def detect_image_reference_problem(
    proposal,
    source_report
):
    """
    Create a safe patch proposal for missing images.

    IMPORTANT:
    This function does not modify the real project.
    """

    resource_url = proposal.get("resource_url")

    source_file = proposal.get("source_file")

    if not resource_url or not source_file:
        return None

    filename = extract_resource_filename(
        resource_url
    )

    if not filename:
        return None

    content = get_source_file_content(
        source_report,
        source_file
    )

    if content is None:
        return None

    references = find_references(
        content,
        filename
    )

    if not references:
        return {
            "status": "MANUAL_REVIEW_REQUIRED",
            "reason": (
                "The source file was identified, "
                "but the exact resource reference "
                "could not be located."
            ),
            "source_file": source_file,
            "resource_url": resource_url,
            "filename": filename,
            "references": []
        }

    return {
        "status": "PATCH_CANDIDATE_FOUND",
        "source_file": source_file,
        "resource_url": resource_url,
        "filename": filename,
        "references": references
    }


def create_safe_copy(
    project_directory,
    source_file,
    patch_name
):
    """
    Copy the original source file into proposed_fixes.

    The original project is never modified.
    """

    if not project_directory:
        return None

    original_path = os.path.join(
        project_directory,
        source_file
    )

    if not os.path.exists(original_path):

        return None

    output_path = os.path.join(
        OUTPUT_FOLDER,
        patch_name
    )

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )

    shutil.copy2(
        original_path,
        output_path
    )

    return output_path


def create_patch_record(
    proposal,
    source_report,
    project_directory,
    index
):

    source_file = proposal.get("source_file")

    resource_url = proposal.get("resource_url")

    if not source_file:

        return {
            "patch_number": index,
            "status": "MANUAL_REVIEW_REQUIRED",
            "reason": "No source file was identified.",
            "source_file": None,
            "resource_url": resource_url
        }

    source_metadata = find_source_file(
        source_report,
        source_file
    )

    if not source_metadata:

        return {
            "patch_number": index,
            "status": "MANUAL_REVIEW_REQUIRED",
            "reason": (
                "Source file was not found "
                "inside source_report.json."
            ),
            "source_file": source_file,
            "resource_url": resource_url
        }

    source_content = source_metadata.get(
        "content",
        ""
    )

    extension = os.path.splitext(
        source_file
    )[1].lower()

    filename = extract_resource_filename(
        resource_url
    )

    references = find_references(
        source_content,
        filename
    )

    patch_name = (
        f"patch_{index}_"
        + os.path.basename(source_file)
    )

    copied_file = create_safe_copy(
        project_directory,
        source_file,
        patch_name
    )

    if copied_file is None:

        return {
            "patch_number": index,
            "status": "MANUAL_REVIEW_REQUIRED",
            "reason": (
                "Could not create a safe copy "
                "of the source file."
            ),
            "source_file": source_file,
            "resource_url": resource_url
        }

    # --------------------------------------------------
    # IMAGE PATCH ANALYSIS
    # --------------------------------------------------

    if extension in [
        ".html",
        ".htm"
    ] and filename:

        image_result = detect_image_reference_problem(
            proposal,
            source_report
        )

        if image_result:

            return {
                "patch_number": index,
                "status": image_result.get(
                    "status",
                    "MANUAL_REVIEW_REQUIRED"
                ),
                "source_file": source_file,
                "resource_url": resource_url,
                "filename": filename,
                "original_copy": copied_file,
                "references": references,
                "recommended_change": (
                    "Review the exact image URL "
                    "and compare it with the Flask "
                    "upload/static configuration "
                    "before changing the path."
                ),
                "automatic_change": False
            }

    # --------------------------------------------------
    # PYTHON FILE
    # --------------------------------------------------

    if extension == ".py":

        return {
            "patch_number": index,
            "status": "MANUAL_REVIEW_REQUIRED",
            "source_file": source_file,
            "resource_url": resource_url,
            "original_copy": copied_file,
            "references": references,
            "recommended_change": (
                "Python/Flask code requires "
                "specific error evidence before "
                "creating an automatic modification."
            ),
            "automatic_change": False
        }

    # --------------------------------------------------
    # GENERIC SOURCE FILE
    # --------------------------------------------------

    return {
        "patch_number": index,
        "status": "MANUAL_REVIEW_REQUIRED",
        "source_file": source_file,
        "resource_url": resource_url,
        "original_copy": copied_file,
        "references": references,
        "recommended_change": (
            "Review the identified source reference "
            "before applying any code modification."
        ),
        "automatic_change": False
    }


def main():

    print()
    print("=" * 60)
    print("SAFE PATCH GENERATOR")
    print("=" * 60)

    master_report = load_json(
        MASTER_REPORT
    )

    source_report = load_json(
        SOURCE_REPORT
    )

    fix_report = load_json(
        FIX_REPORT
    )

    if not master_report:

        print()
        print(
            "master_report.json was not found."
        )
        print(
            "Run unified_report.py first."
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

    if not fix_report:

        print()
        print(
            "fix_proposals.json was not found."
        )
        print(
            "Run fix_proposer.py first."
        )
        return

    project_directory = (
        master_report.get(
            "project_directory"
        )
    )

    if not project_directory:

        project_directory = (
            master_report.get(
                "source_project"
            )
        )

    if not project_directory:

        config_path = "config.json"

        if os.path.exists(config_path):

            try:

                with open(
                    config_path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    config = json.load(file)

                project_directory = config.get(
                    "project_directory"
                )

            except Exception:
                project_directory = None

    if not project_directory:

        print()
        print(
            "Project directory could not be determined."
        )
        return

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    proposals = fix_report.get(
        "proposals",
        []
    )

    patches = []

    print()
    print(
        f"Project: {project_directory}"
    )

    print(
        f"Fix proposals: {len(proposals)}"
    )

    print()

    for index, proposal in enumerate(
        proposals,
        start=1
    ):

        print(
            f"Analyzing proposal {index}..."
        )

        patch = create_patch_record(
            proposal,
            source_report,
            project_directory,
            index
        )

        patches.append(
            patch
        )

    patch_report = {

        "tool": "AI Website Testing Agent",

        "generator": (
            "Safe Proposed Patch Generator"
        ),

        "generated_at": datetime.now().isoformat(),

        "project_directory": project_directory,

        "important_note": (
            "Original project files were not modified."
        ),

        "patches_created": len(patches),

        "patches": patches
    }

    with open(
        PATCH_REPORT,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            patch_report,
            file,
            indent=4,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print("PATCH GENERATION COMPLETE")
    print("=" * 60)

    print(
        f"Patch records: {len(patches)}"
    )

    print(
        f"Output folder: {OUTPUT_FOLDER}"
    )

    print(
        f"Report: {PATCH_REPORT}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "Your original Futsal project was NOT modified."
    )

    print()


if __name__ == "__main__":
    main()