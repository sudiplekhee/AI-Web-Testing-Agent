import json
import os
import re
from datetime import datetime

CONFIG_FILE = "config.json"
OUTPUT_FILE = "reports/project_detection.json"

IGNORE_DIRS = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    "node_modules",
    "dist",
    "build",
    "vendor",
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Could not read config.json: {e}")
        return {}


def save_report(data):
    os.makedirs("reports", exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            return file.read()
    except Exception:
        return ""


def file_exists(project, filename):
    return os.path.isfile(os.path.join(project, filename))


def get_project_files(project):
    files = []

    try:
        for root, dirs, filenames in os.walk(project):

            # Prevent scanning unnecessary directories
            dirs[:] = [
                directory
                for directory in dirs
                if directory not in IGNORE_DIRS
            ]

            for filename in filenames:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(
                    full_path,
                    project
                )

                files.append(relative_path)

    except Exception as e:
        print(f"Could not scan project files: {e}")

    return files


def read_python_files(project, project_files):
    python_files = []

    for relative_path in project_files:

        if not relative_path.lower().endswith(".py"):
            continue

        full_path = os.path.join(
            project,
            relative_path
        )

        content = read_file(full_path)

        python_files.append({
            "file": relative_path,
            "content": content
        })

    return python_files


def detect_python_framework(project, project_files):
    detected = []

    # ---------------------------------------------------------
    # Read dependency files
    # ---------------------------------------------------------

    dependency_content = ""

    dependency_files = [
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "Pipfile",
        "Pipfile.lock",
    ]

    for filename in dependency_files:

        path = os.path.join(
            project,
            filename
        )

        if os.path.isfile(path):
            dependency_content += "\n"
            dependency_content += read_file(path).lower()

    # ---------------------------------------------------------
    # Inspect Python source code
    # ---------------------------------------------------------

    python_files = read_python_files(
        project,
        project_files
    )

    flask_score = 0
    django_score = 0
    fastapi_score = 0
    streamlit_score = 0

    flask_evidence = []
    django_evidence = []
    fastapi_evidence = []
    streamlit_evidence = []

    # Dependency detection

    if "flask" in dependency_content:
        flask_score += 40
        flask_evidence.append("Flask found in dependency files")

    if "django" in dependency_content:
        django_score += 40
        django_evidence.append("Django found in dependency files")

    if "fastapi" in dependency_content:
        fastapi_score += 40
        fastapi_evidence.append("FastAPI found in dependency files")

    if "streamlit" in dependency_content:
        streamlit_score += 40
        streamlit_evidence.append(
            "Streamlit found in dependency files"
        )

    # Source code detection

    for item in python_files:

        filename = item["file"]
        content = item["content"]
        lower = content.lower()

        # Flask

        if re.search(
            r"from\s+flask\s+import",
            lower
        ):
            flask_score += 50
            flask_evidence.append(
                f"{filename}: from flask import"
            )

        if re.search(
            r"import\s+flask",
            lower
        ):
            flask_score += 40
            flask_evidence.append(
                f"{filename}: import flask"
            )

        if "flask(" in lower:
            flask_score += 30
            flask_evidence.append(
                f"{filename}: Flask application instance"
            )

        if "@app.route" in lower:
            flask_score += 30
            flask_evidence.append(
                f"{filename}: @app.route"
            )

        # Django

        if "django." in lower:
            django_score += 50
            django_evidence.append(
                f"{filename}: Django imports"
            )

        if "from django" in lower:
            django_score += 50
            django_evidence.append(
                f"{filename}: from django"
            )

        # FastAPI

        if re.search(
            r"from\s+fastapi\s+import",
            lower
        ):
            fastapi_score += 60
            fastapi_evidence.append(
                f"{filename}: from fastapi import"
            )

        if "fastapi(" in lower:
            fastapi_score += 30
            fastapi_evidence.append(
                f"{filename}: FastAPI application instance"
            )

        # Streamlit

        if "import streamlit" in lower:
            streamlit_score += 60
            streamlit_evidence.append(
                f"{filename}: import streamlit"
            )

        if "st." in lower:
            streamlit_score += 20
            streamlit_evidence.append(
                f"{filename}: Streamlit API usage"
            )

    # manage.py is strong Django evidence

    if file_exists(project, "manage.py"):
        django_score += 100
        django_evidence.append(
            "manage.py found"
        )

    candidates = []

    if flask_score > 0:
        candidates.append({
            "framework": "Flask",
            "score": flask_score,
            "evidence": flask_evidence
        })

    if django_score > 0:
        candidates.append({
            "framework": "Django",
            "score": django_score,
            "evidence": django_evidence
        })

    if fastapi_score > 0:
        candidates.append({
            "framework": "FastAPI",
            "score": fastapi_score,
            "evidence": fastapi_evidence
        })

    if streamlit_score > 0:
        candidates.append({
            "framework": "Streamlit",
            "score": streamlit_score,
            "evidence": streamlit_evidence
        })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return candidates


def detect_node_framework(project):
    package_path = os.path.join(
        project,
        "package.json"
    )

    if not os.path.isfile(package_path):
        return []

    try:
        package_data = json.loads(
            read_file(package_path)
        )
    except Exception:
        return []

    dependencies = {}

    dependencies.update(
        package_data.get(
            "dependencies",
            {}
        )
    )

    dependencies.update(
        package_data.get(
            "devDependencies",
            {}
        )
    )

    dependency_names = {
        name.lower()
        for name in dependencies
    }

    detected = []

    if "express" in dependency_names:
        detected.append("Express")

    if "react" in dependency_names:
        detected.append("React")

    if "next" in dependency_names:
        detected.append("Next.js")

    if "vue" in dependency_names:
        detected.append("Vue")

    if "@angular/core" in dependency_names:
        detected.append("Angular")

    if "svelte" in dependency_names:
        detected.append("Svelte")

    return detected


def detect_php(project, project_files):

    if file_exists(
        project,
        "composer.json"
    ):
        return ["PHP"]

    php_count = 0

    for filename in project_files:

        if filename.lower().endswith(".php"):
            php_count += 1

    if php_count > 0:
        return ["PHP"]

    return []


def detect_static(project, project_files):

    html_files = [
        filename
        for filename in project_files
        if filename.lower().endswith(".html")
    ]

    css_files = [
        filename
        for filename in project_files
        if filename.lower().endswith(".css")
    ]

    js_files = [
        filename
        for filename in project_files
        if filename.lower().endswith(".js")
    ]

    if html_files:
        return {
            "html": len(html_files),
            "css": len(css_files),
            "javascript": len(js_files)
        }

    return None


def detect_server_command(
    project,
    frameworks,
    project_files
):

    # ---------------------------------------------------------
    # Django
    # ---------------------------------------------------------

    if "Django" in frameworks:

        if file_exists(
            project,
            "manage.py"
        ):
            return "python manage.py runserver"

    # ---------------------------------------------------------
    # Flask
    # ---------------------------------------------------------

    if "Flask" in frameworks:

        # Common Flask entry points

        possible_files = [
            "app.py",
            "run.py",
            "main.py",
            "server.py",
            "application.py"
        ]

        for filename in possible_files:

            if file_exists(
                project,
                filename
            ):
                return f"python {filename}"

    # ---------------------------------------------------------
    # FastAPI
    # ---------------------------------------------------------

    if "FastAPI" in frameworks:

        possible_files = [
            "main.py",
            "app.py",
            "server.py"
        ]

        for filename in possible_files:

            if file_exists(
                project,
                filename
            ):

                module = os.path.splitext(
                    filename
                )[0]

                return (
                    f"uvicorn "
                    f"{module}:app "
                    f"--reload"
                )

    # ---------------------------------------------------------
    # Node.js
    # ---------------------------------------------------------

    package_path = os.path.join(
        project,
        "package.json"
    )

    if os.path.isfile(package_path):

        try:

            package_data = json.loads(
                read_file(package_path)
            )

            scripts = package_data.get(
                "scripts",
                {}
            )

            if "dev" in scripts:
                return "npm run dev"

            if "start" in scripts:
                return "npm start"

        except Exception:
            pass

    # ---------------------------------------------------------
    # PHP
    # ---------------------------------------------------------

    if "PHP" in frameworks:

        if file_exists(
            project,
            "index.php"
        ):
            return "php -S 127.0.0.1:8000"

    # ---------------------------------------------------------
    # Static website
    # ---------------------------------------------------------

    static_info = detect_static(
        project,
        project_files
    )

    if static_info:

        return None

    return None


def detect_project(project):

    print()
    print("=" * 60)
    print("PROJECT DETECTOR")
    print("=" * 60)
    print()

    print(
        f"Project directory:\n{project}"
    )

    if not os.path.isdir(project):

        print()
        print(
            "ERROR: Project directory does not exist."
        )

        return None

    # ---------------------------------------------------------
    # Scan project
    # ---------------------------------------------------------

    print()
    print("Scanning project files...")

    project_files = get_project_files(
        project
    )

    print(
        f"Files discovered: {len(project_files)}"
    )

    # ---------------------------------------------------------
    # Detect frameworks
    # ---------------------------------------------------------

    python_candidates = detect_python_framework(
        project,
        project_files
    )

    node_frameworks = detect_node_framework(
        project
    )

    php_frameworks = detect_php(
        project,
        project_files
    )

    frameworks = []

    if python_candidates:

        # Highest scoring Python framework

        frameworks.append(
            python_candidates[0]["framework"]
        )

    frameworks.extend(
        node_frameworks
    )

    frameworks.extend(
        php_frameworks
    )

    # Remove duplicates

    frameworks = list(
        dict.fromkeys(frameworks)
    )

    # ---------------------------------------------------------
    # Static website
    # ---------------------------------------------------------

    static_info = detect_static(
        project,
        project_files
    )

    if not frameworks and static_info:

        frameworks.append(
            "Static HTML/CSS/JavaScript"
        )

    # ---------------------------------------------------------
    # Languages
    # ---------------------------------------------------------

    languages = []

    if any(
        framework in frameworks
        for framework in [
            "Flask",
            "Django",
            "FastAPI",
            "Streamlit"
        ]
    ):
        languages.append("Python")

    if any(
        framework in frameworks
        for framework in [
            "Express",
            "React",
            "Next.js",
            "Vue",
            "Angular",
            "Svelte"
        ]
    ):
        languages.append(
            "JavaScript/TypeScript"
        )

    if "PHP" in frameworks:
        languages.append("PHP")

    if "Static HTML/CSS/JavaScript" in frameworks:

        languages.extend([
            "HTML",
            "CSS",
            "JavaScript"
        ])

    languages = list(
        dict.fromkeys(languages)
    )

    # ---------------------------------------------------------
    # Server command
    # ---------------------------------------------------------

    server_command = detect_server_command(
        project,
        frameworks,
        project_files
    )

    # ---------------------------------------------------------
    # Project type
    # ---------------------------------------------------------

    if frameworks:

        project_type = frameworks[0]

    else:

        project_type = "Unknown"

    # ---------------------------------------------------------
    # Confidence
    # ---------------------------------------------------------

    confidence = 0

    if python_candidates:

        top_score = python_candidates[0]["score"]

        confidence = min(
            99,
            max(
                50,
                top_score
            )
        )

    elif frameworks:

        confidence = 80

    # ---------------------------------------------------------
    # Detection report
    # ---------------------------------------------------------

    result = {

        "agent":
            "AI Website Testing Agent",

        "detector":
            "Project Detector",

        "detection_time":
            datetime.now().isoformat(),

        "project_directory":
            project,

        "project_type":
            project_type,

        "frameworks_detected":
            frameworks,

        "languages_detected":
            languages,

        "server_command":
            server_command,

        "confidence":
            confidence,

        "files_discovered":
            len(project_files),

        "detection_evidence":
            python_candidates,

        "static_files":
            static_info
    }

    save_report(result)

    # ---------------------------------------------------------
    # Display
    # ---------------------------------------------------------

    print()
    print("-" * 60)

    print(
        f"Project type:       "
        f"{project_type}"
    )

    print(
        f"Frameworks:         "
        f"{', '.join(frameworks) or 'None detected'}"
    )

    print(
        f"Languages:          "
        f"{', '.join(languages) or 'Unknown'}"
    )

    print(
        f"Server command:     "
        f"{server_command or 'Not required / unknown'}"
    )

    print(
        f"Files discovered:   "
        f"{len(project_files)}"
    )

    print(
        f"Confidence:         "
        f"{confidence}%"
    )

    print("-" * 60)

    # ---------------------------------------------------------
    # Evidence
    # ---------------------------------------------------------

    if python_candidates:

        print()
        print("Detection evidence:")

        for candidate in python_candidates:

            print(
                f"\n{candidate['framework']}"
            )

            for evidence in candidate[
                "evidence"
            ][:10]:

                print(
                    f"  - {evidence}"
                )

    print()
    print(
        f"Report: {OUTPUT_FILE}"
    )

    return result


if __name__ == "__main__":

    config = load_config()

    project_directory = config.get(
        "project_directory",
        ""
    )

    if not project_directory:

        print()
        print(
            "ERROR: project_directory "
            "is missing from config.json."
        )

        print()
        print("Example:")
        print(
            '"project_directory": '
            '"C:/Projects/my-website"'
        )

    else:

        detect_project(
            os.path.abspath(
                project_directory
            )
        )