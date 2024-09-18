from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection settings
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# Create the SQLAlchemy engine
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
Base = declarative_base()

@contextmanager
def get_db():
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()

# Common database operations
def create_item(db, model, **kwargs):
    """Generic function to create a new item in the database."""
    db_item = model(**kwargs)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_item(db, model, id):
    """Generic function to get an item from the database by ID."""
    return db.query(model).filter(model.id == id).first()

def update_item(db, model, id, **kwargs):
    """Generic function to update an item in the database."""
    db_item = get_item(db, model, id)
    if db_item:
        for key, value in kwargs.items():
            setattr(db_item, key, value)
        db.commit()
        db.refresh(db_item)
    return db_item

def delete_item(db, model, id):
    """Generic function to delete an item from the database."""
    db_item = get_item(db, model, id)
    if db_item:
        db.delete(db_item)
        db.commit()
    return db_item

# You can add more common database operations here
