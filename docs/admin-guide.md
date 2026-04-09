# 관리자 가이드

QueryCreator 운영자를 위한 일상 운영, 업무 사전 유지보수, 트러블슈팅 가이드입니다.

---

## 일상 운영

### 로그 확인

QueryCreator는 쿼리 실행 내역을 로그로 기록합니다.

```bash
# 최근 오류 로그 확인
tail -f logs/querycreator.log | grep ERROR

# 슬로우 쿼리 확인 (기본 임계값: 5초 이상)
grep "SLOW_QUERY" logs/querycreator.log | tail -50

# 일별 쿼리 통계
python -m querycreator --query-stats --date today
```

### 슬로우 쿼리 대응

슬로우 쿼리 로그에서 패턴을 발견하면:

1. 해당 테이블의 인덱스 힌트를 `data/knowledge/` 에 추가합니다.
2. 자주 사용되는 조인 패턴을 `joins` 섹션에 등록합니다.
3. 변경 후 서버를 재시작합니다 (힌트는 핫 리로드 지원).

---

## 업무 사전 유지보수

### 새 테이블 추가

신규 테이블이 DB에 생성된 경우:

1. 메타데이터를 재수집합니다:
   ```bash
   python -m querycreator --collect-metadata --schema SALES
   ```
2. 해당 스키마의 업무 사전 YAML에 테이블 설명을 추가합니다:
   ```yaml
   tables:
     NEW_TABLE:
       description: 새 테이블의 업무 설명
       columns:
         COL1:
           description: 컬럼 설명
   ```

### 새 함수 추가

DB에 새 저장 함수가 추가된 경우:

1. 메타데이터를 재수집합니다.
2. 업무 사전의 `functions` 섹션에 함수 설명과 사용 예시를 추가합니다:
   ```yaml
   functions:
     CALC_DISCOUNT:
       description: 고객 등급에 따른 할인율 계산 함수
       usage: "CALC_DISCOUNT(customer_id, order_amount)"
       returns: "할인 금액 (NUMBER)"
   ```

---

## 운영자 힌트 등록

`data/knowledge/` 디렉터리에 스키마별 YAML 파일로 힌트를 관리합니다.

### 인덱스 힌트

```yaml
# data/knowledge/SALES_hints.yaml
index_hints:
  - table: ORDERS
    hint: "/*+ INDEX(ORDERS IDX_ORDERS_DATE) */"
    condition: "ORDER_DATE 범위 조회 시"
  - table: ORDER_ITEMS
    hint: "/*+ INDEX(ORDER_ITEMS IDX_OI_ORDER_ID) */"
    condition: "ORDER_ID로 상세 조회 시"
```

### 샘플 쿼리 등록

```yaml
sample_queries:
  - description: "월별 매출 집계"
    sql: |
      SELECT TO_CHAR(ORDER_DATE, 'YYYY-MM') AS MONTH,
             SUM(AMOUNT) AS TOTAL_AMOUNT
      FROM ORDERS
      WHERE ORDER_DATE >= ADD_MONTHS(SYSDATE, -12)
      GROUP BY TO_CHAR(ORDER_DATE, 'YYYY-MM')
      ORDER BY 1
```

### 조인 규칙 등록

```yaml
join_rules:
  - tables: [ORDERS, CUSTOMERS]
    join_condition: "ORDERS.CUSTOMER_ID = CUSTOMERS.CUSTOMER_ID"
    note: "항상 CUSTOMER_ID로 조인할 것"
  - tables: [ORDER_ITEMS, PRODUCTS]
    join_condition: "ORDER_ITEMS.PRODUCT_ID = PRODUCTS.PRODUCT_ID"
```

---

## 트러블슈팅

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| 쿼리 타임아웃 | 인덱스 미활용, 대용량 테이블 풀스캔 | `data/knowledge/`에 인덱스 힌트 추가 후 재시도 |
| 잘못된 조회 결과 | 업무 사전의 컬럼·테이블 설명 부족 | 해당 스키마 업무 사전 YAML 보강 (컬럼 의미, 값 범위 명시) |
| 함수 미사용 | 함수 사전 설명 부족 또는 `usage` 예시 누락 | 업무 사전 `functions` 섹션의 `usage` 예시 보강 |
| 조인 오류 | 조인 키 또는 관계 불명확 | `data/knowledge/`의 `join_rules`에 조인 조건 명시 |
| DB 연결 실패 | 환경 변수 오류 또는 네트워크 문제 | 환경 변수 재확인, DB 서버 상태 점검 |
| 메타데이터 오래됨 | 스키마 변경 후 재수집 미실행 | `python -m querycreator --collect-metadata` 실행 |
| 권한 오류 | DB 계정에 조회 권한 누락 | DB 관리자에게 해당 스키마 SELECT 권한 요청 |
