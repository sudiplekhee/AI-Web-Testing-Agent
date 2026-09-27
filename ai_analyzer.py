import json
import os
from openai import OpenAI


REPORT_FILE = "reports/test_report.json"
AI_REPORT_FILE = "reports/ai_analysis.json"


class AIAnalyzer:

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable was not found."
            )

        self.client = OpenAI(api_key=self.api_key)

    def load_test_report(self):
        if not os.path.exists(REPORT_FILE):
            raise FileNotFoundError(
                f"Test report not found: {REPORT_FILE}\n"
                "Run python agent.py first."
            )

        with open(REPORT_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    def analyze(self, report):

        prompt = f"""
You are an expert software testing and debugging assistant.

Analyze the following automated website testing report.

Your job is to:

1. Identify the important failures.
2. Explain what each failure means in simple language.
3. Identify the most likely cause.
4. Suggest where the developer should investigate.
5. Suggest a practical fix.
6. Explain how the developer can verify the fix.
7. Do not claim certainty when the report does not contain enough information.
8. Clearly distinguish confirmed facts from likely causes.

Website:
{report.get("website")}

Test summary:
{json.dumps(report.get("summary", {}), indent=2)}

Detected errors:
{json.dumps(report.get("errors", []), indent=2)}

Page results:
{json.dumps(report.get("pages", []), indent=2)}

Return your answer using this structure:

OVERALL_RESULT

Give a short summary of the test result.

IMPORTANT_PROBLEMS

For every important problem provide:

Problem:
URL:
Type:
What happened:
Confirmed evidence:
Likely cause:
Where to investigate:
Suggested fix:
How to verify:

ADDITIONAL_OBSERVATIONS

Mention anything else that the developer should inspect.

NEXT_TESTS

List useful tests that should be performed next.
"""

        response = self.client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        return response.output_text

    def save_analysis(self, analysis):

        os.makedirs("reports", exist_ok=True)

        data = {
            "analyzer": "AI Website Testing Agent",
            "analysis": analysis
        }

        with open(AI_REPORT_FILE, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

    def run(self):

        print("\nLoading test report...")

        report = self.load_test_report()

        print("Sending test results to AI...")
        print("Please wait...\n")

        analysis = self.analyze(report)

        self.save_analysis(analysis)

        print("=" * 70)
        print("                 AI ERROR ANALYSIS")
        print("=" * 70)

        print(analysis)

        print("=" * 70)
        print(f"AI analysis saved to: {AI_REPORT_FILE}")
        print("=" * 70)


if __name__ == "__main__":

    try:
        analyzer = AIAnalyzer()
        analyzer.run()

    except Exception as error:

        print("\nAI ANALYZER ERROR")
        print("-" * 50)
        print(error)
        print("-" * 50)