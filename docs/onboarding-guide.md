# 새 스키마 온보딩 가이드

새로운 Oracle 스키마를 QueryCreator에 추가할 때 따라야 할 체크리스트입니다.

---

## 온보딩 체크리스트

### 1단계: SELECT 전용 DB 계정 확인

- [ ] DB 관리자에게 해당 스키마에 대한 SELECT 전용 계정 발급을 요청합니다.
- [ ] 계정이 DML(INSERT, UPDATE, DELETE) 및 DDL 권한을 갖지 않는지 확인합니다.
- [ ] 계정으로 DB 접속 테스트를 수행합니다:
  ```sql
  -- 접속 후 권한 확인
  SELECT * FROM SESSION_PRIVS;
  ```

### 2단계: QC_SCHEMAS에 스키마 추가

- [ ] 환경 변수 `QC_SCHEMAS`에 새 스키마명을 추가합니다:
  ```bash
  # 기존: QC_SCHEMAS=HR,SALES
  # 변경: QC_SCHEMAS=HR,SALES,NEW_SCHEMA
  export QC_SCHEMAS=HR,SALES,NEW_SCHEMA
  ```
- [ ] 프로덕션 환경의 `.env` 파일 또는 시크릿 관리 시스템을 업데이트합니다.

### 3단계: 업무 사전 YAML 작성

- [ ] 템플릿을 복사하여 새 YAML 파일을 생성합니다:
  ```bash
  cp data/dictionaries/template.yaml data/dictionaries/NEW_SCHEMA.yaml
  ```
- [ ] 스키마 설명을 작성합니다.
- [ ] 주요 테이블의 설명을 작성합니다 (최소 핵심 테이블).
- [ ] 각 테이블의 핵심 컬럼에 설명을 추가합니다.
- [ ] 코드성 컬럼(상태, 구분 등)의 허용 값을 명시합니다.

```yaml
schema: NEW_SCHEMA
description: 새 스키마의 업무 설명

tables:
  MAIN_TABLE:
    description: 주요 테이블 설명
    columns:
      ID:
        description: 고유 식별자
      STATUS:
        description: 상태 코드 (A=활성, I=비활성, D=삭제)
```

### 4단계: 업무 사전 유효성 검증

- [ ] 사전 파일의 YAML 문법을 검증합니다:
  ```bash
  python -c "import yaml; yaml.safe_load(open('data/dictionaries/NEW_SCHEMA.yaml'))"
  ```
- [ ] 사전에 기술된 테이블명·컬럼명이 실제 DB와 일치하는지 확인합니다.

### 5단계: 지식 힌트 추가 (선택)

- [ ] 필요 시 인덱스 힌트, 샘플 쿼리, 조인 규칙을 추가합니다:
  ```bash
  cp data/knowledge/template_hints.yaml data/knowledge/NEW_SCHEMA_hints.yaml
  ```
- [ ] 슬로우 쿼리 위험이 있는 대용량 테이블의 인덱스 힌트를 등록합니다.
- [ ] 자주 사용될 것으로 예상되는 조인 패턴을 등록합니다.

### 6단계: 테스트

- [ ] 메타데이터 수집을 실행합니다:
  ```bash
  python -m querycreator --collect-metadata --schema NEW_SCHEMA
  ```
- [ ] `data/metadata/NEW_SCHEMA.json` 파일이 생성되었는지 확인합니다.
- [ ] 단위 테스트를 실행합니다:
  ```bash
  python -m pytest tests/ -v --tb=short
  ```
- [ ] 대표 쿼리 3~5개를 수동으로 테스트합니다 (개발 환경에서).

### 7단계: 배포

- [ ] 변경된 환경 변수와 데이터 파일을 스테이징 환경에 반영합니다.
- [ ] 스테이징에서 smoke test를 수행합니다.
- [ ] 이상 없으면 프로덕션에 배포합니다.
- [ ] 서버 재시작 후 로그에서 스키마 초기화 완료 메시지를 확인합니다.

### 8단계: 파일럿 (5명)

- [ ] 해당 스키마를 주로 사용하는 업무 담당자 5명을 파일럿 사용자로 선정합니다.
- [ ] 파일럿 기간(1~2주) 동안 쿼리 이력과 오류를 모니터링합니다.
- [ ] 사용자 피드백을 수집합니다.

### 9단계: 로그 분석 및 개선

- [ ] 파일럿 기간 종료 후 쿼리 로그를 분석합니다:
  ```bash
  python -m querycreator --query-stats --schema NEW_SCHEMA --date-range 2024-01-01,2024-01-14
  ```
- [ ] 자주 실패한 쿼리 패턴을 파악합니다.
- [ ] 업무 사전과 지식 힌트를 보강합니다.
- [ ] 보강 후 전체 배포로 전환합니다.

---

## 온보딩 완료 기준

- 모든 체크리스트 항목 완료
- 파일럿 사용자 만족도 80% 이상
- 쿼리 성공률 90% 이상
- 슬로우 쿼리(5초 이상) 비율 5% 미만
