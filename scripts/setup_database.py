#!/usr/bin/env python3
"""
Database Setup Script
=====================
Creates tables and initial schema for the Yarn/Pattern Recommendation Service.

Usage:
    python scripts/setup_database.py
"""

import os
import sys
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv


class DatabaseSetup:
    """Handle database setup and schema creation."""

    def __init__(self):
        """Initialize database connection parameters from environment."""
        load_dotenv()

        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }

        # Validate configuration
        missing_vars = [k for k, v in self.db_config.items() if not v]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                "Please check your .env file."
            )

        self.connection: Optional[psycopg2.extensions.connection] = None
        self.cursor: Optional[psycopg2.extensions.cursor] = None

    def connect(self) -> None:
        """Establish database connection."""
        try:
            print(f"Connecting to database at {self.db_config['host']}...")
            self.connection = psycopg2.connect(**self.db_config)
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            self.cursor = self.connection.cursor()
            print("✓ Connected successfully")
        except psycopg2.Error as e:
            print(f"✗ Connection failed: {e}")
            sys.exit(1)

    def disconnect(self) -> None:
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("✓ Disconnected from database")

    def load_sql_file(self, filepath: Path) -> str:
        """Load SQL from file.

        Args:
            filepath: Path to SQL file

        Returns:
            SQL content as string
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"✗ SQL file not found: {filepath}")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error reading SQL file: {e}")
            sys.exit(1)

    def execute_sql(self, sql_content: str) -> None:
        """Execute SQL statements.

        Args:
            sql_content: SQL content to execute
        """
        if not self.cursor:
            raise RuntimeError("Database not connected")

        try:
            print("\nExecuting SQL statements...")

            # Split into individual statements (basic approach)
            # For production, consider using a proper SQL parser
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]

            total = len(statements)
            for i, statement in enumerate(statements, 1):
                if not statement:
                    continue

                # Skip comments
                if statement.startswith('--') or statement.startswith('/*'):
                    continue

                try:
                    self.cursor.execute(statement)

                    # Print progress for CREATE statements
                    if 'CREATE TABLE' in statement.upper():
                        table_name = self._extract_table_name(statement)
                        print(f"  [{i}/{total}] ✓ Created table: {table_name}")
                    elif 'CREATE VIEW' in statement.upper():
                        view_name = self._extract_view_name(statement)
                        print(f"  [{i}/{total}] ✓ Created view: {view_name}")
                    elif 'CREATE INDEX' in statement.upper():
                        index_name = self._extract_index_name(statement)
                        print(f"  [{i}/{total}] ✓ Created index: {index_name}")
                    elif 'DROP TABLE' in statement.upper():
                        table_name = self._extract_table_name(statement)
                        print(f"  [{i}/{total}] ✓ Dropped table: {table_name}")

                except psycopg2.Error as e:
                    # Don't fail on DROP statements for tables that don't exist
                    if 'DROP' in statement.upper() and 'does not exist' in str(e):
                        continue
                    print(f"  [{i}/{total}] ✗ Error: {e}")
                    raise

            print("✓ All SQL statements executed successfully")

        except psycopg2.Error as e:
            print(f"✗ SQL execution failed: {e}")
            raise

    def _extract_table_name(self, statement: str) -> str:
        """Extract table name from CREATE/DROP TABLE statement."""
        parts = statement.upper().split()
        try:
            table_idx = parts.index('TABLE')
            table_name = parts[table_idx + 2] if parts[table_idx + 1] == 'IF' else parts[table_idx + 1]
            return table_name.strip('"').strip('(')
        except (ValueError, IndexError):
            return "unknown"

    def _extract_view_name(self, statement: str) -> str:
        """Extract view name from CREATE VIEW statement."""
        parts = statement.upper().split()
        try:
            view_idx = parts.index('VIEW')
            view_name = parts[view_idx + 1]
            return view_name.strip('"')
        except (ValueError, IndexError):
            return "unknown"

    def _extract_index_name(self, statement: str) -> str:
        """Extract index name from CREATE INDEX statement."""
        parts = statement.upper().split()
        try:
            index_idx = parts.index('INDEX')
            index_name = parts[index_idx + 1]
            return index_name.strip('"')
        except (ValueError, IndexError):
            return "unknown"

    def verify_schema(self) -> None:
        """Verify that all tables and views were created."""
        if not self.cursor:
            raise RuntimeError("Database not connected")

        print("\nVerifying schema...")

        # Check tables
        self.cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
              AND table_name IN ('Yarns', 'Patterns', 'PatternYarnLink')
            ORDER BY table_name;
        """)
        tables = [row[0] for row in self.cursor.fetchall()]

        expected_tables = ['PatternYarnLink', 'Patterns', 'Yarns']
        if set(tables) == set(expected_tables):
            print(f"✓ Tables created: {', '.join(tables)}")
        else:
            missing = set(expected_tables) - set(tables)
            print(f"✗ Missing tables: {', '.join(missing)}")

        # Check views
        self.cursor.execute("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        views = [row[0] for row in self.cursor.fetchall()]

        if views:
            print(f"✓ Views created: {', '.join(views)}")
        else:
            print("⚠ No views found")

        # Check indexes
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename IN ('Yarns', 'Patterns', 'PatternYarnLink');
        """)
        index_count = self.cursor.fetchone()[0]
        print(f"✓ Indexes created: {index_count}")

    def run(self) -> None:
        """Run the complete database setup process."""
        print("=" * 60)
        print("Database Setup - Yarn/Pattern Recommendation Service")
        print("=" * 60)

        try:
            # Connect to database
            self.connect()

            # Load SQL file
            sql_file = Path(__file__).parent / 'create_tables.sql'
            print(f"\nLoading SQL file: {sql_file}")
            sql_content = self.load_sql_file(sql_file)
            print(f"✓ Loaded {len(sql_content)} characters")

            # Execute SQL
            self.execute_sql(sql_content)

            # Verify schema
            self.verify_schema()

            print("\n" + "=" * 60)
            print("✓ Database setup completed successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Setup failed: {e}")
            sys.exit(1)
        finally:
            self.disconnect()


def main():
    """Main entry point."""
    setup = DatabaseSetup()
    setup.run()


if __name__ == '__main__':
    main()
