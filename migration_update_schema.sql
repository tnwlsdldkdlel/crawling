-- 기존 테이블 수정: keywords 컬럼 삭제 및 extracted_sentence를 JSONB로 변경

-- 1. keywords 컬럼 삭제
ALTER TABLE public.blog_extractions DROP COLUMN IF EXISTS keywords;

-- 2. extracted_sentence 타입을 TEXT에서 JSONB로 변경
ALTER TABLE public.blog_extractions
ALTER COLUMN extracted_sentence TYPE JSONB USING extracted_sentence::jsonb;

-- 3. 코멘트 업데이트
COMMENT ON COLUMN public.blog_extractions.extracted_sentence IS '추출된 구조화된 데이터 (도안, 실, 바늘 등의 정보를 JSON 형태로 저장)';
