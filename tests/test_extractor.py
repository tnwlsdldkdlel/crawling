"""
Unit tests for the NaverBlogExtractor class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.extractor import NaverBlogExtractor, ExtractionResult


class TestExtractionResult:
    """Test cases for ExtractionResult dataclass."""

    def test_successful_result_creation(self):
        """Test creating a successful extraction result."""
        result = ExtractionResult(
            extracted_sentence="This is a test sentence with yarn, 실, and 바늘.",
            source_url="https://blog.naver.com/test",
            success=True
        )

        assert result.success is True
        assert result.extracted_sentence is not None
        assert result.error_message is None
        assert "yarn" in result.extracted_sentence

    def test_failed_result_creation(self):
        """Test creating a failed extraction result."""
        result = ExtractionResult(
            extracted_sentence=None,
            source_url="https://blog.naver.com/test",
            success=False,
            error_message="No matching sentence found"
        )

        assert result.success is False
        assert result.extracted_sentence is None
        assert result.error_message is not None

    def test_to_json_conversion(self):
        """Test converting result to JSON string."""
        result = ExtractionResult(
            extracted_sentence="Test sentence",
            source_url="https://example.com",
            success=True
        )

        json_str = result.to_json()

        assert isinstance(json_str, str)
        assert "Test sentence" in json_str
        assert "https://example.com" in json_str
        assert "true" in json_str.lower()

    def test_to_dict_conversion(self):
        """Test converting result to dictionary."""
        result = ExtractionResult(
            extracted_sentence="Test sentence",
            source_url="https://example.com",
            success=True
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["extracted_sentence"] == "Test sentence"
        assert result_dict["source_url"] == "https://example.com"
        assert result_dict["success"] is True
        assert result_dict["error_message"] is None


class TestNaverBlogExtractor:
    """Test cases for NaverBlogExtractor class."""

    def test_extractor_initialization(self):
        """Test extractor initialization with default parameters."""
        extractor = NaverBlogExtractor()

        assert extractor.model_name == "llama3"
        assert extractor.headless is True
        assert extractor.verbose is False
        assert extractor.graph_config is not None

    def test_extractor_custom_initialization(self):
        """Test extractor initialization with custom parameters."""
        extractor = NaverBlogExtractor(
            model_name="llama3:13b",
            headless=False,
            verbose=True
        )

        assert extractor.model_name == "llama3:13b"
        assert extractor.headless is False
        assert extractor.verbose is True

    def test_graph_config_structure(self):
        """Test that graph configuration has correct structure."""
        extractor = NaverBlogExtractor()
        config = extractor.graph_config

        assert "llm" in config
        assert "embeddings" in config
        assert "headless" in config
        assert config["llm"]["model"] == "ollama/llama3"
        assert config["llm"]["temperature"] == 0.0
        assert config["llm"]["format"] == "json"

    @patch('src.extractor.SmartScraperGraph')
    def test_extract_from_url_success(self, mock_scraper_class):
        """Test successful extraction from URL."""
        # Setup mock
        mock_scraper = MagicMock()
        mock_scraper.run.return_value = {
            "found": True,
            "sentence": "This sentence contains yarn, 실, and 바늘."
        }
        mock_scraper_class.return_value = mock_scraper

        # Execute
        extractor = NaverBlogExtractor()
        result = extractor.extract_from_url("https://blog.naver.com/test")

        # Assert
        assert result.success is True
        assert result.extracted_sentence is not None
        assert "yarn" in result.extracted_sentence
        assert result.error_message is None
        mock_scraper.run.assert_called_once()

    @patch('src.extractor.SmartScraperGraph')
    def test_extract_from_url_not_found(self, mock_scraper_class):
        """Test extraction when no matching sentence is found."""
        # Setup mock
        mock_scraper = MagicMock()
        mock_scraper.run.return_value = {
            "found": False,
            "sentence": None
        }
        mock_scraper_class.return_value = mock_scraper

        # Execute
        extractor = NaverBlogExtractor()
        result = extractor.extract_from_url("https://blog.naver.com/test")

        # Assert
        assert result.success is False
        assert result.extracted_sentence is None
        assert "No sentence containing all three terms" in result.error_message

    @patch('src.extractor.SmartScraperGraph')
    def test_extract_from_url_exception(self, mock_scraper_class):
        """Test extraction when an exception occurs."""
        # Setup mock to raise exception
        mock_scraper_class.side_effect = Exception("Network error")

        # Execute
        extractor = NaverBlogExtractor()
        result = extractor.extract_from_url("https://blog.naver.com/test")

        # Assert
        assert result.success is False
        assert result.extracted_sentence is None
        assert "Extraction error" in result.error_message
        assert "Network error" in result.error_message

    @patch('src.extractor.SmartScraperGraph')
    def test_extract_from_url_invalid_result(self, mock_scraper_class):
        """Test extraction with invalid result format."""
        # Setup mock with invalid result
        mock_scraper = MagicMock()
        mock_scraper.run.return_value = "invalid result"
        mock_scraper_class.return_value = mock_scraper

        # Execute
        extractor = NaverBlogExtractor()
        result = extractor.extract_from_url("https://blog.naver.com/test")

        # Assert
        assert result.success is False
        assert "Invalid extraction result format" in result.error_message

    @patch('src.extractor.SmartScraperGraph')
    def test_extract_from_multiple_urls(self, mock_scraper_class):
        """Test extraction from multiple URLs."""
        # Setup mock
        mock_scraper = MagicMock()
        mock_scraper.run.return_value = {
            "found": True,
            "sentence": "Test sentence with yarn, 실, and 바늘."
        }
        mock_scraper_class.return_value = mock_scraper

        # Execute
        extractor = NaverBlogExtractor()
        urls = [
            "https://blog.naver.com/test1",
            "https://blog.naver.com/test2",
            "https://blog.naver.com/test3"
        ]
        results = extractor.extract_from_urls(urls)

        # Assert
        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_scraper.run.call_count == 3

    @patch('src.extractor.SmartScraperGraph')
    def test_extract_from_urls_mixed_results(self, mock_scraper_class):
        """Test extraction from multiple URLs with mixed success/failure."""
        # Setup mock with alternating results
        mock_scraper = MagicMock()
        mock_scraper.run.side_effect = [
            {"found": True, "sentence": "Success 1"},
            {"found": False, "sentence": None},
            {"found": True, "sentence": "Success 2"}
        ]
        mock_scraper_class.return_value = mock_scraper

        # Execute
        extractor = NaverBlogExtractor()
        urls = ["url1", "url2", "url3"]
        results = extractor.extract_from_urls(urls)

        # Assert
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

    def test_extract_from_empty_url_list(self):
        """Test extraction from empty URL list."""
        extractor = NaverBlogExtractor()
        results = extractor.extract_from_urls([])

        assert len(results) == 0
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
