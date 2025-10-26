-- ================================================
-- Yarn/Pattern Recommendation Service
-- Database Schema Creation Script
-- ================================================
-- Target: Supabase PostgreSQL
-- Purpose: Create tables for yarn and pattern recommendation system
-- ================================================

-- Drop tables if they exist (in reverse order due to foreign keys)
DROP TABLE IF EXISTS "PatternYarnLink" CASCADE;
DROP TABLE IF EXISTS "Patterns" CASCADE;
DROP TABLE IF EXISTS "Yarns" CASCADE;

-- ================================================
-- A. Yarns Table (Yarn Information)
-- ================================================
CREATE TABLE "Yarns" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    manufacturer TEXT,
    color TEXT,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on name for faster searches
CREATE INDEX idx_yarns_name ON "Yarns"(name);

-- Create index on manufacturer for filtering
CREATE INDEX idx_yarns_manufacturer ON "Yarns"(manufacturer);

COMMENT ON TABLE "Yarns" IS 'Stores information about yarns used in knitting/crochet patterns';
COMMENT ON COLUMN "Yarns".id IS 'Unique identifier for each yarn';
COMMENT ON COLUMN "Yarns".name IS 'Yarn name (e.g., Hera Cotton)';
COMMENT ON COLUMN "Yarns".manufacturer IS 'Manufacturer/Brand name';
COMMENT ON COLUMN "Yarns".color IS 'Yarn color information';
COMMENT ON COLUMN "Yarns".url IS 'URL for yarn information or purchase';

-- ================================================
-- B. Patterns Table (Pattern Information)
-- ================================================
CREATE TABLE "Patterns" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on name for faster searches
CREATE INDEX idx_patterns_name ON "Patterns"(name);

COMMENT ON TABLE "Patterns" IS 'Stores information about knitting/crochet patterns';
COMMENT ON COLUMN "Patterns".id IS 'Unique identifier for each pattern';
COMMENT ON COLUMN "Patterns".name IS 'Pattern name (e.g., Four Seasons Cardigan)';
COMMENT ON COLUMN "Patterns".source_url IS 'Original blog/purchase URL for the pattern';

-- ================================================
-- C. PatternYarnLink Table (Pattern-Yarn Relationship)
-- ================================================
CREATE TABLE "PatternYarnLink" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_id UUID NOT NULL,
    yarn_id UUID NOT NULL,
    source_blog_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraints
    CONSTRAINT fk_pattern
        FOREIGN KEY (pattern_id)
        REFERENCES "Patterns"(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_yarn
        FOREIGN KEY (yarn_id)
        REFERENCES "Yarns"(id)
        ON DELETE CASCADE,

    -- Prevent duplicate entries for the same pattern-yarn pair from the same source
    CONSTRAINT unique_pattern_yarn_source UNIQUE (pattern_id, yarn_id, source_blog_url)
);

-- Create indexes for better query performance
CREATE INDEX idx_pyl_pattern_id ON "PatternYarnLink"(pattern_id);
CREATE INDEX idx_pyl_yarn_id ON "PatternYarnLink"(yarn_id);
CREATE INDEX idx_pyl_created_at ON "PatternYarnLink"(created_at DESC);

COMMENT ON TABLE "PatternYarnLink" IS 'Links patterns and yarns that are mentioned together in blog posts';
COMMENT ON COLUMN "PatternYarnLink".id IS 'Unique identifier for the relationship';
COMMENT ON COLUMN "PatternYarnLink".pattern_id IS 'Reference to the pattern';
COMMENT ON COLUMN "PatternYarnLink".yarn_id IS 'Reference to the yarn';
COMMENT ON COLUMN "PatternYarnLink".source_blog_url IS 'Blog URL where this combination was found';

-- ================================================
-- Helper Functions & Views
-- ================================================

-- View: Get most popular yarns for a specific pattern
CREATE OR REPLACE VIEW pattern_popular_yarns AS
SELECT
    p.id as pattern_id,
    p.name as pattern_name,
    y.id as yarn_id,
    y.name as yarn_name,
    y.manufacturer,
    y.color,
    COUNT(pyl.id) as mention_count
