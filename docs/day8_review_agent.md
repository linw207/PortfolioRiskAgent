# Day8 Review Agent and Memory

Day8 implements trade journal review, historical risk memory, working memory retrieval, and deterministic Reflection checks.

## Implemented Scope

- Trade journal query:
  - `search_trade_journals` MCP tool.
  - Reads `trade_journals` from the current UnitOfWork and supports symbol filtering.
- Historical risk memory:
  - `save_risk_memory` writes review summaries to Chroma `agent_memory_qwen3`.
  - `retrieve_risk_memory` searches prior memories by user, symbol, and query.
- Working memory:
  - `TradeReviewService.build_working_memory` combines recent trade journals and historical memories.
- Reflection:
  - `reflect_trade_journal` compares the original trade reason with current facts.
  - Current facts include quote, financial metrics, announcement risk events, and historical memories.
- ReviewAgent:
  - Queries trade journals.
  - Calls financial tools and announcement RAG tools.
  - Generates questions starting with `请人工复核...`.
  - Saves review summaries back to vector memory.
- Task API:
  - `POST /tasks/{task_id}/run-review-check`

## Reflection Rules

The current implementation is deterministic and auditable:

- Missing buy/add reason -> human review question.
- Growth/profit reason + negative revenue or net profit growth -> human review question.
- Long-term/value reason + price drawdown greater than or equal to 3% -> human review question.
- Announcement risk events -> human review question with evidence title.
- Historical memories are added to the signal context for future comparison.

## Verification

Commands run:

```bash
python3 -B -m compileall -q src config log scripts tests
python3 -B -m unittest discover -s tests
python3 -B scripts/day8_review_smoke.py
```

Smoke result:

- Task status: completed
- Human review questions: 4
- First question: growth thesis needs review because current financial growth is under pressure.
- Memory hits after write: 1

## Known Limits

- Reflection is rule-based in Day8. Model-based critique can be added behind the same `reflect_trade_journal` tool later.
- The review uses current sample/AKShare data boundaries. Report-grade attribution will be consolidated in Day9.
