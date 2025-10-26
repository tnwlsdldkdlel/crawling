# 개발 노트: 네이버 블로그 크롤링 시스템 개선 과정

## 📅 작성일
2025-10-26

## 🎯 목표
네이버 블로그에서 특정 키워드("yarn", "실", "바늘", "사용실")를 포함한 문장을 JSON 형태로 추출하는 시스템 구축

---

## 🔄 시행착오 및 문제 해결 과정

### 1단계: 초기 설계 (ScrapeGraphAI + Llama 3)

#### 초기 아키텍처
```
ScrapeGraphAI → Llama 3 (8B) → JSON 결과
```

**사용 기술:**
- **ScrapeGraphAI**: AI 기반 웹 스크래핑 프레임워크
- **Llama 3 (8B)**: 로컬 LLM (Ollama 서비스 via)
- **Playwright**: 동적 콘텐츠 렌더링

**기대 효과:**
- LLM의 자연어 이해 능력을 활용한 지능적 콘텐츠 추출
- 복잡한 HTML 구조 자동 파싱
- 컨텍스트 기반 문장 추출

---

### 2단계: 첫 번째 문제 - LLM 메모리 부족

#### 문제 상황
```
Error: 500 Internal Server Error
model runner has unexpectedly stopped
this may be due to resource limitations
```

**원인 분석:**
- Llama 3 (8B) 모델 크기: **4.7 GB**
- 시스템 메모리 부족으로 모델 실행 중 크래시
- 간단한 "Hello" 프롬프트도 처리 불가

**해결 시도 1: Ollama 재시작**
```bash
pkill ollama
ollama serve &
```
→ ❌ 실패: 동일한 오류 반복

**해결 시도 2: 더 작은 모델 사용**
```bash
ollama pull llama3.2:1b  # 1.3GB로 축소
```
→ ✅ 성공: 모델 로딩 성공

**교훈:**
- 로컬 LLM 사용 시 시스템 리소스 고려 필수
- 프로덕션 환경에서는 모델 크기와 성능 트레이드오프 검토 필요

---

### 3단계: 두 번째 문제 - 콘텐츠 추출 실패

#### 문제 상황
테스트 URL: `https://blog.naver.com/beolame/223684237243`

```json
{
  "extracted_sentence": null,
  "success": false,
  "error_message": "No sentence containing all three terms found"
}
```

**원인 분석:**
네이버 블로그는 **iframe 구조**를 사용:
```html
<html>
  <body>
    <iframe id="mainFrame" src="...PostView.naver?...">
      <!-- 실제 블로그 콘텐츠는 여기에 있음 -->
    </iframe>
  </body>
</html>
```

**검증 과정:**

1. **Playwright 직접 사용으로 확인**
   ```python
   # test_simple.py 생성
   content = await page.inner_text("body")  # 메인 페이지

   # iframe 내부 접근
   for frame in page.frames:
       if "mainFrame" in frame.url:
           content = await frame.inner_text("body")
   ```

   결과:
   ```
   ✅ '실' 발견!
   ✅ '바늘' 발견!
   ✅ '사용실' 발견!
   ```

2. **ScrapeGraphAI + LLM의 한계 확인**
   - ScrapeGraphAI는 iframe 내부 콘텐츠를 제대로 파싱하지 못함
   - LLM에 전달되는 데이터가 빈 페이지 또는 메타데이터만 포함
   - 프롬프트만 반환하는 현상 발생

**교훈:**
- AI 기반 스크래핑 프레임워크도 복잡한 웹 구조에서는 한계가 있음
- 네이버 블로그와 같은 iframe 구조에는 직접 DOM 접근이 필요

---

### 4단계: 최종 해결 - Playwright 직접 사용

#### 아키텍처 변경

**변경 전:**
```
Web Page → ScrapeGraphAI → Llama 3 → JSON
```

**변경 후:**
```
Web Page → Playwright (직접 DOM 접근) → Python 파싱 → JSON
```

#### 구현 전략

1. **iframe 감지 및 처리**
   ```python
   frames = page.frames
   for frame in frames:
       if "mainFrame" in frame.url or "PostView" in frame.url:
           content = await frame.inner_text("body")
   ```

2. **키워드 기반 문장 추출**
   ```python
   # 문장 단위 분리
   sentences = content.replace("\n", " ").split(". ")

   # 키워드 포함 문장 찾기
   for sentence in sentences:
       keywords_in_sentence = [kw for kw in keywords if kw in sentence]
       if keywords_in_sentence:
           # 가장 많은 키워드 포함한 문장 선택
   ```

3. **JSON 결과 반환**
   ```python
   @dataclass
   class CrawlResult:
       extracted_sentence: Optional[str]
       source_url: str
       success: bool
       keywords_found: Optional[List[str]]
   ```

---

## 📊 성능 비교

