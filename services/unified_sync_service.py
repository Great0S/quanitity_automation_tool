"""
Unified Sync Service for synchronizing products between platforms
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Set, Union, cast
from datetime import datetime
import json
import os
from core.logger import logger
from core.exceptions import APIError, SyncError
from services.unified_product_service import UnifiedProductService
from utils.background_tasks import get_task_manager
from data.repositories import get_sync_repository, get_product_repository

class UnifiedSyncService:
    """Service for synchronizing products between platforms"""
    
    def __init__(self, source_service: UnifiedProductService, target_services: List[UnifiedProductService]):
        """
        Initialize the sync service
        
        Args:
            source_service: Source platform service
            target_services: List of target platform services
        """
        self.source_service = source_service
        self.target_services = target_services
        self.task_manager = get_task_manager()
        self.sync_repo = get_sync_repository()
        self.product_repo = get_product_repository()
        
    def start_sync(self, filter_skus: Optional[List[str]] = None, 
                  batch_size: int = 50, fields: Optional[List[str]] = None) -> str:
        """
        Start a synchronization task
        
        Args:
            filter_skus: Optional list of SKUs to filter
            batch_size: Number of products to process in each batch
            fields: Optional list of fields to sync (price, quantity, status)
            
        Returns:
            Task ID
        """
        # Create a task for the sync operation
        task_id = self.task_manager.create_task(
            name=f"Sync {self.source_service.platform_name} to {', '.join([s.platform_name for s in self.target_services])}",
            description=f"Syncing products from {self.source_service.platform_name} to {len(self.target_services)} platforms"
        )
        
        # Submit the sync task
        self.task_manager.submit_async_task(
            self._run_sync,
            name=f"Sync {self.source_service.platform_name}",
            description=f"Syncing products from {self.source_service.platform_name}",
            task_id=task_id,
            filter_skus=filter_skus,
            batch_size=batch_size,
            fields=fields or ["price", "quantity", "status"]
        )
        
        return task_id
    
    async def _run_sync(self, task_id: str, filter_skus: Optional[List[str]], 
                       batch_size: int, fields: List[str]) -> Dict[str, Any]:
        """
        Run the synchronization process
        
        Args:
            task_id: Task ID
            filter_skus: Optional list of SKUs to filter
            batch_size: Number of products to process in each batch
            fields: List of fields to sync
            
        Returns:
            Sync results
        """
        try:
            # Create sync record
            sync_id = await self.sync_repo.create_sync(
                source_platform=self.source_service.platform_name,
                target_platforms=[s.platform_name for s in self.target_services],
                status="running",
                fields=fields,
                filter_skus=filter_skus
            )
            
            # Update task metadata
            self.task_manager.update_progress(
                task_id=task_id,
                progress=5,
                message=f"Starting sync {sync_id}"
            )
            
            # Get products from source platform
            logger.info(f"Fetching products from {self.source_service.platform_name}")
            source_products = await self.source_service.get_products(force_refresh=True)
            
            # Filter products if needed
            if filter_skus:
                source_products = [p for p in source_products if p["sku"] in filter_skus]
            
            total_products = len(source_products)
            logger.info(f"Found {total_products} products to sync")
            
            if total_products == 0:
                await self.sync_repo.update_sync(
                    sync_id=sync_id,
                    status="completed",
                    success_count=0,
                    error_count=0,
                    completed_at=datetime.now()
                )
                return {"sync_id": sync_id, "status": "completed", "products": 0, "success": 0, "errors": 0}
            
            # Update task progress
            self.task_manager.update_progress(
                task_id=task_id,
                progress=10,
                message=f"Found {total_products} products to sync"
            )
            
            # Process products in batches
            batches = [source_products[i:i+batch_size] for i in range(0, len(source_products), batch_size)]
            total_batches = len(batches)
            
            success_count = 0
            error_count = 0
            results = []
            
            for batch_index, batch in enumerate(batches):
                batch_progress = 10 + (batch_index / total_batches) * 80
                self.task_manager.update_progress(
                    task_id=task_id,
                    progress=int(batch_progress),
                    message=f"Processing batch {batch_index+1}/{total_batches}"
                )
                
                # Process each product in the batch
                batch_results = await self._process_batch(batch, fields)
                results.extend(batch_results)
                
                # Update counts
                batch_success = sum(1 for r in batch_results if r["status"] == "success")
                batch_errors = sum(1 for r in batch_results if r["status"] == "error")
                success_count += batch_success
                error_count += batch_errors
                
                # Update sync record
                await self.sync_repo.update_sync(
                    sync_id=sync_id,
                    success_count=success_count,
                    error_count=error_count
                )
                
                logger.info(f"Batch {batch_index+1}/{total_batches} completed: {batch_success} success, {batch_errors} errors")
            
            # Complete the sync
            await self.sync_repo.update_sync(
                sync_id=sync_id,
                status="completed",
                success_count=success_count,
                error_count=error_count,
                completed_at=datetime.now()
            )
            
            # Save detailed results
            await self.sync_repo.save_sync_results(sync_id, results)
            
            # Update task progress
            self.task_manager.update_progress(
                task_id=task_id,
                progress=100,
                message=f"Sync completed: {success_count} success, {error_count} errors"
            )
            
            return {
                "sync_id": sync_id,
                "status": "completed",
                "products": total_products,
                "success": success_count,
                "errors": error_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Sync error: {str(e)}")
            
            # Update sync record if it was created
            if 'sync_id' in locals():
                await self.sync_repo.update_sync(
                    sync_id=sync_id,
                    status="failed",
                    error=str(e),
                    completed_at=datetime.now()
                )
            
            raise SyncError(f"Sync failed: {str(e)}")
    
    async def _process_batch(self, products: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
        """
        Process a batch of products
        
        Args:
            products: List of products to process
            fields: List of fields to sync
            
        Returns:
            List of results
        """
        results = []
        
        for product in products:
            sku = product["sku"]
            product_data = product["data"]
            
            # Extract fields to sync
            sync_data = {field: product_data.get(field) for field in fields if field in product_data}
            
            # Skip if no data to sync
            if not sync_data:
                results.append({
                    "sku": sku,
                    "status": "skipped",
                    "message": "No data to sync"
                })
                continue
            
            # Process each target platform
            platform_results = []
            for target_service in self.target_services:
                try:
                    # Update product on target platform
                    update_result = await target_service.update_product({
                        "sku": sku,
                        "data": sync_data
                    })
                    
                    platform_results.append({
                        "platform": target_service.platform_name,
                        "status": "success",
                        "message": "Product updated successfully"
                    })
                    
                except Exception as e:
                    logger.error(f"Error updating product {sku} on {target_service.platform_name}: {str(e)}")
                    platform_results.append({
                        "platform": target_service.platform_name,
                        "status": "error",
                        "message": str(e)
                    })
            
            # Determine overall status
            overall_status = "success"
            if all(r["status"] == "error" for r in platform_results):
                overall_status = "error"
            elif any(r["status"] == "error" for r in platform_results):
                overall_status = "partial"
            
            results.append({
                "sku": sku,
                "status": overall_status,
                "platforms": platform_results
            })
        
        return results
    
    async def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get sync history
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of sync records
        """
        return await self.sync_repo.get_syncs(limit=limit)
    
    async def get_sync_details(self, sync_id: int) -> Dict[str, Any]:
        """
        Get detailed sync results
        
        Args:
            sync_id: Sync ID
            
        Returns:
            Sync details
        """
        # Get sync record
        sync = await self.sync_repo.get_sync(sync_id)
        if not sync:
            return {"error": f"Sync {sync_id} not found"}
        
        # Get detailed results
        results = await self.sync_repo.get_sync_results(sync_id)
        
        return {
            "sync": sync,
            "results": results
        }
    
    async def bulk_update_lowest_stock(self, filter_skus: Optional[List[str]] = None) -> str:
        """
        Update all products with the lowest stock quantity across platforms
        
        Args:
            filter_skus: Optional list of SKUs to filter
            
        Returns:
            Task ID
        """
        # Create a task for the bulk update
        task_id = self.task_manager.create_task(
            name="Bulk Update Lowest Stock",
            description="Updating products with lowest stock quantity across platforms"
        )
        
        # Submit the bulk update task
        self.task_manager.submit_async_task(
            self._run_bulk_update_lowest_stock,
            name="Bulk Update Lowest Stock",
            description="Updating products with lowest stock quantity across platforms",
            task_id=task_id,
            filter_skus=filter_skus
        )
        
        return task_id
    
    async def _run_bulk_update_lowest_stock(self, task_id: str, filter_skus: Optional[List[str]]) -> Dict[str, Any]:
        """
        Run the bulk update process for lowest stock
        
        Args:
            task_id: Task ID
            filter_skus: Optional list of SKUs to filter
            
        Returns:
            Update results
        """
        try:
            # Update task progress
            self.task_manager.update_progress(
                task_id=task_id,
                progress=5,
                message="Starting bulk update"
            )
            
            # Get all SKUs across platforms
            all_skus: Set[str] = set()
            platform_products: Dict[str, Dict[str, Dict[str, Any]]] = {}
            
            # Get products from all platforms
            all_platforms = [self.source_service] + self.target_services
            for platform_service in all_platforms:
                platform_name = platform_service.platform_name
                logger.info(f"Fetching products from {platform_name}")
                
                products = await platform_service.get_products(force_refresh=True)
                platform_products[platform_name] = {p["sku"]: p for p in products}
                all_skus.update(p["sku"] for p in products)
            
            # Filter SKUs if needed
            if filter_skus:
                all_skus = {sku for sku in all_skus if sku in filter_skus}
            
            total_skus = len(all_skus)
            logger.info(f"Found {total_skus} unique SKUs across platforms")
            
            if total_skus == 0:
                return {"status": "completed", "products": 0, "success": 0, "errors": 0}
            
            # Update task progress
            self.task_manager.update_progress(
                task_id=task_id,
                progress=10,
                message=f"Found {total_skus} products to update"
            )
            
            # Process each SKU
            success_count = 0
            error_count = 0
            results = []
            
            for i, sku in enumerate(all_skus):
                progress = 10 + (i / total_skus) * 90
                self.task_manager.update_progress(
                    task_id=task_id,
                    progress=int(progress),
                    message=f"Processing product {i+1}/{total_skus}"
                )
                
                # Find lowest stock quantity across platforms
                quantities = []
                for platform_name, products in platform_products.items():
                    if sku in products:
                        product = products[sku]
                        quantity = product.get("data", {}).get("quantity")
                        if quantity is not None:
                            quantities.append((platform_name, quantity))
                
                if not quantities:
                    results.append({
                        "sku": sku,
                        "status": "skipped",
                        "message": "No quantity data found"
                    })
                    continue
                
                # Find platform with lowest quantity
                lowest_platform, lowest_quantity = min(quantities, key=lambda x: x[1])
                
                # Update all platforms with the lowest quantity
                platform_results = []
                for platform_service in all_platforms:
                    platform_name = platform_service.platform_name
                    
                    # Skip if product doesn't exist on this platform
                    if sku not in platform_products.get(platform_name, {}):
                        continue
                    
                    # Skip if quantity is already the lowest
                    current_quantity = platform_products[platform_name][sku].get("data", {}).get("quantity")
                    if current_quantity == lowest_quantity:
                        platform_results.append({
                            "platform": platform_name,
                            "status": "skipped",
                            "message": "Already at lowest quantity"
                        })
                        continue
                    
                    try:
                        # Update product on platform
                        update_result = await platform_service.update_product({
                            "sku": sku,
                            "data": {"quantity": lowest_quantity}
                        })
                        
                        platform_results.append({
                            "platform": platform_name,
                            "status": "success",
                            "message": f"Updated quantity from {current_quantity} to {lowest_quantity}"
                        })
                        
                    except Exception as e:
                        logger.error(f"Error updating product {sku} on {platform_name}: {str(e)}")
                        platform_results.append({
                            "platform": platform_name,
                            "status": "error",
                            "message": str(e)
                        })
                
                # Determine overall status
                overall_status = "success"
                if all(r["status"] == "error" for r in platform_results if r["status"] != "skipped"):
                    overall_status = "error"
                    error_count += 1
                elif any(r["status"] == "error" for r in platform_results):
                    overall_status = "partial"
                    success_count += 1
                else:
                    success_count += 1
                
                results.append({
                    "sku": sku,
                    "status": overall_status,
                    "lowest_quantity": lowest_quantity,
                    "lowest_platform": lowest_platform,
                    "platforms": platform_results
                })
            
            # Update task progress
            self.task_manager.update_progress(
                task_id=task_id,
                progress=100,
                message=f"Bulk update completed: {success_count} success, {error_count} errors"
            )
            
            return {
                "status": "completed",
                "products": total_skus,
                "success": success_count,
                "errors": error_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Bulk update error: {str(e)}")
            raise SyncError(f"Bulk update failed: {str(e)}")
    
    async def update_single_product(self, sku: str, data: Dict[str, Any], 
                                  target_platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Update a single product across platforms
        
        Args:
            sku: Product SKU
            data: Product data to update
            target_platforms: Optional list of target platforms (default: all)
            
        Returns:
            Update results
        """
        results = []
        
        # Determine target platforms
        if target_platforms:
            platforms = [s for s in self.target_services if s.platform_name in target_platforms]
        else:
            platforms = self.target_services
        
        # Update product on each platform
        for platform_service in platforms:
            try:
                update_result = await platform_service.update_product({
                    "sku": sku,
                    "data": data
                })
                
                results.append({
                    "platform": platform_service.platform_name,
                    "status": "success",
                    "message": "Product updated successfully"
                })
                
            except Exception as e:
                logger.error(f"Error updating product {sku} on {platform_service.platform_name}: {str(e)}")
                results.append({
                    "platform": platform_service.platform_name,
                    "status": "error",
                    "message": str(e)
                })
        
        # Determine overall status
        overall_status = "success"
        if all(r["status"] == "error" for r in results):
            overall_status = "error"
        elif any(r["status"] == "error" for r in results):
            overall_status = "partial"
        
        return {
            "sku": sku,
            "status": overall_status,
            "platforms": results
        }
    
    async def update_multiple_products(self, products: List[Dict[str, Any]], 
                                     target_platforms: Optional[List[str]] = None) -> str:
        """
        Update multiple products across platforms
        
        Args:
            products: List of products to update (each with sku and data)
            target_platforms: Optional list of target platforms (default: all)
            
        Returns:
            Task ID
        """
        # Create a task for the multi-product update
        task_id = self.task_manager.create_task(
            name=f"Update {len(products)} Products",
            description=f"Updating {len(products)} products across platforms"
        )
        
        # Submit the update task
        self.task_manager.submit_async_task(
            self._run_multi_product_update,
            name=f"Update {len(products)} Products",
            description=f"Updating {len(products)} products across platforms",
            task_id=task_id,
            products=products,
            target_platforms=target_platforms
        )
        
        return task_id
    
    async def _run_multi_product_update(self, task_id: str, products: List[Dict[str, Any]], 
                                      target_platforms: Optional[List[str]]) -> Dict[str, Any]:
        """
        Run the multi-product update process
        
        Args:
            task_id: Task ID
            products: List of products to update
            target_platforms: Optional list of target platforms
            
        Returns:
            Update results
        """
        try:
            # Update task progress
            self.task_manager.update_progress(
                task_id=task_id,
                progress=5,
                message=f"Starting update for {len(products)} products"
            )
            
            # Determine target platforms
            if target_platforms:
                platforms = [s for s in self.target_services if s.platform_name in target_platforms]
            else:
                platforms = self.target_services
            
            total_products = len(products)
            success_count = 0
            error_count = 0
            results = []
            
            # Process each product
            for i, product in enumerate(products):
                progress = 5 + (i / total_products) * 95
                self.task_manager.update_progress(
                    task_id=task_id,
                    progress=int(progress),
                    message=f"Processing product {i+1}/{total_products}"
                )
                
                sku = product.get("sku")
                data = product.get("data", {})
                
                if not sku or not data:
                    results.append({
                        "sku": sku or "unknown",
                        "status": "error",
                        "message": "Missing SKU or data"
                    })
                    error_count += 1
                    continue
                
                # Update product on each platform
                platform_results = []
                for platform_service in platforms:
                    try:
                        update_result = await platform_service.update_product({
                            "sku": sku,
                            "data": data
                        })
                        
                        platform_results.append({
                            "platform": platform_service.platform_name,
                            "status": "success",
                            "message": "Product updated successfully"
                        })
                        
                    except Exception as e:
                        logger.error(f"Error updating product {sku} on {platform_service.platform_name}: {str(e)}")
                        platform_results.append({
                            "platform": platform_service.platform_name,
                            "status": "error",
                            "message": str(e)
                        })
                
                # Determine overall status
                overall_status = "success"
                if all(r["status"] == "error" for r in platform_results):
                    overall_status = "error"
                    error_count += 1
                elif any(r["status"] == "error" for r in platform_results):
                    overall_status = "partial"
                    success_count += 1
                else:
                    success_count += 1
                
                results.append({
                    "sku": sku,
                    "status": overall_status,
                    "platforms": platform_results
                })
            
            # Update task progress
            self.task_manager.update_progress(
                task_id=task_id,
                progress=100,
                message=f"Update completed: {success_count} success, {error_count} errors"
            )
            
            return {
                "status": "completed",
                "products": total_products,
                "success": success_count,
                "errors": error_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Multi-product update error: {str(e)}")
            raise SyncError(f"Multi-product update failed: {str(e)}")