"""
Unified Synchronization Service combining basic and enhanced functionality
"""

from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

from core.logger import logger
from core.exceptions import ValidationError, APIError, AuthenticationError, NetworkError
from services.unified_product_service import UnifiedProductService
from data.repositories import get_product_repository
from utils.background_tasks import get_task_manager
from utils.helpers import retry_async


class UnifiedSyncService:
    """
    Unified synchronization service with database integration and background tasks
    
    This service combines the functionality of SyncService and EnhancedSyncService:
    - Basic synchronization between platforms
    - Database persistence of sync history
    - Background task processing
    - Progress tracking
    - Enhanced error handling
    - Detailed reporting
    """
    
    def __init__(self, source_service: UnifiedProductService, target_services: List[UnifiedProductService]):
        """
        Initialize unified sync service
        
        Args:
            source_service: Source product service
            target_services: List of target product services
        """
        self.source_service = source_service
        self.target_services = target_services
        self.product_repo = get_product_repository()
        self.task_manager = get_task_manager()
        self.logger = logger
    
    def start_sync(self, **kwargs) -> str:
        """
        Start synchronization in background
        
        Args:
            **kwargs: Sync parameters
                - filter_skus: List of SKUs to sync (if None, sync all)
                - batch_size: Number of products to sync in each batch
                - fields: List of fields to sync (if None, sync all fields)
                
        Returns:
            Task ID for tracking progress
        """
        # Submit task
        task_id = self.task_manager.submit_async_task(
            self._sync_products,
            name=f"Sync {self.source_service.platform_name} to {len(self.target_services)} platforms",
            description=f"Synchronizing products from {self.source_service.platform_name}",
            metadata={
                "source_platform": self.source_service.platform_name,
                "target_platforms": [s.platform_name for s in self.target_services],
                "params": kwargs
            },
            **kwargs
        )
        
        self.logger.info(f"Started sync task {task_id}")
        return task_id
    
    def get_sync_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get sync task status
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status
        """
        return self.task_manager.get_task(task_id)
    
    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get sync history
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of sync history entries
        """
        query = """
        SELECT sh.*, 
               sp.name as source_platform_name, 
               tp.name as target_platform_name
        FROM sync_history sh
        LEFT JOIN platforms sp ON sh.source_platform_id = sp.id
        LEFT JOIN platforms tp ON sh.target_platform_id = tp.id
        ORDER BY sh.started_at DESC
        LIMIT ?
        """
        
        history = self.product_repo.db.fetch_all(query, (limit,))
        
        # Parse JSON fields
        for entry in history:
            if entry.get('details'):
                try:
                    import json
                    entry['details'] = json.loads(entry['details'])
                except:
                    entry['details'] = {}
        
        return history
    
    def get_sync_details(self, sync_id: int) -> Dict[str, Any]:
        """
        Get detailed sync results
        
        Args:
            sync_id: Sync history ID
            
        Returns:
            Detailed sync results
        """
        # Get sync history entry
        sync = self.product_repo.db.fetch_one(
            """
            SELECT sh.*, 
                   sp.name as source_platform_name, 
                   tp.name as target_platform_name
            FROM sync_history sh
            LEFT JOIN platforms sp ON sh.source_platform_id = sp.id
            LEFT JOIN platforms tp ON sh.target_platform_id = tp.id
            WHERE sh.id = ?
            """,
            (sync_id,)
        )
        
        if not sync:
            return {"error": "Sync history not found"}
        
        # Parse JSON fields
        if sync.get('details'):
            try:
                import json
                sync['details'] = json.loads(sync['details'])
            except:
                sync['details'] = {}
        
        # Get product results
        results = self.product_repo.db.fetch_all(
            """
            SELECT spr.*, p.sku
            FROM sync_product_results spr
            JOIN products p ON spr.product_id = p.id
            WHERE spr.sync_id = ?
            """,
            (sync_id,)
        )
        
        # Group results by status
        grouped_results = {
            "success": [],
            "error": [],
            "skipped": []
        }
        
        for result in results:
            status = result.get('status', '').lower()
            if status in grouped_results:
                grouped_results[status].append({
                    "sku": result.get('sku'),
                    "message": result.get('message')
                })
        
        return {
            "sync": sync,
            "results": grouped_results
        }
    
    async def sync_products(self, filter_skus: List[str] = None, 
                           batch_size: int = 50, fields: List[str] = None) -> Dict[str, Any]:
        """
        Synchronize products from source to target platforms (synchronous version)
        
        Args:
            filter_skus: List of SKUs to sync (if None, sync all)
            batch_size: Number of products to sync in each batch
            fields: List of fields to sync (if None, sync all fields)
                
        Returns:
            Dictionary with sync results
        """
        # Create a task ID for tracking
        task_id = self.task_manager.create_task(
            name=f"Sync {self.source_service.platform_name} to {len(self.target_services)} platforms",
            description=f"Synchronizing products from {self.source_service.platform_name}"
        )
        
        # Run the sync in the background
        result = await self._sync_products(
            filter_skus=filter_skus,
            batch_size=batch_size,
            fields=fields,
            task_id=task_id
        )
        
        return result
    
    async def _sync_products(self, filter_skus: List[str] = None, 
                           batch_size: int = 50, fields: List[str] = None,
                           **kwargs) -> Dict[str, Any]:
        """
        Synchronize products from source to target platforms
        
        Args:
            filter_skus: List of SKUs to sync (if None, sync all)
            batch_size: Number of products to sync in each batch
            fields: List of fields to sync (if None, sync all fields)
            **kwargs: Additional parameters
                
        Returns:
            Dictionary with sync results
        """
        try:
            start_time = datetime.now()
            self.logger.info(f"Starting product sync from {self.source_service.platform_name} "
                            f"to {len(self.target_services)} target platforms")
            
            # Create sync history entry
            source_platform = self.product_repo.db.fetch_one(
                "SELECT * FROM platforms WHERE name = ?",
                (self.source_service.platform_name,)
            )
            
            sync_history_id = self.product_repo.db.insert(
                'sync_history',
                {
                    'source_platform_id': source_platform['id'] if source_platform else None,
                    'products_count': 0,
                    'success_count': 0,
                    'error_count': 0,
                    'started_at': start_time.isoformat(),
                    'status': 'running',
                    'details': {
                        'filter_skus': filter_skus,
                        'batch_size': batch_size,
                        'fields': fields,
                        'target_platforms': [s.platform_name for s in self.target_services]
                    }
                }
            )
            
            # Get products from source
            source_products = await self.source_service.get_products()
            
            if not source_products:
                self.logger.warning("No products found in source platform")
                
                # Update sync history
                self.product_repo.db.update(
                    'sync_history',
                    {
                        'completed_at': datetime.now().isoformat(),
                        'status': 'completed',
                        'details': {
                            'filter_skus': filter_skus,
                            'batch_size': batch_size,
                            'fields': fields,
                            'target_platforms': [s.platform_name for s in self.target_services],
                            'duration_seconds': (datetime.now() - start_time).total_seconds(),
                            'message': "No products found in source platform"
                        }
                    },
                    'id = ?',
                    (sync_history_id,)
                )
                
                return {
                    'status': 'completed',
                    'products_synced': 0,
                    'errors': [],
                    'skipped': [],
                    'duration_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            self.logger.info(f"Retrieved {len(source_products)} products from source platform")
            
            # Update sync history with product count
            self.product_repo.db.update(
                'sync_history',
                {
                    'products_count': len(source_products)
                },
                'id = ?',
                (sync_history_id,)
            )
            
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
            
            # Update task progress
            self.task_manager.update_progress(
                kwargs.get('task_id'),
                0,
                f"Processing {len(source_products)} products in {len(batches)} batches"
            )
            
            for batch_index, batch in enumerate(batches):
                self.logger.info(f"Processing batch {batch_index + 1}/{len(batches)} ({len(batch)} products)")
                
                # Update task progress
                progress = int((batch_index / len(batches)) * 100)
                self.task_manager.update_progress(
                    kwargs.get('task_id'),
                    progress,
                    f"Processing batch {batch_index + 1}/{len(batches)}"
                )
                
                # Process each target platform
                for target_service in self.target_services:
                    try:
                        target_name = target_service.platform_name
                        self.logger.info(f"Syncing batch to {target_name}")
                        
                        # Get target platform
                        target_platform = self.product_repo.db.fetch_one(
                            "SELECT * FROM platforms WHERE name = ?",
                            (target_name,)
                        )
                        
                        # Filter fields if needed
                        if fields:
                            filtered_batch = self._filter_product_fields(batch, fields)
                        else:
                            filtered_batch = batch
                        
                        # Update products on target platform
                        result = await target_service.update_products(filtered_batch)
                        
                        # Collect results
                        updated = result.get('updated', [])
                        errors = result.get('errors', [])
                        skipped = result.get('skipped', [])
                        
                        total_updated += len(updated)
                        total_errors.extend([{**err, 'platform': target_name} for err in errors])
                        total_skipped.extend([{**skip, 'platform': target_name} for skip in skipped])
                        
                        # Record results in database
                        for product in filtered_batch:
                            sku = product.get('sku')
                            if not sku:
                                continue
                                
                            # Get product ID
                            db_product = self.product_repo.get_product_by_sku(sku)
                            if not db_product:
                                continue
                                
                            # Determine status and message
                            status = 'success'
                            message = f"Successfully updated on {target_name}"
                            
                            # Check if product had an error
                            error = next((err for err in errors if err.get('sku') == sku), None)
                            if error:
                                status = 'error'
                                message = error.get('error', f"Error updating on {target_name}")
                            
                            # Check if product was skipped
                            skip = next((skip for skip in skipped if skip.get('sku') == sku), None)
                            if skip:
                                status = 'skipped'
                                message = skip.get('reason', f"Skipped on {target_name}")
                            
                            # Record result
                            self.product_repo.db.insert(
                                'sync_product_results',
                                {
                                    'sync_id': sync_history_id,
                                    'product_id': db_product['id'],
                                    'status': status,
                                    'message': message
                                }
                            )
                        
                        self.logger.info(f"Batch sync to {target_name} completed: "
                                        f"{len(updated)} updated, "
                                        f"{len(errors)} errors, "
                                        f"{len(skipped)} skipped")
                        
                    except AuthenticationError as e:
                        self.logger.error(f"Authentication error with {target_service.platform_name}: {str(e)}")
                        total_errors.append({
                            'platform': target_service.platform_name,
                            'error': f"Authentication failed: {str(e)}",
                            'batch': batch_index + 1
                        })
                        
                    except NetworkError as e:
                        self.logger.error(f"Network error with {target_service.platform_name}: {str(e)}")
                        total_errors.append({
                            'platform': target_service.platform_name,
                            'error': f"Network error: {str(e)}",
                            'batch': batch_index + 1
                        })
                        
                    except Exception as e:
                        self.logger.error(f"Error syncing to {target_service.platform_name}: {str(e)}")
                        total_errors.append({
                            'platform': target_service.platform_name,
                            'error': str(e),
                            'batch': batch_index + 1
                        })
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Sync completed in {duration:.2f} seconds: "
                            f"{total_updated} products updated, "
                            f"{len(total_errors)} errors, "
                            f"{len(total_skipped)} skipped")
            
            # Update sync history
            self.product_repo.db.update(
                'sync_history',
                {
                    'completed_at': datetime.now().isoformat(),
                    'status': 'completed',
                    'success_count': total_updated,
                    'error_count': len(total_errors),
                    'details': {
                        'filter_skus': filter_skus,
                        'batch_size': batch_size,
                        'fields': fields,
                        'target_platforms': [s.platform_name for s in self.target_services],
                        'duration_seconds': duration,
                        'errors': total_errors[:100],  # Limit to avoid excessive storage
                        'skipped': total_skipped[:100]  # Limit to avoid excessive storage
                    }
                },
                'id = ?',
                (sync_history_id,)
            )
            
            # Update task progress to 100%
            self.task_manager.update_progress(
                kwargs.get('task_id'),
                100,
                f"Sync completed: {total_updated} products updated"
            )
            
            return {
                'status': 'completed',
                'products_synced': total_updated,
                'errors': total_errors,
                'skipped': total_skipped,
                'duration_seconds': duration,
                'sync_id': sync_history_id
            }
            
        except Exception as e:
            self.logger.error(f"Error during product sync: {str(e)}")
            
            # Update sync history with error
            try:
                self.product_repo.db.update(
                    'sync_history',
                    {
                        'completed_at': datetime.now().isoformat(),
                        'status': 'failed',
                        'details': {
                            'filter_skus': filter_skus,
                            'batch_size': batch_size,
                            'fields': fields,
                            'target_platforms': [s.platform_name for s in self.target_services],
                            'duration_seconds': (datetime.now() - start_time).total_seconds(),
                            'error': str(e)
                        }
                    },
                    'id = ?',
                    (sync_history_id,)
                )
            except:
                pass
            
            raise
    
    def _filter_product_fields(self, products: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
        """
        Filter product fields to only include specified fields
        
        Args:
            products: List of products
            fields: List of fields to include
            
        Returns:
            Filtered products
        """
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