FROM "Patterns" p
JOIN "PatternYarnLink" pyl ON p.id = pyl.pattern_id
JOIN "Yarns" y ON pyl.yarn_id = y.id
GROUP BY p.id, p.name, y.id, y.name, y.manufacturer, y.color
ORDER BY p.id, mention_count DESC;

COMMENT ON VIEW pattern_popular_yarns IS 'Shows the most popular yarns used with each pattern';

-- View: Get most popular patterns for a specific yarn
CREATE OR REPLACE VIEW yarn_popular_patterns AS
SELECT
    y.id as yarn_id,
    y.name as yarn_name,
    p.id as pattern_id,
    p.name as pattern_name,
    p.source_url,
    COUNT(pyl.id) as mention_count
FROM "Yarns" y
JOIN "PatternYarnLink" pyl ON y.id = pyl.yarn_id
JOIN "Patterns" p ON pyl.pattern_id = p.id
GROUP BY y.id, y.name, p.id, p.name, p.source_url
ORDER BY y.id, mention_count DESC;

COMMENT ON VIEW yarn_popular_patterns IS 'Shows the most popular patterns made with each yarn';

-- View: Overall yarn popularity
CREATE OR REPLACE VIEW overall_yarn_popularity AS
SELECT
    y.id,
    y.name,
    y.manufacturer,
    COUNT(pyl.id) as total_mentions,
    COUNT(DISTINCT pyl.pattern_id) as pattern_count
FROM "Yarns" y
LEFT JOIN "PatternYarnLink" pyl ON y.id = pyl.yarn_id
GROUP BY y.id, y.name, y.manufacturer
ORDER BY total_mentions DESC;

COMMENT ON VIEW overall_yarn_popularity IS 'Shows overall yarn popularity across all patterns';

-- View: Overall pattern popularity
CREATE OR REPLACE VIEW overall_pattern_popularity AS
SELECT
    p.id,
    p.name,
    p.source_url,
    COUNT(pyl.id) as total_mentions,
    COUNT(DISTINCT pyl.yarn_id) as yarn_count
FROM "Patterns" p
LEFT JOIN "PatternYarnLink" pyl ON p.id = pyl.pattern_id
GROUP BY p.id, p.name, p.source_url
ORDER BY total_mentions DESC;

COMMENT ON VIEW overall_pattern_popularity IS 'Shows overall pattern popularity across all yarns';

-- ================================================
-- Function: Update updated_at timestamp automatically
-- ================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_yarns_updated_at BEFORE UPDATE ON "Yarns"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patterns_updated_at BEFORE UPDATE ON "Patterns"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- Sample Data (Optional - for testing)
-- ================================================

-- Insert sample yarns
INSERT INTO "Yarns" (name, manufacturer, color, url) VALUES
    ('헤라 코튼', '헤라', '베이지', 'https://example.com/hera-cotton'),
    ('로얄 메리노', '로얄', '네이비', 'https://example.com/royal-merino'),
    ('베이비 울', '베이비', '핑크', 'https://example.com/baby-wool');

-- Insert sample patterns
INSERT INTO "Patterns" (name, source_url) VALUES
    ('사계절 가디건', 'https://blog.naver.com/example1'),
    ('베이비 모자', 'https://blog.naver.com/example2'),
    ('뜨개 가방', 'https://blog.naver.com/example3');

-- Insert sample links (assuming the UUIDs are generated above)
-- Note: In production, use actual UUIDs from the inserted records
-- This is just for demonstration

-- ================================================
-- Verification Queries
-- ================================================

-- Check table creation
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
  AND table_name IN ('Yarns', 'Patterns', 'PatternYarnLink');

-- Check view creation
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'public';

-- Check indexes
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('Yarns', 'Patterns', 'PatternYarnLink')
ORDER BY tablename, indexname;

-- ================================================
-- End of Schema Creation Script
-- ================================================
