# 데이터 처리 전략: 원본 저장 vs 정제 후 저장

## 🤔 질문
크롤링한 JSON 데이터를 **원본 그대로 저장**할 것인가, 아니면 **정규식으로 정제 후 저장**할 것인가?

---

## 📊 두 가지 접근 방식 비교

### 방식 1: 원본 저장 후 처리
```
크롤링 → 원본 JSON 저장 (DB) → 필요 시 정규식 처리 → 사용
```

### 방식 2: 정제 후 저장
```
크롤링 → 정규식 처리 → 정제된 데이터 저장 (DB) → 사용
```

---

## ✅ 권장: 원본 저장 + 정제 데이터 병행 저장

### 아키텍처
```
크롤링 → 원본 저장 → 정규식 처리 → 정제 데이터 추가 컬럼 저장
         (raw_data)              (processed_data)
```

---

## 🎯 원본 저장을 권장하는 이유

### 1. **데이터 복구 가능성**
정제 로직에 버그가 있을 경우 원본으로 되돌릴 수 있습니다.

```python
# 예시: 잘못된 정규식
# 버그: "4.5mm" → "45mm" (소수점 제거 실수)
wrong_pattern = r'(\d+)\.(\d+)mm'
wrong_result = re.sub(wrong_pattern, r'\1\2mm', text)

# 원본이 있으면 재처리 가능
# 원본이 없으면 데이터 손실
```

### 2. **정제 규칙 변경 대응**
비즈니스 요구사항이 변경되어도 원본에서 재처리 가능합니다.

```python
# 초기 요구사항: 바늘 사이즈만 추출
# "4.5mm, 4mm" → ["4.5mm", "4mm"]

# 변경된 요구사항: 바늘 사이즈 + 단위 분리
# "4.5mm, 4mm" → [{"size": 4.5, "unit": "mm"}, {"size": 4, "unit": "mm"}]

# 원본이 있으면 새로운 규칙으로 재처리 가능
```

### 3. **디버깅 및 분석**
원본 데이터를 보면서 정규식 패턴을 개선할 수 있습니다.

```python
# 원본 확인
raw_text = "사용실 : 솜솜뜨개 클라우드 (2합, 400g)"

# 패턴 테스트
pattern1 = r'(\d+)합'  # → "2합"
pattern2 = r'(\d+)g'   # → "400g"

# 원본이 없으면 패턴 검증 어려움
```

### 4. **감사 추적 (Audit Trail)**
누가, 언제, 무엇을 크롤링했는지 추적 가능합니다.

```sql
SELECT
    raw_data,
    processed_data,
    created_at,
    processing_version
FROM blog_extractions
WHERE source_url = '...'
ORDER BY created_at DESC;
```

### 5. **머신러닝 학습 데이터**
향후 ML 모델 학습 시 원본 데이터가 필요할 수 있습니다.

---

## 🏗️ 추천 데이터베이스 스키마

### 옵션 A: 단일 테이블 (간단한 경우)

```sql
CREATE TABLE blog_extractions (
    id SERIAL PRIMARY KEY,

    -- 메타데이터
    source_url TEXT NOT NULL,
    crawled_at TIMESTAMP DEFAULT NOW(),

    -- 원본 데이터 (JSON)
    raw_content JSONB NOT NULL,

    -- 정제된 데이터
    extracted_sentence TEXT,

    -- 정규식 추출 필드들
    yarn_type TEXT,              -- "솜솜뜨개 클라우드"
    yarn_weight TEXT,            -- "2합"
    yarn_amount TEXT,            -- "400g"
    needle_sizes TEXT[],         -- ["4.5mm", "4mm"]

    -- 메타데이터
    keywords_found TEXT[],
    processing_status TEXT,      -- 'pending', 'processed', 'failed'
    processing_error TEXT,
    processing_version INTEGER DEFAULT 1
);

-- 인덱스
CREATE INDEX idx_source_url ON blog_extractions(source_url);
CREATE INDEX idx_processing_status ON blog_extractions(processing_status);
CREATE INDEX idx_crawled_at ON blog_extractions(crawled_at DESC);
```

### 옵션 B: 분리된 테이블 (복잡한 경우)

```sql
-- 원본 데이터 테이블
CREATE TABLE raw_crawl_data (
    id SERIAL PRIMARY KEY,
    source_url TEXT NOT NULL,
    raw_content JSONB NOT NULL,
    crawled_at TIMESTAMP DEFAULT NOW()
);

-- 정제된 데이터 테이블
CREATE TABLE processed_yarn_data (
    id SERIAL PRIMARY KEY,
    raw_data_id INTEGER REFERENCES raw_crawl_data(id),

    -- 정제된 필드들
    yarn_type TEXT,
    yarn_weight_value NUMERIC,
    yarn_weight_unit TEXT,
    yarn_amount_value NUMERIC,
    yarn_amount_unit TEXT,

    -- 바늘 정보 (정규화)
    processed_at TIMESTAMP DEFAULT NOW(),
    processing_version INTEGER DEFAULT 1
);

-- 바늘 정보 별도 테이블
CREATE TABLE needle_sizes (
    id SERIAL PRIMARY KEY,
    processed_data_id INTEGER REFERENCES processed_yarn_data(id),
    size_value NUMERIC,
    size_unit TEXT
);
```

