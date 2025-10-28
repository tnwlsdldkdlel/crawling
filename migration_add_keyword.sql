-- keyword 컬럼 추가
ALTER TABLE public.extractions ADD COLUMN IF NOT EXISTS keyword TEXT;

-- 기존 데이터의 project 값을 keyword로 이동
UPDATE public.extractions
SET keyword = extracted_sentence->>'project'
WHERE extracted_sentence->>'project' IS NOT NULL;

-- extracted_sentence에서 project 필드 제거
UPDATE public.extractions
SET extracted_sentence = extracted_sentence - 'project';

-- 코멘트 추가
COMMENT ON COLUMN public.extractions.keyword IS '검색 키워드 (예: 마들렌자켓)';
