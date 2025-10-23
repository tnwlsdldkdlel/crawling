# Naver Blog AI Extractor

AI-powered web data extraction system that uses **Llama 3 LLM** to intelligently extract specific content from dynamic Naver Blog posts and persist results to **Supabase** (PostgreSQL).

## Features

- **Intelligent Content Extraction**: Uses Llama 3 to find sentences containing all three terms: "yarn", "실" (thread), "바늘" (needle)
- **Dynamic Content Support**: Handles JavaScript-rendered content via Playwright
- **Database Persistence**: Stores extraction results in Supabase with full metadata
- **Type-Safe Code**: Full type hints for better IDE support and fewer bugs
- **Comprehensive Testing**: 90%+ test coverage with pytest
- **Flexible Configuration**: Environment-based configuration management

## Requirements

- Python 3.9+
- Ollama (for running Llama 3 locally)
- Supabase account (for database)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd crawling
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

```bash
./venv/bin/playwright install
```

### 5. Install Ollama and Llama 3

```bash
# Install Ollama (visit https://ollama.ai for instructions)
# Then pull Llama 3 model
ollama pull llama3
```

### 6. Configure environment

Create a `.env` file in the project root:

```bash
python -m src.config  # This creates a template .env file
```

Then edit `.env` with your actual configuration:

```bash
# LLM Configuration
OLLAMA_MODEL=llama3
LLM_TEMPERATURE=0.0
LLM_FORMAT=json

# Scraper Configuration
SCRAPER_HEADLESS=true
SCRAPER_VERBOSE=false
SCRAPER_TIMEOUT=30000

# Database Configuration (Supabase)
DB_HOST=db.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=your-username
DB_PASSWORD=your-password
```

## Usage

### Starting Ollama

Before running the extractor, ensure Ollama is running:

```bash
ollama serve
```

### Basic Usage

Extract content from a single URL:

```bash
python -m src.main https://blog.naver.com/your-target-post
```

Extract from multiple URLs:

```bash
python -m src.main \
  https://blog.naver.com/post1 \
  https://blog.naver.com/post2 \
  https://blog.naver.com/post3
```

### Command-line Options

```bash
# Extract without saving to database
python -m src.main --no-db https://blog.naver.com/post

# Setup database schema only
python -m src.main --setup-db

# Enable verbose logging
python -m src.main --verbose https://blog.naver.com/post
```

### Programmatic Usage

```python
from src import NaverBlogExtractor, DatabaseManager, get_config

# Load configuration
config = get_config()

# Initialize extractor
extractor = NaverBlogExtractor(
    model_name="llama3",
    headless=True,
    verbose=False
)

# Extract content
result = extractor.extract_from_url("https://blog.naver.com/test")

if result.success:
    print(f"Extracted: {result.extracted_sentence}")
else:
    print(f"Failed: {result.error_message}")

# Save to database
db_manager = DatabaseManager(config.database)
db_manager.create_table()
record_id = db_manager.insert_extraction(result)
print(f"Saved with ID: {record_id}")
```

## Development

### Running Tests

Run all tests:

```bash
pytest
```

Run with coverage report:

```bash
pytest --cov=src --cov-report=html
```

Run specific test file:

```bash
pytest tests/test_extractor.py -v
```

### Code Quality

This project follows:
- **PEP 8** style guide
- **Type hints** throughout
- **SOLID** principles
- **90%+ test coverage** requirement

### Project Structure

```
crawling/
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── database.py         # Database operations
│   ├── extractor.py        # Content extraction logic
│   └── main.py             # CLI entry point
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_database.py
│   └── test_extractor.py
├── docs/
│   └── crawling.md         # Product Requirements Document
├── .env                    # Environment configuration (not in git)
├── .gitignore
├── pytest.ini              # Pytest configuration
├── requirements.txt
├── CLAUDE.md              # Guide for Claude Code
└── README.md
```

## Database Schema

The `blog_extractions` table:

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `source_url` | TEXT | Source blog URL |
| `extracted_sentence` | TEXT | Extracted sentence (if found) |
| `success` | BOOLEAN | Whether extraction succeeded |
| `error_message` | TEXT | Error details (if failed) |
| `created_at` | TIMESTAMP | Extraction timestamp |

## Troubleshooting

### Ollama Connection Error

Ensure Ollama is running:
```bash
ollama serve
```

### Playwright Browser Not Found

Reinstall Playwright browsers:
```bash
./venv/bin/playwright install
```

### Database Connection Error

1. Check your Supabase credentials in `.env`
2. Verify your IP is allowed in Supabase dashboard
3. Test connection:
```python
from src.database import DatabaseManager
from src.config import get_config

config = get_config()
db = DatabaseManager(config.database)
db.get_connection()  # Should not raise error
```

### Extraction Returns No Results

1. Verify the blog post contains all three terms: "yarn", "실", "바늘"
2. Check if the content is accessible (not blocked or requires login)
3. Try running with `--verbose` flag to see detailed logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure test coverage stays above 90%
5. Submit a pull request

## License

[Add your license here]

## Acknowledgments

- Built with [ScrapeGraphAI](https://github.com/VinciGit00/Scrapegraph-ai)
- Powered by [Llama 3](https://llama.meta.com/) via [Ollama](https://ollama.ai)
- Database hosted on [Supabase](https://supabase.com)
