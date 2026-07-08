# hermes-omw

**[Hermes Agent](https://github.com/NousResearch/Hermes-Agent)를 위한 cited recall** —
[oh-my-wiki](https://github.com/dandacompany/oh-my-wiki) 지식 vault를 Hermes에 연결하는
브리지 플러그인.

English: [README.md](./README.md)

대부분의 메모리 플러그인은 대화 조각을 감사 불가능한 블랙박스에 자동 저장합니다. hermes-omw는
정반대 포지션입니다: **사람이 검수한 위키**를 도구로 노출해, Hermes가 직접 검토한 페이지에서
**출처(citations)와 함께** 답하게 합니다. 메모리 프로바이더가 아닌 일반 도구 플러그인이라 기존
메모리 시스템과 그대로 공존합니다.

구체적으로는 `plugin.yaml` + `register(ctx)`로 도구 3종과 슬래시 커맨드 1개를 Hermes에 등록하고,
모든 호출을 `omw` CLI를 감싼 표준 라이브러리 전용 subprocess 래퍼 하나로 통과시킵니다.

## 도구

| 도구          | 하는 일                                                           | 래핑 대상         |
| ------------- | ----------------------------------------------------------------- | ----------------- |
| `omw_find`    | 랭킹된 위키 검색(제목/요약/태그/점수). 빠른 조회·페이지 발견용.   | `omw find --json` |
| `omw_context` | 본문 + **citations 매니페스트** 번들. 위키 근거 답변용.           | `omw context`     |
| `omw_ingest`  | 공인 URL을 위키 `raw/`로 수집 + 재색인. URL 전용, 페이지는 안 씀. | `omw fetch`       |
| `/omw-status` | 세션 내 슬래시 커맨드 — 활성 vault 요약.                          | `omw status`      |

모든 도구는 선택적 `vault` 파라미터(기본: 활성 vault)를 받고, 읽기 도구는 `limit`(1–50 클램프)도 받습니다.

## 요구사항

- [oh-my-wiki](https://github.com/dandacompany/oh-my-wiki) CLI: `pipx install oh-my-wiki`
- 활성 wiki 모드 vault:

```bash
omw vault create my-wiki --mode wiki
omw vault use my-wiki
```

`omw` 바이너리가 Hermes의 `PATH`에 없으면 `OMW_BIN` 환경변수로 경로를 지정합니다.

## 설치

Hermes 플러그인은 `~/.hermes/plugins/` 아래에 놓인 디렉토리로, 각각 `plugin.yaml` 매니페스트와
`register(ctx)`를 노출하는 `__init__.py`를 가집니다 — 이 리포는 루트에 이미 그 구조입니다.

### 옵션 A — clone + symlink (개발 시 권장)

```bash
git clone https://github.com/dandacompany/hermes-omw.git ~/src/hermes-omw
mkdir -p ~/.hermes/plugins
ln -s ~/src/hermes-omw ~/.hermes/plugins/omw
```

`cp -r` 복사도 동일하게 동작하며, symlink은 소스 체크아웃에서 `git pull`하면 플러그인에 바로 반영되는 이점이 있습니다.

### 옵션 B — `hermes plugins install`

```bash
hermes plugins install dandacompany/hermes-omw
```

`owner/repo` 축약 또는 전체 git URL을 받아 `~/.hermes/plugins/`로 클론합니다. `Enable 'omw' now? [y/N]`
프롬프트에 `y`, 또는 `--enable` / `--no-enable`로 스크립트 설치 시 프롬프트를 건너뜁니다.

### 확인

```bash
hermes plugins list          # omw, version 0.1.0, not enabled(opt-in 기본)
hermes plugins enable omw
```

활성화 시 `Allow this plugin to replace built-in tools? [y/N]` 프롬프트엔 **no**. hermes-omw는 도구 3종과
커맨드 1개만 등록하고 아무것도 오버라이드하지 않습니다. 세션 재시작(`/reset` 또는 `hermes gateway restart`)
후 연결을 확인합니다:

```
/omw-status
```

> `/omw`가 아닌 `/omw-status`인 이유: oh-my-wiki를 Hermes **스킬**로도 설치한 환경에서는 `/omw`가 스킬
> 로더와 충돌하기 때문입니다.

## 사용

Hermes에게 그냥 말하면 됩니다:

- _"위키에서 attention 관련 페이지 찾아줘"_ → `omw_find`
- _"우리 위키 기준으로 X가 뭐였지? 출처도 알려줘"_ → `omw_context` — 본문을 인용하고 페이지를 출처로 제시
- _"이 링크 위키에 저장해줘 https://…"_ → `omw_ingest` — `raw/`에 저장, 이후 위키 페이지로 정제할 준비 완료

## 설계 노트

- **단일 접근 경로.** 모든 도구 호출은 `omw_client.run_omw()`를 통과합니다 — 표준 라이브러리만 쓰는
  subprocess 래퍼로, 절대 예외를 던지지 않습니다. 미설치·타임아웃·비정상 종료·비JSON 출력 전부 힌트가
  담긴 구조화 에러 JSON으로 돌아옵니다.
- **결정형 쓰기만.** `omw_ingest`는 결정형 `omw fetch`(URL → `raw/` → 재색인)만 래핑합니다. 자유 텍스트
  수집은 LLM 판단이 필요하므로 의도적으로 도구 표면에서 제외 — 그건 대화 속 에이전트의 몫입니다.
- **Hermes 내부 무의존.** Hermes에서 아무것도 import하지 않고 런타임 의존성도 표준 라이브러리뿐이라,
  테스트가 어디서든 돕니다.

## 보안

`omw_ingest`는 네트워크로 나가는 유일한 도구이며, 그 인자(URL)는 LLM이 제어합니다. SSRF를 제한하기 위해
`omw fetch`에 위임하기 **전에** URL을 검증합니다:

- `http`/`https` 스킴만 허용(대소문자 무관).
- 비정규 숫자형 IP 리터럴(정수 `2130706433`, 8진 `0177.0.0.1`, 16진 `0x7f.0.0.1`) 즉시 거부.
- 호스트명을 DNS 해석해 loopback/private/link-local/reserved/multicast/unspecified 주소 —
  클라우드 메타데이터 `169.254.169.254` 포함 — 로 가는 요청을 차단.

**알려진 한계(best-effort):** 실제 페치는 외부 `omw fetch` CLI에 위임되고 그쪽에서 호스트를 **다시**
해석하므로, 이 경계에서 **DNS 리바인딩(TOCTOU)**을 완전히 막을 수는 없습니다. 이를 완전히 닫으려면
해석된 IP를 연결에 고정해야 하는데, 이는 페치를 플러그인 내부에서 수행해야만 가능하며 "얇은 래퍼"
설계에 반합니다. 리터럴·해석-시점 사설 대역이라는 현실적 공격면은 차단하며, 리바인딩 잔여 위험은
문서화된 수용된 한계입니다.

## 구조

표준 Hermes 4-파일 플러그인(`plugin.yaml`, `__init__.py`, `schemas.py`, `tools.py`)에 subprocess 래퍼
`omw_client.py`를 더한 구성입니다. 런타임 의존성은 Python 표준 라이브러리 외엔 없습니다. 소스 체크아웃에서는
omw 설치 없이 테스트가 돕니다(subprocess 경계를 모킹):

```bash
python3 -m pytest tests/ -v
```

## License

[MIT](./LICENSE) © Dante Labs

---

**Dante Labs** · **YouTube** [@dante-labs](https://youtube.com/@dante-labs) · **Email** [dante@dante-labs.com](mailto:dante@dante-labs.com) · **Discord** [Dante Labs Community](https://discord.com/invite/rXyy5e9ujs) · **Support** [Buy Me a Coffee](https://buymeacoffee.com/dante.labs)
