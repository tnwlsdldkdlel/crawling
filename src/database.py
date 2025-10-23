"""
Database utilities for persisting extraction results to Supabase.

This module handles database connections and CRUD operations for the
blog_extractions table.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
import logging

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql

from .extractor import ExtractionResult


logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database connection configuration."""

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


class DatabaseManager:
    """
    Manages database operations for blog extraction results.

    Handles connection pooling, table creation, and CRUD operations
    for the blog_extractions table.
    """

    TABLE_NAME = "blog_extractions"

    def __init__(self, config: DatabaseConfig):
        """
        Initialize database manager.

        Args:
            config: Database configuration object
        """
        self.config = config
        self.connection_string = config.get_connection_string()
        logger.info("Database manager initialized")

    def get_connection(self):
        """
        Create a new database connection.

        Returns:
            psycopg2 connection object

        Raises:
            psycopg2.Error: If connection fails
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            return conn
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def create_table(self) -> None:
        """
        Create the blog_extractions table if it doesn't exist.

        Table schema:
        - id: SERIAL PRIMARY KEY
        - source_url: TEXT NOT NULL
        - extracted_sentence: TEXT
        - success: BOOLEAN NOT NULL
        - error_message: TEXT
        - created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """
        create_table_query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {table} (
                id SERIAL PRIMARY KEY,
                source_url TEXT NOT NULL,
                extracted_sentence TEXT,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_source_url ON {table}(source_url);
            CREATE INDEX IF NOT EXISTS idx_created_at ON {table}(created_at);
        """).format(table=sql.Identifier(self.TABLE_NAME))

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_table_query)
                    conn.commit()
                    logger.info(f"Table {self.TABLE_NAME} created or verified")
        except psycopg2.Error as e:
            logger.error(f"Failed to create table: {e}")
            raise

    def insert_extraction(self, result: ExtractionResult) -> Optional[int]:
        """
        Insert an extraction result into the database.

        Args:
            result: ExtractionResult object to persist

        Returns:
            ID of the inserted record, or None if insertion failed
        """
        insert_query = sql.SQL("""
            INSERT INTO {table} (
                source_url,
                extracted_sentence,
                success,
                error_message
            ) VALUES (%s, %s, %s, %s)
            RETURNING id;
        """).format(table=sql.Identifier(self.TABLE_NAME))

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        insert_query,
                        (
                            result.source_url,
                            result.extracted_sentence,
                            result.success,
                            result.error_message
                        )
                    )
                    record_id = cursor.fetchone()[0]
                    conn.commit()
                    logger.info(f"Inserted extraction record with ID: {record_id}")
                    return record_id
        except psycopg2.Error as e:
            logger.error(f"Failed to insert extraction: {e}")
            return None

    def insert_extractions_batch(
        self,
        results: List[ExtractionResult]
    ) -> List[Optional[int]]:
        """
        Insert multiple extraction results in a single transaction.

        Args:
            results: List of ExtractionResult objects

        Returns:
            List of inserted record IDs
        """
        insert_query = sql.SQL("""
            INSERT INTO {table} (
                source_url,
                extracted_sentence,
                success,
                error_message
            ) VALUES (%s, %s, %s, %s)
            RETURNING id;
        """).format(table=sql.Identifier(self.TABLE_NAME))

        record_ids = []

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for result in results:
                        cursor.execute(
                            insert_query,
                            (
                                result.source_url,
                                result.extracted_sentence,
                                result.success,
                                result.error_message
                            )
                        )
                        record_id = cursor.fetchone()[0]
                        record_ids.append(record_id)

                    conn.commit()
                    logger.info(f"Batch inserted {len(record_ids)} records")
        except psycopg2.Error as e:
            logger.error(f"Failed to batch insert extractions: {e}")
            conn.rollback()

        return record_ids

    def get_extraction_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve an extraction record by ID.

        Args:
            record_id: Primary key of the record

        Returns:
            Dictionary containing record data, or None if not found
        """
        query = sql.SQL("""
            SELECT * FROM {table} WHERE id = %s;
        """).format(table=sql.Identifier(self.TABLE_NAME))

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, (record_id,))
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except psycopg2.Error as e:
            logger.error(f"Failed to fetch record {record_id}: {e}")
            return None

    def get_extractions_by_url(self, url: str) -> List[Dict[str, Any]]:
        """
        Retrieve all extraction records for a specific URL.

        Args:
            url: Source URL to search for

        Returns:
            List of dictionaries containing record data
        """
        query = sql.SQL("""
            SELECT * FROM {table}
            WHERE source_url = %s
            ORDER BY created_at DESC;
        """).format(table=sql.Identifier(self.TABLE_NAME))

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, (url,))
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
        except psycopg2.Error as e:
            logger.error(f"Failed to fetch records for URL {url}: {e}")
            return []

    def get_successful_extractions(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve successful extraction records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of dictionaries containing successful extractions
        """
        query = sql.SQL("""
            SELECT * FROM {table}
            WHERE success = TRUE
            ORDER BY created_at DESC
            LIMIT %s;
        """).format(table=sql.Identifier(self.TABLE_NAME))

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, (limit,))
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
        except psycopg2.Error as e:
            logger.error(f"Failed to fetch successful extractions: {e}")
            return []


def main():
    """Example usage of DatabaseManager."""
    # Example configuration (replace with actual credentials)
    config = DatabaseConfig(
        host="db.supabase.co",
        port=5432,
        database="postgres",
        user="postgres",
        password="your-password-here"
    )

    # Initialize manager
    db_manager = DatabaseManager(config)

    # Create table
    db_manager.create_table()

    print("Database setup complete")


if __name__ == "__main__":
    main()
