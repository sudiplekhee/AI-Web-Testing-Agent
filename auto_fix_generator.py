import json
import os
import re
import shutil
from datetime import datetime


REPORT_FOLDER = "reports"
PROPOSED_FOLDER = "proposed_fixes"

MASTER_REPORT = os.path.join(
    REPORT_FOLDER,
    "master_report.json"
)

SOURCE_REPORT = os.path.join(
    REPORT_FOLDER,
    "source_report.json"
)

FIX_REPORT = os.path.join(
    REPORT_FOLDER,
    "fix_proposals.json"
)

OUTPUT_REPORT = os.path.join(
    REPORT_FOLDER,
    "auto_fix_report.json"
)


def load_json(path):
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


def normalize(path):
    if not path:
        return ""

    return os.path.normpath(
        path
    ).replace("\\", "/")


def read_text(path):
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


def write_text(path, content):
    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(content)


def find_source_content(
    source_report,
    source_file
):
    for item in source_report.get(
        "files",
        []
    ):

        if normalize(
            item.get("file")
        ) == normalize(
            source_file
        ):

            return item.get(
                "content",
                ""
            )

    return None


def extract_filename(url):
    if not url:
        return None

    url = url.split("?")[0]
    url = url.split("#")[0]

    return os.path.basename(url)


def find_image_url_lines(
    content,
    filename
):
    if not content or not filename:
        return []

    results = []

    for number, line in enumerate(
        content.splitlines(),
        start=1
    ):

        if filename.lower() in line.lower():

            results.append({
                "line": number,
                "content": line
            })

    return results