---

## 💻 구현 예시

### 1. 크롤링 → 원본 저장

```python
from dataclasses import dataclass
from typing import List, Optional
import json
import re

@dataclass
class RawCrawlResult:
    """원본 크롤링 결과"""
    source_url: str
    raw_content: dict  # 전체 JSON
    extracted_sentence: str
    keywords_found: List[str]

class DatabaseManager:
    def save_raw_data(self, result: RawCrawlResult) -> int:
        """원본 데이터 저장"""
        query = """
        INSERT INTO blog_extractions
        (source_url, raw_content, extracted_sentence, keywords_found, processing_status)
        VALUES (%s, %s, %s, %s, 'pending')
        RETURNING id
        """

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    result.source_url,
                    json.dumps(result.raw_content, ensure_ascii=False),
                    result.extracted_sentence,
                    result.keywords_found
                ))
                record_id = cur.fetchone()[0]
                conn.commit()

        return record_id
```

### 2. 정규식 처리 (별도 프로세스)

```python
import re
from typing import Dict, List, Optional

class YarnDataProcessor:
    """실 관련 데이터 정규식 처리"""

    @staticmethod
    def extract_yarn_info(text: str) -> Dict:
        """정규식으로 실 정보 추출"""

        result = {
            "yarn_type": None,
            "yarn_weight": None,
            "yarn_amount": None,
            "needle_sizes": []
        }

        # 1. 사용실 타입 추출
        # 예: "사용실 : 솜솜뜨개 클라우드"
        yarn_type_pattern = r'사용실\s*[:：]\s*([^\(]+)'
        yarn_type_match = re.search(yarn_type_pattern, text)
        if yarn_type_match:
            result["yarn_type"] = yarn_type_match.group(1).strip()

        # 2. 실 무게 (합) 추출
        # 예: "2합"
        weight_pattern = r'(\d+)\s*합'
        weight_match = re.search(weight_pattern, text)
        if weight_match:
            result["yarn_weight"] = weight_match.group(1) + "합"

        # 3. 실 양 추출
        # 예: "400g"
        amount_pattern = r'(\d+)\s*g'
        amount_match = re.search(amount_pattern, text)
        if amount_match:
            result["yarn_amount"] = amount_match.group(1) + "g"

        # 4. 바늘 사이즈 추출 (여러 개)
        # 예: "4.5mm", "4mm"
        needle_pattern = r'(\d+(?:\.\d+)?)\s*mm'
        needle_matches = re.findall(needle_pattern, text)
        if needle_matches:
            result["needle_sizes"] = [f"{size}mm" for size in needle_matches]

        return result

    @staticmethod
    def process_record(record_id: int, db_manager: 'DatabaseManager') -> bool:
        """DB 레코드 처리"""
        try:
            # 1. 원본 데이터 가져오기
            query = """
            SELECT extracted_sentence
            FROM blog_extractions
            WHERE id = %s AND processing_status = 'pending'
            """

            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (record_id,))
                    row = cur.fetchone()

                    if not row:
                        return False

                    extracted_sentence = row[0]

            # 2. 정규식 처리
            processed_data = YarnDataProcessor.extract_yarn_info(extracted_sentence)

            # 3. 처리된 데이터 저장
            update_query = """
            UPDATE blog_extractions
            SET
                yarn_type = %s,
                yarn_weight = %s,
                yarn_amount = %s,
                needle_sizes = %s,
                processing_status = 'processed',
                processing_version = 1
            WHERE id = %s
            """

            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(update_query, (
                        processed_data["yarn_type"],
                        processed_data["yarn_weight"],
                        processed_data["yarn_amount"],
                        processed_data["needle_sizes"],
                        record_id
                    ))
                    conn.commit()

            return True

        except Exception as e:
            # 에러 발생 시 상태 업데이트
            error_query = """
            UPDATE blog_extractions
            SET processing_status = 'failed', processing_error = %s
            WHERE id = %s
            """

            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(error_query, (str(e), record_id))
                    conn.commit()

            return False
```

### 3. 배치 처리

