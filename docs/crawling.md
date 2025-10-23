# Product Requirements Document (PRD): AI-Powered Web Data Extractor

## 1. Overview and Goals

This document outlines the complete requirements and setup necessary to develop a system that uses the **Llama 3** LLM for intelligent data extraction from **dynamic web content (Naver Blogs)** and persists the results in a **Supabase** database. The development approach is **Vibe Coding** for practical learning.

### 1.1 Project Goals

1.  **Precise Content Extraction:** Successfully extract the **first sentence** containing all three specific terms ("yarn", "실", and "바늘") from target blog posts.
2.  **Structured Output:** Llama 3 must return the extracted data and the source URL in a clean **JSON** format.
3.  **DB Integration (MCP):** Persist data into Supabase (PostgreSQL) using connection details provided by the Microservice Control Plane (MCP) environment.

---

## 2. Development Environment and Setup

| Category       | Component                 | Requirement & Setup Guidance                                                                 |
| :------------- | :------------------------ | :------------------------------------------------------------------------------------------- |
| **Language**   | **Python 3.x**            | The standard language for AI/Data Science.                                                   |
| **Editor**     | **VS Code**               | Recommended for beginners; ensure the Python extension is installed.                         |
| **LLM Model**  | **Meta Llama 3**          | Free, high-performance model. **Setup:** Must install Ollama and run `ollama pull llama3`.   |
| **LLM Runner** | **Ollama**                | Tool for local LLM execution. Must be running in the background when the script is executed. |
| **DB**         | **Supabase (PostgreSQL)** | Cloud-hosted database. The `blog_extractions` table must be pre-created (see Section 4.1).   |

### 2.1 Required Libraries (Installation)

The following libraries must be installed within your Python virtual environment (`venv`):

```bash
pip install scrapegraphai ollama playwright psycopg2-binary
```
