"""omw CLI subprocess 래퍼 — 플러그인의 유일한 omw 접근 경로."""

from __future__ import annotations

import json
import os
import shutil
import subprocess

DEFAULT_TIMEOUT = 60

_INSTALL_HINT = (
    "omw CLI가 필요합니다: pipx install oh-my-wiki "
    "(또는 OMW_BIN 환경변수로 바이너리 경로 지정)"
)


def resolve_omw_bin() -> str | None:
    """OMW_BIN env 우선, 없으면 PATH에서 omw 탐색. 못 찾으면 None."""
    env = os.environ.get("OMW_BIN")
    if env:
        return env if os.path.exists(env) else None
    return shutil.which("omw")


def run_omw(args: list[str], timeout: int = DEFAULT_TIMEOUT) -> dict:
    """omw CLI를 실행하고 파싱된 JSON dict를 반환한다. 절대 raise하지 않는다.

    stdout이 JSON 배열이면 {"hits": [...]}로 감싸고, 객체면 그대로 반환.
    stderr는 무시한다(fastembed 모델 경고 등 노이즈).
    """
    binary = resolve_omw_bin()
    if binary is None:
        return {"error": "omw CLI not found", "hint": _INSTALL_HINT}
    try:
        proc = subprocess.run(
            [binary, *args], capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "error": f"omw timed out after {timeout}s",
            "hint": "URL 응답이 느리거나 임베딩 모델 초기화 중일 수 있습니다. 다시 시도하세요.",
        }
    except OSError as exc:
        return {"error": f"failed to run omw: {exc}"}
    except Exception as exc:
        # 계약: run_omw는 절대 raise하지 않는다. 인자에 embedded null byte(ValueError),
        # surrogate 문자(UnicodeEncodeError), 잘못된 timeout 타입(TypeError) 등
        # subprocess 셋업 단계의 예외까지 전부 에러 dict로 흡수한다.
        return {"error": f"failed to run omw: {type(exc).__name__}: {exc}"}

    if proc.returncode != 0:
        lines = (proc.stderr or "").strip().splitlines()
        return {
            "error": f"omw exited with code {proc.returncode}",
            "detail": lines[-1] if lines else "",
        }

    out = (proc.stdout or "").strip()
    if not out:
        return {"error": "omw returned empty output"}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"error": "omw output was not JSON", "preview": out[:500]}
    if isinstance(data, list):
        return {"hits": data}
    if isinstance(data, dict):
        return data
    return {"error": f"unexpected omw output type: {type(data).__name__}"}
