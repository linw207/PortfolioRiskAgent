from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from src.app.service.validation import normalize_symbol
from src.app.service.vector_memory_service import VectorMemoryService
from src.infra.external.market_data_gateway import MarketDataGateway


RISK_TAXONOMY: dict[str, dict[str, Any]] = {
    "share_reduction": {"label": "股东减持", "keywords": ["减持", "拟减持", "集中竞价减持"], "severity": "medium"},
    "lawsuit": {"label": "诉讼仲裁", "keywords": ["诉讼", "仲裁", "起诉", "法院"], "severity": "high"},
    "inquiry": {"label": "监管问询", "keywords": ["问询", "问询函", "关注函", "监管函"], "severity": "medium"},
    "loss_warning": {"label": "业绩预亏", "keywords": ["预亏", "业绩预告", "亏损", "净利润下降"], "severity": "high"},
    "pledge": {"label": "股份质押", "keywords": ["质押", "解除质押", "补充质押"], "severity": "medium"},
    "regulatory_penalty": {"label": "监管处罚", "keywords": ["处罚", "立案", "行政监管", "警示函"], "severity": "high"},
    "delisting": {"label": "退市风险", "keywords": ["退市", "风险警示", "终止上市"], "severity": "critical"},
}


@dataclass(slots=True)
class AnnouncementChunk:
    chunk_id: str
    symbol: str
    title: str
    published_at: str
    source: str
    url: str
    text: str
    risk_keywords: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "symbol": self.symbol,
            "title": self.title,
            "published_at": self.published_at,
            "source": self.source,
            "url": self.url,
            "text": self.text,
            "risk_keywords": self.risk_keywords,
        }


class AnnouncementRAGService:
    def __init__(self, market_data: MarketDataGateway, vector_memory: VectorMemoryService) -> None:
        self.market_data = market_data
        self.vector_memory = vector_memory

    def ingest_symbol_announcements(
        self,
        symbol: str,
        limit: int = 10,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        announcements, source, degraded = self.market_data.announcements(
            normalized,
            limit=limit,
            keywords=keywords,
        )
        chunks: list[AnnouncementChunk] = []
        for announcement in announcements:
            chunks.extend(self.chunk_announcement(normalized, announcement))
        upsert = self.vector_memory.upsert_announcement_chunks([chunk.to_dict() for chunk in chunks]) if chunks else {}
        return {
            "symbol": normalized,
            "source": source,
            "degraded": degraded,
            "announcement_count": len(announcements),
            "chunk_count": len(chunks),
            "upsert": upsert,
            "chunks": [chunk.to_dict() for chunk in chunks],
        }

    def retrieve_evidence(
        self,
        symbol: str,
        risk_keywords: list[str] | None = None,
        query: str | None = None,
        limit: int = 5,
        auto_ingest: bool = True,
    ) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        keywords = risk_keywords or all_risk_keywords()
        search_query = query or f"{normalized} {' '.join(keywords[:8])} 公告 风险"
        result = self.vector_memory.search_announcement_chunks(search_query, symbol=normalized, limit=limit)
        items = self._filter_and_rank_evidence(result.get("items", []), keywords)
        if not items and auto_ingest:
            self.ingest_symbol_announcements(normalized, limit=max(limit, 10), keywords=keywords)
            result = self.vector_memory.search_announcement_chunks(search_query, symbol=normalized, limit=limit)
            items = self._filter_and_rank_evidence(result.get("items", []), keywords)
        return {
            "symbol": normalized,
            "query": search_query,
            "risk_keywords": keywords,
            "evidence": items[:limit],
        }

    def analyze_symbol(self, symbol: str, company_name: str = "", limit: int = 5) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        self.ingest_symbol_announcements(normalized, limit=10)
        evidence_result = self.retrieve_evidence(normalized, limit=limit, auto_ingest=False)
        events = self._build_risk_events(normalized, company_name, evidence_result["evidence"])
        return {
            "symbol": normalized,
            "company_name": company_name,
            "risk_event_count": len(events),
            "risk_events": events,
            "evidence": evidence_result["evidence"],
        }

    def chunk_announcement(self, symbol: str, announcement: dict[str, Any], chunk_size: int = 260, overlap: int = 40) -> list[AnnouncementChunk]:
        title = str(announcement.get("title", ""))
        content = str(announcement.get("content") or announcement.get("snippet") or title)
        text = f"{title}\n{content}".strip()
        if not text:
            return []
        chunks = []
        start = 0
        index = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end]
            matched = matched_risk_keywords(title + "\n" + chunk_text)
            chunks.append(
                AnnouncementChunk(
                    chunk_id=self._chunk_id(symbol, announcement, index),
                    symbol=symbol,
                    title=title,
                    published_at=str(announcement.get("published_at", "")),
                    source=str(announcement.get("source", "")),
                    url=str(announcement.get("url", "")),
                    text=chunk_text,
                    risk_keywords=matched,
                )
            )
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
            index += 1
        return chunks

    def _filter_and_rank_evidence(self, items: list[dict[str, Any]], keywords: list[str]) -> list[dict[str, Any]]:
        evidence = []
        for item in items:
            metadata = item.get("metadata", {})
            text = item.get("text", "")
            matched = sorted(set(matched_risk_keywords(f"{metadata.get('title', '')}\n{text}", keywords)))
            if not matched:
                metadata_keywords = str(metadata.get("risk_keywords", ""))
                matched = [keyword for keyword in keywords if keyword and keyword in metadata_keywords]
            if not matched:
                continue
            evidence.append(
                {
                    "chunk_id": item.get("id", ""),
                    "title": metadata.get("title", ""),
                    "published_at": metadata.get("published_at", ""),
                    "source": metadata.get("source", ""),
                    "url": metadata.get("url", ""),
                    "snippet": text[:300],
                    "matched_keywords": matched,
                    "distance": item.get("distance"),
                }
            )
        return sorted(evidence, key=lambda item: (len(item["matched_keywords"]) * -1, item.get("distance") or 0))

    def _build_risk_events(self, symbol: str, company_name: str, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events = []
        seen = set()
        for item in evidence:
            evidence_text = f"{item.get('title', '')}\n{item.get('snippet', '')}"
            for risk_type, config in RISK_TAXONOMY.items():
                hits = [keyword for keyword in config["keywords"] if keyword in evidence_text]
                if not hits:
                    continue
                key = (risk_type, item.get("chunk_id", ""))
                if key in seen:
                    continue
                seen.add(key)
                events.append(
                    {
                        "symbol": symbol,
                        "company_name": company_name,
                        "risk_type": risk_type,
                        "risk_label": config["label"],
                        "severity": config["severity"],
                        "matched_keywords": hits,
                        "evidence": {
                            "title": item.get("title", ""),
                            "published_at": item.get("published_at", ""),
                            "source": item.get("source", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", ""),
                        },
                    }
                )
        return events

    def _chunk_id(self, symbol: str, announcement: dict[str, Any], index: int) -> str:
        raw = "|".join(
            [
                symbol,
                str(announcement.get("url", "")),
                str(announcement.get("title", "")),
                str(announcement.get("published_at", "")),
                str(index),
            ]
        )
        return "ann_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def all_risk_keywords() -> list[str]:
    keywords: list[str] = []
    for config in RISK_TAXONOMY.values():
        keywords.extend(config["keywords"])
    return sorted(set(keywords))


def matched_risk_keywords(text: str, keywords: list[str] | None = None) -> list[str]:
    candidates = keywords or all_risk_keywords()
    return [keyword for keyword in candidates if keyword and keyword in text]
