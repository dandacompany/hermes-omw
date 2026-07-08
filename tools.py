"""도구 핸들러 — 항상 JSON 문자열 반환, 예외 무전파."""

from __future__ import annotations

import ipaddress
import json
import socket
from urllib.parse import urlparse

try:  # Hermes 플러그인 패키지 컨텍스트
    from . import omw_client
except ImportError:  # pytest 직접 실행 컨텍스트
    import omw_client

FETCH_TIMEOUT = 120

# LLM이 제어하는 limit 값의 상한 — 무한/음수 limit로 vault를 통째로 덤프하는 것을 막는다.
MAX_LIMIT = 50


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _clamp_limit(raw) -> int | None:
    """limit을 1..MAX_LIMIT로 클램프. 값이 없거나 정수화 실패 시 None(옵션 생략)."""
    if raw is None or raw == "":
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError, OverflowError):
        # OverflowError: int(float('inf')) — 값 생략으로 처리(omw 기본 limit 사용).
        return None
    return max(1, min(MAX_LIMIT, n))


def _opt_args(args: dict) -> list[str]:
    """공통 옵션을 `--flag=value` 형태로 방출.

    `=` 형태를 쓰는 이유: 선행 대시 값(예: vault="-x")이 argparse에서
    별도 플래그로 오인되는 것을 막는다. 옵션은 항상 positional(`--` 뒤) 앞에 온다.
    """
    extra: list[str] = []
    limit = _clamp_limit(args.get("limit"))
    if limit is not None:
        extra.append(f"--limit={limit}")
    vault = args.get("vault")
    if vault:
        extra.append(f"--vault={vault}")
    return extra


def _is_noncanonical_ip_literal(host: str) -> bool:
    """정규 dotted-quad가 아닌 숫자형 IP 리터럴인지 판별한다.

    `2130706433`(정수), `0177.0.0.1`(8진), `0x7f.0.0.1`(16진) 같은 표기는
    resolver/라이브러리마다 다르게 해석돼(예: 127.0.0.1로 매핑) SSRF 우회에
    쓰인다. 정상 URL은 이런 표기를 쓰지 않으므로 DNS 해석 전에 차단한다.
    """
    h = host.strip("[]")  # IPv6 대괄호 제거
    if h.isdigit():  # 순수 정수형 (예: 2130706433)
        return True
    parts = h.split(".")
    if all(p and (p.isdigit() or p.lower().startswith("0x")) for p in parts):
        for p in parts:
            if p.lower().startswith("0x"):  # 16진 옥텟
                return True
            if len(p) > 1 and p.startswith("0"):  # 8진 옥텟 (leading zero)
                return True
    return False


def _is_public_url(url: str) -> tuple[bool, str]:
    """http(s) URL이고 호스트가 공인망으로 해석되는지 검증한다.

    SSRF 방어: 비정규 숫자형 IP 리터럴을 먼저 차단하고, 호스트명을 DNS
    해석해 loopback/private/link-local/reserved/multicast/unspecified 주소로
    가는 요청을 차단한다(클라우드 메타데이터 169.254.169.254 포함).
    반환: (허용여부, 사유).

    한계 (best-effort): 실제 페치는 외부 `omw fetch` CLI에 위임되고 그쪽에서
    호스트를 **다시** 해석하므로, 이 검증은 DNS 리바인딩(TOCTOU)을 완전히
    막지 못한다 — 검증 시점에 공인 IP로 응답하고 페치 시점에 사설 IP로
    바뀌는 저-TTL DNS 공격은 이 경계에서 닫을 수 없다(연결 대상 IP를 페치에
    고정하려면 페치를 이 래퍼 안에서 직접 수행해야 하는데, 그건 "얇은 래퍼"
    설계 결정에 반한다). 리터럴/해석-시점 사설 대역이라는 현실적 공격면은
    차단하며, 리바인딩 잔여 위험은 문서화된 알려진 한계다. README '## Security'
    참고.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        return False, "only http(s) URLs are supported"
    host = parsed.hostname
    if not host:
        return False, "URL has no host"
    if _is_noncanonical_ip_literal(host):
        return False, f"blocked non-canonical IP literal: {host}"
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False, f"could not resolve host: {host}"
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False, f"unresolvable address for host: {host}"
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False, f"blocked non-public address for host {host}: {ip}"
    return True, ""


def handle_omw_find(args: dict, **kwargs) -> str:
    try:
        query = str(args.get("query") or "").strip()
        if not query:
            return _dump({"error": "query is required"})
        # `--json`/옵션은 positional 앞, 쿼리는 `--` 뒤 — 선행 대시 쿼리의 플래그 주입 차단.
        cmd = ["find", "--json", *_opt_args(args), "--", query]
        return _dump(omw_client.run_omw(cmd))
    except Exception as exc:
        return _dump({"error": f"omw_find failed: {type(exc).__name__}: {exc}"})


def handle_omw_context(args: dict, **kwargs) -> str:
    try:
        query = str(args.get("query") or "").strip()
        if not query:
            return _dump({"error": "query is required"})
        cmd = ["context", *_opt_args(args), "--", query]
        return _dump(omw_client.run_omw(cmd))
    except Exception as exc:
        return _dump({"error": f"omw_context failed: {type(exc).__name__}: {exc}"})


def handle_omw_ingest(args: dict, **kwargs) -> str:
    try:
        url = str(args.get("url") or "").strip()
        if not url:
            return _dump({"error": "url is required"})
        ok, reason = _is_public_url(url)
        if not ok:
            return _dump({"error": reason})
        cmd = ["fetch"]
        vault = args.get("vault")
        if vault:
            cmd.append(f"--vault={vault}")
        cmd += ["--", url]
        return _dump(omw_client.run_omw(cmd, timeout=FETCH_TIMEOUT))
    except Exception as exc:
        return _dump({"error": f"omw_ingest failed: {type(exc).__name__}: {exc}"})


def handle_omw_command(raw_args: str = "", **kwargs) -> str:
    """`/omw` 슬래시 커맨드 — omw status를 사람이 읽기 좋게 요약."""
    try:
        res = omw_client.run_omw(["status"])
        if "error" in res:
            hint = res.get("hint", "")
            return f"omw 상태 확인 실패: {res['error']}" + (f"\n{hint}" if hint else "")
        active = res.get("active") or {}
        if not active:
            return f"등록된 vault {res.get('vault_count', 0)}개 — 활성 vault가 없습니다. `omw vault use <name>`으로 선택하세요."
        return (
            f"omw 활성 vault: {active.get('name')} ({active.get('mode')} 모드, {active.get('type')})\n"
            f"경로: {active.get('path')}\n"
            f"전체 vault: {res.get('vault_count')}개\n"
            f"도구: omw_find(검색) · omw_context(출처 포함 본문) · omw_ingest(URL 수집)"
        )
    except Exception as exc:
        return f"/omw 실패: {type(exc).__name__}: {exc}"
