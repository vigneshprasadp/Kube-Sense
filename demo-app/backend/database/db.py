import os
import time
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database configuration loaded from environment variables
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres-service")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "tasksphere")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = None
SessionLocal = None
Base = declarative_base()

# Establish engine connection with retry logic
def init_db():
    global engine, SessionLocal
    print(f"Connecting to database at: postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    for attempt in range(1, 11):
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as connection:
                print("Successfully connected to the database!")
                break
        except Exception as e:
            print(f"Database connection attempt {attempt} failed: {e}")
            if attempt == 10:
                print("Could not connect to the database. Exiting.")
                raise e
            time.sleep(3)
            
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for retrieving database session context
def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database session not initialized. Run init_db() first.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
