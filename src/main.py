"""
Main application script for the Naver Blog extractor.

This script orchestrates the complete workflow:
1. Load configuration from environment
2. Extract content from target URLs
3. Persist results to Supabase database
"""

import sys
import logging
from typing import List
import argparse

from .config import get_config
from .extractor import NaverBlogExtractor
from .database import DatabaseManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_database(db_manager: DatabaseManager) -> None:
    """
    Initialize database schema.

    Args:
        db_manager: DatabaseManager instance
    """
    logger.info("Setting up database schema...")
    try:
        db_manager.create_table()
        logger.info("Database schema setup complete")
    except Exception as e:
        logger.error(f"Failed to setup database: {e}")
        raise


def process_urls(
    urls: List[str],
    extractor: NaverBlogExtractor,
    db_manager: DatabaseManager,
    save_to_db: bool = True
) -> None:
    """
    Process a list of URLs and optionally save results to database.

    Args:
        urls: List of URLs to process
        extractor: NaverBlogExtractor instance
        db_manager: DatabaseManager instance
        save_to_db: Whether to persist results to database
    """
    logger.info(f"Processing {len(urls)} URL(s)...")

    # Extract content from all URLs
    results = extractor.extract_from_urls(urls)

    # Display results
    print("\n" + "="*80)
    print("EXTRACTION RESULTS")
    print("="*80)

    successful_count = 0
    failed_count = 0

    for i, result in enumerate(results, 1):
        print(f"\n[{i}/{len(results)}] URL: {result.source_url}")
        print(f"Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")

        if result.success and result.extracted_sentence:
            print(f"Extracted: {result.extracted_sentence}")
            successful_count += 1
        else:
            print(f"Error: {result.error_message}")
            failed_count += 1

    print("\n" + "="*80)
    print(f"Summary: {successful_count} successful, {failed_count} failed")
    print("="*80)

    # Save to database if requested
    if save_to_db:
        logger.info("Saving results to database...")
        try:
            record_ids = db_manager.insert_extractions_batch(results)
            logger.info(f"Saved {len(record_ids)} records to database")
            print(f"\nSaved results to database with IDs: {record_ids}")
        except Exception as e:
            logger.error(f"Failed to save results to database: {e}")
            print(f"\n⚠ Warning: Failed to save to database: {e}")


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Extract content from Naver Blog posts using AI"
    )
    parser.add_argument(
        "urls",
        nargs="+",
        help="One or more Naver Blog URLs to extract content from"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip saving results to database"
    )
    parser.add_argument(
        "--setup-db",
        action="store_true",
        help="Only setup database schema and exit"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = get_config()

        # Initialize database manager
        db_manager = DatabaseManager(config.database)

        # If only setting up database, do that and exit
        if args.setup_db:
            setup_database(db_manager)
            print("\n✓ Database setup complete")
            return 0

        # Setup database schema
        setup_database(db_manager)

        # Initialize extractor
        logger.info("Initializing extractor...")
        extractor = NaverBlogExtractor(
            model_name=config.llm.model_name,
            headless=config.scraper.headless,
            verbose=config.scraper.verbose
        )

        # Process URLs
        process_urls(
            urls=args.urls,
            extractor=extractor,
            db_manager=db_manager,
            save_to_db=not args.no_db
        )

        return 0

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n✗ Configuration error: {e}")
        print("\nPlease ensure your .env file is properly configured.")
        print("Run 'python -m src.config' to create a template .env file.")
        return 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\n\nInterrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n✗ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
