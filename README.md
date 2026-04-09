# QueryCreator

Oracle DB 조회 전용 AI 에이전트 도구 서버입니다. Steel Agent(MCP 호환 LLM 에이전트)와 연동하여 자연어 질의를 안전한 Oracle SQL로 변환하고 실행합니다.

## 아키텍처

```
사용자 → Steel Agent → LLM ↔ QueryCreator → Oracle DB
```

1. 사용자가 Steel Agent에 자연어로 질의합니다.
2. Steel Agent는 LLM을 호출하며, LLM은 QueryCreator 도구를 사용합니다.
3. QueryCreator는 메타데이터·업무 사전·지식 힌트를 활용해 SQL을 생성·검증·실행합니다.
4. 결과가 사용자에게 반환됩니다.

## 제공 도구 (Tools)

| 도구 | 설명 |
|------|------|
| `get_metadata` | 스키마·테이블·컬럼·함수 메타데이터 조회 |
| `execute_query` | 안전 규칙 검증 후 SELECT 쿼리 실행 |
| `call_function` | Oracle DB 저장 함수 호출 |

## 빠른 시작

### 설치

```bash
pip install -e .
```

### 환경 변수 설정

```bash
export QC_DB_HOST=your-oracle-host
export QC_DB_PORT=1521
export QC_DB_SERVICE=your-service-name
export QC_DB_USER=your-username
export QC_DB_PASSWORD=your-password
export QC_SCHEMAS=SCHEMA1,SCHEMA2
```

### 테스트 실행

```bash
python -m pytest tests/ -v --tb=short --cov=querycreator --cov-report=term-missing
```

### 서버 실행

```bash
python -m querycreator
```

## 문서

- [설정 가이드](docs/setup-guide.md) — 환경 구성, 업무 사전 작성, 메타데이터 수집
- [관리자 가이드](docs/admin-guide.md) — 일상 운영, 업무 사전 유지보수, 트러블슈팅
- [온보딩 가이드](docs/onboarding-guide.md) — 새 스키마 추가 체크리스트
- [API 레퍼런스](docs/api-reference.md) — 도구별 입출력 명세
- [안전 규칙](docs/safety-rules.md) — SELECT 전용 제약 및 커스터마이징

## 프로젝트 구조

```
querycreator/
├── src/querycreator/       # 소스 코드
│   ├── app.py              # 앱 진입점 (MCP 서버)
│   ├── core/               # 핵심 로직 (분석기, 검증기, 포매터)
│   ├── db/                 # DB 연결 및 실행
│   ├── admin/              # 메타데이터 수집, 사전, 지식 힌트
│   ├── config/             # 설정 관리
│   └── logging/            # 쿼리 로그
├── data/
│   ├── metadata/           # 자동 수집 메타데이터 (JSON)
│   ├── dictionaries/       # 업무 사전 YAML
│   └── knowledge/          # 운영자 힌트 YAML
├── tests/                  # 테스트 스위트
├── docs/                   # 문서
└── pyproject.toml
```

## 라이선스

내부 사용 전용.
