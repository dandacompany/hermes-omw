"""hermes-omw — oh-my-wiki 브리지 플러그인.

사람이 검수한 위키에서 출처 있는 답변(cited recall)을 가져온다.
자동 저장 메모리가 아니라 큐레이션된 지식 베이스를 도구로 노출한다.
"""

from __future__ import annotations

try:  # Hermes 플러그인 패키지 컨텍스트
    from . import schemas, tools
except ImportError:  # pytest 직접 실행 컨텍스트
    import schemas
    import tools

_TOOLS = (
    ("omw_find",    schemas.OMW_FIND_SCHEMA,    tools.handle_omw_find,    "🔎"),
    ("omw_context", schemas.OMW_CONTEXT_SCHEMA, tools.handle_omw_context, "📖"),
    ("omw_ingest",  schemas.OMW_INGEST_SCHEMA,  tools.handle_omw_ingest,  "📥"),
)


def register(ctx) -> None:
    """플러그인 로더 진입점 — 도구 3종 + /omw-status 슬래시 커맨드 등록."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="omw",
            schema=schema,
            handler=handler,
            emoji=emoji,
        )
    # 이름을 "omw"로 하면 oh-my-wiki가 설치하는 Hermes 스킬 `/omw`와 충돌한다
    ctx.register_command(
        "omw-status",
        tools.handle_omw_command,
        description="omw 위키 상태 요약 (활성 vault, 사용 가능한 도구)",
    )
