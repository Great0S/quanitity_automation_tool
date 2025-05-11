"""
Product repository for database operations
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from data.database import get_db
from core.logger import logger


class ProductRepository:
    """Repository for product operations"""
    
    def __init__(self):
        """Initialize repository"""
        self.db = get_db()
    
    def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get product by SKU
        
        Args:
            sku: Product SKU
            
        Returns:
            Product data or None if not found
        """
        product = self.db.fetch_one(
            "SELECT * FROM products WHERE sku = ?",
            (sku,)
        )
        
        if not product:
            return None
            
        # Parse JSON fields
        if product.get('metadata'):
            try:
                import json
                product['metadata'] = json.loads(product['metadata'])
            except:
                product['metadata'] = {}
                
        return product
    
    def get_products(self, filters: Dict[str, Any] = None, 
                    page: int = 1, page_size: int = 50,
                    sort_by: str = 'updated_at', sort_dir: str = 'DESC') -> Tuple[List[Dict[str, Any]], int]:
        """
        Get products with pagination and filtering
        
        Args:
            filters: Filter conditions
            page: Page number (1-based)
            page_size: Page size
            sort_by: Column to sort by
            sort_dir: Sort direction (ASC or DESC)
            
        Returns:
            Tuple of (products list, total count)
        """
        # Build query
        query = "SELECT * FROM products"
        count_query = "SELECT COUNT(*) as count FROM products"
        params = []
        
        # Apply filters
        if filters:
            conditions = []
            
            if 'sku' in filters:
                conditions.append("sku LIKE ?")
                params.append(f"%{filters['sku']}%")
                
            if 'title' in filters:
                conditions.append("title LIKE ?")
                params.append(f"%{filters['title']}%")
                
            if 'status' in filters:
                conditions.append("status = ?")
                params.append(filters['status'])
                
            if 'category' in filters:
                conditions.append("category = ?")
                params.append(filters['category'])
                
            if 'min_price' in filters:
                conditions.append("price >= ?")
                params.append(filters['min_price'])
                
            if 'max_price' in filters:
                conditions.append("price <= ?")
                params.append(filters['max_price'])
                
            if 'min_quantity' in filters:
                conditions.append("quantity >= ?")
                params.append(filters['min_quantity'])
                
            if 'max_quantity' in filters:
                conditions.append("quantity <= ?")
                params.append(filters['max_quantity'])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                count_query += " WHERE " + " AND ".join(conditions)
        
        # Get total count
        count_result = self.db.fetch_one(count_query, tuple(params))
        total_count = count_result['count'] if count_result else 0
        
        # Apply sorting and pagination
        query += f" ORDER BY {sort_by} {sort_dir}"
        query += f" LIMIT {page_size} OFFSET {(page - 1) * page_size}"
        
        # Execute query
        products = self.db.fetch_all(query, tuple(params))
        
        # Parse JSON fields
        for product in products:
            if product.get('metadata'):
                try:
                    import json
                    product['metadata'] = json.loads(product['metadata'])
                except:
                    product['metadata'] = {}
        
        return products, total_count
    
    def create_product(self, product_data: Dict[str, Any]) -> int:
        """
        Create new product
        
        Args:
            product_data: Product data
            
        Returns:
            ID of created product
        """
        # Ensure required fields
        required_fields = ['sku', 'title', 'price', 'quantity']
        for field in required_fields:
            if field not in product_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Check if product with this SKU already exists
        existing = self.get_product_by_sku(product_data['sku'])
        if existing:
            raise ValueError(f"Product with SKU '{product_data['sku']}' already exists")
        
        # Insert product
        product_id = self.db.insert('products', product_data)
        logger.info(f"Created product with ID {product_id} and SKU {product_data['sku']}")
        
        return product_id
    
    def update_product(self, sku: str, product_data: Dict[str, Any]) -> bool:
        """
        Update product
        
        Args:
            sku: Product SKU
            product_data: Product data to update
            
        Returns:
            True if product was updated, False otherwise
        """
        # Check if product exists
        existing = self.get_product_by_sku(sku)
        if not existing:
            logger.warning(f"Cannot update non-existent product with SKU {sku}")
            return False
        
        # Update product
        rows_affected = self.db.update(
            'products',
            product_data,
            'sku = ?',
            (sku,)
        )
        
        if rows_affected > 0:
            logger.info(f"Updated product with SKU {sku}")
            return True
        else:
            logger.warning(f"No changes made to product with SKU {sku}")
            return False
    
    def delete_product(self, sku: str) -> bool:
        """
        Delete product
        
        Args:
            sku: Product SKU
            
        Returns:
            True if product was deleted, False otherwise
        """
        # Check if product exists
        existing = self.get_product_by_sku(sku)
        if not existing:
            logger.warning(f"Cannot delete non-existent product with SKU {sku}")
            return False
        
        # Delete product
        rows_affected = self.db.delete(
            'products',
            'sku = ?',
            (sku,)
        )
        
        if rows_affected > 0:
            logger.info(f"Deleted product with SKU {sku}")
            return True
        else:
            logger.warning(f"Failed to delete product with SKU {sku}")
            return False
    
    def update_product_quantity(self, sku: str, quantity: int) -> bool:
        """
        Update product quantity
        
        Args:
            sku: Product SKU
            quantity: New quantity
            
        Returns:
            True if quantity was updated, False otherwise
        """
        # Check if product exists
        existing = self.get_product_by_sku(sku)
        if not existing:
            logger.warning(f"Cannot update quantity for non-existent product with SKU {sku}")
            return False
        
        # Update quantity
        rows_affected = self.db.update(
            'products',
            {
                'quantity': quantity,
                'updated_at': datetime.now().isoformat()
            },
            'sku = ?',
            (sku,)
        )
        
        if rows_affected > 0:
            logger.info(f"Updated quantity to {quantity} for product with SKU {sku}")
            return True
        else:
            logger.warning(f"No changes made to quantity for product with SKU {sku}")
            return False
    
    def update_product_price(self, sku: str, price: float, sale_price: Optional[float] = None) -> bool:
        """
        Update product price
        
        Args:
            sku: Product SKU
            price: New price
            sale_price: New sale price (optional)
            
        Returns:
            True if price was updated, False otherwise
        """
        # Check if product exists
        existing = self.get_product_by_sku(sku)
        if not existing:
            logger.warning(f"Cannot update price for non-existent product with SKU {sku}")
            return False
        
        # Prepare update data
        update_data = {
            'price': price,
            'updated_at': datetime.now().isoformat()
        }
        
        if sale_price is not None:
            update_data['sale_price'] = sale_price
        
        # Update price
        rows_affected = self.db.update(
            'products',
            update_data,
            'sku = ?',
            (sku,)
        )
        
        if rows_affected > 0:
            logger.info(f"Updated price to {price} for product with SKU {sku}")
            return True
        else:
            logger.warning(f"No changes made to price for product with SKU {sku}")
            return False
    
    def update_product_status(self, sku: str, status: str) -> bool:
        """
        Update product status
        
        Args:
            sku: Product SKU
            status: New status
            
        Returns:
            True if status was updated, False otherwise
        """
        # Check if product exists
        existing = self.get_product_by_sku(sku)
        if not existing:
            logger.warning(f"Cannot update status for non-existent product with SKU {sku}")
            return False
        
        # Validate status
        valid_statuses = ['active', 'inactive', 'draft', 'deleted']
        if status not in valid_statuses:
            logger.warning(f"Invalid status '{status}' for product with SKU {sku}")
            return False
        
        # Update status
        rows_affected = self.db.update(
            'products',
            {
                'status': status,
                'updated_at': datetime.now().isoformat()
            },
            'sku = ?',
            (sku,)
        )
        
        if rows_affected > 0:
            logger.info(f"Updated status to {status} for product with SKU {sku}")
            return True
        else:
            logger.warning(f"No changes made to status for product with SKU {sku}")
            return False
    
    def get_product_platforms(self, sku: str) -> List[Dict[str, Any]]:
        """
        Get platforms for a product
        
        Args:
            sku: Product SKU
            
        Returns:
            List of platform mappings
        """
        query = """
        SELECT pp.*, p.name as platform_name
        FROM platform_products pp
        JOIN products pr ON pp.product_id = pr.id
        JOIN platforms p ON pp.platform_id = p.id
        WHERE pr.sku = ?
        """
        
        platform_products = self.db.fetch_all(query, (sku,))
        
        # Parse JSON fields
        for pp in platform_products:
            if pp.get('metadata'):
                try:
                    import json
                    pp['metadata'] = json.loads(pp['metadata'])
                except:
                    pp['metadata'] = {}
        
        return platform_products
    
    def link_product_to_platform(self, sku: str, platform_name: str, 
                               platform_data: Dict[str, Any]) -> bool:
        """
        Link product to platform
        
        Args:
            sku: Product SKU
            platform_name: Platform name
            platform_data: Platform-specific data
            
        Returns:
            True if link was created or updated, False otherwise
        """
        # Get product and platform IDs
        product = self.get_product_by_sku(sku)
        if not product:
            logger.warning(f"Cannot link non-existent product with SKU {sku}")
            return False
        
        platform = self.db.fetch_one(
            "SELECT * FROM platforms WHERE name = ?",
            (platform_name,)
        )
        
        if not platform:
            logger.warning(f"Cannot link to non-existent platform {platform_name}")
            return False
        
        # Check if link already exists
        existing = self.db.fetch_one(
            """
            SELECT * FROM platform_products
            WHERE product_id = ? AND platform_id = ?
            """,
            (product['id'], platform['id'])
        )
        
        if existing:
            # Update existing link
            platform_data['last_synced'] = datetime.now().isoformat()
            
            rows_affected = self.db.update(
                'platform_products',
                platform_data,
                'id = ?',
                (existing['id'],)
            )
            
            if rows_affected > 0:
                logger.info(f"Updated link between product {sku} and platform {platform_name}")
                return True
            else:
                logger.warning(f"No changes made to link between product {sku} and platform {platform_name}")
                return False
        else:
            # Create new link
            platform_data['product_id'] = product['id']
            platform_data['platform_id'] = platform['id']
            platform_data['last_synced'] = datetime.now().isoformat()
            
            link_id = self.db.insert('platform_products', platform_data)
            
            if link_id:
                logger.info(f"Created link between product {sku} and platform {platform_name}")
                return True
            else:
                logger.warning(f"Failed to create link between product {sku} and platform {platform_name}")
                return False
    
    def unlink_product_from_platform(self, sku: str, platform_name: str) -> bool:
        """
        Unlink product from platform
        
        Args:
            sku: Product SKU
            platform_name: Platform name
            
        Returns:
            True if link was removed, False otherwise
        """
        # Get product and platform IDs
        product = self.get_product_by_sku(sku)
        if not product:
            logger.warning(f"Cannot unlink non-existent product with SKU {sku}")
            return False
        
        platform = self.db.fetch_one(
            "SELECT * FROM platforms WHERE name = ?",
            (platform_name,)
        )
        
        if not platform:
            logger.warning(f"Cannot unlink from non-existent platform {platform_name}")
            return False
        
        # Delete link
        rows_affected = self.db.delete(
            'platform_products',
            'product_id = ? AND platform_id = ?',
            (product['id'], platform['id'])
        )
        
        if rows_affected > 0:
            logger.info(f"Removed link between product {sku} and platform {platform_name}")
            return True
        else:
            logger.warning(f"No link found between product {sku} and platform {platform_name}")
            return False
    
    def get_categories(self) -> List[str]:
        """
        Get all product categories
        
        Returns:
            List of unique categories
        """
        categories = self.db.fetch_all(
            "SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != ''"
        )
        
        return [c['category'] for c in categories]
    
    def get_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get products by category
        
        Args:
            category: Category name
            
        Returns:
            List of products in the category
        """
        products = self.db.fetch_all(
            "SELECT * FROM products WHERE category = ?",
            (category,)
        )
        
        # Parse JSON fields
        for product in products:
            if product.get('metadata'):
                try:
                    import json
                    product['metadata'] = json.loads(product['metadata'])
                except:
                    product['metadata'] = {}
        
        return products
    
    def get_low_stock_products(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """
        Get products with low stock
        
        Args:
            threshold: Stock threshold
            
        Returns:
            List of products with quantity <= threshold
        """
        products = self.db.fetch_all(
            "SELECT * FROM products WHERE quantity <= ? AND status = 'active'",
            (threshold,)
        )
        
        # Parse JSON fields
        for product in products:
            if product.get('metadata'):
                try:
                    import json
                    product['metadata'] = json.loads(product['metadata'])
                except:
                    product['metadata'] = {}
        
        return products
    
    def bulk_update_products(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk update products
        
        Args:
            updates: List of product updates, each with 'sku' and fields to update
            
        Returns:
            Dictionary with success and error counts
        """
        success_count = 0
        error_count = 0
        errors = []
        
        with self.db.transaction():
            for update in updates:
                sku = update.pop('sku', None)
                
                if not sku:
                    error_count += 1
                    errors.append({'error': 'Missing SKU', 'data': update})
                    continue
                
                # Add updated_at timestamp
                update['updated_at'] = datetime.now().isoformat()
                
                try:
                    rows_affected = self.db.update(
                        'products',
                        update,
                        'sku = ?',
                        (sku,)
                    )
                    
                    if rows_affected > 0:
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append({'error': f"Product with SKU {sku} not found", 'sku': sku})
                except Exception as e:
                    error_count += 1
                    errors.append({'error': str(e), 'sku': sku})
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }


# Global repository instance
_product_repo = None

def get_product_repository() -> ProductRepository:
    """Get global product repository instance"""
    global _product_repo
    if _product_repo is None:
        _product_repo = ProductRepository()
    return _product_repo