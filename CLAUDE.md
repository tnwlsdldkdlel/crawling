# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered web data extraction system that uses **Llama 3 LLM** to intelligently extract specific content from **Naver Blog** posts and persists results to a **Supabase (PostgreSQL)** database.

**Core Objective**: Extract the first sentence containing all three terms ("yarn", "실", "바늘") from target blog posts and return structured JSON output.

## Development Environment

### Prerequisites
- **Python 3.9+** with virtual environment (`venv/`)
- **Ollama** running locally for Llama 3 model inference
- **Supabase** account with `blog_extractions` table created
- **Playwright browsers** installed for dynamic web scraping

### Environment Setup

**Activate virtual environment:**
```bash
source venv/bin/activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Install Playwright browsers** (first time only):
```bash
playwright install
```

**Start Ollama service** (required for LLM inference):
```bash
ollama serve
```

**Verify Llama 3 model:**
```bash
ollama list  # Should show llama3:latest
```

## Key Architecture Components

### LLM Integration
- Uses **Llama 3** via Ollama for intelligent content extraction
- Model must return structured JSON with extracted sentence and source URL
- Ollama service must be running before script execution

### Web Scraping
- **ScrapeGraphAI** for AI-powered web scraping
- **Playwright** for handling dynamic JavaScript-rendered content (Naver Blogs)
- Targets Korean blog content with specific keyword matching

### Database Schema
- **Supabase (PostgreSQL)** cloud database
- Table: `blog_extractions` (schema must be pre-created)
- Connection details provided via MCP (Microservice Control Plane) environment

## Python Code Standards

This project follows the **python-pro** agent guidelines:
- PEP 8 compliance and Pythonic idioms
- Type hints throughout
- Comprehensive error handling with custom exceptions
- Async/await for concurrent operations where applicable
- Test coverage target: 90%+
- Use pytest for testing with fixtures and mocking

## Development Workflow

1. Ensure Ollama service is running with Llama 3 model loaded
2. Activate virtual environment
3. Run scripts from project root
4. Database credentials should be configured via environment variables or MCP

## Important Notes

- **Korean Language**: Blog content and search terms are in Korean (한글)
- **Dynamic Content**: Naver Blogs use JavaScript rendering - requires Playwright
- **LLM Dependency**: All extraction logic relies on Llama 3 availability
- **Database**: MCP provides Supabase connection details at runtime
