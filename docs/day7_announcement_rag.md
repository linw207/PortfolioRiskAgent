# Day7 Announcement Agent and Minimal RAG

Day7 implements announcement ingestion, chunking, risk keyword tagging, evidence retrieval, and AnnouncementAgent execution.

## Implemented Scope

- Announcement ingestion:
  - `AnnouncementRAGService.ingest_symbol_announcements`
  - Uses `MarketDataGateway.announcements`; AKShare first, local sample fallback.
- Announcement chunking:
  - `AnnouncementRAGService.chunk_announcement`
  - Stable chunk ids derived from symbol, title, publish date, url, and chunk index.
- Risk keyword tagging:
  - Taxonomy covers share reduction, lawsuit, inquiry, loss warning, pledge, regulatory penalty, and delisting risk.
- Evidence retrieval:
  - `retrieve_announcement_evidence` MCP tool queries Chroma by symbol metadata and risk query embedding.
  - Retrieval output includes title, publish date, source, url, snippet, matched keywords, and distance.
- AnnouncementAgent:
  - Runs per holding through `analyze_announcement_risk`.
  - Saves `AgentRunRecord` and tool calls through the existing MCP registry.
- Task API:
  - `POST /tasks/{task_id}/run-announcement-check`

## Embedding

The vector layer now uses Ollama embedding first:

- Base URL: `OLLAMA_BASE_URL`
- Embedding model: `OLLAMA_EMBEDDING_MODEL`, currently `qwen3-embedding:4b`
- Fallback: deterministic local embedding is available only when no embedder is configured, or when `VECTOR_ALLOW_EMBEDDING_FALLBACK=true`.

The local `.env` uses separate Chroma collections for the qwen embedding dimension:

- `VECTOR_COLLECTION_ANNOUNCEMENTS=announcement_chunks_qwen3`
- `VECTOR_COLLECTION_MEMORY=agent_memory_qwen3`

## Verification

Commands run:

```bash
python3 -B -m compileall -q src config log scripts tests
python3 -B -m unittest discover -s tests
python3 -B scripts/day7_announcement_smoke.py
```

Smoke result:

- Ollama available: true
- Embedding model: `qwen3-embedding:4b`
- Task status: completed
- Risk events: 2
- Summary: regulatory inquiry and share pledge risks were identified with evidence titles.

## Known Limits

- Current classification is deterministic keyword taxonomy plus RAG evidence retrieval; model-based event reasoning is intentionally deferred.
- Sample fallback announcements are short. Real AKShare or trusted announcement search data will improve coverage.
- `VECTOR_ALLOW_EMBEDDING_FALLBACK` defaults to false to avoid writing 64-dimensional fallback vectors into qwen embedding collections.
- Day8 can reuse the same evidence model for historical memory and review reflection.
