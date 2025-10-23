"""
Unit tests for the DatabaseManager class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.database import DatabaseManager, DatabaseConfig
from src.extractor import ExtractionResult


@pytest.fixture
def db_config():
    """Fixture providing test database configuration."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="test_db",
        user="test_user",
        password="test_password"
    )


@pytest.fixture
def db_manager(db_config):
    """Fixture providing DatabaseManager instance."""
    return DatabaseManager(db_config)


@pytest.fixture
def sample_extraction_result():
    """Fixture providing sample ExtractionResult."""
    return ExtractionResult(
        extracted_sentence="This is a test sentence with yarn, 실, and 바늘.",
        source_url="https://blog.naver.com/test",
        success=True
    )


class TestDatabaseConfig:
    """Test cases for DatabaseConfig class."""

    def test_config_creation(self, db_config):
        """Test database configuration creation."""
        assert db_config.host == "localhost"
        assert db_config.port == 5432
        assert db_config.database == "test_db"
        assert db_config.user == "test_user"
        assert db_config.password == "test_password"

    def test_connection_string_generation(self, db_config):
        """Test connection string generation."""
        conn_str = db_config.get_connection_string()

        assert "host=localhost" in conn_str
        assert "port=5432" in conn_str
        assert "dbname=test_db" in conn_str
        assert "user=test_user" in conn_str
        assert "password=test_password" in conn_str


class TestDatabaseManager:
    """Test cases for DatabaseManager class."""

    def test_manager_initialization(self, db_manager, db_config):
        """Test database manager initialization."""
        assert db_manager.config == db_config
        assert db_manager.connection_string is not None
        assert db_manager.TABLE_NAME == "blog_extractions"

    @patch('src.database.psycopg2.connect')
    def test_get_connection_success(self, mock_connect, db_manager):
        """Test successful database connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        conn = db_manager.get_connection()

        assert conn is mock_conn
        mock_connect.assert_called_once_with(db_manager.connection_string)

    @patch('src.database.psycopg2.connect')
    def test_get_connection_failure(self, mock_connect, db_manager):
        """Test database connection failure."""
        import psycopg2
        mock_connect.side_effect = psycopg2.Error("Connection failed")

        with pytest.raises(psycopg2.Error):
            db_manager.get_connection()

    @patch('src.database.psycopg2.connect')
    def test_create_table(self, mock_connect, db_manager):
        """Test table creation."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_connect.return_value = mock_conn

        # Execute
        db_manager.create_table()

        # Assert
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('src.database.psycopg2.connect')
    def test_insert_extraction_success(
        self,
        mock_connect,
        db_manager,
        sample_extraction_result
    ):
        """Test successful extraction insertion."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (123,)  # Mock inserted ID
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_connect.return_value = mock_conn

        # Execute
        record_id = db_manager.insert_extraction(sample_extraction_result)

        # Assert
        assert record_id == 123
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('src.database.psycopg2.connect')
    def test_insert_extraction_failure(
        self,
        mock_connect,
        db_manager,
        sample_extraction_result
    ):
        """Test extraction insertion failure."""
        import psycopg2

        # Setup mock to raise exception
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = psycopg2.Error("Insert failed")
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_connect.return_value = mock_conn

        # Execute
        record_id = db_manager.insert_extraction(sample_extraction_result)

        # Assert
        assert record_id is None

    @patch('src.database.psycopg2.connect')
    def test_insert_extractions_batch(self, mock_connect, db_manager):
        """Test batch insertion of multiple extractions."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(1,), (2,), (3,)]
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_connect.return_value = mock_conn

        # Create sample results
        results = [
            ExtractionResult(
                extracted_sentence=f"Sentence {i}",
                source_url=f"https://example.com/{i}",
                success=True
            )
            for i in range(3)
        ]

        # Execute
        record_ids = db_manager.insert_extractions_batch(results)

        # Assert
        assert len(record_ids) == 3
        assert record_ids == [1, 2, 3]
        assert mock_cursor.execute.call_count == 3
        mock_conn.commit.assert_called_once()

    @patch('src.database.psycopg2.connect')
    def test_get_extraction_by_id_found(self, mock_connect, db_manager):
        """Test retrieving extraction by ID when found."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "source_url": "https://example.com",
            "extracted_sentence": "Test sentence",
            "success": True,
            "error_message": None,
            "created_at": datetime.now()
        }
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_connect.return_value = mock_conn

        # Execute
        result = db_manager.get_extraction_by_id(1)

        # Assert
        assert result is not None
        assert result["id"] == 1
        assert result["source_url"] == "https://example.com"

    @patch('src.database.psycopg2.connect')
    def test_get_extraction_by_id_not_found(self, mock_connect, db_manager):
        """Test retrieving extraction by ID when not found."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_connect.return_value = mock_conn

        # Execute
        result = db_manager.get_extraction_by_id(999)

        # Assert
        assert result is None

    @patch('src.database.psycopg2.connect')
    def test_get_extractions_by_url(self, mock_connect, db_manager):
        """Test retrieving extractions by URL."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "source_url": "https://example.com",
                "extracted_sentence": "Sentence 1",
                "success": True,
                "error_message": None,
                "created_at": datetime.now()
            },
            {
                "id": 2,
                "source_url": "https://example.com",
                "extracted_sentence": "Sentence 2",
                "success": True,
                "error_message": None,
                "created_at": datetime.now()
            }
        ]
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_connect.return_value = mock_conn

        # Execute
        results = db_manager.get_extractions_by_url("https://example.com")

        # Assert
        assert len(results) == 2
        assert all(r["source_url"] == "https://example.com" for r in results)

    @patch('src.database.psycopg2.connect')
    def test_get_successful_extractions(self, mock_connect, db_manager):
        """Test retrieving successful extractions."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "source_url": "https://example.com/1",
                "extracted_sentence": "Sentence 1",
                "success": True,
                "error_message": None,
                "created_at": datetime.now()
            },
            {
                "id": 2,
                "source_url": "https://example.com/2",
                "extracted_sentence": "Sentence 2",
                "success": True,
                "error_message": None,
                "created_at": datetime.now()
            }
        ]
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_connect.return_value = mock_conn

        # Execute
        results = db_manager.get_successful_extractions(limit=100)

        # Assert
        assert len(results) == 2
        assert all(r["success"] is True for r in results)
        mock_cursor.execute.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
