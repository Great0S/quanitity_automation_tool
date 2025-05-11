"""
Data access package
"""

from data.database import get_db, Database, Transaction
from data.repositories import get_product_repository