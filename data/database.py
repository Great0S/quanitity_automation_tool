"""
Database connection and management module
"""

import os
import sqlite3
import threading
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import logging

from core.logger import logger


class Database:
    """SQLite database manager with connection pooling"""
    
    def __init__(self, db_path: str = 'data/app.db'):
        """
        Initialize database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.local = threading.local()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._initialize_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path)
            # Enable foreign keys
            self.local.connection.execute('PRAGMA foreign_keys = ON')
            # Configure connection
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection
    
    def _initialize_db(self) -> None:
        """Initialize database schema"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create products table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL DEFAULT 0,
                sale_price REAL,
                quantity INTEGER NOT NULL DEFAULT 0,
                category TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            )
            ''')
            
            # Create platforms table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS platforms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                api_type TEXT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                config TEXT
            )
            ''')
            
            # Create platform_products table for mapping products to platforms
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                platform_id INTEGER NOT NULL,
                platform_sku TEXT,
                platform_id_value TEXT,
                price REAL,
                sale_price REAL,
                quantity INTEGER,
                status TEXT,
                last_synced TEXT,
                metadata TEXT,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
                FOREIGN KEY (platform_id) REFERENCES platforms (id) ON DELETE CASCADE,
                UNIQUE (product_id, platform_id)
            )
            ''')
            
            # Create sync_history table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_platform_id INTEGER,
                target_platform_id INTEGER,
                products_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (source_platform_id) REFERENCES platforms (id) ON DELETE SET NULL,
                FOREIGN KEY (target_platform_id) REFERENCES platforms (id) ON DELETE SET NULL
            )
            ''')
            
            # Create sync_product_results table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_product_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                FOREIGN KEY (sync_id) REFERENCES sync_history (id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
            ''')
            
            # Create settings table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            # Create audit_log table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                details TEXT,
                timestamp TEXT NOT NULL
            )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_sku ON products (sku)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_status ON products (status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_platform_products_platform ON platform_products (platform_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_platform_products_product ON platform_products (product_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_history_date ON sync_history (started_at)')
            
            conn.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute SQL query
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Database cursor
        """
        conn = self._get_connection()
        return conn.execute(query, params)
    
    def execute_many(self, query: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """
        Execute SQL query with multiple parameter sets
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
            
        Returns:
            Database cursor
        """
        conn = self._get_connection()
        return conn.executemany(query, params_list)
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Fetch single row from database
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Row as dictionary or None if not found
        """
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Fetch all rows from database
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of rows as dictionaries
        """
        cursor = self.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert row into database
        
        Args:
            table: Table name
            data: Row data
            
        Returns:
            ID of inserted row
        """
        # Add timestamps
        if 'created_at' not in data:
            data['created_at'] = datetime.now().isoformat()
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now().isoformat()
        
        # Handle JSON fields
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                data[key] = json.dumps(value)
        
        # Build query
        placeholders = ', '.join(['?'] * len(data))
        columns = ', '.join(data.keys())
        query = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
        
        # Execute query
        conn = self._get_connection()
        cursor = conn.execute(query, tuple(data.values()))
        conn.commit()
        
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
        """
        Update rows in database
        
        Args:
            table: Table name
            data: Row data
            condition: WHERE condition
            params: Condition parameters
            
        Returns:
            Number of rows affected
        """
        # Add updated_at timestamp
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now().isoformat()
        
        # Handle JSON fields
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                data[key] = json.dumps(value)
        
        # Build query
        set_clause = ', '.join([f'{key} = ?' for key in data.keys()])
        query = f'UPDATE {table} SET {set_clause} WHERE {condition}'
        
        # Execute query
        conn = self._get_connection()
        cursor = conn.execute(query, tuple(data.values()) + params)
        conn.commit()
        
        return cursor.rowcount
    
    def delete(self, table: str, condition: str, params: tuple = ()) -> int:
        """
        Delete rows from database
        
        Args:
            table: Table name
            condition: WHERE condition
            params: Condition parameters
            
        Returns:
            Number of rows affected
        """
        query = f'DELETE FROM {table} WHERE {condition}'
        
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        conn.commit()
        
        return cursor.rowcount
    
    def transaction(self):
        """Get transaction context manager"""
        return Transaction(self)
    
    def close(self) -> None:
        """Close database connection"""
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            delattr(self.local, 'connection')


class Transaction:
    """Transaction context manager"""
    
    def __init__(self, db: Database):
        """
        Initialize transaction
        
        Args:
            db: Database instance
        """
        self.db = db
    
    def __enter__(self):
        """Start transaction"""
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit or rollback transaction"""
        conn = self.db._get_connection()
        
        if exc_type is not None:
            # Exception occurred, rollback
            conn.rollback()
            return False
        
        # No exception, commit
        conn.commit()
        return True


# Global database instance
_db = None

def get_db() -> Database:
    """Get global database instance"""
    global _db
    if _db is None:
        _db = Database()
    return _db