from __future__ import annotations

import time

from .incidents import STATE
from .pii import summarize_text
from .tracing import get_langfuse_client, observe

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, logs identify affected requests, traces localize the root cause."],
    "policy": ["Do not expose PII in logs. Use sanitized summaries only."],
}


@observe(name="retrieval", as_type="retriever", capture_input=False, capture_output=False)
def retrieve(message: str) -> list[str]:
    client = get_langfuse_client()
    client.update_current_span(input={"query_preview": summarize_text(message)})
    if STATE["tool_fail"]:
        client.update_current_span(level="ERROR", status_message="Vector store timeout", metadata={"tool_success": False})
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)
    lowered = message.lower()
    for key, docs in CORPUS.items():
        if key in lowered:
            client.update_current_span(metadata={"doc_count": len(docs), "tool_success": True, "matched": True})
            return docs
    client.update_current_span(metadata={"doc_count": 1, "tool_success": True, "matched": False})
    return ["No domain document matched. Use general fallback answer."]
