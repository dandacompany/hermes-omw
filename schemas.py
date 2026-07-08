"""LLM이 보는 도구 스키마 — description이 도구 선택의 판단 근거."""

_STR = {"type": "string"}

OMW_FIND_SCHEMA = {
    "name": "omw_find",
    "description": (
        "Search the user's curated omw wiki and return ranked page hits "
        "(title, summary, tags, score). Use for quick lookups — checking "
        "whether a page exists, listing related pages. For answering "
        "questions with page bodies and citations, use omw_context instead."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural-language search query."},
            "limit": {"type": "integer", "description": "Max hits (default 5)."},
            "vault": {"type": "string", "description": "Vault name (default: active vault)."},
        },
        "required": ["query"],
    },
}

OMW_CONTEXT_SCHEMA = {
    "name": "omw_context",
    "description": (
        "Retrieve cited context from the user's omw wiki: page bodies plus a "
        "citations manifest. Use this when answering a question from the "
        "wiki — quote from hit bodies only and cite the returned pages. "
        "Prefer this over omw_find when the user asks what the wiki says."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The question to ground in the wiki."},
            "limit": {"type": "integer", "description": "Max hits (default 5)."},
            "vault": {"type": "string", "description": "Vault name (default: active vault)."},
        },
        "required": ["query"],
    },
}

OMW_INGEST_SCHEMA = {
    "name": "omw_ingest",
    "description": (
        "Fetch a PUBLIC web URL into the omw wiki's raw/ layer and reindex. Use "
        "when the user asks to save a link/article into their wiki. URL only — "
        "it does not create wiki pages and does not accept free text. Requests to "
        "private/loopback/internal addresses are blocked."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "http(s) URL to fetch."},
            "vault": {"type": "string", "description": "Vault name (default: active vault)."},
        },
        "required": ["url"],
    },
}
