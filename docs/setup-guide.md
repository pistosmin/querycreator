# 설정 가이드

QueryCreator를 처음 구성하는 절차를 단계별로 설명합니다.

---

## 1. Agent 앱 등록

> **플레이스홀더**: Agent 플랫폼의 앱 등록 절차는 조직 내부 가이드를 참조하세요.

일반적인 절차:

1. Agent 관리 콘솔에 로그인합니다.
2. "새 앱 등록" → MCP 서버 유형 선택합니다.
3. 서버 엔드포인트 URL과 인증 토큰을 입력합니다.
4. 제공할 도구(`get_metadata`, `execute_query`, `call_function`)를 등록합니다.
5. 앱 ID와 시크릿을 발급받아 환경 변수에 저장합니다.

---

## 2. 환경 변수

`.env` 파일 또는 시스템 환경 변수로 설정합니다.

| 변수명 | 필수 | 기본값 | 설명 |
|--------|------|--------|------|
| `QC_DB_HOST` | ✓ | — | Oracle DB 호스트명 또는 IP |
| `QC_DB_PORT` | — | `1521` | Oracle DB 리스너 포트 |
| `QC_DB_SERVICE` | ✓ | — | Oracle 서비스명 (SID 또는 서비스명) |
| `QC_DB_USER` | ✓ | — | DB 접속 사용자 (SELECT 전용 계정 권장) |
| `QC_DB_PASSWORD` | ✓ | — | DB 접속 비밀번호 |
| `QC_SCHEMAS` | ✓ | — | 조회 대상 스키마 목록 (쉼표 구분, 예: `HR,SALES,FIN`) |

### 예시 `.env`

```dotenv
QC_DB_HOST=oracle-prod.internal
QC_DB_PORT=1521
QC_DB_SERVICE=ORCL
QC_DB_USER=qc_readonly
QC_DB_PASSWORD=s3cur3p@ss
QC_SCHEMAS=HR,SALES,FIN
```

---

## 3. 업무 사전 작성

업무 사전은 LLM이 테이블·컬럼의 업무 의미를 이해하도록 돕는 YAML 파일입니다.

### 템플릿 복사

```bash
cp data/dictionaries/template.yaml data/dictionaries/<SCHEMA_NAME>.yaml
```

### YAML 편집

```yaml
schema: SALES
description: 영업 관련 테이블 모음

tables:
  ORDERS:
    description: 고객 주문 정보
    columns:
      ORDER_ID:
        description: 주문 고유 식별자
      ORDER_DATE:
        description: 주문 접수 일자
      CUSTOMER_ID:
        description: 고객 ID (CUSTOMERS 테이블 참조)
      STATUS:
        description: 주문 상태 (PENDING/CONFIRMED/SHIPPED/CANCELLED)
```

---

## 4. 메타데이터 자동 수집

서버 시작 시 `QC_SCHEMAS`에 지정된 모든 스키마의 메타데이터를 자동으로 수집합니다.

- 수집 항목: 테이블, 컬럼, 데이터 타입, 주석, 인덱스, 저장 함수
- 저장 위치: `data/metadata/<SCHEMA_NAME>.json`

### 수동 재수집

```bash
python -m querycreator --collect-metadata
```

---

## 5. 테스트 실행

환경 구성 완료 후 테스트 스위트를 실행해 정상 동작을 확인합니다.

```bash
export PATH="$HOME/.pyenv/versions/3.11.0/bin:$PATH"
python -m pytest tests/ -v --tb=short --cov=querycreator --cov-report=term-missing
```

모든 테스트가 통과하면 서버를 기동할 준비가 완료된 것입니다.
