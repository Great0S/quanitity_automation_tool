"""
Hepsiburada API Client
"""

import os
import json
import base64
import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional, Union, cast
from datetime import datetime
from core.exceptions import APIError, AuthenticationError, NetworkError, RateLimitError
from core.logger import logger
from core.error_handler import handle_exceptions, safe_execute, error_handler
from .base_client import BaseAPIClient


class HepsiburadaClient(BaseAPIClient):
    """Hepsiburada API Client"""

    def __init__(self) -> None:
        super().__init__()
        self._setup_credentials()
        self._setup_endpoints()
        self.logger = logger
        self.retry_delay = 2  # seconds

    def _setup_credentials(self) -> None:
        """Setup API credentials"""
        try:
            self.username = os.getenv("HEPSIBURADA_USERNAME")
            self.password = os.getenv("HEPSIBURADA_PASSWORD")
            self.merchant_id = os.getenv(
                "HEPSIBURADA_MERCHANT_ID", self.username
            )  # Use username as merchant ID if not provided

            if not self.username:
                error_context = {
                    "client": "Hepsiburada",
                    "operation": "_setup_credentials",
                    "missing": "HEPSIBURADA_USERNAME",
                }
                error_handler.log_error(
                    AuthenticationError("HEPSIBURADA_USERNAME environment variable is not set"),
                    error_context,
                )
                self.logger.error("HEPSIBURADA_USERNAME environment variable is not set")

            if not self.password:
                error_context = {
                    "client": "Hepsiburada",
                    "operation": "_setup_credentials",
                    "missing": "HEPSIBURADA_PASSWORD",
                }
                error_handler.log_error(
                    AuthenticationError("HEPSIBURADA_PASSWORD environment variable is not set"),
                    error_context,
                )
                self.logger.error("HEPSIBURADA_PASSWORD environment variable is not set")

            if not all([self.username, self.password]):
                raise AuthenticationError("Missing Hepsiburada API credentials")

            # Create Basic Auth header
            auth_string = f"{self.merchant_id}:{self.password}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            # API configuration
            self.base_url = "https://mpop.hepsiburada.com"  # Correct API endpoint for Hepsiburada
            self.api_version = "product/api"  # Updated API version path based on Postman example
            self.headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Basic {auth_b64}",
                "User-Agent": "sentosyazilim_dev",  # Updated User-Agent based on Postman example
            }

            # Override base client settings
            self.request_timeout = 90  # Increase timeout for Hepsiburada
            self.max_retries = 5  # More retries
            self.retry_delay = 3  # Longer delay between retries

            # Log initialization (without sensitive data)
            logger.debug(f"Hepsiburada client initialized for merchant ID: {self.merchant_id}")
        except Exception as e:
            error_context = {"client": "Hepsiburada", "operation": "_setup_credentials"}
            error_handler.log_error(e, error_context)
            raise

    def _setup_endpoints(self) -> None:
        """Setup API endpoints"""
        try:
            # Hepsiburada API endpoints based on their documentation and Postman example
            self.endpoints = {
                "listings": "/listings",
                "products": "/products/all-products-of-merchant",
                "orders": "/orders",
                "inventory": "/inventory",
                "categories": "/categories/get-all-categories",  # Updated based on Postman example
                "merchants": "/merchants",
                "status": "/status",
            }
            logger.debug(f"Hepsiburada endpoints configured: {list(self.endpoints.keys())}")
        except Exception as e:
            error_context = {"client": "Hepsiburada", "operation": "_setup_endpoints"}
            error_handler.log_error(e, error_context)
            raise

    @handle_exceptions
    async def authenticate(self) -> None:
        """Authenticate with Hepsiburada API"""
        try:
            logger.info("Authenticating with Hepsiburada API...")

            # Initialize session if not already done
            if not self.session:
                # Disable SSL verification for development
                connector = aiohttp.TCPConnector(
                    ssl=False,  # Disable SSL verification to avoid certificate issues
                    use_dns_cache=True,
                    ttl_dns_cache=300,  # 5 minutes DNS cache
                    limit=100,  # Connection pool limit
                )
                # Create session without timeout
                self.session = aiohttp.ClientSession(connector=connector)

            # Test authentication with a simple request
            try:
                # Skip status check and go directly to authentication
                logger.debug(f"Skipping status check and proceeding directly to authentication")

                # Try a simple authenticated request to test credentials using the categories endpoint from Postman example
                test_response = await self._make_request(
                    method="GET",
                    url=f"{self.base_url}/{self.api_version}/categories/get-all-categories",
                    headers=self.headers,
                    params={"size": 10},  # Just get a few categories to test authentication
                )

                # Print response for debugging
                logger.debug(f"Hepsiburada authentication response received: {test_response}")

                if not test_response:
                    raise AuthenticationError("Hepsiburada authentication failed: Empty response")

                # Log the structure of the response to help with debugging
                if isinstance(test_response, dict):
                    logger.debug(f"Response keys: {list(test_response.keys())}")
                elif isinstance(test_response, list):
                    logger.debug(f"Response is a list with {len(test_response)} items")

                logger.info("Hepsiburada authentication successful")

            except aiohttp.ClientConnectorError as e:
                error_context = {
                    "client": "Hepsiburada",
                    "operation": "authenticate",
                    "error_type": "ConnectionError",
                }
                error_handler.log_error(e, error_context)
                raise NetworkError(f"Hepsiburada connection error: {str(e)}")

            except aiohttp.ClientResponseError as e:
                error_context = {
                    "client": "Hepsiburada",
                    "operation": "authenticate",
                    "error_type": "ResponseError",
                    "status_code": str(getattr(e, "status", "unknown")),
                }
                error_handler.log_error(e, error_context)

                if getattr(e, "status", 0) == 401 or getattr(e, "status", 0) == 403:
                    raise AuthenticationError(
                        "Hepsiburada authentication failed: Invalid credentials"
                    )
                elif getattr(e, "status", 0) == 429:
                    raise RateLimitError("Hepsiburada rate limit exceeded")
                else:
                    raise APIError(f"Hepsiburada API error: {str(e)}")

            except asyncio.TimeoutError:
                error_context = {
                    "client": "Hepsiburada",
                    "operation": "authenticate",
                    "error_type": "Timeout",
                }
                error_handler.log_error(
                    TimeoutError("Hepsiburada API request timed out"), error_context
                )
                raise NetworkError("Hepsiburada API request timed out")

        except AuthenticationError as e:
            error_context = {
                "client": "Hepsiburada",
                "operation": "authenticate",
                "error_type": "AuthenticationError",
            }
            error_handler.log_error(e, error_context)
            raise

        except NetworkError as e:
            error_context = {
                "client": "Hepsiburada",
                "operation": "authenticate",
                "error_type": "NetworkError",
            }
            error_handler.log_error(e, error_context)
            raise

        except RateLimitError as e:
            error_context = {
                "client": "Hepsiburada",
                "operation": "authenticate",
                "error_type": "RateLimitError",
            }
            error_handler.log_error(e, error_context)
            raise

        except Exception as e:
            error_context = {
                "client": "Hepsiburada",
                "operation": "authenticate",
                "error_type": "UnexpectedError",
            }
            error_handler.log_error(e, error_context)
            raise AuthenticationError(f"Hepsiburada authentication failed: {str(e)}")

    @handle_exceptions
    async def get_products(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Fetch products from Hepsiburada

        Args:
            **kwargs: Optional filters
                - page: Page number (default: 0)
                - size: Page size (default: 100)
                - status: Product status (default: active)
                - barcode: Filter by barcode
                - sku: Filter by SKU
                - category_id: Filter by category ID

        Returns:
            List of products
        """
        try:
            logger.info("Fetching products from Hepsiburada...")

            # Build query parameters
            params = {
                "page": kwargs.get("page", 0),
                "size": kwargs.get("size", 100)
            }

            # Add optional filters if provided
            if "status" in kwargs:
                params["status"] = kwargs["status"]
            if "barcode" in kwargs:
                params["barcode"] = kwargs["barcode"]
            if "sku" in kwargs:
                params["sku"] = kwargs["sku"]
            if "category_id" in kwargs:
                params["categoryId"] = kwargs["category_id"]

            # Make the API request to get products
            # Updated URL format based on the new API structure
            response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/{self.api_version}/products/all-products-of-merchant/{self.merchant_id}",
                params=params,
                headers=self.headers,
            )

            # Check response format
            if not response:
                logger.warning("Hepsiburada returned empty response")
                return []

            # Handle different response formats
            products_data = []
            if "data" in response and isinstance(response["data"], list):
                products_data = response["data"]
            elif isinstance(response, list):
                products_data = response
            else:
                logger.warning(
                    f"Unexpected response format: {response.keys() if isinstance(response, dict) else type(response)}"
                )
                return []

            logger.info(f"Retrieved {len(products_data)} products from Hepsiburada API")

            # Format products
            products = []
            for item in products_data:
                try:
                    product = self._format_product(item)
                    if product:
                        products.append(product)
                except Exception as e:
                    error_context = {
                        "client": "Hepsiburada",
                        "operation": "get_products",
                        "product_id": str(item.get("merchantSku", "unknown")),
                        "error_type": "FormatError",
                    }
                    error_handler.log_error(e, error_context)
                    # Continue with other products

            logger.info(f"Formatted {len(products)} products from Hepsiburada")
            return products

        except Exception as e:
            error_context = {
                "client": "Hepsiburada",
                "operation": "get_products",
                "kwargs": str(kwargs),
            }
            error_handler.log_error(e, error_context)
            raise

    def _format_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format product data from API response"""
        try:
            # Extract SKU
            sku = item.get("merchantSku") or item.get("sku") or item.get("sellerSku")
            if not sku:
                logger.warning(f"Product missing SKU: {item}")
                return None

            # Extract price - Hepsiburada might have empty price strings
            price = 0.0
            if "price" in item and item["price"] and item["price"] != "":
                try:
                    price = float(item["price"])
                except (ValueError, TypeError):
                    price = 0.0

            # Extract quantity - Default to 0
            quantity = 0
            # Quantity is not directly provided in the API response
            # We would need to make another API call to get inventory data
            # For now, we'll set it to 0 and update it later if needed

            # Extract status
            status = "inactive"
            if "status" in item:
                status_value = item["status"]
                if status_value == "MATCHED":
                    status = "active"
                elif status_value == "REJECTED":
                    status = "inactive"
                else:
                    status = status_value.lower()

            # Extract title
            title = (
                item.get("productName") or 
                item.get("title") or 
                item.get("name") or 
                f"Product {sku}"
            )

            # Extract images
            images = []
            if "images" in item and isinstance(item["images"], list):
                images = item["images"]

            # Build product data
            product = {
                "sku": sku,
                "data": {
                    "title": title,
                    "price": price,
                    "quantity": quantity,
                    "status": status,
                    "platform_id": item.get("hbSku", ""),
                    "barcode": item.get("barcode", ""),
                    "category": item.get("categoryName", ""),
                    "brand": item.get("brand", ""),
                    "images": images,
                    "description": item.get("description", ""),
                    "last_updated": datetime.now().isoformat(),
                },
            }

            return product

        except Exception as e:
            logger.error(f"Error formatting product: {str(e)}")
            return None

    @handle_exceptions
    async def update_product(
        self, product_data: Dict[str, Union[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Update product in Hepsiburada

        Args:
            product_data: Product data to update
                - sku: Product SKU (required)
                - data: Product data to update
                    - price: New price
                    - quantity: New quantity
                    - status: New status

        Returns:
            Update result
        """
        try:
            sku = product_data.get("sku")
            if not sku:
                raise ValueError("SKU is required for product update")

            data = cast(Dict[str, Any], product_data.get("data", {}))
            if not data:
                raise ValueError("No data provided for update")

            logger.info(f"Updating product {sku} in Hepsiburada...")

            # Prepare update data
            update_data = {}

            # Handle price update
            if "price" in data:
                update_data["price"] = float(data["price"])

            # Handle quantity update
            if "quantity" in data:
                update_data["quantity"] = int(data["quantity"])

            # Handle status update
            if "status" in data:
                update_data["status"] = data["status"]

            if not update_data:
                logger.warning(f"No valid update data for product {sku}")
                # Return a default response instead of None
                return {"sku": sku, "status": "skipped", "message": "No valid update data"}

            # Make the API request to update the product
            # Updated URL format based on the new API structure
            response = await self._make_request(
                method="PUT",
                url=f"{self.base_url}/{self.api_version}/products/{sku}/update",
                headers=self.headers,
                json=update_data,
            )

            logger.info(f"Product {sku} updated successfully in Hepsiburada")
            return {
                "sku": sku,
                "status": "success",
                "message": "Product updated successfully",
                "response": response,
            }

        except Exception as e:
            error_context = {
                "client": "Hepsiburada",
                "operation": "update_product",
                "sku": product_data.get("sku", "unknown"),
            }
            error_handler.log_error(e, error_context)
            # Return an error response instead of raising
            return {
                "sku": product_data.get("sku", "unknown"),
                "status": "error",
                "message": f"Update failed: {str(e)}",
            }

    @handle_exceptions
    async def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get product by SKU

        Args:
            sku: Product SKU

        Returns:
            Product data or None if not found
        """
        try:
            logger.info(f"Fetching product {sku} from Hepsiburada...")

            # Make the API request to get the product
            # Updated URL format based on the new API structure
            response = await self._make_request(
                method="GET",
                url=f"{self.base_url}/{self.api_version}/products/{sku}",
                headers=self.headers,
            )

            if not response:
                logger.warning(f"Product {sku} not found in Hepsiburada")
                return None

            # Format the product
            product = self._format_product(response)

            if not product:
                logger.warning(f"Failed to format product {sku}")
                return None

            logger.info(f"Retrieved product {sku} from Hepsiburada")
            return product

        except Exception as e:
            error_context = {"client": "Hepsiburada", "operation": "get_product_by_sku", "sku": sku}
            error_handler.log_error(e, error_context)
            # Return None instead of raising an exception for not found
            if isinstance(e, APIError) and "not found" in str(e).lower():
                return None
            return None  # Return None for all errors to match the return type