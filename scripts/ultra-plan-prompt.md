# QueryCreator 울트라 플랜 프롬프트

## 프로젝트 개요

Oracle DB 레거시 시스템의 데이터 조회를 LLM이 자동으로 처리하는 Python 앱 개발.
Steel Agent(Allganize) 플랫폼 위에서 서버리스로 동작하며, LLM이 업무 사전과 DB 메타데이터를 참조하여 SQL을 자동 생성/실행하고 사용자에게 결과를 반환한다.

설계 문서: `docs/superpowers/specs/2026-04-09-querycreator-design.md`

## 핵심 제약조건

- **서버 없음**: Steel Agent가 Python 코드를 서버리스로 실행. 별도 서버 운영 불가.
- **SELECT 전용**: Oracle DB는 읽기 전용 계정으로만 접속.
- **LLM 제어 불가**: LLM은 Steel Agent 플랫폼이 제공. 우리는 도구(Tool)만 제공.
- **패키지 제약**: Steel Agent 런타임에서 사용 가능한 패키지 확인 필요 (oracledb thin 모드 사용 전제).
- **개발 과정별 GitHub 커밋/푸시**: 각 단계 완료 시 커밋하고 원격 저장소에 푸시.

## 구현 목표

LLM에게 3가지 도구를 제공:
1. **get_metadata**: 업무 키워드 또는 테이블명으로 메타데이터(업무사전 + 물리구조 + 코드값 + 운영자 힌트) 조회
2. **execute_query**: SQL 검증 후 Oracle에서 실행, 결과 반환 (타임아웃 30초, 최대 1000건)
3. **call_function**: Oracle 스토어드 펑션 호출, 결과 반환

## 구현 단계

### Phase 1: 프로젝트 기반 구축
**목표**: 프로젝트 구조, 설정, DB 연결 확인

- [ ] 프로젝트 디렉토리 구조 생성 (설계 문서의 컴포넌트 구조 참조)
- [ ] `pyproject.toml` 또는 `requirements.txt` 작성 (oracledb, pyyaml 등)
- [ ] `config/db_config.py`: Oracle 접속 설정 (환경변수 기반)
- [ ] `config/schema_config.py`: 대상 스키마 목록 설정
- [ ] `config/safety_rules.py`: 기본 안전규칙 정의
  - SELECT만 허용
  - ROWNUM/FETCH FIRST 강제
  - 타임아웃 30초
  - 결과 1000건 제한
  - SELECT * 금지
  - LIKE '%..%' 차단
- [ ] DB 연결 테스트 스크립트 작성
- [ ] **커밋 & 푸시**: "feat: 프로젝트 기반 구축 - 설정 및 DB 연결"

### Phase 2: 메타데이터 수집기
**목표**: Oracle 딕셔너리에서 물리 메타데이터 자동 수집

- [ ] `core/metadata/collector.py`:
  - ALL_TABLES에서 테이블 목록 + 행 수 추정치 수집
  - ALL_TAB_COLUMNS에서 컬럼 정보 수집
  - ALL_COL_COMMENTS에서 컬럼 코멘트 수집
  - ALL_IND_COLUMNS에서 인덱스 정보 수집
  - ALL_CONSTRAINTS에서 PK/FK 정보 수집
- [ ] 수집 결과를 구조화된 딕셔너리로 반환
- [ ] 수집기 테스트 작성
- [ ] **커밋 & 푸시**: "feat: Oracle 딕셔너리 메타데이터 자동 수집기"

### Phase 3: 업무 사전 시스템
**목표**: 업무 용어 ↔ DB 객체 매핑 관리

- [ ] `data/dictionaries/` 디렉토리에 YAML 스키마 정의
  - 테이블 매핑 (업무명, 설명, 주요컬럼 설명)
  - 펑션 매핑 (업무명, 설명, 파라미터, 용도)
  - 조인 관계 정의
