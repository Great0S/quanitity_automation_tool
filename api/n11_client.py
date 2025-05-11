from typing import Dict, List, Any, Optional, Union, cast, TypeVar, Callable
import os
import aiohttp
import asyncio
from datetime import datetime
import time
from core.exceptions import APIError, AuthenticationError, RateLimitError, NetworkError
from core.logger import logger
from core.error_handler import handle_exceptions, safe_execute, error_handler
from .base_client import BaseAPIClient

# Type variable for the handle_exceptions decorator
T = TypeVar("T")


class N11Client(BaseAPIClient):
    """
    N11 API Client
    Handles product management and inventory operations
    """

    def __init__(self) -> None:
        """Initialize the N11 client"""
        super().__init__()
        self.logger = logger
        self._setup_credentials()
        # Base URL for N11 API
        self.base_url = "https://api.n11.com"

        # API endpoints
        self.endpoints = {
            "product_query": "/ms/product-query",
            "product_update": "/ms/product-update",
            "categories": "/cdn/categories",
            "orders": "/ms/order-service",
        }

        # Request timeout in seconds
        self.timeout = 30

        # Maximum number of retries
        self.max_retries = 3

        # Delay between retries in seconds
        self.retry_delay = 2

    @error_handler.catch_async
    async def authenticate(self) -> None:
        """Authenticate with N11 API"""
        try:
            self.logger.info("Authenticating with N11 API...")

            # Check if credentials are set
            if not self.app_key:
                raise AuthenticationError("N11 APP_KEY is not set")

            if not self.app_secret:
                raise AuthenticationError("N11 APP_SECRET is not set")

            # Test authentication by getting categories
            try:
                test_response = await self._make_request(
                    method="GET",
                    url=f"{self.base_url}{self.endpoints['categories']}",
                    headers=self.headers,
                )

                # Print response for debugging
                self.logger.debug(f"N11 authentication response type: {type(test_response)}")

                # Categories endpoint returns a list of categories
                if not test_response:
                    self.logger.warning("N11 authentication: Empty response, but continuing anyway")
                    
                # Some N11 responses might not be lists but still be valid
                if not isinstance(test_response, list) and not isinstance(test_response, dict):
                    self.logger.warning(
                        f"N11 authentication: Unexpected response type {type(test_response)}, but continuing anyway"
                    )

                self.logger.info(
                    f"N11 authentication successful, retrieved {len(test_response)} categories"
                )

            except aiohttp.ClientConnectorError as e:
                error_context = {
                    "client": "N11",
                    "operation": "authenticate",
                    "error_type": "ConnectionError",
                }
                error_handler.log_error(e, error_context)
                raise NetworkError(f"N11 connection error: {str(e)}")

            except aiohttp.ClientResponseError as e:
                error_context = {
                    "client": "N11",
                    "operation": "authenticate",
                    "error_type": "ResponseError",
                }
                error_handler.log_error(e, error_context)

                status_code = getattr(e, "status", 0)
                if status_code == 401 or status_code == 403:
                    raise AuthenticationError(
                        f"N11 authentication failed: Invalid credentials (status code: {status_code})"
                    )
                elif status_code == 429:
                    raise RateLimitError(f"N11 rate limit exceeded (status code: {status_code})")
                else:
                    raise APIError(f"N11 HTTP error: {str(e)} (status code: {status_code})")

        except AuthenticationError as e:
            error_context = {
                "client": "N11",
                "operation": "authenticate",
                "error_type": "AuthenticationError",
            }
            error_handler.log_error(e, error_context)
            raise

        except RateLimitError as e:
            error_context = {
                "client": "N11",
                "operation": "authenticate",
                "error_type": "RateLimitError",
            }
            error_handler.log_error(e, error_context)
            raise

        except NetworkError as e:
            error_context = {
                "client": "N11",
                "operation": "authenticate",
                "error_type": "NetworkError",
            }
            error_handler.log_error(e, error_context)
            raise

        except APIError as e:
            error_context = {"client": "N11", "operation": "authenticate", "error_type": "APIError"}
            error_handler.log_error(e, error_context)
            raise

        except Exception as e:
            error_context = {
                "client": "N11",
                "operation": "authenticate",
                "error_type": "UnexpectedError",
            }
            error_handler.log_error(e, error_context)
            raise AuthenticationError(f"N11 authentication failed: {str(e)}")

    def _setup_credentials(self) -> None:
        """Setup API credentials"""
        try:
            self.app_key = os.getenv("N11_APP_KEY")
            self.app_secret = os.getenv("N11_APP_SECRET")

            # Create headers with authentication
            self.headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            }

            if not self.app_key:
                self.logger.error("N11_APP_KEY environment variable is not set")
            if not self.app_secret:
                self.logger.error("N11_APP_SECRET environment variable is not set")

        except Exception as e:
            self.logger.error(f"Error setting up N11 credentials: {str(e)}")
            raise

    async def _make_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        Make a request to the N11 API

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL for the request
            **kwargs: Additional arguments for the request
                - headers: Request headers
                - params: Query parameters
                - json: JSON body
                - data: Form data

        Returns:
            Response data (usually JSON or plain text)

        Raises:
            NetworkError: If there's a connection error
            RateLimitError: If the rate limit is exceeded
            AuthenticationError: If authentication fails
            APIError: For other API errors
        """
        request_context = {"client": "N11", "method": method, "url": url}
        ssl_verify = False
        self.logger.debug(f"N11 API request: {method} {url}")
        if "params" in kwargs:
            self.logger.debug(f"Request params: {kwargs['params']}")
            request_context["params"] = str(kwargs["params"])
        if "json" in kwargs:
            self.logger.debug(f"Request data: {kwargs['json']}")
            request_context["data"] = str(kwargs["json"])

        if "headers" not in kwargs:
            kwargs["headers"] = self.headers

        connector = aiohttp.TCPConnector(ssl=ssl_verify)

        for attempt in range(self.max_retries):
            request_context["attempt"] = str(attempt + 1)
            try:
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.request(
                        method=method,
                        url=url,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        **kwargs,
                    ) as response:
                        self.logger.debug(f"N11 API response status: {response.status}")
                        request_context["status_code"] = str(response.status)

                        if response.status == 429:
                            rate_limit_error = RateLimitError(
                                f"N11 rate limit exceeded (status code: {response.status})"
                            )
                            error_handler.log_error(rate_limit_error, request_context)
                            wait_time = self.retry_delay * (2**attempt)
                            self.logger.warning(f"Rate limit hit, waiting {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue

                        elif response.status in {401, 403}:
                            # Log the response text for debugging
                            response_text = await response.text()
                            self.logger.error(f"N11 authentication response: {response_text}")
                            
                            # Check if the response actually contains an error message
                            if "error" in response_text.lower() or "unauthorized" in response_text.lower():
                                auth_error = AuthenticationError(
                                    f"N11 authentication failed (status code: {response.status}): {response_text}"
                                )
                                error_handler.log_error(auth_error, request_context)
                                raise auth_error
                            else:
                                # If no clear error message, log a warning but continue
                                self.logger.warning(f"N11 returned {response.status} but response doesn't indicate an error: {response_text}")
                                # Try to parse the response anyway
                                try:
                                    return await response.json()
                                except:
                                    return response_text

                        elif response.status >= 400:
                            response_text = await response.text()
                            api_error = APIError(
                                f"N11 API error: {response.status} - {response_text}"
                            )
                            error_handler.log_error(api_error, request_context)
                            if response.status >= 500 and attempt < self.max_retries - 1:
                                wait_time = self.retry_delay * (2**attempt)
                                self.logger.warning(
                                    f"Server error, retrying in {wait_time} seconds..."
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise api_error

                        try:
                            return cast(Union[Dict[Any, Any], str], await response.json())
                        except aiohttp.ContentTypeError:
                            return await response.text()

            except aiohttp.ClientConnectorError as e:
                self.logger.error(f"N11 connection error: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)
                    self.logger.warning(f"Connection error, retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    network_error = NetworkError(
                        f"Connection error after {self.max_retries} attempts: {str(e)}"
                    )
                    error_handler.log_error(network_error, request_context)
                    raise network_error

            except aiohttp.ClientResponseError as e:
                self.logger.error(f"N11 response error: {str(e)}")
                status_code = getattr(e, "status", 0)
                if status_code == 429:
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2**attempt)
                        self.logger.warning(f"Rate limit hit, waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        rate_limit_error = RateLimitError(
                            f"Rate limit exceeded after {self.max_retries} attempts"
                        )
                        error_handler.log_error(rate_limit_error, request_context)
                        raise rate_limit_error
                elif status_code in {401, 403}:
                    auth_error = AuthenticationError(f"Authentication failed: {str(e)}")
                    error_handler.log_error(auth_error, request_context)
                    raise auth_error
                else:
                    api_error = APIError(f"API error: {str(e)}")
                    error_handler.log_error(api_error, request_context)
                    raise api_error

            except asyncio.TimeoutError:
                self.logger.error("N11 request timed out")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)
                    self.logger.warning(f"Timeout, retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    network_error = NetworkError(
                        f"Request timed out after {self.max_retries} attempts"
                    )
                    error_handler.log_error(network_error, request_context)
                    raise network_error

            except Exception as e:
                self.logger.error(f"Unexpected error in N11 request: {str(e)}")
                api_error = APIError(f"Unexpected error: {str(e)}")
                error_handler.log_error(api_error, request_context)
                raise api_error

        # This line is unreachable because all paths in the loop either return a value or raise an exception
        # Removing it to fix the "unreachable code" warning
    
    @handle_exceptions
    async def get_products(self, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Fetch products from N11

        Args:
            **kwargs: Optional filters
                - page: Page number (default: 0)
                - size: Page size (default: 100)
                - status: Product status (default: active)

        Returns:
            List of products
        """
        try:
            self.logger.info("Fetching products from N11...")

            # Build query parameters - Updated to match the example
            params = {
                "page": kwargs.get("page", 0),
                "size": kwargs.get("size", 100),
            }
            
            # Add status if provided
            if "status" in kwargs:
                params["status"] = kwargs["status"]

            # Make the API request - Updated to match the example
            response = await self._make_request(
                method="GET",
                url=f"{self.base_url}{self.endpoints['product_query']}",
                params=params,
            )

            # Log the response for debugging
            self.logger.debug(f"N11 get_products response: {response}")
            
            # Handle different response formats
            if not response:
                self.logger.warning("N11 returned empty response")
                return []
                
            # Extract products from response based on its type
            if isinstance(response, dict):
                if "products" in response:
                    products = response.get("products", [])
                elif "content" in response:
                    # Some N11 responses use "content" instead of "products"
                    products = response.get("content", [])
                else:
                    # If no recognized structure, treat the whole response as a product list
                    self.logger.warning("N11 response has unexpected structure, using raw response")
                    products = [response]
            elif isinstance(response, list):
                # Response is already a list of products
                products = response
            else:
                self.logger.warning("Unexpected response type, expected dict")
                products = []

            # Format products to standard format
            formatted_products: List[Dict[str, Any]] = []
            for product in products:
                try:
                    formatted = self._format_product(product)
                    if formatted:
                        formatted_products.append(formatted)
                except Exception as e:
                    error_context = {
                        "client": "N11",
                        "operation": "get_products",
                        "product_id": product.get("id", "unknown"),
                        "error_type": "FormatError",
                    }
                    error_handler.log_error(e, error_context)
                    # Continue with other products

            return formatted_products

        except Exception as e:
            error_context = {"client": "N11", "operation": "get_products", "kwargs": str(kwargs)}
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to fetch N11 products: {str(e)}")

    def _format_product(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format N11 product data to standard format"""
        try:
            # Extract SKU
            sku = product.get("stockCode", "")
            if not sku:
                self.logger.warning(f"Product missing SKU: {product}")
                return None

            # Extract price
            price = None
            if "price" in product:
                price = float(product["price"])
            elif "prices" in product and product["prices"]:
                if isinstance(product["prices"], dict):
                    price = float(product["prices"].get("sellingPrice", 0))
                elif isinstance(product["prices"], list) and product["prices"]:
                    price = float(product["prices"][0].get("amount", 0))

            # Extract quantity
            quantity = None
            if "quantity" in product:
                quantity = int(product["quantity"])
            elif "stock" in product:
                if isinstance(product["stock"], dict):
                    quantity = int(product["stock"].get("quantity", 0))
                else:
                    quantity = int(product["stock"])

            # Extract status
            status = product.get("approvalStatus", "inactive")

            # Build product data
            formatted_product = {
                "sku": sku,
                "data": {
                    "title": product.get("title", f"Product {sku}"),
                    "price": price if price is not None else 0.0,
                    "quantity": quantity if quantity is not None else 0,
                    "status": status,
                    "platform_id": product.get("id"),
                    "category": product.get("category", {}).get("name"),
                    "last_updated": datetime.now().isoformat(),
                },
            }

            return formatted_product

        except Exception as e:
            self.logger.error(f"Error formatting N11 product: {str(e)}")
            return None

    @handle_exceptions
    async def update_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product in N11

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

            data = product_data.get("data", {})
            if not data:
                raise ValueError("No data provided for update")

            self.logger.info(f"Updating product {sku} in N11...")

            # Prepare update data
            update_data = {"stockCode": sku}

            # Handle price update
            if "price" in data:
                update_data["price"] = float(data["price"])

            # Handle quantity update
            if "quantity" in data:
                update_data["quantity"] = int(data["quantity"])

            # Handle status update
            if "status" in data:
                update_data["approvalStatus"] = data["status"]

            # Make the API request
            response = await self._make_request(
                method="PUT",
                url=f"{self.base_url}{self.endpoints['product_update']}/products/{sku}",
                json=update_data,
            )

            self.logger.info(f"Product {sku} updated successfully in N11")
            return {
                "sku": sku,
                "status": "success",
                "message": "Product updated successfully",
                "response": response,
            }

        except Exception as e:
            error_context = {
                "client": "N11",
                "operation": "update_product",
                "sku": product_data.get("sku", "unknown"),
            }
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to update N11 product: {str(e)}")

    @handle_exceptions
    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get categories from N11

        Returns:
            List of categories
        """
        try:
            self.logger.info("Fetching categories from N11...")

            # Make the API request
            response = await self._make_request(
                method="GET", url=f"{self.base_url}{self.endpoints['categories']}"
            )

            if not response:
                self.logger.warning("N11 returned empty category list")
                return []

            # Format categories
            formatted_categories: List[Dict[str, Any]] = []
            for category in response:
                try:
                    if isinstance(category, dict):
                        formatted = self._format_category(category)
                    else:
                        self.logger.warning(f"Skipping invalid category: {category}")
                        formatted = None
                    if formatted:
                        formatted_categories.append(formatted)
                except Exception as e:
                    self.logger.error(f"Error formatting category: {str(e)}")
                    # Continue with other categories

            return formatted_categories

        except Exception as e:
            error_context = {"client": "N11", "operation": "get_categories"}
            error_handler.log_error(e, error_context)
            raise APIError(f"Failed to fetch N11 categories: {str(e)}")

    def _format_category(self, category: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format N11 category data"""
        try:
            # Extract category ID
            category_id = category.get("id")
            if not category_id:
                self.logger.warning(f"Category missing ID: {category}")
                return None

            # Build category data
            formatted_category: Dict[str, Any] = {
                "id": category_id,
                "name": category.get("name", ""),
                "parent_id": category.get("parentId"),
                "level": category.get("level", 0),
                "has_children": category.get("hasChildren", False),
                "children": [],
            }

            # Add children if available
            if "children" in category and category["children"]:
                for child in category["children"]:
                    child_formatted = self._format_category(child)
                    if child_formatted:
                        formatted_category["children"].append(child_formatted)

            return formatted_category

        except Exception as e:
            self.logger.error(f"Error formatting N11 category: {str(e)}")
            return None