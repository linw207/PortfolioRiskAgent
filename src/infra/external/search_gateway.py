from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from config.settings import SearchSettings


@dataclass(slots=True)
class SearchResultItem:
    title: str
    snippet: str
    url: str
    source: str
    published_at: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at,
        }


class AdvancedSearchGateway:
    """Hybrid web search gateway for Agent tools.

    The gateway intentionally avoids hard dependency imports. Tavily and
    SerpAPI are called through their HTTP APIs when keys are present, so the
    Agent has a stable mature-search boundary even before optional SDKs are
    installed.
    """

    def __init__(self, settings: SearchSettings) -> None:
        self.settings = settings
        self.available_backends = self._setup_backends()

    def status(self) -> dict[str, Any]:
        return {
            "backend": self.settings.backend,
            "available_backends": self.available_backends,
            "configured": bool(self.available_backends),
            "trusted_announcement_domains": list(self.settings.trusted_announcement_domains),
            "trusted_news_domains": list(self.settings.trusted_news_domains),
        }

    def search(
        self,
        query: str,
        max_results: int | None = None,
        domains: list[str] | None = None,
        search_type: str = "general",
    ) -> dict[str, Any]:
        query = query.strip()
        if not query:
            return self._unavailable("搜索查询不能为空")
        if not self.available_backends:
            return self._unavailable(
                "没有可用的搜索源，请配置 TAVILY_API_KEY 或 SERPAPI_API_KEY 环境变量。"
            )

        max_results = max_results or self.settings.max_results
        backends = self._backend_order()
        errors = []
        for backend in backends:
            try:
                if backend == "tavily":
                    return self._search_tavily(query, max_results=max_results, domains=domains, search_type=search_type)
                if backend == "serpapi":
                    return self._search_serpapi(query, max_results=max_results, domains=domains, search_type=search_type)
            except Exception as exc:  # noqa: BLE001 - fallback is the core design
                errors.append({"backend": backend, "error": str(exc)})
                continue
        return {
            "success": False,
            "backend": "none",
            "answer": "",
            "items": [],
            "errors": errors,
            "message": "所有搜索源都失败了，请检查网络连接和 API 密钥配置。",
        }

    def trusted_news_search(self, query: str, max_results: int | None = None) -> dict[str, Any]:
        expanded_query = f"{query} A股 OR 上市公司 OR 公告 OR 财报 OR 风险"
        return self.search(expanded_query, max_results=max_results, search_type="news")

    def trusted_announcement_search(self, symbol: str, company_name: str = "", keywords: list[str] | None = None) -> dict[str, Any]:
        words = " ".join(keywords or ["公告", "问询函", "减持", "质押", "诉讼", "业绩预告"])
        query = f"{symbol} {company_name} {words}".strip()
        result = self.search(
            query,
            max_results=self.settings.max_results,
            domains=list(self.settings.trusted_announcement_domains),
            search_type="announcement",
        )
        if not result.get("success"):
            return result
        primary_terms = [symbol.split(".")[0], company_name]
        filtered_items = self._filter_relevant_items(result.get("items", []), primary_terms)
        result["items"] = filtered_items
        if not filtered_items:
            result["message"] = "可信公告域名中未找到与股票代码、公司名或关键词明确相关的结果。"
        return result

    def _setup_backends(self) -> list[str]:
        available = []
        if self.settings.tavily_api_key:
            available.append("tavily")
        if self.settings.serpapi_api_key:
            available.append("serpapi")
        if self.settings.backend != "hybrid":
            return [backend for backend in available if backend == self.settings.backend]
        return available

    def _backend_order(self) -> list[str]:
        if self.settings.backend == "hybrid":
            return [backend for backend in ("tavily", "serpapi") if backend in self.available_backends]
        return [self.settings.backend] if self.settings.backend in self.available_backends else []

    def _search_tavily(
        self,
        query: str,
        max_results: int,
        domains: list[str] | None,
        search_type: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": True,
            "max_results": max_results,
        }
        if domains:
            payload["include_domains"] = domains
        request = urllib.request.Request(
            "https://api.tavily.com/search",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        items = [
            SearchResultItem(
                title=str(item.get("title", "")),
                snippet=str(item.get("content", ""))[:500],
                url=str(item.get("url", "")),
                source="tavily",
            ).to_dict()
            for item in data.get("results", [])[:max_results]
        ]
        return {
            "success": True,
            "backend": "tavily",
            "search_type": search_type,
            "answer": data.get("answer", ""),
            "items": items,
            "message": "",
        }

    def _search_serpapi(
        self,
        query: str,
        max_results: int,
        domains: list[str] | None,
        search_type: str,
    ) -> dict[str, Any]:
        if domains:
            domain_query = " OR ".join(f"site:{domain}" for domain in domains)
            query = f"({domain_query}) {query}"
        params = urllib.parse.urlencode(
            {
                "engine": "google",
                "q": query,
                "api_key": self.settings.serpapi_api_key,
                "num": max_results,
                "hl": "zh-cn",
            }
        )
        with urllib.request.urlopen(f"https://serpapi.com/search.json?{params}", timeout=self.settings.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        items = [
            SearchResultItem(
                title=str(item.get("title", "")),
                snippet=str(item.get("snippet", ""))[:500],
                url=str(item.get("link", "")),
                source="serpapi",
                published_at=str(item.get("date", "")),
            ).to_dict()
            for item in data.get("organic_results", [])[:max_results]
        ]
        answer = ""
        if "answer_box" in data:
            answer = str(data["answer_box"].get("answer") or data["answer_box"].get("snippet") or "")
        return {
            "success": True,
            "backend": "serpapi",
            "search_type": search_type,
            "answer": answer,
            "items": items,
            "message": "",
        }

    def _unavailable(self, message: str) -> dict[str, Any]:
        return {
            "success": False,
            "backend": "none",
            "search_type": "general",
            "answer": "",
            "items": [],
            "message": message,
        }

    def _filter_relevant_items(self, items: list[dict[str, str]], terms: list[str]) -> list[dict[str, str]]:
        useful_terms = [term.strip() for term in terms if term and term.strip()]
        if not useful_terms:
            return items
        filtered = []
        for item in items:
            haystack = f"{item.get('title', '')} {item.get('snippet', '')} {item.get('url', '')}"
            if any(term in haystack for term in useful_terms):
                filtered.append(item)
        return filtered