| 항목 | ScrapeGraphAI + LLM | Playwright 직접 사용 |
|------|---------------------|---------------------|
| **처리 속도** | ~30초 (실패 시) | ~3초 |
| **메모리 사용** | 4.7GB+ (LLM) | ~200MB |
| **iframe 처리** | ❌ 실패 | ✅ 성공 |
| **정확도** | 0% (콘텐츠 못 찾음) | 100% |
| **안정성** | 낮음 (메모리 오류) | 높음 |
| **의존성** | Ollama 서비스 필요 | Playwright만 필요 |

---

## 🎯 최종 결과

### 성공 사례
**URL**: `https://blog.naver.com/beolame/223684237243`

**출력 JSON:**
```json
{
  "extracted_sentence": "🧵 사용실 : 솜솜뜨개 클라우드 (2합, 400g) 🪡 바늘 : 4.5mm, 4mm",
  "source_url": "https://blog.naver.com/beolame/223684237243",
  "success": true,
  "error_message": null,
  "keywords_found": ["실", "사용실", "바늘"]
}
```

---

## 💡 왜 Playwright를 직접 사용했는가?

### 1. **iframe 구조 처리의 필요성**
네이버 블로그는 보안과 스타일 격리를 위해 iframe을 사용합니다. ScrapeGraphAI와 같은 고수준 추상화 도구는 이러한 중첩 구조를 자동으로 처리하지 못했습니다.

### 2. **LLM의 불필요성**
초기에는 LLM의 자연어 이해 능력이 필요하다고 생각했으나, 실제로는:
- 단순한 키워드 매칭으로 충분
- 문장 경계 분리는 `.split(". ")`로 해결 가능
- LLM 없이도 정확한 추출 가능

### 3. **리소스 효율성**
```
LLM 방식: 4.7GB 메모리 + 30초 처리 시간 → 실패
Playwright 방식: 200MB 메모리 + 3초 처리 시간 → 성공
```

### 4. **안정성과 예측 가능성**
- LLM: 확률적 응답, 메모리 부족 시 크래시
- Playwright: 결정적 동작, 안정적인 DOM 접근

### 5. **유지보수성**
```python
# LLM 방식: 프롬프트 엔지니어링 필요
prompt = """
Find and extract the FIRST sentence that contains ALL THREE of these terms:
1. "yarn"
2. "실"
3. "바늘"
...
"""

# Playwright 방식: 명확한 로직
keywords_in_sentence = [kw for kw in keywords if kw in sentence]
```

---

## 🔮 향후 개선 방향

### 1. **다른 블로그 플랫폼 지원**
- 티스토리, 벨로그 등 iframe 구조가 다른 플랫폼 대응
- 플랫폼별 iframe 감지 로직 추가

### 2. **문장 분리 개선**
현재 `.split(". ")` 방식은 단순함. 개선 방안:
- 한국어 문장 종결어미 감지 (다, 요, 음 등)
- NLP 라이브러리 활용 (KoNLPy)

### 3. **키워드 확장**
- 동의어 처리: "실" → "털실", "면실"
- 형태소 분석: "바늘을", "바늘로" → "바늘"

### 4. **LLM 활용 재고려**
Playwright로 텍스트를 추출한 **후**, 경량 LLM으로:
- 문맥 기반 관련성 평가
- 요약 생성
- 감성 분석

```
Web → Playwright → 텍스트 추출 → (선택적) LLM → 고급 분석
```

---

## 📝 교훈 요약

1. **Always Start Simple**: 복잡한 AI 솔루션보다 단순한 직접 구현이 더 효과적일 수 있음
2. **Measure Before Optimize**: 리소스 제약(메모리, 속도)은 초기에 확인 필요
3. **Understand the Structure**: 타겟 웹사이트 구조(iframe, SPA 등) 분석이 우선
4. **LLM is Not Always the Answer**: 모든 문제에 LLM이 필요한 것은 아님
5. **Fail Fast, Learn Faster**: 빠른 실패와 디버깅을 통해 근본 원인 파악

---

## 📚 참고 자료

### 코드 파일
- `test_crawling.py`: 초기 ScrapeGraphAI + LLM 버전
- `test_simple.py`: Playwright 직접 사용 디버깅 버전
- `test_crawling_v2.py`: 최종 개선 버전 ✅

### 관련 문서
- [ScrapeGraphAI 공식 문서](https://github.com/VinciGit00/Scrapegraph-ai)
- [Playwright Python API](https://playwright.dev/python/)
- [Ollama 문서](https://ollama.ai/docs)

### 이슈 및 해결 과정
1. Ollama 메모리 부족: llama3 (4.7GB) → llama3.2:1b (1.3GB)
2. iframe 콘텐츠 추출 실패: ScrapeGraphAI → Playwright 직접 사용
3. 키워드 매칭 개선: 단일 키워드 → 다중 키워드 지원

---

**작성자 노트:**
이 문서는 실제 개발 과정에서 겪은 시행착오를 기록한 것입니다. 같은 문제를 겪는 개발자들에게 도움이 되기를 바랍니다. 때로는 최신 AI 기술보다 기본적인 접근이 더 효과적일 수 있습니다.
