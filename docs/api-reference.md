# API 레퍼런스

QueryCreator가 제공하는 3개의 MCP 도구에 대한 상세 명세입니다.

---

## 도구 목록

| 도구명 | 용도 |
|--------|------|
| `get_metadata` | 스키마·테이블·컬럼·함수 메타데이터 조회 |
| `execute_query` | 안전 규칙 검증 후 SELECT 쿼리 실행 |
| `call_function` | Oracle DB 저장 함수 호출 |

---

## get_metadata

스키마의 테이블, 컬럼, 데이터 타입, 주석, 인덱스, 저장 함수 정보를 반환합니다.
LLM이 SQL 생성 전에 DB 구조를 파악하기 위해 호출합니다.

### 입력 (JSON)

```json
{
  "schema": "SALES",
  "table": "ORDERS"
}
```

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `schema` | string | ✓ | 조회할 스키마명 (대소문자 무관) |
| `table` | string | — | 특정 테이블로 조회 범위 제한. 생략 시 스키마 전체 반환 |

### 출력

```json
{
  "schema": "SALES",
  "tables": [
    {
      "name": "ORDERS",
      "description": "고객 주문 정보",
      "columns": [
        {
          "name": "ORDER_ID",
          "type": "NUMBER",
          "nullable": false,
          "description": "주문 고유 식별자"
        },
        {
          "name": "ORDER_DATE",
          "type": "DATE",
          "nullable": false,
          "description": "주문 접수 일자"
        }
      ],
      "indexes": [
        {
          "name": "IDX_ORDERS_DATE",
          "columns": ["ORDER_DATE"],
          "unique": false
        }
      ]
    }
  ],
  "functions": [
    {
      "name": "CALC_DISCOUNT",
      "description": "고객 등급에 따른 할인율 계산",
      "arguments": "customer_id IN NUMBER, order_amount IN NUMBER",
      "return_type": "NUMBER"
    }
  ]
}
```

### 오류 코드

| 코드 | 메시지 | 설명 |
|------|--------|------|
| `SCHEMA_NOT_FOUND` | Schema '{schema}' not found | 등록되지 않은 스키마 요청 |
| `TABLE_NOT_FOUND` | Table '{table}' not found in schema '{schema}' | 존재하지 않는 테이블 지정 |
| `METADATA_UNAVAILABLE` | Metadata not collected for schema '{schema}' | 메타데이터 미수집 상태 |

---

## execute_query

안전 규칙을 통과한 SELECT 쿼리를 실행하고 결과를 반환합니다.

### 입력 (JSON)

```json
{
  "query": "SELECT ORDER_ID, ORDER_DATE, AMOUNT FROM SALES.ORDERS WHERE ORDER_DATE >= SYSDATE - 30",
  "schema": "SALES",
  "max_rows": 100
}
```

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `query` | string | ✓ | 실행할 SQL 쿼리 (SELECT만 허용) |
| `schema` | string | — | 기본 스키마 컨텍스트 |
| `max_rows` | integer | — | 최대 반환 행 수 (기본 100, 최대 1000) |

### 출력

```json
{
  "columns": ["ORDER_ID", "ORDER_DATE", "AMOUNT"],
  "rows": [
    [10001, "2024-03-15", 150000],
    [10002, "2024-03-16", 230000]
  ],
  "row_count": 2,
  "truncated": false,
  "execution_time_ms": 145
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `columns` | array | 컬럼명 목록 |
| `rows` | array | 데이터 행 목록 (각 행은 배열) |
| `row_count` | integer | 반환된 실제 행 수 |
| `truncated` | boolean | max_rows에 의해 잘렸으면 true |
| `execution_time_ms` | integer | 쿼리 실행 시간 (밀리초) |

### 오류 코드

| 코드 | 메시지 | 설명 |
|------|--------|------|
| `VALIDATION_FAILED` | Query validation failed: {reason} | 안전 규칙 위반 (DML, SELECT *, 와일드카드 등) |
| `QUERY_TIMEOUT` | Query exceeded timeout of 30s | 30초 타임아웃 초과 |
| `DB_ERROR` | Database error: {oracle_error} | Oracle DB 오류 |
| `MAX_ROWS_EXCEEDED` | max_rows cannot exceed 1000 | 최대 행 수 초과 요청 |

---

## call_function

Oracle DB에 등록된 저장 함수(Stored Function)를 호출하고 반환값을 돌려줍니다.

### 입력 (JSON)

```json
{
  "schema": "SALES",
  "function_name": "CALC_DISCOUNT",
  "arguments": {
    "customer_id": 12345,
    "order_amount": 500000
  }
}
```

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `schema` | string | ✓ | 함수가 속한 스키마명 |
| `function_name` | string | ✓ | 호출할 함수명 |
| `arguments` | object | — | 함수 인수 (이름-값 쌍). 인수 없는 함수는 생략 가능 |

### 출력

```json
{
  "function": "SALES.CALC_DISCOUNT",
  "result": 50000,
  "return_type": "NUMBER",
  "execution_time_ms": 23
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `function` | string | 호출된 함수의 전체 경로 |
| `result` | any | 함수 반환값 (NUMBER, VARCHAR2, DATE 등) |
| `return_type` | string | Oracle 반환 타입 |
| `execution_time_ms` | integer | 실행 시간 (밀리초) |

### 오류 코드

| 코드 | 메시지 | 설명 |
|------|--------|------|
| `FUNCTION_NOT_FOUND` | Function '{function_name}' not found in schema '{schema}' | 존재하지 않는 함수 |
| `INVALID_ARGUMENTS` | Invalid arguments: {detail} | 인수 타입 불일치 또는 필수 인수 누락 |
| `FUNCTION_ERROR` | Function execution error: {oracle_error} | 함수 실행 중 Oracle 오류 |
| `SCHEMA_NOT_FOUND` | Schema '{schema}' not found | 등록되지 않은 스키마 |
