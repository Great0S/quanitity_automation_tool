"""
Unified Product Service combining basic and enhanced functionality
"""

from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import asyncio

from core.logger import logger
from core.exceptions import ValidationError, APIError, AuthenticationError, NetworkError, RateLimitError
from api.base_client import BaseAPIClient
from data.repositories import get_product_repository
from utils.cache import async_cached
from utils.helpers import retry_async, CircuitBreaker


class UnifiedProductService:
    """
    Unified product service with database integration, caching, and enhanced features
    
    This service combines the functionality of ProductService and EnhancedProductService:
    - Basic product operations (get, update)
    - Database persistence
    - Caching
    - Circuit breaker pattern
    - Enhanced error handling
    - Bulk operations
    """
    
    def __init__(self, api_client: BaseAPIClient, platform_name: str):
        """
        Initialize unified product service
        
        Args:
            api_client: API client for the platform
            platform_name: Platform name
        """
        self.api_client = api_client
        self.platform_name = platform_name
        self.product_repo = get_product_repository()
        self.logger = logger
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=3
        )
    
    @async_cached(ttl=300, key_prefix="unified_product_service")
    async def get_products(self, force_refresh: bool = False, **kwargs) -> List[Dict[str, Any]]:
        """
        Get products with caching and database integration
        
        Args:
            force_refresh: Force refresh from API
            **kwargs: Additional parameters for API client
            
        Returns:
            List of products
        """
        try:
            # If force refresh, invalidate cache
            if force_refresh:
                self.get_products.invalidate_cache(force_refresh=force_refresh, **kwargs)
            
            # Get products from API with circuit breaker
            products = await retry_async(
                max_retries=3,
                circuit_breaker=self.circuit_breaker
            )(self._get_products_from_api)(**kwargs)
            
            # Store products in database
            await self._sync_products_to_db(products)
            
            return products
            
        except (AuthenticationError, NetworkError, APIError) as e:
            self.logger.error(f"Error fetching products from {self.platform_name}: {str(e)}")
            
            # Try to get products from database as fallback
            self.logger.info(f"Falling back to database for {self.platform_name} products")
            return self._get_products_from_db()
            
        except Exception as e:
            self.logger.error(f"Unexpected error fetching products from {self.platform_name}: {str(e)}")
            raise
    
    async def _get_products_from_api(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get products directly from API
        
        Args:
            **kwargs: Additional parameters for API client
            
        Returns:
            List of products
        """
        try:
            # Await the API client's get_products call
            products = await self.api_client.get_products(**kwargs)
            self.logger.info(f"Retrieved {len(products)} products from {self.platform_name}")
            return products
            
        except AuthenticationError as e:
            self.logger.error(f"Authentication error while fetching products: {str(e)}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")
            
        except RateLimitError as e:
            self.logger.error(f"Rate limit exceeded while fetching products: {str(e)}")
            raise RateLimitError(f"Rate limit exceeded: {str(e)}")
            
        except NetworkError as e:
            self.logger.error(f"Network error while fetching products: {str(e)}")
            raise NetworkError(f"Network error: {str(e)}")
            
        except APIError as e:
            self.logger.error(f"API error while fetching products: {str(e)}")
            raise APIError(f"API error: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Unexpected error while fetching products: {str(e)}")
            raise Exception(f"Failed to fetch products: {str(e)}")
    
    async def update_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update products with database integration
        
        Args:
            products: List of products to update
            
        Returns:
            Dictionary with update results
        """
        results = []
        errors = []
        skipped = []

        for product in products:
            try:
                # Validate product data before updating
                validation_errors = self.validate_product_data(product)
                if validation_errors:
                    skipped.append({
                        'sku': product.get('sku', 'unknown'),
                        'reason': f"Validation errors: {', '.join(validation_errors)}"
                    })
                    continue
                
                result = await self.api_client.update_product(product)
                results.append(result)
                self.logger.info(f"Updated product {product.get('sku')} successfully")
                
            except AuthenticationError as e:
                self.logger.error(f"Authentication error while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': f"Authentication failed: {str(e)}"
                })
                
            except RateLimitError as e:
                self.logger.error(f"Rate limit exceeded while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': f"Rate limit exceeded: {str(e)}"
                })
                
            except NetworkError as e:
                self.logger.error(f"Network error while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': f"Network error: {str(e)}"
                })
                
            except APIError as e:
                self.logger.error(f"API error while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': f"API error: {str(e)}"
                })
                
            except Exception as e:
                self.logger.error(f"Unexpected error while updating product {product.get('sku')}: {str(e)}")
                errors.append({
                    'sku': product.get('sku', 'unknown'),
                    'error': str(e)
                })

        # Update products in database
        updated_skus = [p.get('sku') for p in results]
        if updated_skus:
            await self._update_products_in_db(products, updated_skus)

        if errors:
            self.logger.warning(f"{len(errors)} products failed to update")
            
        if skipped:
            self.logger.warning(f"{len(skipped)} products were skipped due to validation errors")

        return {
            'updated': results,
            'errors': errors,
            'skipped': skipped
        }
    
    async def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get product by SKU with caching and database integration
        
        Args:
            sku: Product SKU
            
        Returns:
            Product data or None if not found
        """
        try:
            # Try to get from API
            if hasattr(self.api_client, 'get_product_by_sku'):
                product = await self.api_client.get_product_by_sku(sku)
                
                # Store in database if found
                if product:
                    await self._sync_product_to_db(product)
                    
                return product
            else:
                # Fallback: get all products and filter
                products = await self.get_products()
                for product in products:
                    if product.get('sku') == sku:
                        return product
                        
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching product {sku} from {self.platform_name}: {str(e)}")
            
            # Try to get from database as fallback
            self.logger.info(f"Falling back to database for product {sku}")
            return self._get_product_from_db(sku)
    
    async def bulk_update_quantities(self, updates: List[Dict[str, int]]) -> Dict[str, Any]:
        """
        Bulk update product quantities
        
        Args:
            updates: List of dictionaries with 'sku' and 'quantity' keys
            
        Returns:
            Dictionary with update results
        """
        # Convert to product update format
        products_to_update = []
        for update in updates:
            sku = update.get('sku')
            quantity = update.get('quantity')
            
            if sku and quantity is not None:
                products_to_update.append({
                    'sku': sku,
                    'data': {
                        'quantity': quantity
                    }
                })
        
        # Update products
        return await self.update_products(products_to_update)
    
    async def bulk_update_prices(self, updates: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Bulk update product prices
        
        Args:
            updates: List of dictionaries with 'sku', 'price', and optional 'sale_price' keys
            
        Returns:
            Dictionary with update results
        """
        # Convert to product update format
        products_to_update = []
        for update in updates:
            sku = update.get('sku')
            price = update.get('price')
            
            if sku and price is not None:
                product_data = {
                    'price': price
                }
                
                if 'sale_price' in update:
                    product_data['salePrice'] = update['sale_price']
                
                products_to_update.append({
                    'sku': sku,
                    'data': product_data
                })
        
        # Update products
        return await self.update_products(products_to_update)
    
    async def bulk_update_statuses(self, updates: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Bulk update product statuses
        
        Args:
            updates: List of dictionaries with 'sku' and 'status' keys
            
        Returns:
            Dictionary with update results
        """
        # Convert to product update format
        products_to_update = []
        for update in updates:
            sku = update.get('sku')
            status = update.get('status')
            
            if sku and status:
                products_to_update.append({
                    'sku': sku,
                    'data': {
                        'status': status
                    }
                })
        
        # Update products
        return await self.update_products(products_to_update)
    
    def validate_product_data(self, product_data: Dict[str, Any]) -> List[str]:
        """
        Validate product data
        
        Args:
            product_data: Product data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check if product_data is a dictionary
        if not isinstance(product_data, dict):
            return ["Product data must be a dictionary"]
            
        # Check for required SKU
        if not product_data.get('sku'):
            errors.append("Missing required field: sku")
            
        # Check for data dictionary
        data = product_data.get('data')
        if not isinstance(data, dict):
            errors.append("Missing or invalid 'data' field")
            return errors
            
        # Check required fields in data
        required_fields = ['title', 'price', 'quantity']
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
                
        # Validate numeric fields
        if 'price' in data and not isinstance(data['price'], (int, float)) or data.get('price', 0) < 0:
            errors.append("Price must be a non-negative number")
            
        if 'quantity' in data and not isinstance(data['quantity'], int) or data.get('quantity', 0) < 0:
            errors.append("Quantity must be a non-negative integer")

        if errors:
            self.logger.warning(f"Product validation errors for SKU {product_data.get('sku')}: {errors}")

        return errors

    def format_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw product data to standard format
        
        Args:
            raw_data: Raw product data
            
        Returns:
            Formatted product data
        """
        try:
            # Ensure SKU exists
            sku = raw_data.get('sku')
            if not sku:
                raise ValidationError("Missing required field: sku")
                
            # Create standardized product data structure
            return {
                'sku': sku,
                'data': {
                    'title': raw_data.get('title', ''),
                    'price': float(raw_data.get('price', 0)),
                    'salePrice': float(raw_data.get('salePrice', raw_data.get('price', 0))),
                    'listPrice': float(raw_data.get('listPrice', raw_data.get('price', 0))),
                    'quantity': int(raw_data.get('quantity', 0)),
                    'categoryName': raw_data.get('category', ''),
                    'description': raw_data.get('description', ''),
                    'images': raw_data.get('images', [])
                }
            }
        except Exception as e:
            self.logger.error(f"Error formatting product data: {str(e)}")
            raise ValidationError(f"Failed to format product data: {str(e)}")
    
    async def _sync_products_to_db(self, products: List[Dict[str, Any]]) -> None:
        """
        Sync products to database
        
        Args:
            products: List of products to sync
        """
        # Process in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_products_to_db_sync, products)
    
    def _sync_products_to_db_sync(self, products: List[Dict[str, Any]]) -> None:
        """
        Sync products to database (synchronous version)
        
        Args:
            products: List of products to sync
        """
        try:
            for product in products:
                sku = product.get('sku')
                if not sku:
                    continue
                
                # Check if product exists in database
                db_product = self.product_repo.get_product_by_sku(sku)
                
                if db_product:
                    # Update existing product
                    self.product_repo.update_product(sku, {
                        'price': product.get('data', {}).get('price', 0),
                        'sale_price': product.get('data', {}).get('salePrice'),
                        'quantity': product.get('data', {}).get('quantity', 0),
                        'status': product.get('data', {}).get('status', 'active'),
                        'updated_at': datetime.now().isoformat()
                    })
                else:
                    # Create new product
                    self.product_repo.create_product({
                        'sku': sku,
                        'title': product.get('data', {}).get('title', ''),
                        'description': product.get('data', {}).get('description', ''),
                        'price': product.get('data', {}).get('price', 0),
                        'sale_price': product.get('data', {}).get('salePrice'),
                        'quantity': product.get('data', {}).get('quantity', 0),
                        'category': product.get('data', {}).get('categoryName', ''),
                        'status': product.get('data', {}).get('status', 'active'),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'metadata': {
                            'platform': self.platform_name,
                            'images': product.get('data', {}).get('images', [])
                        }
                    })
                
                # Link product to platform
                self.product_repo.link_product_to_platform(
                    sku,
                    self.platform_name,
                    {
                        'platform_sku': sku,
                        'price': product.get('data', {}).get('price', 0),
                        'sale_price': product.get('data', {}).get('salePrice'),
                        'quantity': product.get('data', {}).get('quantity', 0),
                        'status': product.get('data', {}).get('status', 'active'),
                        'metadata': {
                            'images': product.get('data', {}).get('images', [])
                        }
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error syncing products to database: {str(e)}")
    
    async def _sync_product_to_db(self, product: Dict[str, Any]) -> None:
        """
        Sync single product to database
        
        Args:
            product: Product to sync
        """
        # Process in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_product_to_db_sync, product)
    
    def _sync_product_to_db_sync(self, product: Dict[str, Any]) -> None:
        """
        Sync single product to database (synchronous version)
        
        Args:
            product: Product to sync
        """
        try:
            sku = product.get('sku')
            if not sku:
                return
            
            # Check if product exists in database
            db_product = self.product_repo.get_product_by_sku(sku)
            
            if db_product:
                # Update existing product
                self.product_repo.update_product(sku, {
                    'price': product.get('data', {}).get('price', 0),
                    'sale_price': product.get('data', {}).get('salePrice'),
                    'quantity': product.get('data', {}).get('quantity', 0),
                    'status': product.get('data', {}).get('status', 'active'),
                    'updated_at': datetime.now().isoformat()
                })
            else:
                # Create new product
                self.product_repo.create_product({
                    'sku': sku,
                    'title': product.get('data', {}).get('title', ''),
                    'description': product.get('data', {}).get('description', ''),
                    'price': product.get('data', {}).get('price', 0),
                    'sale_price': product.get('data', {}).get('salePrice'),
                    'quantity': product.get('data', {}).get('quantity', 0),
                    'category': product.get('data', {}).get('categoryName', ''),
                    'status': product.get('data', {}).get('status', 'active'),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'metadata': {
                        'platform': self.platform_name,
                        'images': product.get('data', {}).get('images', [])
                    }
                })
            
            # Link product to platform
            self.product_repo.link_product_to_platform(
                sku,
                self.platform_name,
                {
                    'platform_sku': sku,
                    'price': product.get('data', {}).get('price', 0),
                    'sale_price': product.get('data', {}).get('salePrice'),
                    'quantity': product.get('data', {}).get('quantity', 0),
                    'status': product.get('data', {}).get('status', 'active'),
                    'metadata': {
                        'images': product.get('data', {}).get('images', [])
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error syncing product to database: {str(e)}")
    
    async def _update_products_in_db(self, products: List[Dict[str, Any]], updated_skus: List[str]) -> None:
        """
        Update products in database after successful API update
        
        Args:
            products: List of products that were updated
            updated_skus: List of SKUs that were successfully updated
        """
        # Process in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._update_products_in_db_sync, products, updated_skus)
    
    def _update_products_in_db_sync(self, products: List[Dict[str, Any]], updated_skus: List[str]) -> None:
        """
        Update products in database after successful API update (synchronous version)
        
        Args:
            products: List of products that were updated
            updated_skus: List of SKUs that were successfully updated
        """
        try:
            for product in products:
                sku = product.get('sku')
                if not sku or sku not in updated_skus:
                    continue
                
                # Update product in database
                self.product_repo.update_product(sku, {
                    'price': product.get('data', {}).get('price'),
                    'sale_price': product.get('data', {}).get('salePrice'),
                    'quantity': product.get('data', {}).get('quantity'),
                    'status': product.get('data', {}).get('status'),
                    'updated_at': datetime.now().isoformat()
                })
                
                # Update platform link
                self.product_repo.link_product_to_platform(
                    sku,
                    self.platform_name,
                    {
                        'price': product.get('data', {}).get('price'),
                        'sale_price': product.get('data', {}).get('salePrice'),
                        'quantity': product.get('data', {}).get('quantity'),
                        'status': product.get('data', {}).get('status')
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error updating products in database: {str(e)}")
    
    def _get_products_from_db(self) -> List[Dict[str, Any]]:
        """
        Get products from database
        
        Returns:
            List of products from database
        """
        try:
            # Get platform ID
            platform = self.product_repo.db.fetch_one(
                "SELECT * FROM platforms WHERE name = ?",
                (self.platform_name,)
            )
            
            if not platform:
                return []
            
            # Get products linked to this platform
            query = """
            SELECT p.*, pp.price as platform_price, pp.sale_price as platform_sale_price,
                   pp.quantity as platform_quantity, pp.status as platform_status,
                   pp.metadata as platform_metadata
            FROM products p
            JOIN platform_products pp ON p.id = pp.product_id
            WHERE pp.platform_id = ?
            """
            
            products = self.product_repo.db.fetch_all(query, (platform['id'],))
            
            # Convert to API format
            result = []
            for p in products:
                # Parse JSON fields
                metadata = {}
                platform_metadata = {}
                
                if p.get('metadata'):
                    try:
                        import json
                        metadata = json.loads(p['metadata'])
                    except:
                        pass
                        
                if p.get('platform_metadata'):
                    try:
                        import json
                        platform_metadata = json.loads(p['platform_metadata'])
                    except:
                        pass
                
                # Use platform-specific values if available, otherwise use general values
                price = p.get('platform_price') if p.get('platform_price') is not None else p.get('price')
                sale_price = p.get('platform_sale_price') if p.get('platform_sale_price') is not None else p.get('sale_price')
                quantity = p.get('platform_quantity') if p.get('platform_quantity') is not None else p.get('quantity')
                status = p.get('platform_status') if p.get('platform_status') is not None else p.get('status')
                
                result.append({
                    'sku': p['sku'],
                    'data': {
                        'title': p['title'],
                        'description': p.get('description', ''),
                        'price': price,
                        'salePrice': sale_price,
                        'quantity': quantity,
                        'categoryName': p.get('category', ''),
                        'status': status,
                        'images': platform_metadata.get('images', metadata.get('images', []))
                    }
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting products from database: {str(e)}")
            return []
    
    def _get_product_from_db(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get product from database
        
        Args:
            sku: Product SKU
            
        Returns:
            Product data or None if not found
        """
        try:
            # Get product
            product = self.product_repo.get_product_by_sku(sku)
            if not product:
                return None
            
            # Get platform-specific data
            platform_products = self.product_repo.get_product_platforms(sku)
            platform_data = next((pp for pp in platform_products if pp['platform_name'] == self.platform_name), None)
            
            # Parse JSON fields
            metadata = product.get('metadata', {})
            platform_metadata = platform_data.get('metadata', {}) if platform_data else {}
            
            # Use platform-specific values if available, otherwise use general values
            price = platform_data.get('price') if platform_data and platform_data.get('price') is not None else product.get('price')
            sale_price = platform_data.get('sale_price') if platform_data and platform_data.get('sale_price') is not None else product.get('sale_price')
            quantity = platform_data.get('quantity') if platform_data and platform_data.get('quantity') is not None else product.get('quantity')
            status = platform_data.get('status') if platform_data and platform_data.get('status') is not None else product.get('status')
            
            return {
                'sku': product['sku'],
                'data': {
                    'title': product['title'],
                    'description': product.get('description', ''),
                    'price': price,
                    'salePrice': sale_price,
                    'quantity': quantity,
                    'categoryName': product.get('category', ''),
                    'status': status,
                    'images': platform_metadata.get('images', metadata.get('images', []))
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting product from database: {str(e)}")
            return None