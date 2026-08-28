import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Se nenhum banco estiver configurado, usa um SQLite local (facilita testes/dev)
if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///./aissaas.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
