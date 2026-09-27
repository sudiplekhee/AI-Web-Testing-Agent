import json
import os
from datetime import datetime


OUTPUT_FILE = "reports/source_report.json"


class SourceCodeScanner:

    def __init__(self, project_directory):

        self.project_directory = os.path.abspath(project_directory)

        self.allowed_extensions = {
            ".py",
            ".html",
            ".css",
            ".js",
            ".json",
            ".txt",
            ".md",
            ".sql"
        }

        self.ignored_directories = {
            ".git",
            ".github",
            "venv",
            ".venv",
            "__pycache__",
            "node_modules",
            ".idea",
            ".vscode",
            "dist",
            "build"
        }

    def should_ignore_directory(self, directory_name):

        return directory_name in self.ignored_directories

    def scan_files(self):

        files = []

        if not os.path.exists(self.project_directory):

            raise FileNotFoundError(
                f"Project directory does not exist:\n"
                f"{self.project_directory}"
            )

        for root, directories, filenames in os.walk(
            self.project_directory
        ):

            directories[:] = [
                directory
                for directory in directories
                if not self.should_ignore_directory(directory)
            ]

            for filename in filenames:

                extension = os.path.splitext(
                    filename
                )[1].lower()

                if extension in self.allowed_extensions:

                    full_path = os.path.join(
                        root,
                        filename
                    )

                    files.append(full_path)

        return files

    def read_file(self, file_path):

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                return file.read()

        except UnicodeDecodeError:

            try:

                with open(
                    file_path,
                    "r",
                    encoding="utf-8-sig"
                ) as file:

                    return file.read()

            except Exception as error:

                return f"[Unable to read file: {error}]"

        except Exception as error:

            return f"[Unable to read file: {error}]"

    def create_file_info(self, file_path):

        content = self.read_file(file_path)

        relative_path = os.path.relpath(
            file_path,
            self.project_directory
        )

        lines = content.count("\n") + 1

        return {
            "file": relative_path.replace("\\", "/"),
            "extension": os.path.splitext(file_path)[1].lower(),
            "lines": lines,
            "characters": len(content),
            "content": content
        }

    def scan_project(self):

        print("\nScanning project source code...")
        print(f"Project: {self.project_directory}\n")

        files = self.scan_files()

        source_files = []

        for file_path in files:

            relative_path = os.path.relpath(
                file_path,
                self.project_directory
            )

            print(f"Reading: {relative_path}")

            file_info = self.create_file_info(
                file_path
            )

            source_files.append(file_info)

        report = {
            "scanner": "AI Website Testing Agent",
            "scan_time": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "project_directory": self.project_directory,
            "files_found": len(source_files),
            "files": source_files
        }

        return report

    def save_report(self, report):

        os.makedirs(
            "reports",
            exist_ok=True
        )

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

    def run(self):

        try:

            report = self.scan_project()

            self.save_report(report)

            print("\n" + "=" * 60)
            print("SOURCE CODE SCAN COMPLETE")
            print("=" * 60)

            print(
                f"Project files found: "
                f"{report['files_found']}"
            )

            print(
                f"Report saved to: "
                f"{OUTPUT_FILE}"
            )

            print("=" * 60)

        except Exception as error:

            print("\nSOURCE CODE SCANNER ERROR")
            print("-" * 60)
            print(error)
            print("-" * 60)


if __name__ == "__main__":

    if not os.path.exists("config.json"):

        print("config.json was not found.")

    else:

        with open(
            "config.json",
            "r",
            encoding="utf-8"
        ) as file:

            config = json.load(file)

        project_directory = config.get(
            "project_directory"
        )

        if not project_directory:

            print(
                "project_directory is missing "
                "from config.json"
            )

        else:

            scanner = SourceCodeScanner(
                project_directory
            )

            scanner.run()