"""
Configuration management for the web data extractor.

This module handles loading configuration from environment variables
and provides type-safe configuration objects.
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


@dataclass
class LLMConfig:
    """Configuration for LLM/Ollama."""

    model_name: str = "llama3"
    temperature: float = 0.0
    format: str = "json"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load LLM configuration from environment variables."""
        return cls(
            model_name=os.getenv("OLLAMA_MODEL", "llama3"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            format=os.getenv("LLM_FORMAT", "json")
        )


@dataclass
class ScraperConfig:
    """Configuration for web scraping."""

    headless: bool = True
    verbose: bool = False
    timeout: int = 30000  # milliseconds

    @classmethod
    def from_env(cls) -> "ScraperConfig":
        """Load scraper configuration from environment variables."""
        return cls(
            headless=os.getenv("SCRAPER_HEADLESS", "true").lower() == "true",
            verbose=os.getenv("SCRAPER_VERBOSE", "false").lower() == "true",
            timeout=int(os.getenv("SCRAPER_TIMEOUT", "30000"))
        )


@dataclass
class DatabaseConfig:
    """Configuration for Supabase/PostgreSQL database."""

    host: str
    port: int
    database: str
    user: str
    password: str

    def get_connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.database} "
            f"user={self.user} "
            f"password={self.password}"
        )

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """
        Load database configuration from environment variables.

        Required environment variables:
        - DB_HOST: Database host
        - DB_PORT: Database port
        - DB_NAME: Database name
        - DB_USER: Database user
        - DB_PASSWORD: Database password

        Raises:
            ValueError: If required environment variables are missing
        """
        host = os.getenv("DB_HOST")
        port_str = os.getenv("DB_PORT")
        database = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        missing_vars = []
        if not host:
            missing_vars.append("DB_HOST")
        if not port_str:
            missing_vars.append("DB_PORT")
        if not database:
            missing_vars.append("DB_NAME")
        if not user:
            missing_vars.append("DB_USER")
        if not password:
            missing_vars.append("DB_PASSWORD")

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"DB_PORT must be an integer, got: {port_str}")

        return cls(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )


@dataclass
class AppConfig:
    """Main application configuration."""

    llm: LLMConfig
    scraper: ScraperConfig
    database: DatabaseConfig

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load complete application configuration from environment."""
        return cls(
            llm=LLMConfig.from_env(),
            scraper=ScraperConfig.from_env(),
            database=DatabaseConfig.from_env()
        )


def get_config() -> AppConfig:
    """
    Get application configuration.

    Returns:
        Complete application configuration object

    Raises:
        ValueError: If required configuration is missing
    """
    return AppConfig.from_env()


def create_env_template() -> None:
    """
    Create a template .env file with all required variables.

    This is useful for first-time setup.
    """
    template = """# LLM Configuration
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
DB_USER=postgres
DB_PASSWORD=your-password-here
"""

    env_path = Path(".env")

    if env_path.exists():
        print(f".env file already exists at {env_path.absolute()}")
        response = input("Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled")
            return

    env_path.write_text(template)
    print(f"Created .env template at {env_path.absolute()}")
    print("Please update the values with your actual configuration.")


if __name__ == "__main__":
    # Create .env template if run directly
    create_env_template()
