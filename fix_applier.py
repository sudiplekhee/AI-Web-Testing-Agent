import os
import json
import shutil
import difflib
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

REPORT_FOLDER = "reports"

AUTO_FIX_REPORT = os.path.join(
    REPORT_FOLDER,
    "auto_fix_report.json"
)

MASTER_REPORT = os.path.join(
    REPORT_FOLDER,
    "master_report.json"
)

CONFIG_FILE = "config.json"

BACKUP_FOLDER = "backups"

APPLY_REPORT = os.path.join(
    REPORT_FOLDER,
    "fix_apply_report.json"
)


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"Could not read {path}: {e}")
        return None


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def load_config():
    config = load_json(CONFIG_FILE)

    if config is None:
        print("config.json was not found.")
        return {}

    return config


def get_project_directory(config):
    project_directory = config.get(
        "project_directory"
    )

    if not project_directory:
        return None

    return os.path.abspath(
        project_directory
    )


def normalize_path(path):
    if not path:
        return None

    return os.path.normpath(
        os.path.abspath(path)
    )


def get_timestamp():
    return datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


# ============================================================
# FIND AUTOMATIC PATCHES
# ============================================================

def find_patch_candidates(auto_fix_report):
    candidates = []

    if not auto_fix_report:
        return candidates

    fixes = auto_fix_report.get(
        "fixes",
        auto_fix_report.get(
            "patches",
            []
        )
    )

    if not isinstance(fixes, list):
        return candidates

    for index, fix in enumerate(fixes, start=1):

        if not isinstance(fix, dict):
            continue

        status = str(
            fix.get("status", "")
        ).upper()

        if status == "PATCH_CREATED":

            candidates.append({
                "id": index,
                "data": fix
            })

    return candidates


# ============================================================
# EXTRACT PATCH PATHS
# ============================================================

def get_original_file(fix):
    possible_keys = [
        "original_file",
        "source_file",
        "target_file",
        "file"
    ]

    for key in possible_keys:
        value = fix.get(key)

        if value:
            return value

    return None


def get_patch_file(fix):
    possible_keys = [
        "patch_file",
        "proposed_file",
        "patched_file",
        "output_file"
    ]

    for key in possible_keys:
        value = fix.get(key)

        if value:
            return value

    return None


# ============================================================
# SAFETY CHECK
# ============================================================

def is_inside_project(file_path, project_directory):
    try:

        file_path = normalize_path(file_path)
        project_directory = normalize_path(
            project_directory
        )

        common = os.path.commonpath([
            file_path,
            project_directory
        ])

        return common == project_directory

    except Exception:
        return False


def resolve_project_file(path, project_directory):
    if not path:
        return None

    path = os.path.expandvars(path)

    if os.path.isabs(path):
        return normalize_path(path)

    return normalize_path(
        os.path.join(
            project_directory,
            path
        )
    )


# ============================================================
# SHOW PATCH DIFF
# ============================================================

def show_diff(original_file, patch_file):

    if not os.path.exists(original_file):
        print(
            f"Original file does not exist:\n"
            f"{original_file}"
        )
        return False

    if not os.path.exists(patch_file):
        print(
            f"Patch file does not exist:\n"
            f"{patch_file}"
        )
        return False

    try:

        with open(
            original_file,
            "r",
            encoding="utf-8"
        ) as f:
            original = f.readlines()

        with open(
            patch_file,
            "r",
            encoding="utf-8"
        ) as f:
            patched = f.readlines()

    except Exception as e:

        print(
            f"Could not read patch files: {e}"
        )

        return False

    diff = list(
        difflib.unified_diff(
            original,
            patched,
            fromfile="ORIGINAL",
            tofile="PROPOSED",
            lineterm=""
        )
    )

    print()
    print("=" * 60)
    print("PROPOSED CHANGE")
    print("=" * 60)

    if not diff:
        print("No changes detected.")
        return False

    for line in diff:
        print(line)

    print("=" * 60)

    return True


# ============================================================
# CREATE BACKUP
# ============================================================

def create_backup(
    original_file,
    project_directory
):

    timestamp = get_timestamp()

    backup_root = os.path.join(
        BACKUP_FOLDER,
        timestamp
    )

    os.makedirs(
        backup_root,
        exist_ok=True
    )

    relative_path = os.path.relpath(
        original_file,
        project_directory
    )

    backup_file = os.path.join(
        backup_root,
        relative_path
    )

    os.makedirs(
        os.path.dirname(backup_file),
        exist_ok=True
    )

    shutil.copy2(
        original_file,
        backup_file
    )

    return backup_file


