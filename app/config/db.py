from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData
# Load environment variables from .env file
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Render PostgreSQL URLs are in format: postgresql://user:pass@host:port/dbname
# Convert to asyncpg format: postgresql+asyncpg://user:pass@host:port/dbname
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif not DATABASE_URL.startswith("postgresql+asyncpg://"):
    # If it's already in the correct format or needs adjustment
    if "postgresql" in DATABASE_URL and "asyncpg" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql", "postgresql+asyncpg", 1)

# Create async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production to reduce logging
    future=True,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,  # Number of connections to maintain in the pool
    max_overflow=10,  # Additional connections beyond pool_size
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for declarative models
Base = declarative_base()

# Metadata for table definitions (if using Core API)
meta = MetaData()

# Dependency to get database session (for FastAPI route dependencies)
async def get_db() -> AsyncSession:
    """
    Dependency function to get database session.
    Use this in FastAPI route dependencies like:
    
    @app.get("/items")
    async def get_items(db: AsyncSession = Depends(get_db)):
        # Use db here
        pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# For backward compatibility (if you have existing code using 'conn')
# Note: This is synchronous, consider migrating to async
async def get_connection():
    """
    Get a database connection (async).
    Use this for raw SQL queries if needed.
    """
    async with engine.begin() as conn:
        return conn
    
#conn = get_connection()