```python
class BatchProcessor:
    """미처리 레코드 일괄 처리"""

    @staticmethod
    def process_pending_records(db_manager: 'DatabaseManager') -> Dict:
        """대기 중인 모든 레코드 처리"""

        # 미처리 레코드 조회
        query = """
        SELECT id
        FROM blog_extractions
        WHERE processing_status = 'pending'
        ORDER BY crawled_at ASC
        """

        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                pending_ids = [row[0] for row in cur.fetchall()]

        # 처리 결과
        results = {
            "total": len(pending_ids),
            "success": 0,
            "failed": 0
        }

        # 각 레코드 처리
        for record_id in pending_ids:
            if YarnDataProcessor.process_record(record_id, db_manager):
                results["success"] += 1
            else:
                results["failed"] += 1

        return results
```

---

## 🔄 워크플로우 예시

### 실시간 처리
```python
# 1. 크롤링
result = await crawl_naver_blog(url, keywords)

# 2. 원본 저장
record_id = db_manager.save_raw_data(result)

# 3. 즉시 처리 (선택사항)
YarnDataProcessor.process_record(record_id, db_manager)
```

### 배치 처리
```python
# 1. 크롤링만 수행 (빠름)
for url in urls:
    result = await crawl_naver_blog(url, keywords)
    db_manager.save_raw_data(result)

# 2. 나중에 일괄 처리
results = BatchProcessor.process_pending_records(db_manager)
print(f"처리 완료: {results['success']}/{results['total']}")
```

---

## 🎨 정규식 패턴 예시

```python
class RegexPatterns:
    """자주 사용하는 정규식 패턴 모음"""

    # 실 관련
    YARN_TYPE = r'사용실\s*[:：]\s*([^\(]+)'
    YARN_WEIGHT = r'(\d+)\s*합'
    YARN_AMOUNT = r'(\d+(?:\.\d+)?)\s*g'

    # 바늘 관련
    NEEDLE_SIZE = r'(\d+(?:\.\d+)?)\s*mm'
    NEEDLE_TYPE = r'(대바늘|코바늘|돗바늘|막바늘)'

    # 기간
    DATE_RANGE = r'(\d{2}\.\d{1,2}\.\d{1,2})\s*~\s*(\d{1,2}\.\d{1,2})'

    # 브랜드
    BRAND = r'(치아오구|클로버|튤립)'

    @classmethod
    def extract_all(cls, text: str) -> Dict:
        """모든 패턴 적용"""
        return {
            "yarn_type": re.search(cls.YARN_TYPE, text),
            "yarn_weight": re.search(cls.YARN_WEIGHT, text),
            "yarn_amount": re.search(cls.YARN_AMOUNT, text),
            "needle_sizes": re.findall(cls.NEEDLE_SIZE, text),
            "needle_types": re.findall(cls.NEEDLE_TYPE, text),
            "date_range": re.search(cls.DATE_RANGE, text),
            "brands": re.findall(cls.BRAND, text)
        }
```

---

## 📈 장단점 비교표

| 구분 | 원본 저장 후 처리 | 정제 후 저장 |
|------|------------------|-------------|
| **데이터 안정성** | ✅ 높음 (복구 가능) | ⚠️ 낮음 (원본 손실) |
| **저장 공간** | ⚠️ 더 많이 필요 | ✅ 적게 필요 |
| **처리 속도** | ⚠️ 2단계 (저장 + 처리) | ✅ 1단계 |
| **유연성** | ✅ 높음 (재처리 가능) | ❌ 낮음 |
| **디버깅** | ✅ 쉬움 | ⚠️ 어려움 |
| **규칙 변경** | ✅ 쉬움 | ❌ 어려움 |
| **복잡도** | ⚠️ 약간 높음 | ✅ 낮음 |

---

## 🎯 최종 권장 사항

### ✅ **원본 저장 + 정제 데이터 병행**을 권장합니다

**이유:**
1. 디스크는 저렴하지만, 데이터 손실은 복구 불가능
2. 정규식 로직은 변경될 가능성이 높음
3. 원본 데이터는 향후 다양한 용도로 활용 가능
4. PostgreSQL의 JSONB는 인덱싱과 쿼리 모두 효율적

**구현 팁:**
```python
# raw_content에 전체 JSON 저장
raw_content = {
    "extracted_sentence": "...",
    "full_text": "...",
    "keywords_found": [...],
    "metadata": {
        "crawled_at": "...",
        "user_agent": "..."
    }
}

# 별도 컬럼에 정제된 데이터 저장
yarn_type = "솜솜뜨개 클라우드"
needle_sizes = ["4.5mm", "4mm"]
```

---

## 💾 디스크 용량 고려사항

### 예상 데이터 크기

**원본 JSON (평균)**
- 한글 블로그 포스트 1개: ~5KB
- 1,000개: ~5MB
- 100,000개: ~500MB

**결론:** 현대 환경에서 원본 저장 비용은 무시할 수 있는 수준

---

**최종 결론:** 처음에는 귀찮아 보일 수 있지만, 원본 데이터를 저장하는 것이 장기적으로 훨씬 안전하고 유연한 선택입니다. 💪
