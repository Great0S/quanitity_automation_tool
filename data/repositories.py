"""
Repository classes for data access
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from core.logger import logger

# Singleton repositories
_product_repository = None
_sync_repository = None

class ProductRepository:
    """Repository for product data"""
    
    def __init__(self, db_path: str = "data/products.db"):
        """Initialize the repository"""
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Ensure the database exists and has the required tables"""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create products table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # Create index on platform
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_platform ON products (platform)')
        
        conn.commit()
        conn.close()
    
    async def save_product(self, sku: str, platform: str, data: Dict[str, Any]) -> None:
        """
        Save a product to the database
        
        Args:
            sku: Product SKU
            platform: Platform name
            data: Product data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Check if product exists
        cursor.execute(
            'SELECT 1 FROM products WHERE sku = ? AND platform = ?',
            (sku, platform)
        )
        
        if cursor.fetchone():
            # Update existing product
            cursor.execute(
                'UPDATE products SET data = ?, updated_at = ? WHERE sku = ? AND platform = ?',
                (json.dumps(data), now, sku, platform)
            )
        else:
            # Insert new product
            cursor.execute(
                'INSERT INTO products (sku, platform, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                (sku, platform, json.dumps(data), now, now)
            )
        
        conn.commit()
        conn.close()
    
    async def get_product(self, sku: str, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get a product from the database
        
        Args:
            sku: Product SKU
            platform: Platform name
            
        Returns:
            Product data or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT data FROM products WHERE sku = ? AND platform = ?',
            (sku, platform)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        
        return None
    
    async def get_products(self, platform: str) -> List[Dict[str, Any]]:
        """
        Get all products for a platform
        
        Args:
            platform: Platform name
            
        Returns:
            List of products
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT sku, data FROM products WHERE platform = ?',
            (platform,)
        )
        
        products = []
        for row in cursor.fetchall():
            sku, data = row
            product_data = json.loads(data)
            products.append({
                "sku": sku,
                "data": product_data
            })
        
        conn.close()
        return products
    
    async def delete_product(self, sku: str, platform: str) -> bool:
        """
        Delete a product from the database
        
        Args:
            sku: Product SKU
            platform: Platform name
            
        Returns:
            True if product was deleted, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'DELETE FROM products WHERE sku = ? AND platform = ?',
            (sku, platform)
        )
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted


class SyncRepository:
    """Repository for sync data"""
    
    def __init__(self, db_path: str = "data/sync.db"):
        """Initialize the repository"""
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Ensure the database exists and has the required tables"""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create syncs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS syncs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_platform TEXT NOT NULL,
            target_platforms TEXT NOT NULL,
            status TEXT NOT NULL,
            fields TEXT NOT NULL,
            filter_skus TEXT,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            error TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
        ''')
        
        # Create sync_results table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_results (
            sync_id INTEGER NOT NULL,
            results TEXT NOT NULL,
            FOREIGN KEY (sync_id) REFERENCES syncs (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_sync(self, source_platform: str, target_platforms: List[str], 
                         status: str, fields: List[str], filter_skus: Optional[List[str]] = None) -> int:
        """
        Create a new sync record
        
        Args:
            source_platform: Source platform name
            target_platforms: List of target platform names
            status: Sync status
            fields: List of fields to sync
            filter_skus: Optional list of SKUs to filter
            
        Returns:
            Sync ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute(
            '''
            INSERT INTO syncs (
                source_platform, target_platforms, status, fields, filter_skus, 
                created_at, success_count, error_count
            ) VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            ''',
            (
                source_platform,
                json.dumps(target_platforms),
                status,
                json.dumps(fields),
                json.dumps(filter_skus) if filter_skus else None,
                now
            )
        )
        
        sync_id = cursor.lastrowid
        if sync_id is None:
            conn.close()
            raise ValueError("Failed to create sync record: lastrowid is None")
        
        conn.commit()
        conn.close()
        
        return sync_id
    
    async def update_sync(self, sync_id: int, status: Optional[str] = None, 
                         success_count: Optional[int] = None, error_count: Optional[int] = None,
                         error: Optional[str] = None, completed_at: Optional[datetime] = None) -> None:
        """
        Update a sync record
        
        Args:
            sync_id: Sync ID
            status: New status
            success_count: Number of successful updates
            error_count: Number of failed updates
            error: Error message
            completed_at: Completion timestamp
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build update query
        query_parts = []
        params = []
        
        if status is not None:
            query_parts.append("status = ?")
            params.append(status)
        
        if success_count is not None:
            query_parts.append("success_count = ?")
            params.append(success_count)
        
        if error_count is not None:
            query_parts.append("error_count = ?")
            params.append(error_count)
        
        if error is not None:
            query_parts.append("error = ?")
            params.append(error)
        
        if completed_at is not None:
            query_parts.append("completed_at = ?")
            params.append(completed_at.isoformat())
        
        if not query_parts:
            conn.close()
            return
        
        # Add sync_id to params
        params.append(sync_id)
        
        # Execute update
        cursor.execute(
            f"UPDATE syncs SET {', '.join(query_parts)} WHERE id = ?",
            params
        )
        
        conn.commit()
        conn.close()
    
    async def save_sync_results(self, sync_id: int, results: List[Dict[str, Any]]) -> None:
        """
        Save detailed sync results
        
        Args:
            sync_id: Sync ID
            results: List of sync results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO sync_results (sync_id, results) VALUES (?, ?)',
            (sync_id, json.dumps(results))
        )
        
        conn.commit()
        conn.close()
    
    async def get_sync(self, sync_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a sync record
        
        Args:
            sync_id: Sync ID
            
        Returns:
            Sync record or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            SELECT id, source_platform, target_platforms, status, fields, filter_skus,
                   success_count, error_count, error, created_at, completed_at
            FROM syncs WHERE id = ?
            ''',
            (sync_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row["id"],
            "source_platform": row["source_platform"],
            "target_platforms": json.loads(row["target_platforms"]),
            "status": row["status"],
            "fields": json.loads(row["fields"]),
            "filter_skus": json.loads(row["filter_skus"]) if row["filter_skus"] else None,
            "success_count": row["success_count"],
            "error_count": row["error_count"],
            "error": row["error"],
            "created_at": row["created_at"],
            "completed_at": row["completed_at"]
        }
    
    async def get_sync_results(self, sync_id: int) -> List[Dict[str, Any]]:
        """
        Get detailed sync results
        
        Args:
            sync_id: Sync ID
            
        Returns:
            List of sync results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT results FROM sync_results WHERE sync_id = ?',
            (sync_id,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return []
        
        return json.loads(row[0])
    
    async def get_syncs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent sync records
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of sync records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            SELECT id, source_platform, target_platforms, status, fields,
                   success_count, error_count, created_at, completed_at
            FROM syncs
            ORDER BY created_at DESC
            LIMIT ?
            ''',
            (limit,)
        )
        
        syncs = []
        for row in cursor.fetchall():
            syncs.append({
                "id": row["id"],
                "source_platform": row["source_platform"],
                "target_platforms": json.loads(row["target_platforms"]),
                "status": row["status"],
                "fields": json.loads(row["fields"]),
                "success_count": row["success_count"],
                "error_count": row["error_count"],
                "created_at": row["created_at"],
                "completed_at": row["completed_at"]
            })
        
        conn.close()
        return syncs


def get_product_repository() -> ProductRepository:
    """Get the singleton product repository"""
    global _product_repository
    if _product_repository is None:
        _product_repository = ProductRepository()
    return _product_repository


def get_sync_repository() -> SyncRepository:
    """Get the singleton sync repository"""
    global _sync_repository
    if _sync_repository is None:
        _sync_repository = SyncRepository()
    return _sync_repository