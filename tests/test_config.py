"""
Unit tests for the configuration module.
"""

import pytest
import os
from unittest.mock import patch

from src.config import (
    LLMConfig,
    ScraperConfig,
    DatabaseConfig,
    AppConfig,
    get_config
)


class TestLLMConfig:
    """Test cases for LLMConfig class."""

    def test_default_values(self):
        """Test LLM config with default values."""
        config = LLMConfig()

        assert config.model_name == "llama3"
        assert config.temperature == 0.0
        assert config.format == "json"

    def test_custom_values(self):
        """Test LLM config with custom values."""
        config = LLMConfig(
            model_name="llama3:13b",
            temperature=0.5,
            format="text"
        )

        assert config.model_name == "llama3:13b"
        assert config.temperature == 0.5
        assert config.format == "text"

    @patch.dict(os.environ, {
        "OLLAMA_MODEL": "llama3:70b",
        "LLM_TEMPERATURE": "0.7",
        "LLM_FORMAT": "markdown"
    })
    def test_from_env(self):
        """Test loading LLM config from environment variables."""
        config = LLMConfig.from_env()

        assert config.model_name == "llama3:70b"
        assert config.temperature == 0.7
        assert config.format == "markdown"

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_with_defaults(self):
        """Test loading LLM config with default values when env vars missing."""
        config = LLMConfig.from_env()

        assert config.model_name == "llama3"
        assert config.temperature == 0.0
        assert config.format == "json"


class TestScraperConfig:
    """Test cases for ScraperConfig class."""

    def test_default_values(self):
        """Test scraper config with default values."""
        config = ScraperConfig()

        assert config.headless is True
        assert config.verbose is False
        assert config.timeout == 30000

    def test_custom_values(self):
        """Test scraper config with custom values."""
        config = ScraperConfig(
            headless=False,
            verbose=True,
            timeout=60000
        )

        assert config.headless is False
        assert config.verbose is True
        assert config.timeout == 60000

    @patch.dict(os.environ, {
        "SCRAPER_HEADLESS": "false",
        "SCRAPER_VERBOSE": "true",
        "SCRAPER_TIMEOUT": "45000"
    })
    def test_from_env(self):
        """Test loading scraper config from environment variables."""
        config = ScraperConfig.from_env()

        assert config.headless is False
        assert config.verbose is True
        assert config.timeout == 45000

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_with_defaults(self):
        """Test loading scraper config with defaults when env vars missing."""
        config = ScraperConfig.from_env()

        assert config.headless is True
        assert config.verbose is False
        assert config.timeout == 30000


class TestDatabaseConfig:
    """Test cases for DatabaseConfig class."""

    def test_config_creation(self):
        """Test database config creation."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass"
        )

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "test_db"
        assert config.user == "test_user"
        assert config.password == "test_pass"

    def test_connection_string(self):
        """Test connection string generation."""
        config = DatabaseConfig(
            host="db.example.com",
            port=5432,
            database="my_db",
            user="my_user",
            password="my_pass"
        )

        conn_str = config.get_connection_string()

        assert "host=db.example.com" in conn_str
        assert "port=5432" in conn_str
        assert "dbname=my_db" in conn_str
        assert "user=my_user" in conn_str
        assert "password=my_pass" in conn_str

    @patch.dict(os.environ, {
        "DB_HOST": "supabase.co",
        "DB_PORT": "5432",
        "DB_NAME": "postgres",
        "DB_USER": "admin",
        "DB_PASSWORD": "secret123"
    })
    def test_from_env_success(self):
        """Test loading database config from environment variables."""
        config = DatabaseConfig.from_env()

        assert config.host == "supabase.co"
        assert config.port == 5432
        assert config.database == "postgres"
        assert config.user == "admin"
        assert config.password == "secret123"

    @patch.dict(os.environ, {
        "DB_HOST": "localhost",
        "DB_PORT": "invalid_port",
        "DB_NAME": "test",
        "DB_USER": "user",
        "DB_PASSWORD": "pass"
    })
    def test_from_env_invalid_port(self):
        """Test loading database config with invalid port."""
        with pytest.raises(ValueError, match="DB_PORT must be an integer"):
            DatabaseConfig.from_env()

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_variables(self):
        """Test loading database config with missing environment variables."""
        with pytest.raises(ValueError, match="Missing required environment variables"):
            DatabaseConfig.from_env()

    @patch.dict(os.environ, {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test"
        # Missing DB_USER and DB_PASSWORD
    })
    def test_from_env_partial_variables(self):
        """Test loading database config with some missing variables."""
        with pytest.raises(ValueError) as exc_info:
            DatabaseConfig.from_env()

        error_msg = str(exc_info.value)
        assert "DB_USER" in error_msg
        assert "DB_PASSWORD" in error_msg


class TestAppConfig:
    """Test cases for AppConfig class."""

    @patch.dict(os.environ, {
        "OLLAMA_MODEL": "llama3",
        "LLM_TEMPERATURE": "0.0",
        "LLM_FORMAT": "json",
        "SCRAPER_HEADLESS": "true",
        "SCRAPER_VERBOSE": "false",
        "SCRAPER_TIMEOUT": "30000",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_pass"
    })
    def test_from_env_complete(self):
        """Test loading complete app config from environment."""
        config = AppConfig.from_env()

        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.scraper, ScraperConfig)
        assert isinstance(config.database, DatabaseConfig)

        assert config.llm.model_name == "llama3"
        assert config.scraper.headless is True
        assert config.database.host == "localhost"

    @patch.dict(os.environ, {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test",
        "DB_USER": "user",
        "DB_PASSWORD": "pass"
    })
    def test_from_env_with_defaults(self):
        """Test loading app config with some default values."""
        config = AppConfig.from_env()

        # LLM and Scraper should use defaults
        assert config.llm.model_name == "llama3"
        assert config.scraper.headless is True

        # Database should use env vars
        assert config.database.host == "localhost"

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_database(self):
        """Test loading app config without required database variables."""
        with pytest.raises(ValueError):
            AppConfig.from_env()


class TestGetConfig:
    """Test cases for get_config function."""

    @patch.dict(os.environ, {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test",
        "DB_USER": "user",
        "DB_PASSWORD": "pass"
    })
    def test_get_config_success(self):
        """Test getting configuration successfully."""
        config = get_config()

        assert isinstance(config, AppConfig)
        assert config.database.host == "localhost"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_config_missing_required(self):
        """Test getting configuration with missing required variables."""
        with pytest.raises(ValueError):
            get_config()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
