# Day9 Report Agent and Guardrail

Day9 implements Markdown report generation, safety review, violation rewriting, report archival, and report query API.

## Implemented Scope

- Report template:
  - `ReportService.render_report`
  - Sections: holdings overview, financial risk, announcement risk events, trade review questions, data sources and audit notes.
- Report Agent:
  - `ReportAgent` collects Day6 finance, Day7 announcement, and Day8 review results.
  - If missing, it invokes the corresponding agent/service chain to complete the sections.
- Rule guardrail:
  - `ReportService.guardrail_check`
  - Blocks and rewrites buy/sell advice, target prices, guaranteed returns, and promotional phrases.
- Model guardrail:
  - Uses Ollama as a supplemental safety reviewer when available.
  - Rule guardrail remains the deterministic source of truth.
- Violation rewriting:
  - `rewrite_report_violations` MCP tool.
- Report archival:
  - `save_report` persists `ReportArchive` with guardrail metadata.
- Query API:
  - `GET /reports/tasks/{task_id}`
- Task API:
  - `POST /tasks/{task_id}/run-report-check`

## MCP Tools

- `render_report`
- `guardrail_check`
- `rewrite_report_violations`
- `save_report`
- `get_report`

## Verification

Commands run:

```bash
python3 -B -m compileall -q src config log scripts tests
python3 -B -m unittest discover -s tests
python3 -B scripts/day9_report_smoke.py
```

Smoke result:

- Task status: completed
- Report archived with a `report_id`
- Guardrail passed: true
- Markdown report contains the report title
- Markdown report contains human review questions

## Known Limits

- The model guardrail currently parses model output conservatively and treats rule guardrail as the reliable layer.
- PDF export is not part of Day9; it is scheduled later in the plan.
