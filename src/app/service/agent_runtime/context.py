from __future__ import annotations


def truncate_context(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    marker = "\n...[context truncated]...\n"
    if max_chars <= len(marker) + 20:
        return text[:max_chars]
    keep = max_chars - len(marker)
    head = keep // 2
    tail = keep - head
    return text[:head] + marker + text[-tail:]
