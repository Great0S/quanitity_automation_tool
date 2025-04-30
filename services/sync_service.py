from typing import Dict, List, Any
from services.product_service import ProductService
from core.exceptions import SyncError
from datetime import datetime
from core.logger import logger

class SyncService:
    def __init__(self, source_service: ProductService, target_service: ProductService):
        """
        Initialize sync service
        
        Args:   
            source_service: Source platform service
            target_service: Target platform service
        """
        if not isinstance(source_service, ProductService):
            raise ValueError("source_service must implement ProductService")
        if not isinstance(target_service, ProductService):
            raise ValueError("target_service must implement ProductService")
            
        self.source_service = source_service
        self.target_service = target_service
        self.logger = logger

    async def sync_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sync products from source to target
        
        Args:
            products: List of products to sync
            
        Returns:
            Dict with sync results
        """
        try:
            start_time = datetime.now()
            self.logger.info(f"Starting product sync at {start_time}")

            results = {
                'total': len(products),
                'successful': 0,
                'failed': 0,
                'errors': [],
                'start_time': start_time,
                'end_time': None,
                'duration': None
            }

            for product in products:
                try:
                    # Validate product data
                    errors = self.target_service.validate_product_data(product)
                    if errors:
                        raise SyncError(f"Product validation failed: {errors}")

                    # Update product
                    await self.target_service.update_products([product])
                    results['successful'] += 1

                except Exception as e:
                    self.logger.error(f"Error syncing product {product.get('sku')}: {str(e)}")
                    results['failed'] += 1
                    results['errors'].append({
                        'sku': product.get('sku'),
                        'error': str(e)
                    })

            end_time = datetime.now()
            results['end_time'] = end_time
            results['duration'] = (end_time - start_time).total_seconds()

            self.logger.info(f"Sync completed. Success: {results['successful']}, Failed: {results['failed']}")
            return results

        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}")
            raise SyncError(f"Sync failed: {str(e)}")

    def verify_sync(self, source_products: List[Dict[str, Any]], 
                   target_products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify sync results"""
        verification = {
            'total': len(source_products),
            'matched': 0,
            'mismatched': 0,
            'missing': 0,
            'discrepancies': []
        }

        source_dict = {p['sku']: p for p in source_products}
        target_dict = {p['sku']: p for p in target_products}

        for sku, source_product in source_dict.items():
            if sku not in target_dict:
                verification['missing'] += 1
                verification['discrepancies'].append({
                    'sku': sku,
                    'type': 'missing',
                    'details': 'Product not found in target'
                })
                continue

            target_product = target_dict[sku]
            discrepancies = self._compare_products(source_product, target_product)

            if discrepancies:
                verification['mismatched'] += 1
                verification['discrepancies'].append({
                    'sku': sku,
                    'type': 'mismatch',
                    'details': discrepancies
                })
            else:
                verification['matched'] += 1

        return verification

    def _compare_products(self, source: Dict[str, Any], 
                         target: Dict[str, Any]) -> List[str]:
        """Compare source and target products"""
        discrepancies = []
        fields_to_compare = ['price', 'quantity', 'title']

        for field in fields_to_compare:
            source_value = source.get('data', {}).get(field)
            target_value = target.get('data', {}).get(field)

            if source_value != target_value:
                discrepancies.append(f"{field}: {source_value} != {target_value}")

        return discrepancies
