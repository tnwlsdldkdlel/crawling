"""
AI-powered web data extractor for Naver Blogs.

This module uses Llama 3 LLM via Ollama to intelligently extract content
from dynamic web pages containing specific Korean terms.
"""

from typing import Optional, Dict, Any
import json
import logging
from dataclasses import dataclass, asdict

from scrapegraphai.graphs import SmartScraperGraph


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Structured result from content extraction."""

    extracted_sentence: Optional[str]
    source_url: str
    success: bool
    error_message: Optional[str] = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class NaverBlogExtractor:
    """
    Extracts specific content from Naver Blog posts using Llama 3 LLM.

    This extractor finds the first sentence containing all three terms:
    - "yarn"
    - "실" (thread in Korean)
    - "바늘" (needle in Korean)
    """

    def __init__(
        self,
        model_name: str = "llama3",
        headless: bool = True,
        verbose: bool = False
    ):
        """
        Initialize the Naver Blog extractor.

        Args:
            model_name: Name of the Ollama model to use
            headless: Whether to run browser in headless mode
            verbose: Enable verbose logging
        """
        self.model_name = model_name
        self.headless = headless
        self.verbose = verbose

        # Configure ScrapeGraphAI
        self.graph_config = {
            "llm": {
                "model": f"ollama/{model_name}",
                "temperature": 0.0,  # Deterministic extraction
                "format": "json",
            },
            "embeddings": {
                "model": f"ollama/{model_name}",
            },
            "headless": headless,
            "verbose": verbose,
        }

        logger.info(f"Initialized NaverBlogExtractor with model: {model_name}")

    def extract_from_url(self, url: str) -> ExtractionResult:
        """
        Extract content from a Naver Blog URL.

        Args:
            url: Target Naver Blog URL

        Returns:
            ExtractionResult with extracted content or error information
        """
        logger.info(f"Starting extraction from URL: {url}")

        # Define the extraction prompt
        prompt = """
        Find and extract the FIRST sentence that contains ALL THREE of these terms:
        1. "yarn"
        2. "실" (Korean word for thread)
        3. "바늘" (Korean word for needle)

        Return ONLY the complete sentence in JSON format with this structure:
        {
            "sentence": "the extracted sentence here",
            "found": true
        }

        If no sentence contains all three terms, return:
        {
            "sentence": null,
            "found": false
        }
        """

        try:
            # Create the smart scraper
            smart_scraper = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=self.graph_config
            )

            # Execute extraction
            result = smart_scraper.run()
            logger.debug(f"Raw extraction result: {result}")

            # Parse and validate result
            if result and isinstance(result, dict):
                found = result.get("found", False)
                sentence = result.get("sentence")

                if found and sentence:
                    logger.info(f"Successfully extracted sentence: {sentence[:50]}...")
                    return ExtractionResult(
                        extracted_sentence=sentence,
                        source_url=url,
                        success=True
                    )
                else:
                    logger.warning(f"No matching sentence found in URL: {url}")
                    return ExtractionResult(
                        extracted_sentence=None,
                        source_url=url,
                        success=False,
                        error_message="No sentence containing all three terms found"
                    )
            else:
                logger.error(f"Invalid result format: {result}")
                return ExtractionResult(
                    extracted_sentence=None,
                    source_url=url,
                    success=False,
                    error_message="Invalid extraction result format"
                )

        except Exception as e:
            logger.error(f"Extraction failed for {url}: {str(e)}", exc_info=True)
            return ExtractionResult(
                extracted_sentence=None,
                source_url=url,
                success=False,
                error_message=f"Extraction error: {str(e)}"
            )

    def extract_from_urls(self, urls: list[str]) -> list[ExtractionResult]:
        """
        Extract content from multiple URLs.

        Args:
            urls: List of target URLs

        Returns:
            List of ExtractionResult objects
        """
        results = []
        for url in urls:
            result = self.extract_from_url(url)
            results.append(result)

        logger.info(f"Completed extraction for {len(urls)} URLs")
        return results


def main():
    """Example usage of NaverBlogExtractor."""
    # Example Naver Blog URL (replace with actual target URL)
    test_url = "https://blog.naver.com/example-post"

    # Initialize extractor
    extractor = NaverBlogExtractor(
        model_name="llama3",
        headless=True,
        verbose=True
    )

    # Extract content
    result = extractor.extract_from_url(test_url)

    # Print result
    print("\n" + "="*60)
    print("EXTRACTION RESULT")
    print("="*60)
    print(result.to_json())
    print("="*60)

    return result


if __name__ == "__main__":
    main()
