import json
import os
from datetime import datetime


REPORT_FOLDER = "reports"

ORIGINAL_REPORT = os.path.join(
    REPORT_FOLDER,
    "test_report.json"
)

PATCH_REPORT = os.path.join(
    REPORT_FOLDER,
    "patch_test_report.json"
)

OUTPUT_REPORT = os.path.join(
    REPORT_FOLDER,
    "fix_verification_report.json"
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


def count_original_errors(report):
    """
    Count errors from the original browser test.
    """

    if not report:
        return 0

    summary = report.get(
        "summary",
        {}
    )

    errors = summary.get(
        "errors_found"
    )

    if isinstance(errors, int):
        return errors

    total = 0

    for page in report.get(
        "pages",
        []
    ):

        total += len(
            page.get(
                "interaction_errors",
                []
            )
        )

        if page.get("error"):
            total += 1

    return total


def count_patch_errors(report):
    """
    Count errors from the patched website.
    """

    if not report:
        return 0

    total = 0

    results = report.get(
        "results",
        []
    )

    for result in results:

        browser_results = result.get(
            "browser_results",
            []
        )

        for browser_result in browser_results:

            total += len(
                browser_result.get(
                    "console_errors",
                    []
                )
            )

            total += len(
                browser_result.get(
                    "network_errors",
                    []
                )
            )

            if browser_result.get(
                "error"
            ):

                total += 1

            status = browser_result.get(
                "http_status"
            )

            if (
                status is not None
                and status >= 400
            ):

                total += 1

    return total


def collect_original_errors(report):
    """
    Collect readable original errors.
    """

    errors = []

    if not report:
        return errors

    for page in report.get(
        "pages",
        []
    ):

        page_url = page.get(
            "url"
        )

        for error in page.get(
            "interaction_errors",
            []
        ):

            if isinstance(
                error,
                dict
            ):

                errors.append(
                    {
                        "url": page_url,
                        "type": error.get(
                            "type",
                            "Unknown"
                        ),
                        "details": error.get(
                            "details",
                            ""
                        )
                    }
                )

            else:

                errors.append(
                    {
                        "url": page_url,
                        "type": "Unknown",
                        "details": str(
                            error
                        )
                    }
                )

        if page.get("error"):

            errors.append(
                {
                    "url": page_url,
                    "type": "Page Error",
                    "details": page.get(
                        "error"
                    )
                }
            )

    return errors


def collect_patch_errors(report):
    """
    Collect readable patched errors.
    """

    errors = []

    if not report:
        return errors

    for result in report.get(
        "results",
        []
    ):

        for browser_result in result.get(
            "browser_results",
            []
        ):

            page_url = browser_result.get(
                "url"
            )

            for error in browser_result.get(
                "console_errors",
                []
            ):

                errors.append(
                    {
                        "url": page_url,
                        "type": "Console Error",
                        "details": error.get(
                            "text",
                            ""
                        )
                    }
                )

            for error in browser_result.get(
                "network_errors",
                []
            ):

                errors.append(
                    {
                        "url": page_url,
                        "type": "Network Error",
                        "details": (
                            f"{error.get('url')} "
                            f"HTTP "
                            f"{error.get('status')}"
                        )
                    }
                )

            if browser_result.get(
                "error"
            ):

                errors.append(
                    {
                        "url": page_url,
                        "type": "Browser Error",
                        "details": browser_result.get(
                            "error"
                        )
                    }
                )

            status = browser_result.get(
                "http_status"
            )

            if (
                status is not None
                and status >= 400
            ):

                errors.append(
                    {
                        "url": page_url,
                        "type": "HTTP Error",
                        "details": (
                            f"HTTP {status}"
                        )
                    }
                )

    return errors


def normalize_error_text(error):
    """
    Normalize error text for comparison.
    """

    if not error:
        return ""

    text = " ".join(
        [
            str(error.get("url", "")),
            str(error.get("type", "")),
            str(error.get("details", ""))
        ]
    )

    return (
        text
        .lower()
        .replace("\\", "/")
        .strip()
    )


def error_still_exists(
    original_error,
    patched_errors
):
    """
    Determine whether an original error
    appears to still exist.
    """

    original_text = normalize_error_text(
        original_error
    )

    if not original_text:
        return False

    # Extract useful pieces instead of requiring
    # an exact complete match.

    original_url = str(
        original_error.get(
            "url",
            ""
        )
    ).lower()

    original_details = str(
        original_error.get(
            "details",
            ""
        )
    ).lower()

    for patched_error in patched_errors:

        patched_text = normalize_error_text(
            patched_error
        )

        if (
            original_url
            and original_url in patched_text
        ):

            return True

        important_words = []

        for word in (
            original_details
            .replace(
                "/",
                " "
            )
            .replace(
                "\\",
                " "
            )
            .split()
        ):

            if len(word) >= 6:

                important_words.append(
                    word
                )

        matches = 0

        for word in important_words:

            if word in patched_text:

                matches += 1

        if (
            important_words
            and matches >= 2
        ):

            return True

    return False


def determine_status(
    original_count,
    patched_count,
    original_errors,
    patched_errors
):
    """
    Determine verification result.
    """

    if original_count == 0:

        return (
            "NO_ORIGINAL_ERRORS",
            "The original test report contains "
            "no detected errors."
        )

    if patched_count == 0:

        return (
            "FIX_VERIFIED",
            "The patched website produced "
            "no detected browser errors."
        )

    if patched_count < original_count:

        remaining = []

        for error in original_errors:

            if error_still_exists(
                error,
                patched_errors
            ):

                remaining.append(
                    error
                )

        if not remaining:

            return (
                "FIX_VERIFIED",
                "The original detected errors "
                "could not be reproduced after "
                "the proposed patch."
            )

        return (
            "FIX_PARTIALLY_IMPROVED",
            "The patched website has fewer "
            "detected errors, but some errors "
            "may still remain."
        )

    if patched_count == original_count:

        return (
            "FIX_DID_NOT_IMPROVE",
            "The number of detected errors "
            "did not decrease."
        )

    return (
        "FIX_MADE_RESULT_WORSE",
        "The patched website produced "
        "more detected errors than the "
        "original test."
    )


def main():

    print()
    print("=" * 60)
    print("FIX VERIFICATION ENGINE")
    print("=" * 60)

    original_report = load_json(
        ORIGINAL_REPORT
    )

    patch_report = load_json(
        PATCH_REPORT
    )

    if not original_report:

        print()
        print(
            "Original test_report.json "
            "was not found."
        )

        print(
            "Run agent.py first."
        )

        return

    if not patch_report:

        print()
        print(
            "patch_test_report.json "
            "was not found."
        )

        print(
            "Run patch_tester.py first."
        )

        return

    original_errors = (
        collect_original_errors(
            original_report
        )
    )

    patched_errors = (
        collect_patch_errors(
            patch_report
        )
    )

    original_count = count_original_errors(
        original_report
    )

    patched_count = count_patch_errors(
        patch_report
    )

    status, explanation = determine_status(
        original_count,
        patched_count,
        original_errors,
        patched_errors
    )

    print()
    print(
        "ORIGINAL WEBSITE"
    )

    print(
        f"Detected errors: "
        f"{original_count}"
    )

    print()
    print(
        "PATCHED WEBSITE"
    )

    print(
        f"Detected errors: "
        f"{patched_count}"
    )

    print()
    print(
        "VERIFICATION RESULT"
    )

    print(
        f"Status: {status}"
    )

    print(
        f"Explanation: {explanation}"
    )

    # --------------------------------------------------
    # Compare individual original errors
    # --------------------------------------------------

    comparisons = []

    for error in original_errors:

        still_exists = error_still_exists(
            error,
            patched_errors
        )

        comparisons.append(
            {
                "original_error": error,
                "still_detected_after_patch":
                    still_exists,

                "result": (
                    "NOT_FIXED"
                    if still_exists
                    else "NOT_REPRODUCED"
                )
            }
        )

    report = {

        "tool":
            "AI Website Testing Agent",

        "verifier":
            "Fix Verification Engine",

        "verification_time":
            datetime.now().isoformat(),

        "original_project_modified":
            False,

        "summary": {

            "original_errors":
                original_count,

            "patched_errors":
                patched_count,

            "errors_removed":
                max(
                    0,
                    original_count
                    - patched_count
                ),

            "verification_status":
                status
        },

        "explanation":
            explanation,

        "original_errors":
            original_errors,

        "patched_errors":
            patched_errors,

        "comparisons":
            comparisons
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
    print("VERIFICATION COMPLETE")
    print("=" * 60)

    print(
        f"Original errors: "
        f"{original_count}"
    )

    print(
        f"Patched errors: "
        f"{patched_count}"
    )

    print(
        f"Errors removed: "
        f"{max(0, original_count - patched_count)}"
    )

    print()
    print(
        f"RESULT: {status}"
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
        OUTPUT_REPORT
    )

    print()


if __name__ == "__main__":
    main()