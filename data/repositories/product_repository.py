"""
Repository for product data
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from core.logger import logger
import asyncio

# Singleton repository instance
_product_repository = None

class ProductRepository:
    """Repository for product data"""
    
    def __init__(self, db_path: str = "data/products.db"):
        """Initialize the repository"""
        self.db_path = db_path
        self._ensure_db_exists()
        self.lock = asyncio.Lock()
    
    def _ensure_db_exists(self):
        """Ensure the database exists and has the required tables"""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if we need to migrate the schema
        cursor.execute("PRAGMA table_info(products)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if columns and "sku" in column_names and "platform" in column_names:
            # Check if we have a primary key constraint
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='products'")
            table_sql = cursor.fetchone()[0]
            
            # If the table doesn't have a composite primary key, we need to recreate it
            if "PRIMARY KEY" in table_sql and "platform" not in table_sql.split("PRIMARY KEY")[1]:
                logger.info("Migrating products table to use composite primary key")
                
                # Rename the old table
                cursor.execute("ALTER TABLE products RENAME TO products_old")
                
                # Create the new table with composite primary key
                cursor.execute('''
                CREATE TABLE products (
                    sku TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (sku, platform)
                )
                ''')
                
                # Copy data from old table to new table
                cursor.execute("INSERT INTO products SELECT * FROM products_old")
                
                # Drop the old table
                cursor.execute("DROP TABLE products_old")
                
                # Create index on platform
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_platform ON products (platform)')
                
                conn.commit()
                logger.info("Migration completed successfully")
        else:
            # Create products table with composite primary key
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (sku, platform)
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
        async with self.lock:
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
    
    async def save_products_batch(self, products: List[Dict[str, Any]], platform: str, batch_size: int = 50) -> None:
        """
        Save multiple products to the database in batches
        
        Args:
            products: List of products to save
            platform: Platform name
            batch_size: Number of products to save in each batch
        """
        # Process products in batches
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]
            logger.info(f"Saving batch {i//batch_size + 1}/{(len(products) + batch_size - 1)//batch_size} ({len(batch)} products)")
            
            async with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                # Begin transaction
                conn.execute('BEGIN TRANSACTION')
                
                try:
                    for product in batch:
                        sku = product["sku"]
                        data = product["data"]
                        
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
                    
                    # Commit transaction
                    conn.commit()
                except sqlite3.Error as e:
                    # Rollback transaction on error
                    conn.rollback()
                    logger.error(f"Database error while saving batch: {str(e)}")
                    raise
                finally:
                    conn.close()
            
            # Small delay between batches to prevent database locking
            await asyncio.sleep(0.1)
    
    async def get_product(self, sku: str, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get a product from the database
        
        Args:
            sku: Product SKU
            platform: Platform name
            
        Returns:
            Product data or None if not found
        """
        async with self.lock:
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
        async with self.lock:
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
        async with self.lock:
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


def get_product_repository() -> ProductRepository:
    """Get the singleton product repository instance"""
    global _product_repository
    if _product_repository is None:
        _product_repository = ProductRepository()
    return _product_repository