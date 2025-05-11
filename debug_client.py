"""
Debug script for testing API clients individually
"""

import os
import asyncio
import json
from dotenv import load_dotenv
import ssl

# Load environment variables
load_dotenv()

# Fix SSL certificate issues on macOS
if os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true':
    # This is insecure and should only be used for development
    ssl._create_default_https_context = ssl._create_unverified_context
    print("WARNING: SSL certificate verification is disabled. This is insecure!")

# Import API clients
from api.n11_client import N11Client
from api.trendyol_client import TrendyolClient
from api.hepsiburada_client import HepsiburadaClient
from api.pazarama_client import PazaramaClient
from api.pttavm_client import PTTAVMClient
from api.wordpress_client import WordPressClient

async def test_n11_client():
    """Test N11 client"""
    print("\n=== Testing N11 Client ===")
    try:
        client = N11Client()
        await client.authenticate()
        print("Authentication successful")
        
        # Get categories
        print("\nFetching categories...")
        categories = await client.get_categories()
        print(f"Retrieved {len(categories)} categories")
        
        # Print first 5 leaf categories
        leaf_categories = [c for c in categories if c['is_leaf']]
        print(f"\nFound {len(leaf_categories)} leaf categories")
        print("First 5 leaf categories:")
        for i, category in enumerate(leaf_categories[:5]):
            print(f"{i+1}. {category['path']} (ID: {category['id']})")
        
        # Get products
        print("\nFetching products...")
        products = await client.get_products(size=5)
        print(f"Retrieved {len(products)} products")
        
        # Print first product
        if products:
            print(f"\nFirst product: {json.dumps(products[0], indent=2)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

async def test_trendyol_client():
    """Test Trendyol client"""
    print("\n=== Testing Trendyol Client ===")
    try:
        client = TrendyolClient()
        await client.authenticate()
        print("Authentication successful")
        
        # Get products
        products = await client.get_products(size=5)
        print(f"Retrieved {len(products)} products")
        
        # Print first product
        if products:
            print(f"First product: {json.dumps(products[0], indent=2)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

async def test_hepsiburada_client():
    """Test Hepsiburada client"""
    print("\n=== Testing Hepsiburada Client ===")
    try:
        client = HepsiburadaClient()
        await client.authenticate()
        print("Authentication successful")
        
        # Get products
        products = await client.get_products(size=5)
        print(f"Retrieved {len(products)} products")
        
        # Print first product
        if products:
            print(f"First product: {json.dumps(products[0], indent=2)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

async def test_pazarama_client():
    """Test Pazarama client"""
    print("\n=== Testing Pazarama Client ===")
    try:
        client = PazaramaClient()
        await client.authenticate()
        print("Authentication successful")
        
        # Get products
        products = await client.get_products(size=5)
        print(f"Retrieved {len(products)} products")
        
        # Print first product
        if products:
            print(f"First product: {json.dumps(products[0], indent=2)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

async def main():
    """Main function"""
    # Choose which client to test
    client_to_test = input("""
Which client would you like to test?
1. N11
2. Trendyol
3. Hepsiburada
4. Pazarama
5. All clients
Enter number: """)
    
    if client_to_test == "1":
        await test_n11_client()
    elif client_to_test == "2":
        await test_trendyol_client()
    elif client_to_test == "3":
        await test_hepsiburada_client()
    elif client_to_test == "4":
        await test_pazarama_client()
    elif client_to_test == "5":
        await test_n11_client()
        await test_trendyol_client()
        await test_hepsiburada_client()
        await test_pazarama_client()
    else:
        print("Invalid selection")

if __name__ == "__main__":
    asyncio.run(main())