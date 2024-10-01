import pytest
from api.base_api import BaseAPI
from api.n11_api import N11API
from unittest.mock import patch, MagicMock

@pytest.fixture
def base_api():
    return BaseAPI(base_url="https://api.example.com", api_key="test_key")

@pytest.fixture
def n11_api():
    return N11API()

def test_base_api_initialization(base_api):
    assert base_api.base_url == "https://api.example.com"
    assert base_api.api_key == "test_key"

@patch('requests.Session.request')
def test_base_api_get_request(mock_request, base_api):
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "value"}
    mock_request.return_value = mock_response

    result = base_api.get("endpoint")
    assert result == {"key": "value"}
    mock_request.assert_called_once_with("GET", "https://api.example.com/endpoint", params=None, json=None)

@patch('api.n11_api.N11API._make_request')
def test_n11_api_get_products(mock_make_request, n11_api):
    mock_make_request.return_value = {"products": [{"id": 1, "name": "Test Product"}]}

    result = n11_api.get_products()
    assert result == {"products": [{"id": 1, "name": "Test Product"}]}
    mock_make_request.assert_called_once_with("GET", "products", params={"rawData": "false", "page": 1, "size": 100})

# Add more tests for other API methods and classes