def find_existing_image(
    project_directory,
    filename
):
    """
    Search common locations for the missing image.
    """

    locations = [
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

    for path in locations:

        if os.path.isfile(path):

            return path

    return None


def generate_image_fix(
    project_directory,
    source_file,
    resource_url,
    source_content
):
    """
    Generate a safe image-path fix.

    Only changes the proposed copy.
    """

    filename = extract_filename(
        resource_url
    )

    if not filename:

        return {
            "status": "SKIPPED",
            "reason": (
                "Could not determine "
                "image filename."
            )
        }

    actual_image = find_existing_image(
        project_directory,
        filename
    )

    if not actual_image:

        return {
            "status": "MANUAL_REVIEW_REQUIRED",
            "filename": filename,
            "reason": (
                "The image could not be found "
                "in the common project locations. "
                "The agent will not invent a path."
            )
        }

    relative_image = os.path.relpath(
        actual_image,
        project_directory
    )

    relative_image = normalize(
        relative_image
    )

    references = find_image_url_lines(
        source_content,
        filename
    )

    if not references:

        return {
            "status": "MANUAL_REVIEW_REQUIRED",
            "filename": filename,
            "reason": (
                "Image filename was not found "
                "inside the identified source file."
            )
        }

    return {
        "status": "FIX_CANDIDATE",
        "filename": filename,
        "actual_file": relative_image,
        "references": references
    }


def create_proposed_file(
    project_directory,
    source_file,
    resource_url,
    source_content,
    patch_number
):
    """
    Create a modified COPY of the source file.

    The real project remains untouched.
    """

    filename = extract_filename(
        resource_url
    )

    if not filename:

        return {
            "status": "SKIPPED"
        }

    if not source_file:

        return {
            "status": "SKIPPED"
        }

    extension = os.path.splitext(
        source_file
    )[1].lower()

    if extension not in [
        ".html",
        ".htm"
    ]:

        return {
            "status": "MANUAL_REVIEW_REQUIRED",
            "reason": (
                "Automatic image-path correction "
                "currently supports HTML files only."
            )
        }

    image_result = generate_image_fix(
        project_directory,
        source_file,
        resource_url,
        source_content
    )

    if image_result.get(
        "status"
    ) != "FIX_CANDIDATE":

        return image_result

    actual_file = image_result[
        "actual_file"
    ]

    old_reference = resource_url

    # Determine candidate URLs.
    if actual_file.startswith(
        "static/"
    ):

        new_reference = "/" + actual_file

    elif actual_file.startswith(
        "uploads/"
    ):

        new_reference = "/" + actual_file

    else:

        new_reference = "/" + actual_file

    if old_reference == new_reference:

        return {
            "status": "NO_CHANGE",
            "reason": (
                "The proposed URL is identical "
                "to the existing URL."
            )
        }

    # Only replace the exact resource URL.
    proposed_content = source_content.replace(
        old_reference,
        new_reference
    )

    if proposed_content == source_content:

        # Try a quoted form if exact URL wasn't found.
        escaped_old = re.escape(
            old_reference
        )

        proposed_content = re.sub(
            escaped_old,
            new_reference,
            source_content
        )

    if proposed_content == source_content:

        return {
            "status": "MANUAL_REVIEW_REQUIRED",
            "reason": (
                "The exact URL could not be safely "
                "replaced."
            )
        }

    output_name = (
        f"auto_patch_{patch_number}_"
        + os.path.basename(source_file)
    )

    output_path = os.path.join(
        PROPOSED_FOLDER,
        output_name
    )

    write_text(
        output_path,
        proposed_content
    )

    return {
        "status": "PATCH_CREATED",
        "source_file": source_file,
        "original_file": os.path.join(
            project_directory,
            source_file
        ),
        "proposed_file": output_path,
        "filename": filename,
        "old_reference": old_reference,
        "new_reference": new_reference,
        "actual_file": actual_file,
        "automatic_change": True
    }


def main():

    print()
    print("=" * 60)
    print("SAFE AUTOMATIC FIX GENERATOR")
    print("=" * 60)

    master = load_json(
        MASTER_REPORT
    )

    source_report = load_json(
        SOURCE_REPORT
    )

    fix_report = load_json(
        FIX_REPORT
    )

    if not master:

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
        print(
            "Run source_code_scanner.py first."
        )
        return

    if not fix_report:

        print(
            "fix_proposals.json not found."
        )
        print(
            "Run fix_proposer.py first."
        )
        return

    project_directory = master.get(
        "project_directory"
    )

    if not project_directory:

        project_directory = source_report.get(
            "project_directory"
        )

    if not project_directory:

        print(
            "Project directory not found."
        )
        return

    os.makedirs(
        PROPOSED_FOLDER,
        exist_ok=True
    )

    proposals = fix_report.get(
        "proposals",
        []
    )

    results = []

    for number, proposal in enumerate(
        proposals,
        start=1
    ):

        print()
        print(
            f"Analyzing fix #{number}"
        )

        source_file = proposal.get(
            "source_file"
        )

        resource_url = proposal.get(
            "resource_url"
        )

        if not source_file:

            results.append({
                "fix_number": number,
                "status": (
                    "MANUAL_REVIEW_REQUIRED"
                ),
                "reason": (
                    "No source file identified."
                )
            })

            continue

        source_content = find_source_content(
            source_report,
            source_file
        )

        if source_content is None:

            results.append({
                "fix_number": number,
                "status": (
                    "MANUAL_REVIEW_REQUIRED"
                ),
                "source_file": source_file,
                "reason": (
                    "Source content not found."
                )
            })

            continue

        result = create_proposed_file(
            project_directory,
            source_file,
            resource_url,
            source_content,
            number
        )

        result["fix_number"] = number

        results.append(
            result
        )

        print(
            f"Status: {result.get('status')}"
        )

        if result.get(
            "proposed_file"
        ):

            print(
                "Proposed file:"
            )

            print(
                result[
                    "proposed_file"
                ]
            )

    created = sum(
        1
        for result in results
        if result.get(
            "status"
        ) == "PATCH_CREATED"
    )

    manual = sum(
        1
        for result in results
        if result.get(
            "status"
        ) == "MANUAL_REVIEW_REQUIRED"
    )

    skipped = sum(
        1
        for result in results
        if result.get(
            "status"
        ) in [
            "SKIPPED",
            "NO_CHANGE"
        ]
    )

    report = {

        "tool": (
            "AI Website Testing Agent"
        ),

        "generator": (
            "Safe Automatic Fix Generator"
        ),

        "generated_at": (
            datetime.now().isoformat()
        ),

        "project_directory": (
            project_directory
        ),

        "original_project_modified": False,

        "summary": {

            "fixes_analyzed": len(
                results
            ),

            "patches_created": created,

            "manual_review_required": manual,

            "skipped": skipped
        },

        "results": results
    }

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
    print("AUTOMATIC FIX GENERATION COMPLETE")
    print("=" * 60)

    print(
        f"Fixes analyzed: {len(results)}"
    )

    print(
        f"Patches created: {created}"
    )

    print(
        f"Manual review: {manual}"
    )

    print(
        f"Skipped: {skipped}"
    )

    print()
    print(
        "Original Futsal project modified: NO"
    )

    print()
    print(
        f"Report: {OUTPUT_REPORT}"
    )

    print()


if __name__ == "__main__":
    main()