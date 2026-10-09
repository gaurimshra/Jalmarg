import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Ensure data directory exists
data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
os.makedirs(data_dir, exist_ok=True)
os.makedirs(os.path.join(data_dir, 'uploads'), exist_ok=True)

db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///./") and "sqlite:///./jalmarg.db" in db_url:
    # Rewrite relative to data dir
    db_path = os.path.join(data_dir, 'jalmarg.db')
    db_url = f"sqlite:///{db_path}"

engine = create_engine(
    db_url, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
