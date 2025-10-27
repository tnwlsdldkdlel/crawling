-- 블로그 콘텐츠 추출 결과를 저장하는 테이블
CREATE TABLE IF NOT EXISTS public.blog_extractions (
    id BIGSERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    extracted_sentence TEXT,
    keywords TEXT[] DEFAULT ARRAY['yarn', '실', '바늘'],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성 (URL 검색 최적화)
CREATE INDEX IF NOT EXISTS idx_blog_extractions_url ON public.blog_extractions(url);

-- 인덱스 생성 (생성일 검색 최적화)
CREATE INDEX IF NOT EXISTS idx_blog_extractions_created_at ON public.blog_extractions(created_at DESC);

-- RLS (Row Level Security) 활성화
ALTER TABLE public.blog_extractions ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 읽기 가능
CREATE POLICY "Enable read access for all users" ON public.blog_extractions
    FOR SELECT USING (true);

-- anon 키로 삽입/업데이트 가능
CREATE POLICY "Enable insert for authenticated users" ON public.blog_extractions
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for authenticated users" ON public.blog_extractions
    FOR UPDATE USING (true);

-- 코멘트 추가
COMMENT ON TABLE public.blog_extractions IS '네이버 블로그에서 추출한 콘텐츠를 저장하는 테이블';
COMMENT ON COLUMN public.blog_extractions.url IS '블로그 포스트 URL';
COMMENT ON COLUMN public.blog_extractions.extracted_sentence IS '추출된 문장 (yarn, 실, 바늘 포함)';
COMMENT ON COLUMN public.blog_extractions.keywords IS '검색에 사용된 키워드 배열';
