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
    
    connected = False
    for attempt in range(1, 4):
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as connection:
                print("Successfully connected to the database!")
                connected = True
                break
        except Exception as e:
            print(f"Database connection attempt {attempt} failed: {e}")
            if attempt < 3:
                time.sleep(1)
                
    if not connected:
        print("Could not connect to PostgreSQL. Falling back to local SQLite database (tasksphere.db)...")
        sqlite_url = "sqlite:///tasksphere.db"
        engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
            
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
