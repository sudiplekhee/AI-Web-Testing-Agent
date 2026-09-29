import os
import json
from datetime import datetime


TEST_REPORT = "reports/test_report.json"
SOURCE_REPORT = "reports/source_report.json"
OUTPUT_REPORT = "reports/error_source_map.json"


def load_json(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not read {path}: {e}")
        return None


def save_json(path, data):
    folder = os.path.dirname(path)

    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def normalize(value):
    if value is None:
        return ""

    return str(value).replace("\\", "/").lower()


# ============================================================
# EXTRACT ALL RESOURCE ERRORS
# ============================================================

def extract_resource_errors(test_report):

    errors = []
    seen = set()

    def add_error(source_page, error):

        if not isinstance(error, dict):
            return

        details = error.get("details", {})

        if not isinstance(details, dict):
            return

        # --------------------------------------------
        # Possible resource URL
        # --------------------------------------------

        resource_url = details.get("url")

        if not resource_url:
            resource_url = error.get("url")

        if not resource_url:
            return

        # --------------------------------------------
        # Resource type
        # --------------------------------------------

        inner_type = details.get(
            "type",
            error.get("type", "")
        )

        resource_type = details.get(
            "resource_type",
            ""
        )

        details_text = str(
            details
        ).lower()

        error_text = str(
            error
        ).lower()

        # --------------------------------------------
        # Determine whether this is a resource error
        # --------------------------------------------

        is_resource_error = False

        if inner_type in [
            "HTTP Resource Error",
            "Network Request Failed"
        ]:
            is_resource_error = True

        if resource_type:
            is_resource_error = True

        if "http 404" in details_text:
            is_resource_error = True

        if "resource error" in error_text:
            is_resource_error = True

        if "failed to load resource" in details_text:
            is_resource_error = True

        if not is_resource_error:
            return

        key = (
            str(source_page),
            str(resource_url),
            str(resource_type)
        )

        if key in seen:
            return

        seen.add(key)

        errors.append({
            "source_page": source_page,
            "error_type": inner_type,
            "resource_url": resource_url,
            "resource_type": resource_type,
            "details": details
        })

    # ========================================================
    # METHOD 1 — PAGE RESULTS
    # ========================================================

    pages = test_report.get(
        "pages",
        []
    )

    if isinstance(pages, list):

        for page in pages:

            if not isinstance(page, dict):
                continue

            source_page = page.get(
                "url",
                ""
            )

            interaction_errors = page.get(
                "interaction_errors",
                []
            )

            if isinstance(
                interaction_errors,
                list
            ):

                for error in interaction_errors:

                    add_error(
                        source_page,
                        error
                    )

    # ========================================================
    # METHOD 2 — TOP LEVEL ERRORS
    # ========================================================

    top_errors = test_report.get(
        "errors",
        []
    )

    if isinstance(
        top_errors,
        list
    ):

        for error in top_errors:

            if not isinstance(
                error,
                dict
            ):
                continue

            source_page = (
                error.get("source_page")
                or error.get("url")
                or ""
            )

            add_error(
                source_page,
                error
            )

    return errors


# ============================================================
# FILENAME
# ============================================================

def extract_filename(url):

    if not url:
        return None

    clean = str(url)

    clean = clean.split("?")[0]
    clean = clean.split("#")[0]

    filename = clean.rstrip(
        "/"
    ).split("/")[-1]

    return filename or None


# ============================================================
# EXACT SOURCE MATCH
# ============================================================

def find_exact_matches(
    source_files,
    resource_url,
    filename
):

    matches = []

    url_normalized = normalize(
        resource_url
    )

    filename_normalized = normalize(
        filename
    )

    for source in source_files:

        file_path = source.get(
            "file",
            ""
        )

        content = source.get(
            "content",
            ""
        )

        if not content:
            continue

        lines = content.splitlines()

        for line_number, line in enumerate(
            lines,
            start=1
        ):

            line_normalized = normalize(
                line
            )

            # ----------------------------------------
            # Exact URL
            # ----------------------------------------

            if (
                url_normalized
                and url_normalized in line_normalized
            ):

                matches.append({
                    "file": file_path,
                    "line": line_number,
                    "code": line.strip(),
                    "match_type": "exact_url",
                    "confidence": 100
                })

                continue

            # ----------------------------------------
            # Exact filename
            # ----------------------------------------

            if (
                filename_normalized
                and filename_normalized in line_normalized
            ):

                matches.append({
                    "file": file_path,
                    "line": line_number,
                    "code": line.strip(),
                    "match_type": "exact_filename",
                    "confidence": 95
                })

    return matches


# ============================================================
# DYNAMIC IMAGE REFERENCES
# ============================================================

def find_dynamic_image_matches(source_files):

    matches = []

    for source in source_files:

        file_path = source.get(
            "file",
            ""
        )

        content = source.get(
            "content",
            ""
        )

        normalized_path = normalize(
            file_path
        )

        if not (
            normalized_path.endswith(".html")
            or normalized_path.endswith(".htm")
        ):
            continue

        lines = content.splitlines()

        for line_number, line in enumerate(
            lines,
            start=1
        ):

            lower = line.lower()

            # <img ...>
            if "<img" in lower:

                matches.append({
                    "file": file_path,
                    "line": line_number,
                    "code": line.strip(),
                    "match_type": "html_image_tag",
                    "confidence": 80
                })

                continue

            # url_for + image/upload
            if (
                "url_for" in lower
                and (
                    "upload" in lower
                    or "image" in lower
                )
            ):

                matches.append({
                    "file": file_path,
                    "line": line_number,
                    "code": line.strip(),
                    "match_type": "dynamic_upload_url",
                    "confidence": 78
                })

                continue

            # upload path
            if (
                "/uploads/" in lower
                or "uploads/" in lower
            ):

                matches.append({
                    "file": file_path,
                    "line": line_number,
                    "code": line.strip(),
                    "match_type": "upload_path",
                    "confidence": 76
                })

                continue

            # image variable
            if (
                ".image" in lower
                or "image" in lower
            ):

                if "src" in lower:

                    matches.append({
                        "file": file_path,
                        "line": line_number,
                        "code": line.strip(),
                        "match_type": "image_variable",
                        "confidence": 70
                    })

    return matches


# ============================================================
# EXISTING FILE
# ============================================================

def find_existing_file(
    project_directory,
    filename
):

    if not project_directory or not filename:
        return None

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

        if os.path.exists(path):
            return path

    return None


# ============================================================
# MAP ONE ERROR
# ============================================================

def map_error(
    error,
    source_files,
    project_directory
):

    resource_url = error.get(
        "resource_url"
    )

    filename = extract_filename(
        resource_url
    )

    resource_type = error.get(
        "resource_type",
        ""
    )

    result = {
        "source_page": error.get(
            "source_page"
        ),
        "error_type": error.get(
            "error_type"
        ),
        "resource_url": resource_url,
        "resource_filename": filename,
        "resource_type": resource_type,
        "existing_file": find_existing_file(
            project_directory,
            filename
        ),
        "exact_matches": [],
        "dynamic_matches": [],
        "best_source": None
    }

    # Exact matching
    exact_matches = find_exact_matches(
        source_files,
        resource_url,
        filename
    )

    result["exact_matches"] = exact_matches

    candidates = list(
        exact_matches
    )

    # Dynamic image matching
    if resource_type == "image":

        dynamic_matches = find_dynamic_image_matches(
            source_files
        )

        result["dynamic_matches"] = (
            dynamic_matches
        )

        candidates.extend(
            dynamic_matches
        )

    candidates.sort(
        key=lambda item: item.get(
            "confidence",
            0
        ),
        reverse=True
    )

    if candidates:

        best = candidates[0]

        result["best_source"] = {
            "file": best["file"],
            "line": best["line"],
            "code": best["code"],
            "match_type": best["match_type"],
            "confidence": best["confidence"]
        }

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("SMART ERROR SOURCE MAPPER")
    print("=" * 60)
    print()

    test_report = load_json(
        TEST_REPORT
    )

    source_report = load_json(
        SOURCE_REPORT
    )

    if test_report is None:
        print(
            "test_report.json was not found."
        )
        return

    if source_report is None:
        print(
            "source_report.json was not found."
        )
        return

    source_files = source_report.get(
        "files",
        []
    )

    project_directory = source_report.get(
        "project_directory"
    )

    errors = extract_resource_errors(
        test_report
    )

    print(
        f"Resource errors found: {len(errors)}"
    )

    mappings = []

    for index, error in enumerate(
        errors,
        start=1
    ):

        print()
        print(
            f"Analyzing resource error {index}"
        )

        mapping = map_error(
            error,
            source_files,
            project_directory
        )

        mappings.append(
            mapping
        )

        print(
            f"Resource: "
            f"{mapping['resource_url']}"
        )

        best = mapping.get(
            "best_source"
        )

        if best:

            print(
                f"Source:   {best['file']}"
            )

            print(
                f"Line:     {best['line']}"
            )

            print(
                f"Match:    {best['match_type']}"
            )

            print(
                f"Confidence: {best['confidence']}"
            )

            print(
                f"Code:     {best['code']}"
            )

        else:

            print(
                "Source: NOT FOUND"
            )

        if mapping.get(
            "existing_file"
        ):

            print(
                "File exists: "
                f"{mapping['existing_file']}"
            )

        else:

            print(
                "File exists: NO"
            )

    report = {
        "tool": "AI Website Testing Agent",
        "report_type": "Smart Error Source Mapping",
        "generated_at": datetime.now().isoformat(),
        "errors_analyzed": len(errors),
        "mappings": mappings
    }

    save_json(
        OUTPUT_REPORT,
        report
    )

    print()
    print("=" * 60)
    print("MAPPING COMPLETE")
    print("=" * 60)
    print()

    print(
        f"Report: {OUTPUT_REPORT}"
    )


if __name__ == "__main__":
    main()