# ============================================================
# APPLY PATCH
# ============================================================

def apply_patch(
    original_file,
    patch_file
):

    shutil.copy2(
        patch_file,
        original_file
    )


# ============================================================
# RESTORE BACKUP
# ============================================================

def restore_backup(
    original_file,
    backup_file
):

    if not os.path.exists(backup_file):
        print(
            "Backup file was not found."
        )
        return False

    shutil.copy2(
        backup_file,
        original_file
    )

    return True


# ============================================================
# VERIFY FILE AFTER APPLY
# ============================================================

def verify_applied_file(
    original_file,
    patch_file
):

    try:

        with open(
            original_file,
            "rb"
        ) as f:
            applied_data = f.read()

        with open(
            patch_file,
            "rb"
        ) as f:
            patch_data = f.read()

        return applied_data == patch_data

    except Exception:
        return False


# ============================================================
# BUILD REPORT
# ============================================================

def build_report():

    return {
        "agent": "AI Website Testing Agent",
        "report_type": "Safe Fix Apply Report",
        "generated_at": datetime.now().isoformat(),
        "status": "NOTHING_APPLIED",
        "approved": False,
        "modified_files": [],
        "backup_files": [],
        "message": ""
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("SAFE FIX APPLY ENGINE")
    print("=" * 60)
    print()

    report = build_report()

    config = load_config()

    project_directory = get_project_directory(
        config
    )

    if not project_directory:

        print(
            "project_directory is missing "
            "from config.json."
        )

        report["status"] = "ERROR"
        report["message"] = (
            "project_directory is missing."
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    print(
        "Project:"
    )
    print(project_directory)
    print()

    if not os.path.exists(
        project_directory
    ):

        print(
            "Project directory does not exist."
        )

        report["status"] = "ERROR"
        report["message"] = (
            "Project directory does not exist."
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    auto_fix_report = load_json(
        AUTO_FIX_REPORT
    )

    if auto_fix_report is None:

        print(
            "auto_fix_report.json was not found."
        )

        print()
        print(
            "Run auto_fix_generator.py first."
        )

        report["status"] = "NO_PATCH_REPORT"
        report["message"] = (
            "auto_fix_report.json was not found."
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    candidates = find_patch_candidates(
        auto_fix_report
    )

    print(
        f"Automatic patch candidates: "
        f"{len(candidates)}"
    )
    print()

    if not candidates:

        print("=" * 60)
        print("NO SAFE AUTOMATIC PATCHES")
        print("=" * 60)
        print()

        print(
            "There are currently no "
            "PATCH_CREATED changes."
        )

        print()
        print(
            "No files will be modified."
        )

        report["status"] = (
            "NO_AUTOMATIC_PATCHES"
        )

        report["message"] = (
            "No automatically generated "
            "patches are available."
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    # --------------------------------------------------------
    # SHOW AVAILABLE PATCHES
    # --------------------------------------------------------

    for candidate in candidates:

        fix_id = candidate["id"]
        fix = candidate["data"]

        original_file = get_original_file(
            fix
        )

        patch_file = get_patch_file(
            fix
        )

        print(
            f"[{fix_id}] "
            f"{original_file}"
        )

        print(
            f"    Patch: {patch_file}"
        )

        print()

    print(
        "IMPORTANT:"
    )

    print(
        "Only an explicitly approved patch "
        "can be applied."
    )

    print(
        "Manual-review proposals are NOT "
        "eligible for automatic application."
    )

    print()

    # --------------------------------------------------------
    # USER APPROVAL
    # --------------------------------------------------------

    choice = input(
        "Enter patch number to approve "
        "(or press Enter to cancel): "
    ).strip()

    if not choice:

        print()
        print(
            "No approval given."
        )

        print(
            "Nothing was modified."
        )

        report["status"] = (
            "APPROVAL_CANCELLED"
        )

        report["message"] = (
            "User did not approve a patch."
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    try:
        selected_id = int(choice)

    except ValueError:

        print()
        print(
            "Invalid patch number."
        )

        print(
            "Nothing was modified."
        )

        report["status"] = (
            "INVALID_APPROVAL"
        )

        report["message"] = (
            "Invalid patch number."
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    selected = None

    for candidate in candidates:

        if candidate["id"] == selected_id:
            selected = candidate
            break

    if selected is None:

        print()
        print(
            "That patch does not exist."
        )

        print(
            "Nothing was modified."
        )

        report["status"] = (
            "INVALID_PATCH"
        )

        report["message"] = (
            "Selected patch does not exist."
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    fix = selected["data"]

    original_file = get_original_file(
        fix
    )

    patch_file = get_patch_file(
        fix
    )

    original_file = resolve_project_file(
        original_file,
        project_directory
    )

    patch_file = resolve_project_file(
        patch_file,
        os.getcwd()
    )

    print()
    print("=" * 60)
    print("SELECTED PATCH")
    print("=" * 60)

    print(
        f"Original: {original_file}"
    )

    print(
        f"Patch:    {patch_file}"
    )

    print()

    # --------------------------------------------------------
    # SAFETY CHECKS
    # --------------------------------------------------------

    if not original_file:

        print(
            "Original file is missing."
        )

        return

    if not patch_file:

        print(
            "Patch file is missing."
        )

        return

    if not os.path.exists(
        original_file
    ):

        print(
            "Original file does not exist."
        )

        print(
            "Nothing was modified."
        )

        return

    if not os.path.exists(
        patch_file
    ):

        print(
            "Patch file does not exist."
        )

        print(
            "Nothing was modified."
        )

        return

    if not is_inside_project(
        original_file,
        project_directory
    ):

        print(
            "SAFETY CHECK FAILED:"
        )

        print(
            "The target file is outside "
            "the configured project."
        )

        print(
            "Nothing was modified."
        )

        return

    # --------------------------------------------------------
    # SHOW EXACT DIFF
    # --------------------------------------------------------

    if not show_diff(
        original_file,
        patch_file
    ):

        print()
        print(
            "There is no valid change to apply."
        )

        print(
            "Nothing was modified."
        )

        return

    print()
    print(
        "You are about to modify the REAL "
        "project."
    )

    confirmation = input(
        "Type APPLY to continue: "
    ).strip()

    if confirmation != "APPLY":

        print()
        print(
            "Approval cancelled."
        )

        print(
            "Nothing was modified."
        )

        report["status"] = (
            "APPROVAL_CANCELLED"
        )

        report["message"] = (
            "Final APPLY confirmation "
            "was not provided."
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    # --------------------------------------------------------
    # BACKUP
    # --------------------------------------------------------

    print()
    print(
        "Creating backup..."
    )

    try:

        backup_file = create_backup(
            original_file,
            project_directory
        )

        print(
            f"Backup created:"
        )

        print(
            backup_file
        )

    except Exception as e:

        print()
        print(
            "BACKUP FAILED."
        )

        print(
            str(e)
        )

        print(
            "Nothing was modified."
        )

        report["status"] = (
            "BACKUP_FAILED"
        )

        report["message"] = str(e)

        save_json(
            APPLY_REPORT,
            report
        )

        return

    # --------------------------------------------------------
    # APPLY
    # --------------------------------------------------------

    print()
    print(
        "Applying approved patch..."
    )

    try:

        apply_patch(
            original_file,
            patch_file
        )

    except Exception as e:

        print()
        print(
            "PATCH APPLICATION FAILED."
        )

        print(
            str(e)
        )

        print(
            "Restoring backup..."
        )

        restore_backup(
            original_file,
            backup_file
        )

        report["status"] = (
            "APPLY_FAILED_ROLLED_BACK"
        )

        report["message"] = str(e)

        report["backup_files"].append(
            backup_file
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    # --------------------------------------------------------
    # VERIFY COPY
    # --------------------------------------------------------

    print(
        "Verifying applied file..."
    )

    verified = verify_applied_file(
        original_file,
        patch_file
    )

    if not verified:

        print()
        print(
            "VERIFICATION FAILED."
        )

        print(
            "Restoring backup..."
        )

        restore_backup(
            original_file,
            backup_file
        )

        report["status"] = (
            "VERIFY_FAILED_ROLLED_BACK"
        )

        report["message"] = (
            "Applied file did not match "
            "the approved patch."
        )

        report["backup_files"].append(
            backup_file
        )

        save_json(
            APPLY_REPORT,
            report
        )

        return

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("PATCH APPLIED SUCCESSFULLY")
    print("=" * 60)
    print()

    print(
        "Modified file:"
    )

    print(
        original_file
    )

    print()

    print(
        "Backup:"
    )

    print(
        backup_file
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "The website should now be tested "
        "again before considering the fix final."
    )

    report["status"] = (
        "PATCH_APPLIED_PENDING_TEST"
    )

    report["approved"] = True

    report["modified_files"].append(
        original_file
    )

    report["backup_files"].append(
        backup_file
    )

    report["message"] = (
        "Approved patch was applied. "
        "A full website test should be "
        "run before keeping the change."
    )

    save_json(
        APPLY_REPORT,
        report
    )

    print()
    print(
        f"Report: {APPLY_REPORT}"
    )


if __name__ == "__main__":
    main()