- [ ] `core/metadata/dictionary.py`:
  - YAML 파일 로드/파싱
  - 업무 키워드로 관련 테이블/펑션 검색
  - 사용자가 테이블명 직접 언급 시 바로 매칭
- [ ] 샘플 업무 사전 YAML 작성 (테스트용)
- [ ] 업무 사전 검색 테스트 작성
- [ ] **커밋 & 푸시**: "feat: 업무 사전 시스템 - 업무용어 ↔ DB객체 매핑"

### Phase 4: 메타데이터 통합 카탈로그
**목표**: 물리 메타 + 업무 사전 + 공통코드를 통합 조회

- [ ] `core/metadata/catalog.py`:
  - collector(물리) + dictionary(업무) + 공통코드 통합
  - 키워드 검색 시 관련 테이블의 전체 정보를 한 번에 반환
  - 대용량 테이블 경고, 인덱스 정보, 힌트 포함
- [ ] 공통코드 테이블 조회 및 매핑 기능
- [ ] 카탈로그 통합 테스트 작성
- [ ] **커밋 & 푸시**: "feat: 메타데이터 통합 카탈로그"

### Phase 5: 쿼리 검증기
**목표**: LLM이 생성한 SQL의 안전성 검증

- [ ] `core/query/validator.py`:
  - SQL 파싱: SELECT 문만 허용 (INSERT/UPDATE/DELETE/DROP 등 차단)
  - ROWNUM/FETCH FIRST 존재 확인, 없으면 자동 추가 또는 거부
  - SELECT * 감지 및 차단
  - LIKE '%..%' 패턴 감지 및 차단
  - 대용량 테이블(NUM_ROWS 기반) 사용 시 WHERE 조건 존재 확인
  - 운영자 등록 금지 패턴 체크
- [ ] 검증 결과를 구조화된 객체로 반환 (통과/실패 + 사유)
- [ ] 검증기 단위 테스트 (정상 쿼리, 위험 쿼리, 경계 케이스)
- [ ] **커밋 & 푸시**: "feat: SQL 쿼리 검증기 - 안전규칙 체크"

### Phase 6: 쿼리 실행기
**목표**: 검증된 쿼리를 Oracle에서 안전하게 실행

- [ ] `core/query/executor.py`:
  - 바인드 변수 지원
  - 타임아웃 30초 적용
  - 결과 행 수 제한 (1000건)
  - 실행 시간 측정
  - 에러 핸들링 (ORA 에러 코드별 사용자 친화적 메시지)
- [ ] `core/query/formatter.py`:
  - 쿼리 결과를 LLM이 해석하기 좋은 형태로 포맷팅
  - 코드값 → 업무명 자동 변환 (공통코드 매핑 활용)
  - 결과가 너무 큰 경우 요약 처리
- [ ] 실행기 통합 테스트 작성
- [ ] **커밋 & 푸시**: "feat: Oracle 쿼리 실행기 + 결과 포맷터"

### Phase 7: LLM 도구 정의
**목표**: Steel Agent에서 LLM이 호출할 수 있는 도구(Tool) 구현

- [ ] `core/tools/get_metadata.py`:
  - 입력: 업무 키워드 또는 테이블명
  - 출력: 관련 테이블/컬럼/코드/펑션/힌트 통합 정보
  - 카탈로그 연동
- [ ] `core/tools/execute_query.py`:
  - 입력: SQL 문자열
  - 처리: 검증 → 실행 → 포맷팅
  - 검증 실패 시 사유 반환 (LLM이 수정할 수 있도록)
- [ ] `core/tools/call_function.py`:
  - 입력: 펑션명 + 파라미터
  - 처리: 펑션 카탈로그에서 존재 확인 → 호출 → 결과 반환
- [ ] `app.py`: Steel Agent 진입점 — 도구 등록 및 초기화
- [ ] 도구 통합 테스트 (메타데이터 조회 → 쿼리 생성 시나리오 시뮬레이션)
- [ ] **커밋 & 푸시**: "feat: LLM 도구 정의 - get_metadata, execute_query, call_function"

