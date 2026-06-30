from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.factory import create_container


def main() -> None:
    result = create_container().evaluation_service.run_all()
    output_dir = Path("data/evaluation/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"evaluation_{timestamp}.json"
    report_path = output_dir / f"evaluation_report_{timestamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(_render_markdown(result), encoding="utf-8")
    print(f"evaluation_json={json_path}")
    print(f"evaluation_report={report_path}")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


def _render_markdown(result: dict) -> str:
    summary = result["summary"]
    lines = [
        "# PortfolioRiskAgent Day13 Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Tool call accuracy: {_pct(summary['tool_call_accuracy'])}",
        f"- Risk identification F1: {_pct(summary['risk_identification_f1'])}",
        f"- Guardrail interception rate: {_pct(summary['guardrail_interception_rate'])}",
        f"- End-to-end completion rate: {_pct(summary['end_to_end_completion_rate'])}",
        f"- Stability pass rate: {_pct(summary['stability_pass_rate'])}",
        f"- Elapsed: {summary['elapsed_ms']} ms",
        "",
        "## Methodology",
        "",
    ]
    for name, description in result["methodology"].items():
        lines.append(f"- `{name}`: {description}")
    lines.extend(["", "## Suites", ""])
    for name, suite in result["suites"].items():
        lines.extend([f"### {name}", "", f"- Cases: {suite['case_count']}", "- Metrics:"])
        for metric, value in suite["metrics"].items():
            lines.append(f"  - `{metric}`: {value}")
        lines.extend(["", "| Case | Passed |", "| --- | --- |"])
        for detail in suite["details"]:
            passed = detail.get("correct", detail.get("passed"))
            lines.append(f"| `{detail['id']}` | {passed} |")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


if __name__ == "__main__":
    main()
