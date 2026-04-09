# 안전 규칙

QueryCreator는 Oracle DB를 안전하게 조회하기 위해 7가지 핵심 안전 규칙을 적용합니다.
이 규칙들은 데이터 변조 방지, 성능 보호, 보안 강화를 목적으로 합니다.

---

## 안전 규칙 테이블

| # | 규칙명 | 설명 | 기본값 | 위반 시 동작 |
|---|--------|------|--------|------------|
| 1 | **SELECT 전용** | DML(INSERT/UPDATE/DELETE) 및 DDL(CREATE/DROP 등) 구문 차단 | 항상 적용 | `VALIDATION_FAILED` 오류 반환 |
| 2 | **SELECT * 금지** | 전체 컬럼 와일드카드(`SELECT *`) 사용 금지 | 항상 적용 | `VALIDATION_FAILED` 오류 반환 |
| 3 | **앞자리 와일드카드 금지** | LIKE 조건에서 앞자리 `%` 와일드카드 사용 금지 (예: `LIKE '%홍길동'`) | 항상 적용 | `VALIDATION_FAILED` 오류 반환 |
| 4 | **대용량 테이블 WHERE 필수** | 지정된 대용량 테이블 조회 시 WHERE 조건 필수 | 설정 가능 | `VALIDATION_FAILED` 오류 반환 |
| 5 | **타임아웃 30초** | 쿼리 실행 시간이 30초를 초과하면 강제 종료 | 30초 | `QUERY_TIMEOUT` 오류 반환 |
| 6 | **최대 1000행** | 단일 쿼리의 반환 행 수를 최대 1000행으로 제한 | 1000행 | 초과분 자동 잘라냄 (`truncated: true`) |
| 7 | **다중 구문 금지** | 세미콜론으로 구분된 여러 SQL 구문 동시 실행 금지 | 항상 적용 | `VALIDATION_FAILED` 오류 반환 |

---

## 규칙 상세 설명

### 규칙 1: SELECT 전용

데이터 변조를 원천 차단합니다. `SELECT`로 시작하지 않는 모든 쿼리는 실행 전에 거부됩니다.

차단 예시:
```sql
INSERT INTO ORDERS VALUES (...)    -- 차단
UPDATE ORDERS SET STATUS = 'A'    -- 차단
DELETE FROM ORDERS WHERE ...      -- 차단
CREATE TABLE TEMP AS SELECT ...   -- 차단
```

### 규칙 2: SELECT * 금지

불필요한 데이터 전송과 성능 저하를 방지합니다.

```sql
SELECT * FROM ORDERS              -- 차단
SELECT ORDER_ID, ORDER_DATE FROM ORDERS  -- 허용
```

### 규칙 3: 앞자리 와일드카드 금지

인덱스를 무효화하는 앞자리 `%` LIKE 패턴을 금지합니다.

```sql
WHERE NAME LIKE '%홍길동'          -- 차단 (풀스캔 유발)
WHERE NAME LIKE '홍길동%'          -- 허용 (인덱스 활용 가능)
WHERE NAME LIKE '%길동%'           -- 차단 (앞자리 % 포함)
```

### 규칙 4: 대용량 테이블 WHERE 필수

설정된 대용량 테이블 조회 시 반드시 WHERE 조건이 있어야 합니다.

```sql
SELECT ORDER_ID FROM ORDERS        -- 차단 (ORDERS가 대용량 테이블로 지정된 경우)
SELECT ORDER_ID FROM ORDERS WHERE ORDER_DATE >= SYSDATE - 30  -- 허용
```

### 규칙 5: 타임아웃 30초

30초 이상 실행되는 쿼리는 자동으로 종료됩니다.

### 규칙 6: 최대 1000행

`max_rows` 파라미터로 1~1000 사이의 값을 지정할 수 있습니다.
결과가 지정한 행 수를 초과하면 잘라내고 `truncated: true`를 반환합니다.

### 규칙 7: 다중 구문 금지

SQL 인젝션 방지 및 예측 불가한 동작 차단을 위해 하나의 쿼리만 허용합니다.

```sql
SELECT 1 FROM DUAL; SELECT 2 FROM DUAL  -- 차단 (세미콜론으로 구분된 2개 구문)
```

---

## 커스터마이징 가이드

일부 규칙은 환경 변수 또는 설정 파일로 조정할 수 있습니다.

### 타임아웃 변경

```bash
# 환경 변수로 설정 (초 단위)
export QC_QUERY_TIMEOUT=60
```

### 최대 행 수 변경

```bash
# 기본 최대 행 수 변경 (1000 이하)
export QC_MAX_ROWS=500
```

### 대용량 테이블 지정

`data/knowledge/<SCHEMA>_hints.yaml`에 대용량 테이블을 지정합니다:

```yaml
large_tables:
  - table: ORDERS
    require_where: true
  - table: TRANSACTIONS
    require_where: true
```

### 변경 불가 규칙

규칙 1(SELECT 전용), 규칙 2(SELECT * 금지), 규칙 7(다중 구문 금지)은 보안상 이유로
설정에 관계없이 항상 적용되며 비활성화할 수 없습니다.