### Phase 8: 로깅 시스템
**목표**: 쿼리 실행 이력 수집 및 분석 기반 마련

- [ ] `logging/query_log.py`:
  - 실행 이력 기록: 사용자 질문, 생성 SQL, 사용 테이블, 실행시간, 성공/실패, 결과 건수
  - 저장소: 로컬 파일(JSON Lines) 또는 별도 로그 테이블
- [ ] `logging/analyzer.py`:
  - 테이블/조인 패턴별 실행시간 집계
  - 타임아웃/실패 빈도 높은 패턴 감지
  - 개선 필요 대상 리포트 생성
- [ ] 로깅 테스트 작성
- [ ] **커밋 & 푸시**: "feat: 쿼리 실행 로깅 및 분석기"

### Phase 9: 운영자 지식 관리
**목표**: 운영자가 힌트/샘플쿼리/규칙을 점진적으로 등록

- [ ] `core/metadata/knowledge.py`:
  - 인덱스 힌트 등록/조회
  - 샘플 쿼리 등록/조회
  - 위험 테이블 표시
  - 조인 규칙 등록
  - 금지 패턴 등록
- [ ] 지식 저장소: YAML 파일 기반
- [ ] 카탈로그/검증기와 연동 (등록된 지식이 메타데이터 조회와 쿼리 검증에 반영)
- [ ] **커밋 & 푸시**: "feat: 운영자 지식 관리 시스템"

### Phase 10: 통합 테스트 및 E2E 시나리오
**목표**: 전체 흐름 검증

- [ ] E2E 시나리오 테스트:
  - "주문 A001의 공정별 생산량" → 펑션 호출 경로
  - "오늘 생산된 제품 목록" → 직접 쿼리 경로
  - "TB_ORDER에서 CUST_CD가 C100인 건" → 사용자 직접 지정 경로
  - 검증 실패 → 재시도 경로
  - 타임아웃 경로
- [ ] 프롬프트 튜닝: LLM이 도구를 효과적으로 활용하도록 시스템 프롬프트 작성
- [ ] **커밋 & 푸시**: "test: E2E 통합 테스트 및 프롬프트 튜닝"

### Phase 11 (후순위): 관리자 페이지
**목표**: 웹 기반 관리 인터페이스

- [ ] FastAPI 기반 관리자 API
- [ ] 로그 조회 페이지
- [ ] 느린 쿼리 대시보드
- [ ] 업무 사전 편집 UI
- [ ] 운영자 힌트 관리 UI
- [ ] **커밋 & 푸시**: "feat: 관리자 페이지"

## 기술 스택

| 구분 | 기술 | 이유 |
|------|------|------|
| 런타임 | Python 3.11+ | Steel Agent 플랫폼 호환 |
| DB 드라이버 | oracledb (thin 모드) | Oracle Client 설치 불필요, cx_Oracle 후속 |
| 설정 관리 | PyYAML | 업무 사전/지식 파일 관리 |
| SQL 파싱 | sqlparse | 쿼리 검증을 위한 SQL 파싱 |
| 테스트 | pytest | 단위/통합 테스트 |
| 관리자 페이지 | FastAPI + Jinja2 | 후순위, 경량 웹 프레임워크 |

## 주의사항

- Steel Agent의 Python 런타임 제약을 Phase 1에서 반드시 확인할 것 (설치 가능 패키지, 실행 시간 제한, 네트워크 접근 범위)
- Oracle DB thin 모드 연결이 Steel Agent 환경에서 동작하는지 Phase 1에서 검증할 것
- 업무 사전 YAML은 실제 테이블 구조를 반영해야 하므로, 운영자(시스템 담당자)와 협의하여 작성
- 각 Phase 완료 시 반드시 GitHub에 커밋 & 푸시하여 개발 이력 관리
