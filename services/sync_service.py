"""
Synchronization service for product data between platforms
"""

from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime
from core.exceptions import ValidationError, APIError, AuthenticationError, NetworkError
from core.logger import logger
from services.product_service import ProductService

class SyncService:
    """Service for synchronizing product data between platforms"""
    
    def __init__(self, source_service: ProductService, target_services: List[ProductService]):
        self.source_service = source_service
        self.target_services = target_services
        self.logger = logger

    async def sync_products(self, **kwargs) -> Dict[str, Any]:
        """
        Synchronize products from source to target platforms
        
        Args:
            **kwargs: Optional parameters
                - filter_skus: List of SKUs to sync (if None, sync all)
                - batch_size: Number of products to sync in each batch
                - fields: List of fields to sync (if None, sync all fields)
                
        Returns:
            Dict with sync results
        """
        try:
            start_time = datetime.now()
            self.logger.info(f"Starting product sync from {self.source_service.api_client.__class__.__name__} "
                            f"to {len(self.target_services)} target platforms")
            
            # Get filter parameters
            filter_skus = kwargs.get('filter_skus')
            batch_size = kwargs.get('batch_size', 50)
            fields_to_sync = kwargs.get('fields', None)
            
            # Get products from source
            source_products = await self.source_service.get_products()
            
            if not source_products:
                self.logger.warning("No products found in source platform")
                return {
                    'status': 'completed',
                    'products_synced': 0,
                    'errors': [],
                    'skipped': [],
                    'duration_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            self.logger.info(f"Retrieved {len(source_products)} products from source platform")
            
            # Filter products if needed
            if filter_skus:
                source_products = [p for p in source_products if p.get('sku') in filter_skus]
                self.logger.info(f"Filtered to {len(source_products)} products based on SKU list")
            
            # Process in batches
            total_updated = 0
            total_errors = []
            total_skipped = []
            
            # Split into batches
            batches = [source_products[i:i + batch_size] for i in range(0, len(source_products), batch_size)]
            
            for batch_index, batch in enumerate(batches):
                self.logger.info(f"Processing batch {batch_index + 1}/{len(batches)} ({len(batch)} products)")
                
                # Process each target platform
                for target_service in self.target_services:
                    try:
                        target_name = target_service.api_client.__class__.__name__
                        self.logger.info(f"Syncing batch to {target_name}")
                        
                        # Filter fields if needed
                        if fields_to_sync:
                            filtered_batch = self._filter_product_fields(batch, fields_to_sync)
                        else:
                            filtered_batch = batch
                        
                        # Update products on target platform
                        result = await target_service.update_products(filtered_batch)
                        
                        # Collect results
                        total_updated += len(result.get('updated', []))
                        total_errors.extend([{**err, 'platform': target_name} for err in result.get('errors', [])])
                        total_skipped.extend([{**skip, 'platform': target_name} for skip in result.get('skipped', [])])
                        
                        self.logger.info(f"Batch sync to {target_name} completed: "
                                        f"{len(result.get('updated', []))} updated, "
                                        f"{len(result.get('errors', []))} errors, "
                                        f"{len(result.get('skipped', []))} skipped")
                        
                    except AuthenticationError as e:
                        self.logger.error(f"Authentication error with {target_service.api_client.__class__.__name__}: {str(e)}")
                        total_errors.append({
                            'platform': target_service.api_client.__class__.__name__,
                            'error': f"Authentication failed: {str(e)}",
                            'batch': batch_index + 1
                        })
                        
                    except NetworkError as e:
                        self.logger.error(f"Network error with {target_service.api_client.__class__.__name__}: {str(e)}")
                        total_errors.append({
                            'platform': target_service.api_client.__class__.__name__,
                            'error': f"Network error: {str(e)}",
                            'batch': batch_index + 1
                        })
                        
                    except Exception as e:
                        self.logger.error(f"Error syncing to {target_service.api_client.__class__.__name__}: {str(e)}")
                        total_errors.append({
                            'platform': target_service.api_client.__class__.__name__,
                            'error': str(e),
                            'batch': batch_index + 1
                        })
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Sync completed in {duration:.2f} seconds: "
                            f"{total_updated} products updated, "
                            f"{len(total_errors)} errors, "
                            f"{len(total_skipped)} skipped")
            
            return {
                'status': 'completed',
                'products_synced': total_updated,
                'errors': total_errors,
                'skipped': total_skipped,
                'duration_seconds': duration
            }
            
        except AuthenticationError as e:
            self.logger.error(f"Authentication error during sync: {str(e)}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")
            
        except NetworkError as e:
            self.logger.error(f"Network error during sync: {str(e)}")
            raise AuthenticationError(f"Network error: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error during product sync: {str(e)}")
            raise AuthenticationError(f"Sync failed: {str(e)}")

    def _filter_product_fields(self, products: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
        """Filter product fields to only include specified fields"""
        filtered_products = []
        
        for product in products:
            # Always include SKU
            filtered_product = {'sku': product.get('sku')}
            
            # Filter data fields
            if 'data' in product:
                filtered_data = {}
                for field in fields:
                    if field in product['data']:
                        filtered_data[field] = product['data'][field]
                
                filtered_product['data'] = filtered_data
            
            filtered_products.append(filtered_product)
        
        return filtered_products